#!/usr/bin/env python3

import argparse
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
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

from model_receipt import attach_model_receipt, attach_claude_model_receipt
from execution_metrics import FIELDS, normalize_metrics
from model_routing import default_model, load_config, runner_efforts

ROUTING_CONFIG = load_config()
DEFAULT_MODEL = default_model("claude", ROUTING_CONFIG)
DEFAULT_EFFORT = ROUTING_CONFIG["runners"]["claude"]["default_effort"]

ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "adversarial": "Act as an adversarial reviewer. Pressure-test assumptions, attack weak reasoning, and surface concrete failure modes with evidence.",
    "challenger": "Act as a constructive challenger. Argue against the leading option, name viable alternatives, and force explicit tradeoff handling.",
    "researcher": "Act as a research specialist. Distinguish facts from inference, gather evidence, and cite sources or concrete artifacts when available.",
}

# Roles that modify the workspace; every other role defaults to read tools only.
WRITE_ROLES = {"implementer"}
TOOL_PROFILES = {"no_tools": [], "repo_read_only": ["Read", "Glob", "Grep"], "write": None}

EFFORT_LEVELS = runner_efforts("claude", accepted=True, config=ROUTING_CONFIG)


PROVIDER_BY_RUNNER = {
    "claude": "anthropic",
    "codex": "openai",
    "gemini": "google",
    "qwen": "qwen",
    "gemma": "google",
    "glm": "zai",
    "glm-critical": "zai",
    "kimi": "moonshotai",
    "minimax": "minimax",
}


def normalize_envelope(
    result: dict[str, Any],
    requested_runner: str,
    requested_model: str | None = DEFAULT_MODEL,
) -> dict[str, Any]:
    effective_runner = str(
        result.get("effective_runner") or result.get("runner") or requested_runner
    )
    result["runner"] = requested_runner
    result["effective_runner"] = effective_runner

    attach_model_receipt(
        result,
        requested_model,
        observed_source="not_observed",
    )

    result.setdefault("fallback_reason", None)

    # Preserve the fallback runner's auth_ok when one was used; the fallback
    # reason already explains why the originally requested runner did not run.
    # Missing CLI / errors before auth leave auth_ok null (untested), never
    # false — false is reserved for a detected authentication failure.
    if "auth_ok" not in result or result.get("auth_ok") is None:
        result["auth_ok"] = True if result.get("return_code") == 0 else None

    result["effective_provider"] = result.get(
        "effective_provider"
    ) or PROVIDER_BY_RUNNER.get(
        effective_runner,
        effective_runner,
    )

    if result.get("return_code") == -2 and not result.get("status"):
        result["status"] = "seat_unavailable"

    return result


