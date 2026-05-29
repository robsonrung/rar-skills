#!/usr/bin/env python3
"""Execute prompts via OpenCode CLI headless mode (opencode run)."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional


ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "challenger": "Act as a devil's advocate. Argue against the emerging consensus, surface blind spots, unstated assumptions, and unexplored alternatives.",
    "researcher": "Act as a thorough investigator. Cite sources, distinguish fact from inference, and surface uncertainty.",
}


PROVIDER_BY_RUNNER = {
    "claude": "anthropic",
    "codex": "openai",
    "gemini": "google",
    "qwen": "qwen",
    "gemma": "google",
    "glm": "z-ai",
    "glm-critical": "z-ai",
    "kimi": "moonshot",
    "minimax": "minimax",
    "opencode": "opencode",
}


def normalize_envelope(
    result: dict[str, Any],
    requested_runner: str,
    requested_model: str | None = None,
) -> dict[str, Any]:
    effective_runner = str(result.get("effective_runner") or result.get("runner") or requested_runner)
    result["runner"] = requested_runner
    result["effective_runner"] = effective_runner

    if result.get("effective_model") is None:
        result["effective_model"] = result.get("model") or requested_model

    result.setdefault("fallback_reason", None)

    if effective_runner != requested_runner and result.get("fallback_reason"):
        result["auth_ok"] = False
    elif "auth_ok" not in result or result.get("auth_ok") is None:
        code = result.get("return_code")
        if code == 0:
            result["auth_ok"] = True
        elif code == -2:
            result["auth_ok"] = False
        else:
            result["auth_ok"] = None

    result["effective_provider"] = result.get("effective_provider") or PROVIDER_BY_RUNNER.get(
        effective_runner,
        effective_runner,
    )

    if result.get("return_code") == -2 and not result.get("status"):
        result["status"] = "seat_unavailable"

    return result


def _safehouse_prefix(
    cwd: str,
    no_safehouse: bool,
    require_safehouse: bool,
) -> tuple[list[str], str, str | None]:
    if no_safehouse:
        return [], "disabled", None
    if shutil.which("safehouse") is None:
        message = (
            "Agent Safehouse is required for this run but was not found in PATH."
            if require_safehouse
            else None
        )
        return [], "missing", message
    return ["safehouse", f"--workdir={cwd}", "--enable=cloud-credentials", "--"], "active", None


def load_text_file(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def build_prompt(
    prompt: str,
    prompt_file: Optional[str],
    role: Optional[str],
    session_file: Optional[str],
    metadata_json: Optional[str],
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

    prompt_text = load_text_file(prompt_file) if prompt_file else prompt
    sections.append(prompt_text)
    return "\n\n".join(section for section in sections if section.strip())


def parse_json_output(raw_stdout: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    agent_messages: list[str] = []

    for line in raw_stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            agent_messages.append(line)
            continue
        events.append(event)

    if len(events) == 1 and not agent_messages:
        single = events[0]
        return {
            "agent_message": single.get("response", single.get("result", "")),
            "usage": single.get("stats", single.get("usage", {})),
            "events": events,
        }

    return {
        "agent_message": "\n".join(agent_messages) if agent_messages else "",
        "usage": {},
        "events": events,
    }


def format_opencode_event(event: dict[str, Any]) -> Optional[str]:
    event_type = event.get("type", "")
    if event_type in ("message", "assistant"):
        text = event.get("text") or event.get("content", "")
        role = event.get("role", "assistant")
        if text and role != "user":
            return f"[opencode] {text}"
    elif event_type == "tool_use":
        tool = event.get("name") or event.get("tool", "")
        return f"[opencode:tool] {tool}"
    elif event_type == "tool_result":
        tool = event.get("name") or event.get("tool", "")
        return f"[opencode:tool_result] {tool}"
    elif event_type == "result":
        text = event.get("response") or event.get("result", "")
        if text:
            preview = text[:200] + ("..." if len(text) > 200 else "")
            return f"[opencode:result] {preview}"
    elif event_type == "item.completed":
        item = event.get("item", {})
        item_type = item.get("type", "")
        if item_type == "agent_message" and item.get("text"):
            return f"[opencode] {item['text']}"
        elif item_type == "tool_call":
            tool = item.get("name") or item.get("tool", "")
            return f"[opencode:tool] {tool}"
    elif event_type == "turn.completed":
        return "[opencode:turn_completed]"

    text = event.get("text") or event.get("content") or event.get("response", "")
    if text:
        return f"[opencode] {text}"
    return None


def run_opencode_streaming(
    command: list[str],
    cwd: Optional[str],
    timeout: int,
    command_display: str,
    role: Optional[str],
    session_file: Optional[str],
    prompt_file: Optional[str],
    child_env: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=child_env,
        )
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "OpenCode CLI not found. Install via: brew install opencode-ai/tap/opencode",
            "return_code": -2,
            "command": command_display,
            "working_dir": cwd or "current directory",
            "runner": "opencode",
            "effective_runner": None,
        }

    collected_lines: list[str] = []
    try:
        assert process.stdout is not None
        for line in process.stdout:
            collected_lines.append(line)
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
                formatted = format_opencode_event(event)
                if formatted:
                    print(formatted, file=sys.stderr, flush=True)
            except json.JSONDecodeError:
                print(f"[opencode] {stripped}", file=sys.stderr, flush=True)

        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "success": False,
            "stdout": "".join(collected_lines),
            "stderr": f"Command exceeded timeout of {timeout} seconds",
            "return_code": -1,
            "command": command_display,
            "working_dir": cwd or "current directory",
            "runner": "opencode",
            "effective_runner": "opencode",
            "role": role,
        }

    raw_stdout = "".join(collected_lines)
    stderr_output = process.stderr.read() if process.stderr else ""
    parsed = parse_json_output(raw_stdout)

    return {
        "success": process.returncode == 0,
        "stdout": parsed.get("agent_message") or raw_stdout,
        "stderr": stderr_output,
        "return_code": process.returncode,
        "command": command_display,
        "working_dir": cwd or "current directory",
        "runner": "opencode",
        "effective_runner": "opencode",
        "role": role,
        "session_file": session_file,
        "prompt_file": prompt_file,
        "agent_message": parsed.get("agent_message", ""),
        "usage": parsed.get("usage", {}),
        "events": parsed.get("events", []),
    }


def run_opencode(
    prompt: str,
    timeout: int = 3600,
    working_dir: Optional[str] = None,
    model: Optional[str] = None,
    prompt_file: Optional[str] = None,
    role: Optional[str] = None,
    session_file: Optional[str] = None,
    metadata_json: Optional[str] = None,
    use_json: bool = False,
    stream: bool = False,
    no_safehouse: bool = False,
    require_safehouse: bool = False,
    continue_session: bool = False,
    resume_session: Optional[str] = None,
    file_attachments: Optional[list[str]] = None,
    title: Optional[str] = None,
    agent: Optional[str] = None,
) -> dict[str, Any]:
    command = ["opencode", "run"]
    command_display = "opencode run"

    if working_dir and not Path(working_dir).is_dir():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Working directory does not exist: {working_dir}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir,
            "runner": "opencode",
        }

    if prompt_file and not Path(prompt_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Prompt file does not exist: {prompt_file}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
            "runner": "opencode",
        }

    if session_file and not Path(session_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Session file does not exist: {session_file}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
            "runner": "opencode",
        }

    final_prompt = build_prompt(prompt, prompt_file, role, session_file, metadata_json)

    if model:
        command.extend(["--model", model])

    if use_json or stream:
        command.extend(["--format", "json"])

    if continue_session:
        command.append("--continue")

    if resume_session:
        command.extend(["--session", resume_session])

    if file_attachments:
        for f in file_attachments:
            command.extend(["--file", f])

    if title:
        command.extend(["--title", title])

    if agent:
        command.extend(["--agent", agent])

    command.append(final_prompt)

    command_display = " ".join(shlex.quote(part) for part in command)

    prefix, safehouse_status, safehouse_error = _safehouse_prefix(
        working_dir or os.getcwd(),
        no_safehouse,
        require_safehouse,
    )
    if safehouse_error:
        return {
            "success": False,
            "stdout": "",
            "stderr": safehouse_error,
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "safehouse_status": safehouse_status,
        }
    command = prefix + command
    command_display = " ".join(shlex.quote(p) for p in command)

    if shutil.which("opencode") is None:
        return {
            "success": False,
            "stdout": "",
            "stderr": "OpenCode CLI not found. Install via: brew install opencode-ai/tap/opencode",
            "return_code": -2,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "effective_runner": None,
            "safehouse_status": safehouse_status,
        }

    child_env = os.environ.copy()

    if stream:
        streamed_output = run_opencode_streaming(
            command=command,
            cwd=working_dir,
            timeout=timeout,
            command_display=command_display,
            role=role,
            session_file=session_file,
            prompt_file=prompt_file,
            child_env=child_env,
        )
        streamed_output["safehouse_status"] = safehouse_status
        return streamed_output

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            env=child_env,
        )

        output: dict[str, Any] = {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "effective_runner": "opencode",
            "role": role,
            "session_file": session_file,
            "prompt_file": prompt_file,
            "safehouse_status": safehouse_status,
        }

        if use_json and result.stdout:
            parsed = parse_json_output(result.stdout)
            output["agent_message"] = parsed["agent_message"]
            output["usage"] = parsed["usage"]
            output["events"] = parsed["events"]

        return output

    except subprocess.TimeoutExpired as e:
        partial_stdout = ""
        if e.stdout:
            partial_stdout = (
                e.stdout
                if isinstance(e.stdout, str)
                else e.stdout.decode("utf-8", errors="replace")
            )
        return {
            "success": False,
            "stdout": partial_stdout,
            "stderr": f"Command exceeded timeout of {timeout} seconds",
            "return_code": -1,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "effective_runner": "opencode",
            "role": role,
            "safehouse_status": safehouse_status,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "OpenCode CLI not found. Install via: brew install opencode-ai/tap/opencode",
            "return_code": -2,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "effective_runner": None,
            "safehouse_status": safehouse_status,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "opencode",
            "effective_runner": "opencode",
            "role": role,
            "safehouse_status": safehouse_status,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Execute prompts via OpenCode CLI headless mode"
    )
    parser.add_argument("prompt", nargs="?", default="", help="The prompt to execute")
    parser.add_argument(
        "--timeout", "-t", type=int, default=3600,
        help="Timeout in seconds (default: 3600)",
    )
    parser.add_argument(
        "--working-dir", "-w", type=str, default=None,
        help="Working directory for execution",
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Return output in JSON envelope",
    )
    parser.add_argument(
        "--model", "-m", type=str, default=None,
        help="Model in provider/model format (e.g., openrouter/anthropic/claude-sonnet-4.6)",
    )
    parser.add_argument(
        "--prompt-file", type=str, default=None,
        help="Read the prompt body from a file instead of positional argument",
    )
    parser.add_argument(
        "--role", type=str, choices=sorted(ROLE_INSTRUCTIONS), default=None,
        help="Apply a role overlay before running the prompt",
    )
    parser.add_argument(
        "--session-file", type=str, default=None,
        help="Append prior discussion context from a file for continuation",
    )
    parser.add_argument(
        "--metadata-json", type=str, default=None,
        help="JSON string to embed as execution metadata",
    )
    parser.add_argument(
        "--stream", action="store_true",
        help="Stream JSON events to stderr in real-time (forces --format json)",
    )
    parser.add_argument(
        "--no-safehouse", action="store_true",
        help="Skip safehouse OS-level sandboxing even when installed",
    )
    parser.add_argument(
        "--require-safehouse", action="store_true",
        help="Fail unless Agent Safehouse is available for this run",
    )
    parser.add_argument(
        "--continue", "-c", action="store_true", dest="continue_session",
        help="Continue the last session",
    )
    parser.add_argument(
        "--session", "-s", type=str, default=None, dest="resume_session",
        help="Session ID to continue",
    )
    parser.add_argument(
        "--file", "-f", action="append", default=None, dest="file_attachments",
        help="File(s) to attach to message (repeatable)",
    )
    parser.add_argument(
        "--title", type=str, default=None,
        help="Title for the session",
    )
    parser.add_argument(
        "--agent", type=str, default=None,
        help="Agent to use",
    )
    args = parser.parse_args()

    if not args.prompt and not args.prompt_file:
        parser.error("Provide a prompt argument or --prompt-file")

    result = run_opencode(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model,
        prompt_file=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        use_json=args.json,
        stream=args.stream,
        no_safehouse=args.no_safehouse,
        require_safehouse=args.require_safehouse,
        continue_session=args.continue_session,
        resume_session=args.resume_session,
        file_attachments=args.file_attachments,
        title=args.title,
        agent=args.agent,
    )

    result = normalize_envelope(result, requested_runner="opencode", requested_model=args.model)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print("=== OPENCODE OUTPUT ===")
            print(result["stdout"])
            if result["stderr"]:
                print("\n=== STDERR ===")
                print(result["stderr"])
        else:
            print("=== ERROR ===")
            print(f"Return code: {result['return_code']}")
            print(f"Command: {result['command']}")
            if result["stderr"]:
                print(f"Error: {result['stderr']}")
            if result["stdout"]:
                print(f"Output: {result['stdout']}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
