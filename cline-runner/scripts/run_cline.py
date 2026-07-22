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


DEFAULT_MODEL = None  # None = whatever `cline auth` already configured locally
DEFAULT_RUNNER = "cline"
DEFAULT_OUTPUT_FORMAT = "stream-json"

# Seat labels that delegate to this wrapper (glm-runner, kimi-runner, ...) map
# to their real vendor here, used only when the native stream provides no
# model id to infer a vendor from (see infer_provider_from_model).
PROVIDER_BY_RUNNER = {
    "cline": "cline",
    "glm": "z-ai",
    "kimi": "moonshot",
}


def infer_provider_from_model(model_id: str | None) -> str | None:
    # Cline model ids are `vendor/model` (e.g. zai/glm-5.2, moonshotai/kimi-k3,
    # anthropic/claude-sonnet-4-5) — the prefix is the real vendor. The stream's own
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
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        delete=False,
    )
    temp_name = handle.name
    try:
        with handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, target)
    except BaseException:
        # Never leave an orphaned temp file behind if the write/replace fails.
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


def resolve_restrict_tools(role: str | None, restrict_tools: bool, allow_write: bool) -> bool:
    if restrict_tools:
        return True
    if allow_write:
        return False
    return bool(role) and role not in WRITE_ROLES


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
    restrict_tools: bool,
) -> str:
    sections: list[str] = []

    if role:
        sections.append(f"Role: {role}\n{ROLE_INSTRUCTIONS.get(role, '')}".strip())

    if restrict_tools:
        sections.append(
            "Execution constraint:\n"
            "Stay in read-only analysis mode. Do not edit files, create commits, "
            "or take write actions unless the prompt explicitly overrides this."
        )

    if metadata_json:
        sections.append(f"Execution metadata:\n{metadata_json}")

    if session_file:
        sections.append(
            "Prior conversation context to continue from:\n"
            f"{load_text_file(session_file)}"
        )

    if output_schema:
        sections.append(
            "Return valid JSON matching this schema exactly:\n"
            f"{load_text_file(output_schema)}"
        )

    if prompt_files:
        sections.extend(load_text_file(path) for path in prompt_files)

    if prompt:
        sections.append(prompt)

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
    restrict_tools = resolve_restrict_tools(role, restrict_tools, allow_write)

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
        restrict_tools=restrict_tools,
    )

    if not final_prompt.strip():
        return error("Provide a prompt argument or at least one --prompt-file", -3)

    # `--auto-approve false` is a genuine enforcement boundary for Cline (tool
    # calls fail cleanly with an error instead of hanging on a nonexistent
    # TTY), unlike the prompt-only overlays other runners fall back to.
    auto_approve = not restrict_tools

    command = [
        "cline",
        final_prompt,
        "--cwd",
        cwd,
        "--auto-approve",
        "true" if auto_approve else "false",
    ]

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
        "restrict_tools": restrict_tools,
        "session_id": session_id,
        "agent_message": None,
    }

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
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout if timeout > 0 else None,
        )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        # Any nonzero native exit normalizes to -3; the raw code stays in
        # native_return_code so the wrapper's -1/-2/-3 codes are unambiguous.
        result["return_code"] = 0 if process.returncode == 0 else -3
        result["native_return_code"] = process.returncode

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

    except Exception as exc:
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
  %(prog)s "Explain this module" --model anthropic/claude-sonnet-4-5
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
        help="Cline model id in `provider/model` form (e.g. anthropic/claude-sonnet-4-5, "
        "openai/gpt-5.1, zai/glm-5.2). Omit to use whatever `cline auth` already configured locally.",
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
        help="Force native --auto-approve false (default for analysis roles): tool calls fail cleanly "
        "instead of running, a real enforcement boundary rather than a prompt overlay",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Opt an analysis role out of the default --auto-approve false restriction",
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
        help="Append a JSON Schema file to the prompt as an output contract (prompt-enforced, not natively validated)",
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
) -> None:
    parser = build_parser(
        default_model=default_model,
        description=description or "Execute prompts using Cline CLI in headless mode.",
    )
    args = parser.parse_args()

    if args.background:
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
                manifest_extra={"role": args.role, "model": args.model or default_model},
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_cline(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model or default_model,
        provider=args.provider,
        output_format=args.output_format,
        prompt_files=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        output_schema=args.output_schema,
        restrict_tools=args.restrict_tools,
        allow_write=args.allow_write,
        thinking=args.thinking,
        session_id=args.session_id,
        worktree=args.worktree,
        data_dir=args.data_dir,
        config_dir=args.config_dir,
        system_prompt=args.system_prompt,
        disable_fallback=args.disable_fallback,
        no_session_persistence=args.no_session_persistence,
        ephemeral=args.ephemeral,
        safe=args.safe,
        bare=args.bare,
        runner_name=runner_name,
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
