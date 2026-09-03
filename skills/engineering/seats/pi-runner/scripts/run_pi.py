#!/usr/bin/env python3
"""Execute prompts through the Pi coding agent CLI in headless print mode.

Pi pins provider and model per invocation (`--provider openrouter --model
<vendor/model>` with credentials from the provider's env var or Pi's own auth
store), so the seats served by this wrapper carry no shared mutable provider
state: there is nothing to lane-isolate and no fallback chain to disable.
Named seats (`--seat kimi|glm|qwen|gemma`) rely on the runner identity
split to report e.g. runner=kimi, effective_runner=pi.

Runs are hermetic: extensions, skills, prompt templates, themes, and
AGENTS.md/CLAUDE.md context-file discovery are always disabled, so the prompt
(and --prompt-file material) is the seat's entire input surface.
"""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _skills_root() -> Path:
    """Directory owning shared/scripts/ — the flat installed layout or the nested source checkout."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "shared" / "scripts" / "runner_jobs.py").is_file():
            return parent
    return here.parents[2]


def _skill_dir(name: str) -> Path:
    """Sibling skill directory by name, in either layout."""
    root = _skills_root()
    shared = str(root / "shared" / "scripts")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        from skill_paths import skill_dir
    except ImportError:
        return root / name
    return skill_dir(name, root=root)

_SHARED_SCRIPTS = _skills_root() / "shared" / "scripts"
if str(_SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SHARED_SCRIPTS))

from output_contract import validate_output_contract

DEFAULT_MODEL = None
DEFAULT_PROVIDER = "openrouter"
DEFAULT_RUNNER = "pi"
DEFAULT_OUTPUT_FORMAT = "stream-json"

# Marker Pi prints (exit code 0, no agent events) when the selected provider
# has no credentials in env or its auth store.
AUTH_HINT_MARKER = "Use /login to log into a provider"

# Seat labels served by this wrapper map to their real vendor here,
# used only when the event stream provides no model id to infer a vendor from
# (see infer_provider_from_model).
PROVIDER_BY_RUNNER = {
    "pi": "pi",
    "kimi": "moonshotai",
    "glm": "z-ai",
    "qwen": "qwen",
    "gemma": "google",
}

# Named seats served by this wrapper. `--seat <name>` pins the seat's model on
# OpenRouter and reports `runner=<name>, effective_runner=pi` in the envelope.
# Model ids are mirrored in shared/references/model-roster.md and the
# SEAT_SPECS table in shared/scripts/discover_runners.py — change all three.
PI_SEATS = {
    "kimi": "moonshotai/kimi-k3",
    "glm": "z-ai/glm-5.3-flash",
    "qwen": "qwen/qwen3.8-max",
    "gemma": "google/gemma-4-31b-it",
}


def infer_provider_from_model(model_id: str | None) -> str | None:
    # OpenRouter model ids are `vendor/model` (e.g. z-ai/glm-5.3-flash,
    # moonshotai/kimi-k3) — the prefix is the real vendor. The stream's own
    # `provider` field is the serving gateway (openrouter), not the vendor, so
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
        or infer_provider_from_model(result.get("model"))
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
# - "act": Pi's full built-in toolset (read, bash, edit, write).
# - "restricted": `--tools read` — file reading only. Unlike Cline plan mode
#   there is no search tool and no read-only shell in this mode.
# - "no_tools": native `--no-tools`; the seat answers from the prompt alone.
TOOL_MODE_ACT = "act"
TOOL_MODE_RESTRICTED = "restricted"
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
        return TOOL_MODE_RESTRICTED
    if allow_write:
        return TOOL_MODE_ACT
    if role and role not in WRITE_ROLES:
        return TOOL_MODE_RESTRICTED
    return TOOL_MODE_ACT


def load_runner_jobs():
    shared_dir = _skills_root() / "shared" / "scripts"
    if not (shared_dir / "runner_jobs.py").is_file():
        return None
    sys.path.insert(0, str(shared_dir))
    import runner_jobs

    return runner_jobs


def inspect_native_stream(stdout: str) -> tuple[dict | None, str | None, str | None, str | None, str | None]:
    """Parse Pi's `--mode json` NDJSON event stream.

    Returns (final_message, agent_message, native_model_id, native_provider,
    stop_reason). Pi emits one JSON object per line; streaming deltas arrive
    as `message_update` events and the terminal `message_end` / `agent_end`
    events carry the complete assistant message with the resolved provider,
    model id, usage, and stopReason — the serving receipt.
    """
    final_message = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        if payload.get("type") == "message_end":
            message = payload.get("message")
            if isinstance(message, dict) and message.get("role") == "assistant":
                final_message = message
        elif payload.get("type") == "agent_end":
            messages = payload.get("messages")
            if isinstance(messages, list):
                for message in reversed(messages):
                    if isinstance(message, dict) and message.get("role") == "assistant":
                        final_message = message
                        break

    if final_message is None:
        return None, None, None, None, None

    texts = [
        block.get("text")
        for block in final_message.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ]
    agent_message = "\n".join(texts).strip() or None
    native_model_id = final_message.get("model")
    native_provider = final_message.get("provider")
    stop_reason = final_message.get("stopReason")

    return final_message, agent_message, native_model_id, native_provider, stop_reason


def compact_stream(stdout: str) -> str:
    """Drop per-token `message_update` delta lines from the stored stdout.

    The full delta stream is O(answer tokens) lines of near-duplicate JSON;
    the terminal events already carry the complete message and receipt, so
    only non-delta lines are worth persisting on the envelope.
    """
    kept: list[str] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and '"type":"message_update"' in stripped:
            continue
        kept.append(line)
    return "\n".join(kept)


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
    if tool_mode == TOOL_MODE_RESTRICTED:
        sections.append(
            "Execution constraint:\n"
            "You are running in read-only mode. The file-reading tool is available "
            "— use it to verify claims against the actual code. There is no search "
            "tool, no shell, and no file editing in this mode; do not attempt them."
        )
    elif tool_mode == TOOL_MODE_NO_TOOLS:
        sections.append(
            "Execution constraint:\n"
            "No tools are available in this session, including file reads. Do not "
            "attempt any tool call or retry alternate tools. Answer using only the "
            "material already in this prompt."
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


def run_pi(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Public entry point: every exit path (including early validation errors)
    returns a fully normalized envelope, whether invoked via the CLI or
    imported and called programmatically."""
    requested_model = kwargs.get("model") if "model" in kwargs else (args[3] if len(args) > 3 else None)
    runner_name = kwargs.get("runner_name", DEFAULT_RUNNER)
    result = _run_pi(*args, **kwargs)
    return normalize_envelope(result, requested_runner=runner_name, requested_model=requested_model)


