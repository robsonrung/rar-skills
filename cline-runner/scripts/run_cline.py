#!/usr/bin/env python3
"""Execute prompts through Cline CLI headless mode."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SHARED_SCRIPTS = Path(__file__).resolve().parents[2] / "_shared" / "scripts"
if str(_SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SHARED_SCRIPTS))

from output_contract import validate_output_contract

from cline_lanes import (
    ClineLane,
    LaneCapacityError,
    LaneConfigError,
    acquire_lane_slot,
    apply_lane,
    load_lane,
)

DEFAULT_MODEL = None  # None = whatever `cline auth` already configured locally
DEFAULT_RUNNER = "cline"
DEFAULT_OUTPUT_FORMAT = "stream-json"

# Seat labels that delegate to this wrapper (glm-runner, kimi-runner, ...) map
# to their real vendor here, used only when the native stream provides no
# model id to infer a vendor from (see infer_provider_from_model).
PROVIDER_BY_RUNNER = {
    "cline": "cline",
    "gemma": "google",
    "glm": "zai",
    "kimi": "moonshotai",
    "minimax": "minimax",
    "muse": "meta",
    "qwen": "qwen",
}


def infer_provider_from_model(model_id: str | None) -> str | None:
    # Cline model ids are `vendor/model` (e.g. zai/glm-5.3-flash, moonshotai/kimi-k3,
    # anthropic/claude-sonnet-5) — the prefix is the real vendor. The stream's own
    # `model.provider` field is the *account* (cline, cline-pass), not the vendor, so
    # it is intentionally not used for effective_provider.
    if isinstance(model_id, str) and "/" in model_id:
        vendor = model_id.split("/", 1)[0].strip()
        return vendor or None
    return None


ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "adversarial": "Act as an adversarial reviewer. Pressure-test assumptions, attack weak reasoning, and surface concrete failure modes with evidence.",
    "challenger": "Act as a constructive challenger. Argue against the leading option, name viable alternatives, and force explicit tradeoff handling.",
    "researcher": "Act as a research specialist. Distinguish facts from inference, gather evidence, and cite sources or concrete artifacts when available.",
}

# Roles that modify the workspace; every other role defaults to restricted analysis mode.
WRITE_ROLES = {"implementer"}


def normalize_envelope(
    result: dict[str, Any],
    requested_runner: str,
    requested_model: str | None = None,
) -> dict[str, Any]:
    # `runner` is the requested seat identity (cline, or a delegating seat
    # label like glm/kimi); `effective_runner` is the CLI that actually ran
    # the prompt — always "cline" itself, since this wrapper has no fallback
    # chain. Seat-labelled callers (glm-runner, kimi-runner) rely on this
    # split to report e.g. runner=glm, effective_runner=cline.
    effective_runner = str(result.get("effective_runner") or DEFAULT_RUNNER)
    result["runner"] = requested_runner
    result["effective_runner"] = effective_runner

    if result.get("effective_model") is None:
        result["effective_model"] = result.get("native_model_id") or result.get("model") or requested_model

    result.setdefault("fallback_reason", None)

    # Missing CLI / errors before auth leave auth_ok null (untested), never
    # false — false is reserved for a detected authentication failure.
    if "auth_ok" not in result or result.get("auth_ok") is None:
        result["auth_ok"] = True if result.get("return_code") == 0 else None

    result["effective_provider"] = (
        result.get("effective_provider")
        or infer_provider_from_model(result.get("native_model_id"))
        or PROVIDER_BY_RUNNER.get(requested_runner)
        or result.get("native_provider")
        or effective_runner
    )

    if result.get("return_code") == -2 and not result.get("status"):
        result["status"] = "seat_unavailable"

    return result


def load_text_file(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def write_json_output_file(path: str, payload: dict[str, Any]) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            delete=False,
        ) as handle:
            temp_name = handle.name
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, target)
    except BaseException:
        # Never leave an orphaned temp file behind if the write/replace fails.
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
        raise
    return str(target)


def resolve_input_path(path: str, working_dir: str | None) -> str:
    """Resolve a relative input path against --working-dir, not the process cwd."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and working_dir:
        return str(Path(working_dir).expanduser() / candidate)
    return str(candidate)