def load_text_file(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def resolve_input_path(path: str, working_dir: str | None) -> str:
    """Resolve a relative input path against --working-dir, not the process cwd."""
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and working_dir:
        return str(Path(working_dir).expanduser() / candidate)
    return str(candidate)


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


def resolve_restrict_tools(
    role: str | None, restrict_tools: bool, allow_write: bool
) -> bool:
    if restrict_tools:
        return True
    if allow_write:
        return False
    return bool(role) and role not in WRITE_ROLES


def extract_output_fields(
    stdout: str, output_format: str
) -> tuple[str | None, str | None]:
    """Return (agent_message, session_id) parsed from Claude print-mode stdout."""
    if output_format in {"json", "stream-json"}:
        event = structured_result(stdout, output_format) or {}
        message = event.get("result")
        session_id = event.get("session_id")
        return (message if isinstance(message, str) and message.strip() else None,
                session_id if isinstance(session_id, str) and session_id else None)

    text = stdout.strip()
    return (text or None), None


def load_runner_jobs():
    shared_dir = _skills_root() / "shared" / "scripts"
    if not (shared_dir / "runner_jobs.py").is_file():
        return None
    sys.path.insert(0, str(shared_dir))
    import runner_jobs

    return runner_jobs


def structured_result(stdout: str, output_format: str) -> dict | None:
    results = [event for event in structured_events(stdout, output_format) if event.get("type") == "result"]
    return results[-1] if results else None


def structured_events(stdout: str, output_format: str) -> list[dict]:
    try:
        if output_format == "json":
            payload = json.loads(stdout)
            events = payload if isinstance(payload, list) else [payload]
        elif output_format == "stream-json":
            from stream_capture import parse_events
            events = parse_events(stdout)
        else:
            return []
    except json.JSONDecodeError:
        return []
    return [event for event in events if isinstance(event, dict)]


def tool_profile_receipt(events: list[dict], profile: str) -> dict:
    allowed = TOOL_PROFILES[profile]
    receipt = {"profile": profile, "status": "unverified", "observed_tools": None,
               "observed_mcp_servers": None, "errors": []}
    if allowed is None:
        receipt["status"] = "not_restricted"
        return receipt
    for event in events:
        if event.get("type") != "system" or event.get("subtype") != "init":
            continue
        if "tools" in event:
            observed = event["tools"]
            receipt["observed_tools"] = observed
            if not isinstance(observed, list) or any(tool not in allowed for tool in observed):
                receipt["errors"].append("Startup tools exceed the selected profile.")
        if "mcp_servers" in event:
            receipt["observed_mcp_servers"] = event["mcp_servers"]
            if event["mcp_servers"] != []:
                receipt["errors"].append("Startup MCP servers are not empty.")
    if receipt["errors"]:
        receipt["status"] = "violated"
    elif receipt["observed_tools"] is not None and receipt["observed_mcp_servers"] is not None:
        receipt["status"] = "verified"
    return receipt


def validate_limits(timeout: float, max_turns: int | None, max_budget_usd: float | None) -> None:
    for name, value in (("timeout", timeout), ("max_budget_usd", max_budget_usd)):
        if value is None and name != "timeout":
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite number.")
    if max_turns is not None and (type(max_turns) is not int or max_turns <= 0):
        raise ValueError("max_turns must be a positive integer.")


def infer_claude_success(return_code: int, stdout: str, output_format: str) -> bool:
    if return_code != 0:
        return False
    if output_format == "text":
        return bool(stdout.strip())
    result = structured_result(stdout, output_format)
    return bool(result and result.get("is_error") is not True
                and result.get("subtype") == "success"
                and isinstance(result.get("result"), str) and result["result"].strip())


def build_prompt(
    prompt: str,
    prompt_files: list[str],
    role: str | None,
    session_file: str | None,
    metadata_json: str | None,
) -> str:
    sections: list[str] = []
    if role:
        sections.append(f"Role: {role}\n{ROLE_INSTRUCTIONS.get(role, '')}".strip())
    if metadata_json:
        sections.append(f"Execution metadata:\n{metadata_json}")
    if session_file:
        sections.append(
            "Prior conversation context to continue from:\n"
            f"{load_text_file(session_file)}"
        )
    if prompt_files:
        prompt_text = "\n\n---\n\n".join(load_text_file(f) for f in prompt_files)
    else:
        prompt_text = prompt
    sections.append(prompt_text)
    return "\n\n".join(section for section in sections if section.strip())


def invoke_fallback(
    runner_script: Path,
    prompt: str,
    timeout: int,
    working_dir: str | None,
    prompt_files: list[str],
    role: str | None,
    session_file: str | None,
    metadata_json: str | None,
    restrict_tools: bool,
) -> dict[str, Any]:
    command = [sys.executable, str(runner_script), "--json", "--disable-fallback"]

    if prompt_files:
        for pf in prompt_files:
            command.extend(["--prompt-file", pf])
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
    if restrict_tools:
        command.append("--restrict-tools")

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "stdout": (
                exc.stdout
                if isinstance(exc.stdout, str)
                else (
                    exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
                )
            ),
            "stderr": f"Fallback runner timed out after {timeout} seconds",
            "return_code": -1,
            "command": " ".join(shlex.quote(part) for part in command),
        }
    except Exception as exc:  # noqa: BLE001
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


def resolve_claude_oauth_token() -> str | None:
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
    if token:
        return token

    shell = os.environ.get("SHELL") or "/bin/zsh"
    shell_name = Path(shell).name
    if shell_name not in {"zsh", "bash"}:
        shell = "/bin/zsh"

    shell_args = [shell, "-lic", 'printf %s "$CLAUDE_CODE_OAUTH_TOKEN"']
    if Path(shell).name == "bash":
        shell_args = [shell, "-ilc", 'printf %s "$CLAUDE_CODE_OAUTH_TOKEN"']

    try:
        result = subprocess.run(
            shell_args,
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ.copy(),
            check=False,
        )
    except Exception:  # noqa: BLE001
        return None

    if result.returncode != 0:
        return None

    token = result.stdout.strip()
    return token or None


