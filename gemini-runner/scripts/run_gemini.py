#!/usr/bin/env python3
"""
Gemini Runner - A wrapper for Antigravity CLI (`agy`) headless execution.

Executes prompts using Antigravity CLI print mode. Permission bypass is opt in.
The file name and public function names stay stable for existing Gemini-seat
workflows.
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
from typing import Any, Optional

# The agy binary can be overridden for non-standard installs / tests.
AGY_CLI = os.environ.get("AGY_CLI_PATH", "agy")
# Premium Gemini seat: Gemini 3.1 Pro (product discovery / product thinking).
# For broad independent perspective and cross-file consistency, callers pass
# `--model gemini-3.5-flash`. NOTE: agy uses whichever model its own
# settings/model picker is configured with — `--model` here is a metadata label
# reflected in `effective_model`, not forwarded to the CLI. Configure agy's
# model picker to match the intended premium seat.
DEFAULT_MODEL = "gemini-3.1-pro"

# Keys every emitted envelope must carry (the shared runner-envelope contract).
REQUIRED_ENVELOPE_KEYS = (
    "runner",
    "effective_runner",
    "effective_model",
    "effective_provider",
    "auth_ok",
    "fallback_reason",
    "success",
    "return_code",
)

# Substrings that indicate agy could not authenticate. Matched against stderr
# (and, only on a non-zero exit, stdout) so a successful answer that merely
# *mentions* authentication does not get misclassified as an auth failure.
AUTH_FAILURE_MARKERS = (
    "authentication required",
    "waiting for authentication",
    "not authenticated",
    "authentication failed",
    "please authenticate",
    "login required",
    "unauthorized",
)

ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "adversarial": "Act as an adversarial reviewer. Pressure-test assumptions, attack weak reasoning, and surface concrete failure modes with evidence.",
    "challenger": "Act as a constructive challenger. Argue against the leading option, name viable alternatives, and force explicit tradeoff handling.",
    "researcher": "Act as a research specialist. Distinguish facts from inference, gather evidence, and cite sources or concrete artifacts when available.",
}

# Roles that modify the workspace; every other role defaults to a read-only prompt overlay.
WRITE_ROLES = {"implementer"}


PROVIDER_BY_RUNNER = {
    "claude": "anthropic",
    "codex": "openai",
    "gemini": "google",
    "agy": "google",
    "qwen": "qwen",
    "gemma": "google",
    "glm": "z-ai",
    "glm-critical": "z-ai",
    "kimi": "moonshot",
    "minimax": "minimax",
}


def normalize_envelope(
    result: dict[str, Any],
    requested_runner: str,
    requested_model: str | None = None,
) -> dict[str, Any]:
    """Fill in the shared-envelope keys on *result*. Idempotent."""
    result.setdefault("return_code", None)
    result.setdefault("success", result.get("return_code") == 0)

    effective_runner = str(result.get("effective_runner") or result.get("runner") or requested_runner)
    result["runner"] = requested_runner
    result["effective_runner"] = effective_runner

    if result.get("effective_model") is None:
        result["effective_model"] = result.get("model") or requested_model

    result.setdefault("fallback_reason", None)

    # Derive auth_ok only when an explicit value was not already set (e.g. by the
    # auth-failure heuristic or a fallback runner). A successful exit means auth
    # worked; everything else — including a missing CLI (-2) — is "untested"
    # (None), because no authentication exchange is known to have failed.
    if "auth_ok" not in result or result.get("auth_ok") is None:
        result["auth_ok"] = True if result.get("return_code") == 0 else None

    # effective_provider is required and must not be null: fall back from the
    # effective runner to the requested runner's provider before giving up.
    result["effective_provider"] = (
        result.get("effective_provider")
        or PROVIDER_BY_RUNNER.get(effective_runner)
        or PROVIDER_BY_RUNNER.get(requested_runner)
        or effective_runner
    )

    if result.get("return_code") == -2 and not result.get("status"):
        result["status"] = "seat_unavailable"

    return result


def validate_envelope(envelope: dict[str, Any]) -> list[str]:
    """Return the list of required envelope keys missing from *envelope* (empty == valid)."""
    return [key for key in REQUIRED_ENVELOPE_KEYS if key not in envelope]


def load_text_file(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def resolve_input_path(path: str, working_dir: Optional[str]) -> str:
    """Resolve a relative prompt/session path against --working-dir, not the process cwd."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and working_dir:
        return str(Path(working_dir).expanduser() / candidate)
    return str(candidate)


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