def normalize_prompt_files(prompt_files: list[str] | None, working_dir: str | None = None) -> list[str]:
    return [resolve_input_path(path, working_dir) for path in (prompt_files or [])]


# Tool modes, from most to least capable:
# - "act": full toolset, auto-approved (write roles, --allow-write, or no role).
# - "plan": Cline plan mode with tools auto-approved — the read-only analysis
#   boundary. Plan mode's toolset has no file-editing tool and blocks write
#   actions (including shell redirection) at the policy layer, while file
#   reads, search, and read-only commands still run headlessly.
# - "no_tools": --auto-approve false. Every tool call fails at the approval
#   layer, so the seat must answer from the prompt alone.
TOOL_MODE_ACT = "act"
TOOL_MODE_PLAN = "plan"
TOOL_MODE_NO_TOOLS = "no_tools"


def resolve_tool_mode(
    role: str | None,
    restrict_tools: bool,
    no_tools: bool,
    allow_write: bool,
) -> str:
    if no_tools:
        return TOOL_MODE_NO_TOOLS
    if restrict_tools:
        return TOOL_MODE_PLAN
    if allow_write:
        return TOOL_MODE_ACT
    if role and role not in WRITE_ROLES:
        return TOOL_MODE_PLAN
    return TOOL_MODE_ACT