def bare_mode_has_supported_auth(env: dict[str, str]) -> bool:
    return bool(env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN"))


def run_claude(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Public entry point: every exit path (including early validation errors
    and fallback results) returns a fully normalized envelope, whether invoked
    via the CLI or imported and called programmatically."""
    requested_model = kwargs.get("model") if "model" in kwargs else (args[3] if len(args) > 3 else DEFAULT_MODEL)
    result = _run_claude(*args, **kwargs)
    metadata = kwargs.get("metadata_json") if "metadata_json" in kwargs else (args[8] if len(args) > 8 else None)
    if metadata:
        try:
            parsed = json.loads(metadata)
            if isinstance(parsed, dict):
                result["dispatch_metadata"] = parsed
        except (TypeError, ValueError):
            pass  # Metadata is optional context, not execution authority.
    return normalize_envelope(result, requested_runner="claude", requested_model=requested_model)


def _run_claude(
    prompt: str,
    timeout: int = 3600,
    working_dir: str | None = None,
    model: str | None = DEFAULT_MODEL,
    safe_mode: bool = True,
    prompt_files: list[str] | None = None,
    role: str | None = None,
    session_file: str | None = None,
    metadata_json: str | None = None,
    output_format: str = "text",
    bare: bool = False,
    no_session_persistence: bool = False,
    restrict_tools: bool = False,
    allow_write: bool = False,
    effort: str | None = DEFAULT_EFFORT,
    resume: str | None = None,
    continue_last: bool = False,
    disable_fallback: bool = False,
    event_log: str | None = None,
    tool_profile: str | None = None,
    max_turns: int | None = None,
    max_budget_usd: float | None = None,
) -> dict[str, Any]:
    cwd = str(Path(working_dir or os.getcwd()).expanduser().resolve())
    try:
        validate_limits(timeout, max_turns, max_budget_usd)
        if tool_profile is not None and tool_profile not in TOOL_PROFILES:
            raise ValueError("Unknown tool_profile.")
        if allow_write and (restrict_tools or tool_profile in {"no_tools", "repo_read_only"}):
            raise ValueError("allow_write conflicts with the restricted tool profile.")
        if restrict_tools and tool_profile == "write":
            raise ValueError("restrict_tools conflicts with the write profile.")
    except ValueError as exc:
        return {"success": False, "print_invocation_started": False, "return_code": -3, "status": "invalid_input",
                "stdout": "", "stderr": str(exc), "model": model, "working_dir": cwd}
    explicit_profile = tool_profile is not None
    tool_profile = tool_profile or ("repo_read_only" if resolve_restrict_tools(role, restrict_tools, allow_write) else "write")
    restrict_tools = tool_profile != "write"
    fallback_preserves_constraints = not (restrict_tools or explicit_profile or allow_write or max_turns is not None or max_budget_usd is not None)
    cmd = ["claude"]

    if resume and continue_last:
        return {
            "success": False, "print_invocation_started": False,
            "stdout": "",
            "stderr": "Use either --resume SESSION_ID or --continue, not both.",
            "return_code": -3,
            "command": "claude -p",
            "working_dir": cwd,
            "model": model,
            "safe_mode": safe_mode,
            "output_format": output_format,
            "bare": bare,
            "no_session_persistence": no_session_persistence,
            "restrict_tools": restrict_tools,
        }

    # Relative input paths resolve against --working-dir (not the process cwd),
    # with ~ expanded — matching gemini-runner's documented behavior.
    prompt_files = [resolve_input_path(p, working_dir) for p in prompt_files] if prompt_files else prompt_files
    session_file = resolve_input_path(session_file, working_dir) if session_file else session_file

    for pf in prompt_files or []:
        if not Path(pf).is_file():
            return {
                "success": False, "print_invocation_started": False,
                "stdout": "",
                "stderr": f"Prompt file does not exist: {pf}",
                "return_code": -3,
                "command": "claude -p",
                "working_dir": cwd,
                "model": model,
                "safe_mode": safe_mode,
                "output_format": output_format,
                "bare": bare,
                "no_session_persistence": no_session_persistence,
                "restrict_tools": restrict_tools,
            }

    if session_file and not Path(session_file).is_file():
        return {
            "success": False, "print_invocation_started": False,
            "stdout": "",
            "stderr": f"Session file does not exist: {session_file}",
            "return_code": -3,
            "command": "claude -p",
            "working_dir": cwd,
            "model": model,
            "safe_mode": safe_mode,
            "output_format": output_format,
            "bare": bare,
            "no_session_persistence": no_session_persistence,
            "restrict_tools": restrict_tools,
        }

    final_prompt = build_prompt(
        prompt, prompt_files or [], role, session_file, metadata_json
    )
    if (resume or continue_last) and not final_prompt.strip():
        final_prompt = (
            "Continue from the current conversation state. Pick the next "
            "highest-value step and follow through until the task is resolved."
        )
    if bare:
        cmd.append("--bare")

    if output_format and output_format != "text":
        cmd.extend(["--output-format", output_format])
        cmd.append("--verbose")

    if no_session_persistence:
        cmd.append("--no-session-persistence")

    if restrict_tools:
        cmd.extend(["--safe-mode", "--tools", ",".join(TOOL_PROFILES[tool_profile]),
                    "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
                    "--permission-mode", "plan"])

    if max_turns is not None:
        cmd.extend(["--max-turns", str(max_turns)])
    if max_budget_usd is not None:
        cmd.extend(["--max-budget-usd", str(max_budget_usd)])

    if model:
        cmd.extend(["--model", model])

    if effort:
        cmd.extend(["--effort", effort])

    if resume:
        cmd.extend(["--resume", resume])
    elif continue_last:
        cmd.append("--continue")

    cmd.extend(["-p", final_prompt])

    command_display = " ".join(shlex.quote(part) for part in cmd)

    if working_dir and not Path(working_dir).is_dir():
        return {
            "success": False, "print_invocation_started": False,
            "stdout": "",
            "stderr": f"Working directory does not exist: {working_dir}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir,
            "model": model,
            "safe_mode": safe_mode,
            "output_format": output_format,
            "bare": bare,
            "no_session_persistence": no_session_persistence,
            "restrict_tools": restrict_tools,
        }

    # Resolve relative PATH entries in the same directory used by the child.
    search_path = os.pathsep.join(
        str(Path(cwd) / part) if not Path(part).is_absolute() else part
        for part in os.environ.get("PATH", os.defpath).split(os.pathsep)
    )
    cli_path = shutil.which("claude", path=search_path)
    if cli_path is None:
        if not disable_fallback and fallback_preserves_constraints:
            fallback_runner = ROUTING_CONFIG["runners"]["claude"]["fallback_runner"]
            fallback_script = _skill_dir(f"{fallback_runner}-runner") / "scripts" / f"run_{fallback_runner}.py"
            if fallback_script.is_file():
                fallback_result = invoke_fallback(
                    fallback_script,
                    prompt,
                    timeout,
                    working_dir,
                    prompt_files or [],
                    role,
                    session_file,
                    metadata_json,
                    restrict_tools,
                )
                fallback_result["fallback_from"] = "claude"
                fallback_result["fallback_reason"] = "Claude CLI not found"
                fallback_result["requested_model"] = model
                fallback_result["fallback_model_forwarded"] = False
                return fallback_result
        return {
            "success": False, "print_invocation_started": False,
            "stdout": "",
            "stderr": "Claude CLI not found. Please ensure 'claude' is installed and in PATH."
                      + (" Fallback blocked because it cannot preserve the selected tool profile or limits." if not fallback_preserves_constraints else ""),
            "return_code": -2,
            "command": command_display,
            "working_dir": cwd,
            "model": model,
            "safe_mode": safe_mode,
            "output_format": output_format,
            "bare": bare,
            "no_session_persistence": no_session_persistence,
            "restrict_tools": restrict_tools,
        }

    cmd[0] = str(Path(cli_path).absolute())
    command_display = " ".join(shlex.quote(part) for part in cmd)
    result = {
        "success": False, "print_invocation_started": False,
        "stdout": "",
        "stderr": "",
        "return_code": 0,
        "command": command_display,
        "working_dir": cwd,
        "model": model,
        "safe_mode": safe_mode,
        "output_format": output_format,
        "bare": bare,
        "no_session_persistence": no_session_persistence,
        "restrict_tools": restrict_tools,
        "runner": "claude",
        "effective_runner": "claude",
        "role": role,
        "session_file": session_file,
        "prompt_files": prompt_files or [],
        "effort": effort,
        "resume": resume or ("--continue" if continue_last else None),
        "agent_message": None,
        "session_id": None,
        "tool_profile": tool_profile,
        "tool_profile_receipt": tool_profile_receipt([], tool_profile),
        "limits": {"timeout_seconds": timeout, "max_turns": max_turns,
                   "max_budget_usd": max_budget_usd, "response_length": "advisory_only"},
    }

    child_env = os.environ.copy()
    oauth_token = resolve_claude_oauth_token()
    if oauth_token:
        child_env["CLAUDE_CODE_OAUTH_TOKEN"] = oauth_token

    if bare and not bare_mode_has_supported_auth(child_env):
        result["stderr"] = (
            "Claude bare mode disables OAuth/keychain auth. "
            "Use non-bare mode for OAuth-backed Claude sessions, or provide "
            "ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN explicitly."
        )
        result["return_code"] = -4
        return result

    preflight_started = time.monotonic()
    try:
        from runner_preflight import check_claude
        result["preflight"] = check_claude(
            model, effort, cli_path=cmd[0], working_dir=cwd, env=child_env,
        )
    except Exception as exc:  # noqa: BLE001
        result["preflight"] = {
            "blocked": True, "reasons": ["Local preflight could not complete."],
            "evidence": {"error_type": type(exc).__name__},
        }
    if result["preflight"]["blocked"]:
        result.update(return_code=-3, terminal_status="preflight_blocked",
                      status="seat_unavailable", auth_ok=None,
                      stderr="Preflight blocked: " + "; ".join(result["preflight"]["reasons"]))
        if result["preflight"].get("evidence", {}).get("provider_calls") == 0:
            result["metrics"] = {key: 0 for key in FIELDS}
            result["metrics"]["duration_ms"] = (time.monotonic() - preflight_started) * 1000
            result["metrics_complete"] = True
        return result

    try:
        if event_log and output_format == "stream-json":
            from stream_capture import capture
            result["print_invocation_started"] = True
            process = capture(cmd, cwd, child_env, timeout, event_log)
            result["event_log"] = str(Path(event_log).resolve())
        else:
            result["print_invocation_started"] = True
            process = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True,
                timeout=timeout, env=child_env, check=False,
            )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["return_code"] = process.returncode
        result["success"] = infer_claude_success(
            process.returncode,
            process.stdout,
            output_format,
        )
        if not result["success"] and result["return_code"] == 0:
            result["return_code"] = 1
        agent_message, session_id = extract_output_fields(process.stdout, output_format)
        result["agent_message"] = agent_message
        result["session_id"] = session_id
        native_result = structured_result(process.stdout, output_format)
        result["metrics"] = normalize_metrics(native_result or {})
        result["terminal_status"] = "completed" if result["success"] else "failed"
        if output_format != "text" and result["success"] and not no_session_persistence and not session_id:
            result.update(success=False, return_code=1, terminal_status="invalid_receipt",
                          error="Structured result has no session ID; reconcile before retrying.")
        elif output_format != "text" and native_result is None:
            result.update(terminal_status="invalid_receipt", error="Missing or malformed structured terminal result.")
    except subprocess.TimeoutExpired as e:
        result["stderr"] = f"Timeout expired after {timeout} seconds"
        result["stdout"] = (
            e.stdout
            if isinstance(e.stdout, str)
            else (e.stdout.decode("utf-8", errors="replace") if e.stdout else "")
        )
        partial_stderr = (
            e.stderr
            if isinstance(e.stderr, str)
            else (e.stderr.decode("utf-8", errors="replace") if e.stderr else "")
        )
        if partial_stderr:
            result["stderr"] = f"{result['stderr']}\n{partial_stderr}"
        result["return_code"] = -1
        result["terminal_status"] = "interrupted"
        from stream_capture import parse_events, progress
        partial = progress(parse_events(result["stdout"]))
        result["session_id"] = partial["session_id"] or resume
        result["metrics"] = partial["metrics"]
        result["metrics_complete"] = False
        if event_log:
            result["event_log"] = str(Path(event_log).resolve())
    except Exception as e:  # noqa: BLE001
        result["stderr"] = f"Unexpected error: {e!s}"
        result["return_code"] = -3

    events = structured_events(result["stdout"], output_format)
    attach_claude_model_receipt(result, events, model)
    result["tool_profile_receipt"] = tool_profile_receipt(events, tool_profile)
    receipt_error = result["model_identity_error"]
    if result["tool_profile_receipt"]["status"] == "violated":
        receipt_error = "; ".join(result["tool_profile_receipt"]["errors"])
    if receipt_error:
        result.update(success=False, error=receipt_error)
        if result["return_code"] == 0:
            result.update(return_code=1, terminal_status="invalid_receipt")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Execute prompts using Claude CLI in headless mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is 2+2?"
  %(prog)s "List Python files" --working-dir /path/to/project
  %(prog)s "Explain this code" --json --timeout 3600
  %(prog)s "Summarize this repo" --model <approved-model>
  %(prog)s "Review this code"
        """,
    )

    parser.add_argument("prompt", nargs="?", default="", help="The prompt to execute")
    parser.add_argument(
        "--prompt-file",
        type=str,
        action="append",
        default=None,
        dest="prompt_files",
        metavar="FILE",
        help="Read prompt from a file (can be repeated; files are concatenated in order)",
    )

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
        "--model",
        "-m",
        type=str,
        default=DEFAULT_MODEL,
        help="Claude model alias ('fable', 'opus', 'sonnet') or a full model id; approved routes use the pin in shared/model-routing.json",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=["text", "json", "stream-json"],
        default="text",
        help="Claude print-mode output format (default: text)",
    )

    parser.add_argument(
        "--safe",
        action="store_true",
        default=True,
        help="Keep Claude permission checks enabled. This is the default.",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Run Claude in bare mode for faster startup and fewer implicit context sources",
    )
    parser.add_argument(
        "--no-session-persistence",
        action="store_true",
        help="Do not persist Claude session files to disk",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Use the repo_read_only tool profile (default for analysis roles)",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Allow the normal write tool set for an analysis role",
    )
    parser.add_argument("--tool-profile", choices=sorted(TOOL_PROFILES), help="Explicit tool authority; restricted profiles also disable customizations and MCP")
    parser.add_argument("--max-turns", type=int, help="Positive maximum number of native turns")
    parser.add_argument("--max-budget-usd", type=float, help="Positive reported USD cost cap enforced by the native CLI")
    parser.add_argument(
        "--effort",
        "-e",
        type=str,
        choices=EFFORT_LEVELS,
        default=DEFAULT_EFFORT,
        help="Claude effort level override",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="SESSION_ID",
        help="Natively resume a Claude session by session id",
    )
    parser.add_argument(
        "--continue",
        dest="continue_last",
        action="store_true",
        help="Natively resume the most recent Claude conversation in this project",
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
        "--disable-fallback",
        action="store_true",
        help="Do not route to another runner if Claude CLI is unavailable",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write the wrapper JSON result to this file atomically",
    )

    parser.add_argument("--event-log", help="exclusive durable stream-json log; defaults beside --output-file")
    args = parser.parse_args()
    try:
        validate_limits(args.timeout, args.max_turns, args.max_budget_usd)
    except ValueError as exc:
        parser.error(str(exc))

    if (
        not args.prompt
        and not args.prompt_files
        and not (args.resume or args.continue_last)
    ):
        parser.error("Provide a prompt argument, --prompt-file, or --resume/--continue")

    if args.background:
        jobs = load_runner_jobs()
        if jobs is None:
            parser.error(
                "--background requires the shared jobs module (shared/scripts/runner_jobs.py), which was not found"
            )
        prompt_source = args.prompt or (
            f"prompt files: {', '.join(args.prompt_files)}"
            if args.prompt_files
            else "(resume)"
        )
        try:
            summary = jobs.launch_background(
                "claude",
                Path(__file__),
                sys.argv[1:],
                working_dir=args.working_dir,
                prompt_excerpt=prompt_source,
                manifest_extra={
                    "role": args.role,
                    "model": args.model,
                    "effort": args.effort,
                },
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_claude(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model,
        safe_mode=args.safe,
        prompt_files=args.prompt_files,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        output_format=args.output_format,
        bare=args.bare,
        no_session_persistence=args.no_session_persistence,
        restrict_tools=args.restrict_tools,
        allow_write=args.allow_write,
        effort=args.effort,
        resume=args.resume,
        continue_last=args.continue_last,
        disable_fallback=args.disable_fallback,
        event_log=args.event_log or (str(Path(args.output_file).with_suffix(".events.jsonl")) if args.output_file and args.output_format == "stream-json" else None),
        tool_profile=args.tool_profile,
        max_turns=args.max_turns,
        max_budget_usd=args.max_budget_usd,
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
