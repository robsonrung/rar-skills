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

AGY_CLI = "agy"
DEFAULT_MODEL = "agy-configured-model"
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


def load_text_file(path: str) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8")


def write_json_output_file(path: str, payload: dict[str, Any]) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=target.parent,
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, target)
    return str(target)


def resolve_restrict_tools(role: Optional[str], restrict_tools: bool, allow_write: bool) -> bool:
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


def format_print_timeout(timeout: int) -> str:
    return f"{max(1, int(timeout))}s"


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
    if restrict_tools:
        command.append("--restrict-tools")

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

    Args:
        prompt: The prompt to execute
        timeout: Maximum wait time in seconds (default: 3600)
        working_dir: Working directory for execution (default: current directory)
        model: Accepted for compatibility; Antigravity CLI currently uses its
            configured model from settings/model picker.
        output_format: Compatibility hint - 'text', 'json', or 'stream-json'
            (default: 'text')
        agy_continue: Resume the most recent Antigravity CLI conversation.

    Returns:
        dict with keys: success, stdout, stderr, return_code, command, working_dir
    """
    requested_model = model
    model = model or DEFAULT_MODEL
    restrict_tools = resolve_restrict_tools(role, restrict_tools, allow_write)

    for prompt_file in prompt_files or []:
        if not Path(prompt_file).is_file():
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Prompt file does not exist: {prompt_file}",
                "return_code": -3,
                "command": f"{AGY_CLI} --print",
                "working_dir": working_dir or os.getcwd(),
                "model": model,
                "requested_model": requested_model,
                "effective_model": DEFAULT_MODEL,
                "output_format": output_format,
                "agy_continue": agy_continue,
            }

    if session_file and not Path(session_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Session file does not exist: {session_file}",
            "return_code": -3,
            "command": f"{AGY_CLI} --print",
            "working_dir": working_dir or os.getcwd(),
            "model": model,
            "requested_model": requested_model,
            "effective_model": DEFAULT_MODEL,
            "output_format": output_format,
            "agy_continue": agy_continue,
        }

    final_prompt = build_prompt(prompt, prompt_files, role, session_file, metadata_json, restrict_tools)
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
    cmd.extend(["--print-timeout", format_print_timeout(timeout)])
    cmd.extend(["--print", final_prompt])

    cwd = working_dir if working_dir else os.getcwd()
    command_display = " ".join(shlex.quote(part) for part in cmd)

    if working_dir and not Path(working_dir).is_dir():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Working directory does not exist: {working_dir}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir,
            "model": model,
            "requested_model": requested_model,
            "effective_model": DEFAULT_MODEL,
            "output_format": output_format,
            "agy_continue": agy_continue,
        }

    if shutil.which(AGY_CLI) is None:
        if not disable_fallback:
            fallback_candidates = [
                Path(__file__).resolve().parents[2] / "qwen-runner" / "scripts" / "run_qwen.py",
                Path(__file__).resolve().parents[2] / "kimi-runner" / "scripts" / "run_kimi.py",
                Path(__file__).resolve().parents[2] / "codex-runner" / "scripts" / "run_codex.py",
                Path(__file__).resolve().parents[2] / "claude-runner" / "scripts" / "run_claude.py",
            ]
            attempted_fallbacks: list[dict[str, Any]] = []
            for fallback_script in fallback_candidates:
                if fallback_script.is_file():
                    fallback_result = invoke_fallback(
                        fallback_script,
                        prompt,
                        timeout,
                        working_dir,
                        prompt_files,
                        role,
                        session_file,
                        metadata_json,
                        restrict_tools,
                    )
                    if (
                        fallback_result.get("return_code") == -2
                        or fallback_result.get("status") == "seat_unavailable"
                    ):
                        attempted_fallbacks.append(
                            {
                                "script": str(fallback_script),
                                "return_code": fallback_result.get("return_code"),
                                "status": fallback_result.get("status"),
                                "stderr": fallback_result.get("stderr", ""),
                            }
                        )
                        continue
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
        return {
            "success": False,
            "stdout": "",
            "stderr": "Antigravity CLI (agy) not found. Check if it is installed and in PATH.",
            "return_code": -2,
            "command": command_display,
            "working_dir": cwd,
            "model": model,
            "requested_model": requested_model,
            "effective_model": DEFAULT_MODEL,
            "output_format": output_format,
            "agy_continue": agy_continue,
            "runner": "gemini",
            "effective_runner": None,
        }

    result: dict[str, Any] = {
        "success": False,
        "stdout": "",
        "stderr": "",
        "return_code": 0,
        "command": command_display,
        "working_dir": cwd,
        "model": model,
        "requested_model": requested_model,
        "effective_model": DEFAULT_MODEL,
        "model_forwarded": False,
        "output_format": output_format,
        "output_format_forwarded": False,
        "agy_print_timeout": format_print_timeout(timeout),
        "agy_continue": agy_continue,
        "runner": "gemini",
        "effective_runner": "agy",
        "role": role,
        "session_file": session_file,
        "prompt_file": prompt_files[0] if prompt_files and len(prompt_files) == 1 else None,
        "prompt_files": prompt_files or [],
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
            timeout=timeout,
        )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["return_code"] = process.returncode
        result["success"] = process.returncode == 0
        if result["success"]:
            result["agent_message"] = process.stdout.strip() or None
        combined_output = f"{process.stdout}\n{process.stderr}".lower()
        if (
            "authentication required" in combined_output
            or "waiting for authentication" in combined_output
            or "not authenticated" in combined_output
        ):
            result["auth_ok"] = False

    except subprocess.TimeoutExpired as e:
        result["stderr"] = f"Timeout expired after {timeout} seconds"
        result["stdout"] = (
            (e.stdout or "")
            if isinstance(e.stdout, str)
            else (e.stdout.decode("utf-8", errors="replace") if e.stdout else "")
        )
        result["return_code"] = -1

    except FileNotFoundError:
        result["stderr"] = "Antigravity CLI (agy) not found. Check if it is installed and in PATH."
        result["return_code"] = -2
        result["effective_runner"] = None

    except Exception as e:
        result["stderr"] = f"Unexpected error: {str(e)}"
        result["return_code"] = -3

    return result


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

    result = normalize_envelope(result, requested_runner="gemini", requested_model=args.model or DEFAULT_MODEL)

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
                    }
                )
            )
        else:
            print(json.dumps(result, indent=2))
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