def resolve_restrict_tools(role: Optional[str], restrict_tools: bool, allow_write: bool) -> bool:
    """Decide whether to apply the read-only overlay.

    Precedence (highest first): an explicit ``--restrict-tools`` always wins, then
    ``--allow-write`` opts out, otherwise analysis roles (every role except the
    write roles) default to read-only and a bare prompt with no role does not.
    """
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


def compute_timeouts(timeout: int) -> tuple[int, int]:
    """Return (agy_print_timeout, subprocess_timeout) seconds.

    The agy print-timeout is set a little *below* the subprocess timeout so agy
    terminates its own print cleanly (flushing partial output and returning its
    own exit code) before the wrapper's hard ``subprocess`` timeout would SIGKILL
    it. The subprocess timeout stays equal to the caller's budget so the overall
    cap is honored.
    """
    total = max(1, int(timeout))
    buffer = max(1, min(10, total // 10))
    agy_print = max(1, total - buffer)
    return agy_print, total


def format_print_timeout(timeout: int) -> str:
    """Backward-compatible helper: agy --print-timeout string for *timeout* seconds."""
    agy_print, _ = compute_timeouts(timeout)
    return f"{agy_print}s"


def strip_json_fences(text: str) -> tuple[str, bool]:
    """Best-effort: strip ```json fences and report whether the result parses as JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    try:
        json.loads(cleaned)
        return cleaned, True
    except (json.JSONDecodeError, ValueError):
        return cleaned, False


def output_format_instruction(output_format: str) -> str:
    if output_format == "json":
        return (
            "Response format request: return valid JSON only. Do not wrap the "
            "JSON in Markdown fences or explanatory prose."
        )
    if output_format == "stream-json":
        return (
            "Response format request: Antigravity CLI print mode is captured as "
            "final stdout by this wrapper. Return newline-delimited JSON objects "
            "if an event-style response is needed."
        )
    return ""


def build_prompt(
    prompt: str,
    prompt_files: Optional[list[str]],
    role: Optional[str],
    session_file: Optional[str],
    metadata_json: Optional[str],
    restrict_tools: bool = False,
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
    if prompt_files:
        sections.extend(load_text_file(path) for path in prompt_files)
    else:
        sections.append(prompt)
    return "\n\n".join(section for section in sections if section.strip())


_FLAG_SUPPORT_CACHE: dict[tuple[str, str], bool] = {}


def runner_supports_flag(runner_script: Path, flag: str) -> bool:
    """Whether a sibling runner advertises *flag* in its --help (cached).

    Used so fallback only forwards optional flags a given sibling actually
    accepts (e.g. codex-runner has no --output-format), instead of hardcoding
    sibling internals or risking an "unrecognized arguments" failure.
    """
    key = (str(runner_script), flag)
    if key in _FLAG_SUPPORT_CACHE:
        return _FLAG_SUPPORT_CACHE[key]
    supported = False
    try:
        completed = subprocess.run(
            [sys.executable, str(runner_script), "--help"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        supported = flag in (completed.stdout + completed.stderr)
    except Exception:
        supported = False
    _FLAG_SUPPORT_CACHE[key] = supported
    return supported


def invoke_fallback(
    runner_script: Path,
    prompt: str,
    timeout: int,
    working_dir: Optional[str],
    prompt_files: Optional[list[str]],
    role: Optional[str],
    session_file: Optional[str],
    metadata_json: Optional[str],
    restrict_tools: bool = False,
    allow_write: bool = False,
    output_format: str = "text",
) -> dict[str, Any]:
    command = [sys.executable, str(runner_script), "--json"]
    command.append("--disable-fallback")

    if prompt_files:
        for prompt_file in prompt_files:
            command.extend(["--prompt-file", prompt_file])
    else:
        command.append(prompt)

    command.extend(["--timeout", str(timeout)])

    if working_dir:
        command.extend(["--working-dir", working_dir])
    if role:
        command.extend(["--role", role])
    if session_file:
        command.extend(["--session-file", session_file])
    if metadata_json:
        command.extend(["--metadata-json", metadata_json])
    # Forward the resolved read-only/allow-write intent so a sibling does not
    # re-derive a different default for an analysis role.
    if restrict_tools:
        command.append("--restrict-tools")
    elif allow_write:
        command.append("--allow-write")
    # Forward a non-default output format only to siblings that accept it.
    if output_format and output_format != "text" and runner_supports_flag(runner_script, "--output-format"):
        command.extend(["--output-format", output_format])

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "stdout": (
                exc.stdout
                if isinstance(exc.stdout, str)
                else (exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "")
            ),
            "stderr": f"Fallback runner timed out after {timeout} seconds",
            "return_code": -1,
            "command": " ".join(shlex.quote(part) for part in command),
        }
    except Exception as exc:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Fallback runner failed: {exc}",
            "return_code": -3,
            "command": " ".join(shlex.quote(part) for part in command),
        }

    stdout = completed.stdout.strip()
    try:
        fallback_result = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        fallback_result = {
            "success": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "return_code": completed.returncode,
            "command": " ".join(shlex.quote(part) for part in command),
        }

    if completed.stderr and not fallback_result.get("stderr"):
        fallback_result["stderr"] = completed.stderr

    return fallback_result


def _annotate_fallback(
    fallback_result: dict[str, Any],
    requested_model: Optional[str],
    model: str,
    agy_continue: bool,
    attempted_fallbacks: list[dict[str, Any]],
) -> dict[str, Any]:
    fallback_result["fallback_from"] = "gemini"
    fallback_result["fallback_reason"] = "Antigravity CLI (agy) not found"
    fallback_result["requested_model"] = requested_model or model
    fallback_result["fallback_model_forwarded"] = False
    fallback_result["agy_continue_requested"] = agy_continue
    if agy_continue:
        fallback_result["fallback_ignored_options"] = ["--agy-continue"]
    if attempted_fallbacks:
        fallback_result["fallback_attempts"] = attempted_fallbacks
    return fallback_result


def _fallback_attempt_record(script: Path, fallback_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "script": str(script),
        "return_code": fallback_result.get("return_code"),
        "status": fallback_result.get("status"),
        "success": fallback_result.get("success"),
        "stderr": (fallback_result.get("stderr") or "")[:500],
    }


def _run_gemini_impl(
    prompt: str,
    timeout: int = 3600,
    working_dir: Optional[str] = None,
    model: Optional[str] = None,
    output_format: str = "text",
    prompt_files: Optional[list[str]] = None,
    role: Optional[str] = None,
    session_file: Optional[str] = None,
    metadata_json: Optional[str] = None,
    agy_continue: bool = False,
    restrict_tools: bool = False,
    allow_write: bool = False,
    disable_fallback: bool = False,
) -> dict:
    requested_model = model
    model = model or DEFAULT_MODEL
    effective_model = requested_model or DEFAULT_MODEL
    restrict_tools = resolve_restrict_tools(role, restrict_tools, allow_write)
    agy_print, subprocess_timeout = compute_timeouts(timeout)
    print_timeout_str = f"{agy_print}s"

    def error_envelope(message: str, code: int, command: str = f"{AGY_CLI} --print") -> dict[str, Any]:
        return {
            "success": False,
            "stdout": "",
            "stderr": message,
            "return_code": code,
            "command": command,
            "working_dir": working_dir or os.getcwd(),
            "model": model,
            "requested_model": requested_model,
            "effective_model": effective_model,
            "output_format": output_format,
            "agy_continue": agy_continue,
            "runner": "gemini",
        }

    # Validate the working directory first so relative input paths resolve
    # against a real directory.
    if working_dir and not Path(working_dir).is_dir():
        return error_envelope(f"Working directory does not exist: {working_dir}", -3)

    # Resolve relative prompt/session paths against --working-dir (not the
    # process cwd) before validating or reading them.
    resolved_prompt_files = (
        [resolve_input_path(p, working_dir) for p in prompt_files] if prompt_files else None
    )
    resolved_session_file = resolve_input_path(session_file, working_dir) if session_file else None

    for prompt_file in resolved_prompt_files or []:
        if not Path(prompt_file).is_file():
            return error_envelope(f"Prompt file does not exist: {prompt_file}", -3)

    if resolved_session_file and not Path(resolved_session_file).is_file():
        return error_envelope(f"Session file does not exist: {resolved_session_file}", -3)

    # Assemble the prompt. File reads happen here, so guard against read errors
    # (permissions, encoding) and return a clean envelope instead of a traceback.
    try:
        final_prompt = build_prompt(
            prompt, resolved_prompt_files, role, resolved_session_file, metadata_json, restrict_tools
        )
    except OSError as exc:
        return error_envelope(f"Failed to read input file: {exc}", -3)

    if agy_continue and not final_prompt.strip():
        final_prompt = (
            "Continue from the current conversation state. Pick the next "
            "highest-value step and follow through until the task is resolved."
        )
    format_instruction = output_format_instruction(output_format)
    if format_instruction:
        final_prompt = "\n\n".join([final_prompt, format_instruction])

    cmd = [AGY_CLI]
    if agy_continue:
        cmd.append("--continue")
    cmd.extend(["--print-timeout", print_timeout_str])
    cmd.extend(["--print", final_prompt])

    cwd = working_dir if working_dir else os.getcwd()
    command_display = " ".join(shlex.quote(part) for part in cmd)

    if shutil.which(AGY_CLI) is None:
        unavailable_env = {
            "success": False,
            "stdout": "",
            "stderr": "Antigravity CLI (agy) not found. Check if it is installed and in PATH.",
            "return_code": -2,
            "command": command_display,
            "working_dir": cwd,
            "model": model,
            "requested_model": requested_model,
            "effective_model": effective_model,
            "output_format": output_format,
            "agy_continue": agy_continue,
            "runner": "gemini",
            "effective_runner": None,
        }
        if disable_fallback:
            return unavailable_env

        fallback_candidates = [
            Path(__file__).resolve().parents[2] / "qwen-runner" / "scripts" / "run_qwen.py",
            Path(__file__).resolve().parents[2] / "kimi-runner" / "scripts" / "run_kimi.py",
            Path(__file__).resolve().parents[2] / "codex-runner" / "scripts" / "run_codex.py",
            Path(__file__).resolve().parents[2] / "claude-runner" / "scripts" / "run_claude.py",
        ]
        attempted_fallbacks: list[dict[str, Any]] = []
        last_failure: Optional[dict[str, Any]] = None
        for fallback_script in fallback_candidates:
            if not fallback_script.is_file():
                # Record absent siblings so the attempt log is complete.
                attempted_fallbacks.append(
                    {"script": str(fallback_script), "status": "not_installed", "return_code": None}
                )
                continue
            fallback_result = invoke_fallback(
                fallback_script,
                prompt,
                subprocess_timeout,
                working_dir,
                resolved_prompt_files,
                role,
                resolved_session_file,
                metadata_json,
                restrict_tools,
                allow_write,
                output_format,
            )
            # Accept only a genuinely successful fallback as the chosen result.
            if fallback_result.get("success") and fallback_result.get("return_code") == 0:
                return _annotate_fallback(
                    fallback_result, requested_model, model, agy_continue, attempted_fallbacks
                )
            attempted_fallbacks.append(_fallback_attempt_record(fallback_script, fallback_result))
            # Unavailable siblings are skipped; other failures are remembered so
            # the most informative one can be surfaced if nothing succeeds.
            if not (
                fallback_result.get("return_code") == -2
                or fallback_result.get("status") == "seat_unavailable"
            ):
                last_failure = fallback_result

        if last_failure is not None:
            return _annotate_fallback(
                last_failure, requested_model, model, agy_continue, attempted_fallbacks
            )
        if attempted_fallbacks:
            unavailable_env["fallback_attempts"] = attempted_fallbacks
        return unavailable_env

    result: dict[str, Any] = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_code": 0,
        "command": command_display,
        "working_dir": cwd,
        "model": model,
        "requested_model": requested_model,
        "effective_model": effective_model,
        "model_forwarded": False,
        "output_format": output_format,
        "output_format_forwarded": False,
        "agy_print_timeout": print_timeout_str,
        "agy_continue": agy_continue,
        "runner": "gemini",
        "effective_runner": "agy",
        "role": role,
        "session_file": resolved_session_file,
        "prompt_file": resolved_prompt_files[0] if resolved_prompt_files else None,
        "prompt_files": resolved_prompt_files or [],
        "restrict_tools": restrict_tools,
        "agent_message": None,
        "session_id": None,
    }

    try:
        process = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=subprocess_timeout,
        )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["return_code"] = process.returncode
        result["success"] = process.returncode == 0

        # Detect auth failure on stderr; only consult stdout when the run already
        # failed, so a successful answer that merely mentions authentication is
        # not misread as an auth failure.
        scan = (process.stderr or "").lower()
        if process.returncode != 0:
            scan += "\n" + (process.stdout or "").lower()
        if any(marker in scan for marker in AUTH_FAILURE_MARKERS):
            # A run that did not authenticate produced no trustworthy output:
            # keep the envelope internally consistent by failing it.
            result["auth_ok"] = False
            result["success"] = False
            result["status"] = "auth_failed"
            if result["return_code"] == 0:
                result["return_code"] = 1

        if result["success"]:
            result["agent_message"] = process.stdout.strip() or None
            result["auth_ok"] = True
            # output_format=json/stream-json is an advisory prompt hint; do a
            # best-effort fence-strip and record whether it parsed.
            if output_format == "json" and result["agent_message"]:
                cleaned, valid = strip_json_fences(result["agent_message"])
                result["agent_message"] = cleaned
                result["output_json_valid"] = valid

    except subprocess.TimeoutExpired as e:
        result["stderr"] = f"Timeout expired after {subprocess_timeout} seconds"
        result["stdout"] = (
            (e.stdout or "")
            if isinstance(e.stdout, str)
            else (e.stdout.decode("utf-8", errors="replace") if e.stdout else "")
        )
        result["return_code"] = -1
        result["status"] = "timeout"

    except FileNotFoundError:
        result["stderr"] = "Antigravity CLI (agy) not found. Check if it is installed and in PATH."
        result["return_code"] = -2
        result["effective_runner"] = None

    except Exception as e:
        result["stderr"] = f"Unexpected error: {str(e)}"
        result["return_code"] = -3

    return result


def run_gemini(
    prompt: str,
    timeout: int = 3600,
    working_dir: Optional[str] = None,
    model: Optional[str] = None,
    output_format: str = "text",
    prompt_files: Optional[list[str]] = None,
    role: Optional[str] = None,
    session_file: Optional[str] = None,
    metadata_json: Optional[str] = None,
    agy_continue: bool = False,
    restrict_tools: bool = False,
    allow_write: bool = False,
    disable_fallback: bool = False,
) -> dict:
    """
    Execute a prompt using Antigravity CLI (`agy`) print mode.

    Every return path — success, timeout, input error, missing CLI, and fallback
    — is passed through ``normalize_envelope`` so the shared-envelope keys are
    always present, including for programmatic (non-CLI) callers.

    Args:
        prompt: The prompt to execute.
        timeout: Maximum wait time in seconds (default: 3600). agy's own
            print-timeout is set slightly below this so it self-terminates before
            the hard subprocess timeout.
        working_dir: Working directory for execution (default: current
            directory). Relative ``prompt_files``/``session_file`` paths resolve
            against this directory.
        model: Accepted for compatibility; agy uses its configured model from
            settings/model picker. When supplied, the label is reflected in
            ``effective_model``; otherwise ``effective_model`` is the
            ``gemini-3.1-pro`` premium-seat label (set agy's own picker to
            Gemini 3.1 Pro, or Gemini 3.5 Flash for broad-perspective seats).
        output_format: Compatibility hint - 'text', 'json', or 'stream-json'
            (default: 'text'). Advisory only; for 'json' the wrapper does a
            best-effort fence-strip and sets ``output_json_valid``.
        prompt_files: Files concatenated (in order) to form the prompt body.
        role: PAL-style role overlay.
        session_file: Prior context appended for cross-runner continuation.
        metadata_json: Structured metadata embedded in the prompt.
        agy_continue: Resume the most recent agy conversation (--continue).
        restrict_tools: Apply the read-only overlay. Wins over allow_write.
        allow_write: Opt an analysis role out of the default read-only overlay.
        disable_fallback: Fail instead of routing to another runner.

    Returns:
        A normalized envelope dict (see ``REQUIRED_ENVELOPE_KEYS``).
    """
    raw = _run_gemini_impl(
        prompt=prompt,
        timeout=timeout,
        working_dir=working_dir,
        model=model,
        output_format=output_format,
        prompt_files=prompt_files,
        role=role,
        session_file=session_file,
        metadata_json=metadata_json,
        agy_continue=agy_continue,
        restrict_tools=restrict_tools,
        allow_write=allow_write,
        disable_fallback=disable_fallback,
    )
    return normalize_envelope(
        raw, requested_runner="gemini", requested_model=(model or DEFAULT_MODEL)
    )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Execute prompts using Antigravity CLI (agy) in headless print mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is 2+2?"
  %(prog)s "List Python files" --working-dir /path/to/project
  %(prog)s "Explain this code" --json --timeout 3600
  %(prog)s "Review this diff" --role codereviewer
        """,
    )

    parser.add_argument("prompt", nargs="?", default="", help="The prompt to execute")

    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=3600,
        help="Maximum execution time in seconds (default: 3600)",
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
        help="Output script results in JSON format",
    )
    parser.add_argument(
        "--prompt-file",
        action="append",
        default=None,
        dest="prompt_files",
        help="Read the prompt body from a file (repeatable; files are concatenated in order)",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Add a read-only analysis overlay to the prompt (default for analysis roles)",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Opt an analysis role out of the default read-only overlay",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run as a tracked background job and return a job id immediately",
    )

    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help=(
            "Requested model label for metadata. agy uses its configured model "
            f"from settings/model picker (default metadata: {DEFAULT_MODEL})"
        ),
    )

    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=["text", "json", "stream-json"],
        default="text",
        help="Requested response format hint (agy print mode has no output-format flag)",
    )

    parser.add_argument(
        "--role",
        type=str,
        choices=sorted(ROLE_INSTRUCTIONS),
        default=None,
        help="Apply a PAL-style role overlay before running the prompt",
    )
    parser.add_argument(
        "--session-file",
        type=str,
        default=None,
        help="Append prior discussion context from a file for continuation or handoff",
    )
    parser.add_argument(
        "--metadata-json",
        type=str,
        default=None,
        help="JSON string to embed as execution metadata for downstream parsing",
    )
    parser.add_argument(
        "--agy-continue",
        action="store_true",
        help="Pass --continue to agy to resume the most recent Antigravity CLI conversation",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Do not route to another runner if Antigravity CLI (agy) is unavailable",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write the wrapper JSON result to this file atomically",
    )

    args = parser.parse_args()

    if not args.prompt and not args.prompt_files and not args.agy_continue:
        parser.error("Provide a prompt argument, --prompt-file, or --agy-continue")

    if args.prompt and args.prompt_files:
        parser.error("Provide either a positional prompt OR --prompt-file, not both")

    if args.metadata_json is not None:
        try:
            json.loads(args.metadata_json)
        except json.JSONDecodeError as exc:
            parser.error(f"--metadata-json must be valid JSON: {exc}")

    if args.background:
        jobs = load_runner_jobs()
        if jobs is None:
            parser.error(
                "--background requires the shared jobs module (_shared/scripts/runner_jobs.py), which was not found"
            )
        prompt_source = args.prompt or (
            f"prompt files: {', '.join(args.prompt_files)}" if args.prompt_files else "(continue)"
        )
        try:
            summary = jobs.launch_background(
                "gemini",
                Path(__file__),
                sys.argv[1:],
                working_dir=args.working_dir,
                prompt_excerpt=prompt_source,
                manifest_extra={"role": args.role, "model": args.model},
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_gemini(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model,
        output_format=args.output_format,
        prompt_files=args.prompt_files,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        agy_continue=args.agy_continue,
        restrict_tools=args.restrict_tools,
        allow_write=args.allow_write,
        disable_fallback=args.disable_fallback,
    )

    output_file = None
    if args.output_file:
        output_file = write_json_output_file(args.output_file, result)

    if args.json:
        if output_file:
            # Keep enough provenance in the pointer that an orchestrator reading
            # stdout knows which seat/fallback answered without opening the file.
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
                    }
                )
            )
        else:
            print(json.dumps(result, indent=2))
    else:
        # Prefer the cleaned agent_message over raw stdout when available.
        if result.get("agent_message"):
            print(result["agent_message"])
        elif result.get("stdout"):
            print(result["stdout"], end="")
        if result.get("stderr"):
            print(result["stderr"], file=sys.stderr)
        if output_file:
            print(f"Result written to {output_file}")

    sys.exit(result["return_code"] if result["return_code"] >= 0 else 1)


if __name__ == "__main__":
    main()