def _run_pi(
    prompt: str,
    timeout: int = 3600,
    working_dir: str | None = None,
    model: str | None = None,
    provider: str | None = DEFAULT_PROVIDER,
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
    system_prompt: str | None = None,
    disable_fallback: bool = False,
    no_session_persistence: bool = False,
    ephemeral: bool = False,
    safe: bool = False,
    bare: bool = False,
    runner_name: str = DEFAULT_RUNNER,
) -> dict[str, Any]:
    del disable_fallback  # Pi pins the provider per call; there is no fallback chain.
    del safe
    del bare

    # Relative input paths resolve against --working-dir (not the process cwd),
    # with ~ expanded — matching the other runners' documented behavior.
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
            "command": "pi",
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
        tool_mode=tool_mode,
    )

    if not final_prompt.strip():
        return error("Provide a prompt argument or at least one --prompt-file", -3)

    command = [
        "pi",
        "--print",
        # Hermetic run: no user extensions, skills, templates, themes, or
        # AGENTS.md/CLAUDE.md discovery — the prompt is the whole input.
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
    ]

    if output_format == "stream-json":
        command.extend(["--mode", "json"])

    if provider:
        command.extend(["--provider", provider])
    if model:
        command.extend(["--model", model])
    if thinking:
        command.extend(["--thinking", "off" if thinking == "none" else thinking])
    if session_id:
        command.extend(["--session", session_id])
    elif no_session_persistence or ephemeral:
        command.append("--no-session")
    if system_prompt:
        command.extend(["--system-prompt", system_prompt])

    if tool_mode == TOOL_MODE_RESTRICTED:
        command.extend(["--tools", "read"])
    elif tool_mode == TOOL_MODE_NO_TOOLS:
        command.append("--no-tools")

    command.append(final_prompt)

    command_display = " ".join(shlex.quote(part) for part in command)

    if shutil.which("pi") is None:
        return {
            **error(
                "Pi CLI not found. Check if `pi` is installed and in PATH "
                "(npm install -g @mariozechner/pi-coding-agent).",
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
        "provider": provider,
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

    if thinking:
        result["thinking"] = thinking

    if len(prompt_files) == 1:
        result["prompt_file"] = prompt_files[0]
    elif prompt_files:
        result["prompt_files"] = prompt_files

    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout if timeout > 0 else None,
            check=False,
            # Pi reads a piped stdin as prompt input and blocks until EOF;
            # close it so headless runs never hang on an inherited pipe.
            stdin=subprocess.DEVNULL,
        )
        result["stdout"] = compact_stream(process.stdout) if output_format == "stream-json" else process.stdout
        result["stderr"] = process.stderr
        # Any nonzero native exit normalizes to -3; the raw code stays in
        # native_return_code so the wrapper's -1/-2/-3 codes are unambiguous.
        result["return_code"] = 0 if process.returncode == 0 else -3
        result["native_return_code"] = process.returncode

        final_message, agent_message, native_model_id, native_provider, stop_reason = (
            inspect_native_stream(process.stdout)
            if output_format == "stream-json"
            else (None, None, None, None, None)
        )

        if stop_reason is not None:
            result["finish_reason"] = stop_reason
        if native_model_id:
            result["native_model_id"] = native_model_id
        if native_provider:
            result["native_provider"] = native_provider
        if isinstance(final_message, dict) and isinstance(final_message.get("usage"), dict):
            result["native_usage"] = final_message["usage"]

        if agent_message:
            result["agent_message"] = agent_message
        elif result["return_code"] == 0 and output_format == "text":
            result["agent_message"] = process.stdout.strip() or None

        # Pi exits 0 with a bare "Use /login ..." hint (and no agent events)
        # when the provider has no credentials — never report that as success.
        combined = f"{process.stdout}\n{process.stderr}"
        if AUTH_HINT_MARKER in combined and result["agent_message"] is None:
            result["success"] = False
            result["return_code"] = -3
            result["auth_ok"] = False
            result["status"] = "auth_missing"
            result["stderr"] = (
                f"No credentials for provider '{provider}'. Set the provider's API key "
                "env var (OPENROUTER_API_KEY for openrouter) or run `pi` interactively "
                "and use /login."
            )
        elif process.returncode == 0 and output_format == "stream-json" and result["agent_message"] is None:
            # A clean exit with no terminal assistant message is a failed run,
            # whatever the exit code claims.
            result["success"] = False
            result["return_code"] = -3
            result["status"] = "empty_response"
        else:
            result["success"] = process.returncode == 0 and (
                output_format != "stream-json" or result["agent_message"] is not None
            )
            if result["success"]:
                result["auth_ok"] = True

        # Pi has no native JSON-schema switch. A schema prompt alone is
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

    except subprocess.TimeoutExpired as exc:
        result["stderr"] = f"Timeout expired after {timeout} seconds"
        result["stdout"] = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "")
        )
        result["return_code"] = -1

    except FileNotFoundError:
        result["stderr"] = "Pi CLI not found. Check if `pi` is installed and in PATH."
        result["return_code"] = -2

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
  %(prog)s "Explain this module" --model moonshotai/kimi-k3
  %(prog)s --prompt-file .ai-workflow/prompts/review.md --role codereviewer
  %(prog)s "Read-only analysis" --restrict-tools --json
        """,
    )

    parser.add_argument("prompt", nargs="?", default="", help="The prompt to execute")
    parser.add_argument(
        "--seat",
        type=str,
        choices=sorted(PI_SEATS),
        default=None,
        help="Run as a named seat: pins that seat's OpenRouter model (unless --model overrides it) "
        "and labels the envelope runner=<seat>, effective_runner=pi. "
        + ", ".join(f"{seat}={model}" for seat, model in PI_SEATS.items()),
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=3600,
        help="Maximum execution time in seconds; 0 disables the wrapper timeout (default: 3600)",
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
        help="Model id in `vendor/model` form as listed by the serving provider's catalog "
        "(e.g. moonshotai/kimi-k3, z-ai/glm-5.3-flash on OpenRouter). Ids absent from Pi's bundled "
        "catalog are passed through to the provider unchanged. Omit to use the runner default.",
    )
    parser.add_argument(
        "--provider",
        "-P",
        type=str,
        default=DEFAULT_PROVIDER,
        help=f"Pi provider id (default: {DEFAULT_PROVIDER}). Credentials come from the "
        "provider's env var (OPENROUTER_API_KEY for openrouter) or Pi's own auth store.",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=["text", "stream-json"],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"Pi output format: plain text or NDJSON event stream via native --mode json (default: {DEFAULT_OUTPUT_FORMAT})",
    )
    parser.add_argument(
        "--thinking",
        type=str,
        choices=["none", "off", "minimal", "low", "medium", "high", "xhigh"],
        default=None,
        help="Reasoning effort passed to native --thinking; `none` is accepted as an alias for `off` (default: provider default)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        dest="session_id",
        help="Resume a specific Pi session by id or path (native --session)",
    )
    parser.add_argument(
        "--system",
        type=str,
        default=None,
        dest="system_prompt",
        help="Override the default Pi system prompt (native --system-prompt)",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Read-only mode (default for analysis roles): only Pi's file-reading tool is "
        "enabled — no search tool, no shell, no file editing",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable all tools (native --no-tools): the seat answers from the prompt alone. "
        "Strongest isolation; overrides --restrict-tools.",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Opt an analysis role out of the read-only default",
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
        help="Do not persist the Pi session (native --no-session)",
    )
    parser.add_argument(
        "--no-session-persistence",
        action="store_true",
        help="Do not persist the Pi session (native --no-session)",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Accepted for runner parity; no effect on Pi CLI",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Accepted for runner parity; no effect on Pi CLI",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Accepted for runner parity; Pi runner never falls back — the provider is pinned per call",
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
        description=description or "Execute prompts using the Pi coding agent CLI in headless print mode.",
    )
    args = parser.parse_args()

    if args.seat:
        # A seat is a pinned model plus a runner label; --model still wins so a
        # caller can test a seat against a newer id without editing the table.
        default_model = PI_SEATS[args.seat]
        runner_name = args.seat
    resolved_model = args.model or default_model

    if args.background:
        jobs = load_runner_jobs()
        if jobs is None:
            parser.error(
                "--background requires the shared jobs module (shared/scripts/runner_jobs.py), which was not found"
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
                },
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_pi(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=resolved_model,
        provider=args.provider,
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