def read_last_used_provider(data_dir: str | None = None, config_dir: str | None = None) -> str | None:
    """Best-effort read of cline's persisted lastUsedProvider, honoring the
    same state-directory overrides the CLI itself uses. Headless runs route
    through this provider unless --provider overrides it."""
    if data_dir:
        base = Path(data_dir).expanduser()
    elif config_dir:
        base = Path(config_dir).expanduser() / "data"
    else:
        base = Path.home() / ".cline" / "data"
    try:
        payload = json.loads((base / "settings" / "providers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    provider = payload.get("lastUsedProvider") if isinstance(payload, dict) else None
    return provider if isinstance(provider, str) and provider else None


def resolve_default_model(
    default_model: str | None,
    default_model_by_provider: dict[str, str] | None,
    provider: str | None,
    data_dir: str | None,
    config_dir: str | None,
) -> str | None:
    """Pick the seat's default model id for the provider that will serve the
    run. Cline providers do not share one model-id namespace (OpenRouter lists
    GLM as z-ai/glm-5.3-flash; the cline gateway uses zai/glm-5.3-flash), so seat shims
    can pass a per-provider map instead of a single id. "*" is the map's
    fallback entry for unrecognized providers."""
    if not default_model_by_provider:
        return default_model
    effective = provider or read_last_used_provider(data_dir, config_dir)
    if effective and effective in default_model_by_provider:
        return default_model_by_provider[effective]
    return default_model_by_provider.get("*", default_model)


def load_runner_jobs():
    shared_dir = Path(__file__).resolve().parents[2] / "_shared" / "scripts"
    if not (shared_dir / "runner_jobs.py").is_file():
        return None
    sys.path.insert(0, str(shared_dir))
    import runner_jobs

    return runner_jobs


def inspect_native_stream(stdout: str) -> tuple[dict | None, str | None, str | None, str | None]:
    """Parse Cline's NDJSON `--json` stream.

    Returns (run_result, agent_message, native_model_id, native_provider).
    Cline emits one JSON object per line (hook_event / agent_event / error /
    run_result); the terminal `run_result` line carries the final answer
    (`text`), `finishReason`, and the resolved `model` block. No session id
    is ever present in the stream — see the Gotchas section in SKILL.md for
    how the wrapper recovers it from `cline history` instead.
    """
    run_result = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict) and payload.get("type") == "run_result":
            run_result = payload

    if run_result is None:
        return None, None, None, None

    agent_message = run_result.get("text") if isinstance(run_result.get("text"), str) else None
    model_block = run_result.get("model") if isinstance(run_result.get("model"), dict) else {}
    native_model_id = model_block.get("id")
    native_provider = model_block.get("provider")

    return run_result, agent_message, native_model_id, native_provider


def lookup_session_id(cline_bin: str, cwd: str, since_iso: str, extra_env: dict[str, str]) -> str | None:
    """Best-effort: Cline's `--json` stream never reports a session id, so the
    wrapper cross-references `cline history --json` by cwd + start time to
    recover the id needed for a later `--id` resume."""
    try:
        proc = subprocess.run(
            [cline_bin, "history", "--json", "--limit", "5"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
            env=extra_env,
            check=False,
        )
        if proc.returncode != 0:
            return None
        entries = json.loads(proc.stdout)
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("cwd") != cwd:
                continue
            started_at = entry.get("startedAt")
            if isinstance(started_at, str) and started_at >= since_iso:
                session_id = entry.get("sessionId")
                if isinstance(session_id, str):
                    return session_id
        return None
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError, ValueError):
        return None


def build_prompt(
    prompt: str,
    prompt_files: list[str],
    role: str | None,
    session_file: str | None,
    metadata_json: str | None,
    output_schema: str | None,
    tool_mode: str,
) -> str:
    sections: list[str] = []

    if role:
        sections.append(f"Role: {role}\n{ROLE_INSTRUCTIONS.get(role, '')}".strip())

    # The constraint text must match what the mode actually enforces: a seat
    # told "read-only" while reads are blocked burns its retry budget hunting
    # for a working read path and aborts.
    if tool_mode == TOOL_MODE_PLAN:
        sections.append(
            "Execution constraint:\n"
            "You are running in plan mode. Read-only tools (file reading, search, "
            "read-only commands) are available and pre-approved — use them to verify "
            "claims against the actual code. File edits and other write actions are "
            "not available in this mode; do not attempt them."
        )
    elif tool_mode == TOOL_MODE_NO_TOOLS:
        sections.append(
            "Execution constraint:\n"
            "No tools are approved in this session: every tool call fails with an "
            "approval error, including file reads. Do not attempt any tool call or "
            "retry alternate tools. Answer using only the material already in this "
            "prompt."
        )

    if metadata_json:
        sections.append(f"Execution metadata:\n{metadata_json}")

    if session_file:
        sections.append(
            "Prior conversation context to continue from:\n"
            f"{load_text_file(session_file)}"
        )

    if prompt_files:
        sections.extend(load_text_file(path) for path in prompt_files)

    if prompt:
        sections.append(prompt)

    # Keep the contract last so task material cannot accidentally supersede
    # the required final-answer shape.
    if output_schema:
        sections.append(
            "Output contract: return exactly one JSON value matching this schema. "
            "Do not use Markdown fences, prose, progress updates, or append a second JSON value.\n"
            f"{load_text_file(output_schema)}"
        )

    return "\n\n".join(section for section in sections if section.strip())


def run_cline(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Public entry point: every exit path (including early validation errors)
    returns a fully normalized envelope, whether invoked via the CLI or
    imported and called programmatically."""
    requested_model = kwargs.get("model") if "model" in kwargs else (args[3] if len(args) > 3 else None)
    runner_name = kwargs.get("runner_name", DEFAULT_RUNNER)
    result = _run_cline(*args, **kwargs)
    return normalize_envelope(result, requested_runner=runner_name, requested_model=requested_model)


def _run_cline(
    prompt: str,
    timeout: int = 3600,
    working_dir: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    prompt_files: list[str] | None = None,
    role: str | None = None,
    session_file: str | None = None,
    metadata_json: str | None = None,
    output_schema: str | None = None,
    restrict_tools: bool = False,
    no_tools: bool = False,
    allow_write: bool = False,
    thinking: str | None = None,
    session_id: str | None = None,
    worktree: bool = False,
    data_dir: str | None = None,
    config_dir: str | None = None,
    system_prompt: str | None = None,
    disable_fallback: bool = False,
    no_session_persistence: bool = False,
    ephemeral: bool = False,
    safe: bool = False,
    bare: bool = False,
    runner_name: str = DEFAULT_RUNNER,
    lane: ClineLane | None = None,
    lane_error: str | None = None,
    lane_wait_timeout: float = 30,
) -> dict[str, Any]:
    del disable_fallback
    del no_session_persistence
    del ephemeral
    del safe
    del bare

    # Relative input paths resolve against --working-dir (not the process cwd),
    # with ~ expanded — matching gemini-runner's documented behavior.
    prompt_files = normalize_prompt_files(prompt_files, working_dir)
    session_file = resolve_input_path(session_file, working_dir) if session_file else session_file
    output_schema = resolve_input_path(output_schema, working_dir) if output_schema else output_schema
    cwd = working_dir or os.getcwd()
    tool_mode = resolve_tool_mode(role, restrict_tools, no_tools, allow_write)

    def error(stderr: str, return_code: int) -> dict[str, Any]:
        return {
            "success": False,
            "stdout": "",
            "stderr": stderr,
            "return_code": return_code,
            "command": "cline",
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": DEFAULT_RUNNER,
        }

    if lane_error:
        lane_result = error(lane_error, -3)
        lane_result["status"] = "lane_unavailable"
        return lane_result

    if working_dir and not Path(working_dir).is_dir():
        return error(f"Working directory does not exist: {working_dir}", -3)

    for prompt_file in prompt_files:
        if not Path(prompt_file).is_file():
            return error(f"Prompt file does not exist: {prompt_file}", -3)

    if session_file and not Path(session_file).is_file():
        return error(f"Session file does not exist: {session_file}", -3)

    if output_schema and not Path(output_schema).is_file():
        return error(f"Output schema file does not exist: {output_schema}", -3)

    final_prompt = build_prompt(
        prompt=prompt,
        prompt_files=prompt_files,
        role=role,
        session_file=session_file,
        metadata_json=metadata_json,
        output_schema=output_schema,
        tool_mode=tool_mode,
    )

    if not final_prompt.strip():
        return error("Provide a prompt argument or at least one --prompt-file", -3)

    # Both restricted modes are genuine enforcement boundaries, not prompt
    # overlays: plan mode ships a toolset with no file-editing tool and blocks
    # write actions at the policy layer (reads stay auto-approved so headless
    # analysis can verify code), while `--auto-approve false` makes every tool
    # call fail cleanly instead of hanging on a nonexistent TTY.
    auto_approve = tool_mode != TOOL_MODE_NO_TOOLS

    command = [
        "cline",
        final_prompt,
        "--cwd",
        cwd,
        "--auto-approve",
        "true" if auto_approve else "false",
    ]

    if tool_mode == TOOL_MODE_PLAN:
        command.append("--plan")

    if output_format == "stream-json":
        command.append("--json")

    if model:
        command.extend(["--model", model])
    if provider:
        command.extend(["--provider", provider])
    if thinking:
        command.extend(["--thinking", thinking])
    if session_id:
        command.extend(["--id", session_id])
    if worktree:
        command.append("--worktree")
    if data_dir:
        command.extend(["--data-dir", data_dir])
    if config_dir:
        command.extend(["--config", config_dir])
    if system_prompt:
        command.extend(["--system", system_prompt])

    # Ask the native CLI to self-terminate slightly before the wrapper's hard
    # subprocess timeout, so a natural timeout still reports a clean
    # finishReason instead of a bare SIGTERM.
    if timeout > 0:
        native_timeout = max(1, timeout - 5)
        command.extend(["--timeout", str(native_timeout)])

    command_display = " ".join(shlex.quote(part) for part in command)

    if shutil.which("cline") is None:
        return {
            **error(
                "Cline CLI not found. Check if `cline` is installed and in PATH (npm install -g cline).",
                -2,
            ),
            "command": command_display,
        }

    result: dict[str, Any] = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_code": 0,
        "command": command_display,
        "working_dir": cwd,
        "model": model,
        "output_format": output_format,
        "runner": runner_name,
        "effective_runner": DEFAULT_RUNNER,
        "role": role,
        "session_file": session_file,
        "restrict_tools": tool_mode != TOOL_MODE_ACT,
        "tool_mode": tool_mode,
        "session_id": session_id,
        "agent_message": None,
    }

    if lane:
        result.update(
            {
                "lane": lane.name,
                "credential_pool": lane.credential_pool,
                "lane_max_concurrency": lane.max_concurrency,
                "state_isolated": True,
            }
        )

    if thinking:
        result["thinking"] = thinking

    # Forwarding --model without an isolating --data-dir rewrites the user's
    # persisted provider default in ~/.cline/data/settings/providers.json as a
    # side effect; surface that on the envelope so orchestrators can see it.
    if model and not data_dir:
        result["provider_config_mutated"] = True

    if len(prompt_files) == 1:
        result["prompt_file"] = prompt_files[0]
    elif prompt_files:
        result["prompt_files"] = prompt_files

    run_started_at = datetime.now(timezone.utc).isoformat()

    try:
        if lane:
            with acquire_lane_slot(lane, lane_wait_timeout) as slot:
                result["lane_slot"] = slot
                process = subprocess.run(
                    command,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=timeout if timeout > 0 else None,
                    check=False,
                )
        else:
            process = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout if timeout > 0 else None,
                check=False,
            )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        # Any nonzero native exit normalizes to -3; the raw code stays in
        # native_return_code so the wrapper's -1/-2/-3 codes are unambiguous.
        result["return_code"] = 0 if process.returncode == 0 else -3
        result["native_return_code"] = process.returncode
        # A native process that exited cleanly exercised authentication even
        # if its final answer subsequently fails our output contract.
        if process.returncode == 0:
            result["auth_ok"] = True

        run_result, agent_message, native_model_id, native_provider = inspect_native_stream(process.stdout)
        if run_result is not None:
            result["native_result"] = run_result
            finish_reason = run_result.get("finishReason")
            result["finish_reason"] = finish_reason
            # Trust the process exit code first; fall back to finishReason so
            # a stream that reports an error is never reported as success
            # even on the rare exit-code/finishReason mismatch.
            if process.returncode == 0 and finish_reason not in ("completed", None):
                result["success"] = False
                result["return_code"] = -3
            else:
                result["success"] = process.returncode == 0
        else:
            result["success"] = process.returncode == 0

        if agent_message:
            result["agent_message"] = agent_message
        elif result["success"] and output_format == "text":
            result["agent_message"] = process.stdout.strip() or None

        # Cline has no native JSON-schema switch. A schema prompt alone is
        # advisory, so turn it into a hard postcondition before a council can
        # count this response as a vote. This also rejects concatenated JSON
        # and prose wrapped around an otherwise valid object.
        if result["success"] and output_schema:
            contract = validate_output_contract(result["agent_message"], output_schema)
            result["output_json_valid"] = contract.error_kind not in {
                "missing_output",
                "invalid_json",
            }
            result["schema_valid"] = contract.valid
            if contract.valid:
                result["structured_output"] = contract.value
                result["agent_message"] = json.dumps(contract.value, ensure_ascii=False)
            else:
                result["success"] = False
                result["return_code"] = -3
                result["status"] = "malformed_output"
                result["output_contract_error"] = contract.error

        if native_model_id:
            result["native_model_id"] = native_model_id
        if native_provider:
            result["native_provider"] = native_provider

        if not session_id:
            found_session_id = lookup_session_id(
                "cline",
                cwd,
                run_started_at,
                extra_env=os.environ.copy(),
            )
            if found_session_id:
                result["session_id"] = found_session_id

    except LaneCapacityError as exc:
        result["stderr"] = str(exc)
        result["return_code"] = -3
        result["status"] = "lane_unavailable"

    except subprocess.TimeoutExpired as exc:
        result["stderr"] = f"Timeout expired after {timeout} seconds"
        result["stdout"] = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "")
        )
        result["return_code"] = -1

    except FileNotFoundError:
        result["stderr"] = "Cline CLI not found. Check if `cline` is installed and in PATH."
        result["return_code"] = -2
        # cline never ran, so the user's provider config was not touched.
        result.pop("provider_config_mutated", None)

    except Exception as exc:  # noqa: BLE001
        result["stderr"] = f"Unexpected error: {exc}"
        result["return_code"] = -3

    return result


def build_parser(default_model: str | None, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is 2+2?"
  %(prog)s "Explain this module" --model anthropic/claude-sonnet-5
  %(prog)s --prompt-file /tmp/review.md --role codereviewer
  %(prog)s "Implement the fix" --role implementer --model openai/gpt-5.1
  %(prog)s "Resume and continue" --session 1782865158637_s2n62
        """,
    )

    parser.add_argument("prompt", nargs="?", default="", help="The prompt to execute")
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=3600,
        help="Maximum execution time in seconds; 0 disables both the native and wrapper timeout (default: 3600)",
    )
    parser.add_argument(
        "--working-dir",
        "-w",
        type=str,
        default=None,
        help="Working directory for execution",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output wrapper results in JSON format",
    )
    parser.add_argument(
        "--prompt-file",
        action="append",
        default=[],
        help="Read prompt content from a file. Repeat the flag to concatenate multiple files.",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Cline model id in `provider/model` form (e.g. anthropic/claude-sonnet-5, "
        "openai/gpt-5.1). Ids are catalog-specific per provider — OpenRouter lists GLM as "
        "z-ai/glm-5.3-flash while the cline gateway uses zai/glm-5.3-flash. Omit to use the runner default.",
    )
    parser.add_argument(
        "--provider",
        "-P",
        type=str,
        default=None,
        help="Cline provider id (e.g. cline, cline-pass, anthropic, openrouter). Default: cline's own configured default.",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=["text", "stream-json"],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"Cline output format: styled text or NDJSON event stream via native --json (default: {DEFAULT_OUTPUT_FORMAT})",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        choices=["none", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort passed to native --thinking (default: provider default)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        dest="session_id",
        help="Resume a specific Cline session by id (native --id)",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        help="Auto-create a detached git worktree under ~/.cline/worktrees/ and run the task there (native --worktree)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Isolated local state directory (native --data-dir). Recommended for automated/CI runs so the "
        "wrapper never mutates the interactive user's ~/.cline config (see Gotchas).",
    )
    parser.add_argument(
        "--lane",
        type=str,
        default=None,
        help="Named isolated Cline lane. "
        "Built-in kimi/glm lanes need no configuration; a lane fixes provider, model, and data-dir for a safe concurrent run.",
    )
    parser.add_argument(
        "--lane-file",
        type=str,
        default=None,
        help="Optional local JSON lane configuration for custom lanes; built-in kimi/glm lanes need no file.",
    )
    parser.add_argument(
        "--lane-wait-timeout",
        type=float,
        default=30,
        help="Seconds to wait for a credential-pool slot when using --lane (default: 30).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        dest="config_dir",
        help="Configuration directory (native --config)",
    )
    parser.add_argument(
        "--system",
        type=str,
        default=None,
        dest="system_prompt",
        help="Override the default Cline system prompt (native --system)",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Run in Cline plan mode (default for analysis roles): file reads, search, and "
        "read-only commands run headlessly, while file edits and write actions are unavailable "
        "— a real enforcement boundary rather than a prompt overlay",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Force native --auto-approve false: every tool call fails at the approval layer, "
        "so the seat answers from the prompt alone. Strongest isolation; overrides --restrict-tools.",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Opt an analysis role out of the read-only plan-mode default",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run as a tracked background job and return a job id immediately",
    )
    parser.add_argument(
        "--role",
        type=str,
        choices=sorted(ROLE_INSTRUCTIONS),
        default=None,
        help="Apply a role overlay before running the prompt",
    )
    parser.add_argument(
        "--session-file",
        type=str,
        default=None,
        help="Append prior workflow context from a file",
    )
    parser.add_argument(
        "--metadata-json",
        type=str,
        default=None,
        help="JSON string to embed as execution metadata",
    )
    parser.add_argument(
        "--output-schema",
        type=str,
        default=None,
        help="Append a JSON Schema output contract and locally reject a final answer that is not exactly one schema-valid JSON value",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Accepted for runner parity; no effect on Cline CLI (use --data-dir for real isolation)",
    )
    parser.add_argument(
        "--no-session-persistence",
        action="store_true",
        help="Accepted for runner parity; no effect on Cline CLI (Cline always records session history)",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Accepted for runner parity; no effect on Cline CLI",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Accepted for runner parity; no effect on Cline CLI",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Accepted for runner parity; Cline runner never falls back to another provider",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write the wrapper JSON result to this file atomically",
    )

    return parser


def main(
    default_model: str | None = DEFAULT_MODEL,
    runner_name: str = DEFAULT_RUNNER,
    description: str | None = None,
    default_model_by_provider: dict[str, str] | None = None,
) -> None:
    parser = build_parser(
        default_model=default_model,
        description=description or "Execute prompts using Cline CLI in headless mode.",
    )
    args = parser.parse_args()

    lane = None
    lane_error = None
    resolved_provider = args.provider
    resolved_data_dir = args.data_dir
    if args.lane:
        try:
            lane = load_lane(args.lane, args.lane_file)
            # Built-in lanes infer their provider from their isolated Cline
            # state. Resolve a provider-specific default (notably GLM's
            # catalog slug) before the lane checks that final model.
            candidate_model = args.model or resolve_default_model(
                default_model,
                default_model_by_provider,
                provider=lane.provider,
                data_dir=lane.data_dir,
                config_dir=args.config_dir,
            )
            resolved_provider, resolved_model, resolved_data_dir = apply_lane(
                lane, args.provider, candidate_model, args.data_dir
            )
        except LaneConfigError as exc:
            lane_error = str(exc)
            resolved_model = args.model or default_model
    else:
        resolved_model = args.model or resolve_default_model(
            default_model,
            default_model_by_provider,
            provider=args.provider,
            data_dir=args.data_dir,
            config_dir=args.config_dir,
        )

    if args.background:
        if lane_error:
            parser.error(f"--lane: {lane_error}")
        jobs = load_runner_jobs()
        if jobs is None:
            parser.error(
                "--background requires the shared jobs module (_shared/scripts/runner_jobs.py), which was not found"
            )
        prompt_source = args.prompt or (
            f"prompt files: {', '.join(args.prompt_file)}" if args.prompt_file else ""
        )
        try:
            summary = jobs.launch_background(
                runner_name,
                Path(sys.argv[0]),
                sys.argv[1:],
                working_dir=args.working_dir,
                prompt_excerpt=prompt_source,
                manifest_extra={
                    "role": args.role,
                    "model": resolved_model,
                    "lane": lane.name if lane else None,
                    "credential_pool": lane.credential_pool if lane else None,
                },
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_cline(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=resolved_model,
        provider=resolved_provider,
        output_format=args.output_format,
        prompt_files=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        output_schema=args.output_schema,
        restrict_tools=args.restrict_tools,
        no_tools=args.no_tools,
        allow_write=args.allow_write,
        thinking=args.thinking,
        session_id=args.session_id,
        worktree=args.worktree,
        data_dir=resolved_data_dir,
        config_dir=args.config_dir,
        system_prompt=args.system_prompt,
        disable_fallback=args.disable_fallback,
        no_session_persistence=args.no_session_persistence,
        ephemeral=args.ephemeral,
        safe=args.safe,
        bare=args.bare,
        runner_name=runner_name,
        lane=lane,
        lane_error=lane_error,
        lane_wait_timeout=args.lane_wait_timeout,
    )

    output_file = None
    if args.output_file:
        output_file = write_json_output_file(args.output_file, result)

    if args.json:
        if output_file:
            print(
                json.dumps(
                    {
                        "success": result["success"],
                        "return_code": result["return_code"],
                        "output_file": output_file,
                        "runner": result.get("runner"),
                        "effective_runner": result.get("effective_runner"),
                        "effective_provider": result.get("effective_provider"),
                        "fallback_from": result.get("fallback_from"),
                        "status": result.get("status"),
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["stdout"]:
            print(result["stdout"], end="")
        if result["stderr"]:
            print(result["stderr"], file=sys.stderr)
        if output_file:
            print(f"Result written to {output_file}")

    sys.exit(result["return_code"] if result["return_code"] >= 0 else 1)


if __name__ == "__main__":
    main()
