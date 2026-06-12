#!/usr/bin/env python3
"""Execute prompts in Codex CLI exec mode with role and continuation support."""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional


ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "adversarial": "Act as an adversarial reviewer. Pressure-test assumptions, attack weak reasoning, and surface concrete failure modes with evidence.",
    "challenger": "Act as a constructive challenger. Argue against the leading option, name viable alternatives, and force explicit tradeoff handling.",
    "researcher": "Act as a research specialist. Distinguish facts from inference, gather evidence, and cite sources or concrete artifacts when available.",
}

# Roles that modify the workspace; every other role defaults to a read-only sandbox.
WRITE_ROLES = {"implementer"}

MODEL_ALIASES = {
    "spark": "gpt-5.3-codex-spark",
}

EFFORT_LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh")

DEFAULT_CONTINUE_PROMPT = (
    "Continue from the current thread state. Pick the next highest-value step "
    "and follow through until the task is resolved."
)

SESSION_ID_PATTERNS = (
    re.compile(r"session id:\s*([0-9a-fA-F][0-9a-fA-F-]{34}[0-9a-fA-F])"),
    re.compile(r'"session_id"\s*:\s*"([0-9a-fA-F][0-9a-fA-F-]{34}[0-9a-fA-F])"'),
    re.compile(r"\bsession_id=([0-9a-fA-F][0-9a-fA-F-]{34}[0-9a-fA-F])"),
)


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


def resolve_model(model: Optional[str]) -> Optional[str]:
    if model is None:
        return None
    return MODEL_ALIASES.get(model, model)


def resolve_restrict_tools(
    role: Optional[str],
    restrict_tools: bool,
    allow_write: bool,
    sandbox: Optional[str],
    full_auto: bool,
) -> bool:
    if restrict_tools:
        return True
    if allow_write or full_auto or sandbox:
        return False
    return bool(role) and role not in WRITE_ROLES


def extract_session_id(*streams: str) -> Optional[str]:
    for stream in streams:
        if not stream:
            continue
        for pattern in SESSION_ID_PATTERNS:
            match = pattern.search(stream)
            if match:
                return match.group(1)
    return None


def build_prompt(
    prompt: str,
    prompt_files: Optional[list[str]],
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
    restrict_tools: bool,
) -> dict[str, Any]:
    command = [sys.executable, str(runner_script), "--json", "--disable-fallback"]

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


def run_codex(
    prompt: str,
    timeout: int = 3600,
    working_dir: Optional[str] = None,
    model: Optional[str] = None,
    effort: Optional[str] = None,
    sandbox: Optional[str] = None,
    approval_policy: Optional[str] = None,
    skip_git_repo_check: bool = False,
    prompt_files: Optional[list[str]] = None,
    role: Optional[str] = None,
    session_file: Optional[str] = None,
    metadata_json: Optional[str] = None,
    ephemeral: bool = False,
    output_schema: Optional[str] = None,
    restrict_tools: bool = False,
    allow_write: bool = False,
    full_auto: bool = False,
    resume: Optional[str] = None,
    resume_last: bool = False,
    add_dirs: Optional[list[str]] = None,
    images: Optional[list[str]] = None,
    disable_fallback: bool = False,
) -> dict[str, Any]:
    resuming = bool(resume or resume_last)
    resolved_model = resolve_model(model)
    restrict_effective = resolve_restrict_tools(role, restrict_tools, allow_write, sandbox, full_auto)
    resolved_sandbox = sandbox or ("read-only" if restrict_effective else None)
    command_display = "codex exec resume" if resuming else "codex exec"

    def error_result(message: str, code: int = -3) -> dict[str, Any]:
        return {
            "success": False,
            "stdout": "",
            "stderr": message,
            "return_code": code,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
        }

    if working_dir and not Path(working_dir).is_dir():
        return error_result(f"Working directory does not exist: {working_dir}")

    for prompt_file in prompt_files or []:
        if not Path(prompt_file).is_file():
            return error_result(f"Prompt file does not exist: {prompt_file}")

    if session_file and not Path(session_file).is_file():
        return error_result(f"Session file does not exist: {session_file}")

    if output_schema and not Path(output_schema).is_file():
        return error_result(f"Output schema file does not exist: {output_schema}")

    for image in images or []:
        if not Path(image).is_file():
            return error_result(f"Image file does not exist: {image}")

    if resuming and add_dirs:
        return error_result("--add-dir is not supported by codex exec resume")

    final_prompt = build_prompt(prompt, prompt_files, role, session_file, metadata_json)
    if resuming and not final_prompt.strip():
        final_prompt = DEFAULT_CONTINUE_PROMPT

    if resuming:
        command = ["codex", "exec", "resume"]
        command.append("--last" if resume_last else resume)
    else:
        command = ["codex", "exec"]
        if working_dir:
            command.extend(["--cd", working_dir])

    if resolved_model:
        command.extend(["--model", resolved_model])

    if effort:
        command.extend(["--config", f"model_reasoning_effort={json.dumps(effort)}"])

    if resuming:
        # `codex exec resume` lacks --sandbox/--full-auto/--ask-for-approval; use config overrides.
        if resolved_sandbox:
            command.extend(["--config", f"sandbox_mode={json.dumps(resolved_sandbox)}"])
        elif full_auto:
            command.extend(["--config", 'sandbox_mode="workspace-write"'])
            command.extend(["--config", 'approval_policy="on-failure"'])
        if approval_policy:
            command.extend(["--config", f"approval_policy={json.dumps(approval_policy)}"])
    else:
        if resolved_sandbox:
            command.extend(["--sandbox", resolved_sandbox])
        elif full_auto:
            command.append("--full-auto")
        if approval_policy:
            command.extend(["--ask-for-approval", approval_policy])
        for add_dir in add_dirs or []:
            command.extend(["--add-dir", add_dir])

    for image in images or []:
        command.extend(["--image", image])

    if skip_git_repo_check:
        command.append("--skip-git-repo-check")

    if ephemeral:
        command.append("--ephemeral")

    if output_schema:
        command.extend(["--output-schema", output_schema])

    last_message_fd, last_message_path = tempfile.mkstemp(prefix="codex-last-message-", suffix=".txt")
    os.close(last_message_fd)
    command.extend(["--output-last-message", last_message_path])

    command.append(final_prompt)

    command_display = " ".join(shlex.quote(part) for part in command)

    def read_agent_message() -> Optional[str]:
        try:
            text = Path(last_message_path).read_text(encoding="utf-8").strip()
            return text or None
        except OSError:
            return None

    def cleanup_last_message() -> None:
        try:
            os.unlink(last_message_path)
        except OSError:
            pass

    meta = {
        "command": command_display,
        "working_dir": working_dir or "current directory",
        "runner": "codex",
        "effective_runner": "codex",
        "model": resolved_model,
        "effort": effort,
        "role": role,
        "session_file": session_file,
        "prompt_file": prompt_files[0] if prompt_files and len(prompt_files) == 1 else None,
        "prompt_files": prompt_files,
        "sandbox": resolved_sandbox,
        "ephemeral": ephemeral,
        "output_schema": output_schema,
        "restrict_tools": restrict_effective,
        "full_auto": full_auto,
        "resume": "--last" if resume_last else resume,
    }

    if shutil.which("codex") is None:
        cleanup_last_message()
        if resuming:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Codex CLI not found and --resume requires a Codex session; no fallback is possible.",
                "return_code": -2,
                **meta,
            }
        if not disable_fallback:
            fallback_script = (
                Path(__file__).resolve().parents[2] / "claude-runner" / "scripts" / "run_claude.py"
            )
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
                    restrict_effective,
                )
                fallback_result["fallback_from"] = "codex"
                fallback_result["fallback_reason"] = "Codex CLI not found"
                fallback_result["requested_model"] = model
                fallback_result["fallback_model_forwarded"] = False
                return fallback_result
        return {
            "success": False,
            "stdout": "",
            "stderr": "Codex CLI not found. Check if it is installed and in PATH.",
            "return_code": -2,
            **meta,
        }

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "agent_message": read_agent_message(),
            "session_id": extract_session_id(result.stdout, result.stderr),
            "return_code": result.returncode,
            **meta,
        }

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
            "agent_message": read_agent_message(),
            "session_id": extract_session_id(partial_stdout),
            "return_code": -1,
            **meta,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Codex CLI not found. Check if it is installed and in PATH.",
            "return_code": -2,
            **meta,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "return_code": -3,
            **meta,
        }
    finally:
        cleanup_last_message()


def load_runner_jobs():
    shared_dir = Path(__file__).resolve().parents[2] / "_shared" / "scripts"
    if not (shared_dir / "runner_jobs.py").is_file():
        return None
    sys.path.insert(0, str(shared_dir))
    import runner_jobs

    return runner_jobs


def main():
    parser = argparse.ArgumentParser(
        description="Execute prompts in Codex CLI exec mode"
    )
    parser.add_argument("prompt", nargs="?", default="", help="The prompt to be executed by Codex")
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=3600,
        help="Timeout in seconds (default: 3600)",
    )
    parser.add_argument(
        "--working-dir",
        "-w",
        type=str,
        default=None,
        help="Working directory for execution",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Return output in JSON format"
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Codex model alias (e.g. spark maps to gpt-5.3-codex-spark)",
    )
    parser.add_argument(
        "--effort",
        "-e",
        type=str,
        choices=EFFORT_LEVELS,
        default=None,
        help="Model reasoning effort override",
    )
    parser.add_argument(
        "--sandbox",
        "-s",
        type=str,
        default=None,
        help="Codex sandbox mode override",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Force the Codex read-only sandbox (default for analysis roles)",
    )
    parser.add_argument(
        "--allow-write",
        action="store_true",
        help="Opt an analysis role out of the default read-only sandbox",
    )
    parser.add_argument(
        "--full-auto",
        action="store_true",
        help="Pass Codex full auto mode for an explicitly approved unattended run",
    )
    parser.add_argument(
        "--approval-policy",
        "-a",
        type=str,
        default=None,
        help="Codex approval policy override",
    )
    parser.add_argument(
        "--skip-git-repo-check",
        action="store_true",
        help="Allow running Codex outside a Git repository",
    )
    parser.add_argument(
        "--prompt-file",
        action="append",
        default=None,
        help="Read the prompt body from a file instead of the positional argument (repeatable; files are concatenated in order)",
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
        help="Append prior discussion context from a file for cross-runner continuation",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="SESSION_ID",
        help="Resume a Codex session natively by session id (preferred over --session-file)",
    )
    parser.add_argument(
        "--resume-last",
        action="store_true",
        help="Resume the most recent recorded Codex session",
    )
    parser.add_argument(
        "--metadata-json",
        type=str,
        default=None,
        help="JSON string to embed as execution metadata for downstream parsing",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Run Codex without persisting session files to disk",
    )
    parser.add_argument(
        "--output-schema",
        type=str,
        default=None,
        help="Path to a JSON Schema file describing the final response shape",
    )
    parser.add_argument(
        "--add-dir",
        action="append",
        default=None,
        help="Additional writable directory (repeatable; not supported with --resume)",
    )
    parser.add_argument(
        "--image",
        "-i",
        action="append",
        default=None,
        help="Attach an image file to the prompt (repeatable)",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run as a tracked background job and return a job id immediately",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Do not route to another runner if Codex CLI is unavailable",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write the wrapper JSON result to this file atomically",
    )

    args = parser.parse_args()

    if args.resume and args.resume_last:
        parser.error("Use either --resume SESSION_ID or --resume-last, not both")

    resuming = bool(args.resume or args.resume_last)
    if not args.prompt and not args.prompt_file and not resuming:
        parser.error("Provide a prompt argument, --prompt-file, or --resume/--resume-last")

    if args.background:
        jobs = load_runner_jobs()
        if jobs is None:
            parser.error(
                "--background requires the shared jobs module (_shared/scripts/runner_jobs.py), which was not found"
            )
        prompt_source = args.prompt or (
            f"prompt files: {', '.join(args.prompt_file)}" if args.prompt_file else "(resume)"
        )
        try:
            summary = jobs.launch_background(
                "codex",
                Path(__file__),
                sys.argv[1:],
                working_dir=args.working_dir,
                prompt_excerpt=prompt_source,
                manifest_extra={
                    "role": args.role,
                    "model": resolve_model(args.model),
                    "effort": args.effort,
                    "resume": "--last" if args.resume_last else args.resume,
                },
            )
        except ValueError as exc:
            parser.error(str(exc))
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        sys.exit(0)

    result = run_codex(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model,
        effort=args.effort,
        sandbox=args.sandbox,
        approval_policy=args.approval_policy,
        skip_git_repo_check=args.skip_git_repo_check,
        prompt_files=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        ephemeral=args.ephemeral,
        output_schema=args.output_schema,
        restrict_tools=args.restrict_tools,
        allow_write=args.allow_write,
        full_auto=args.full_auto,
        resume=args.resume,
        resume_last=args.resume_last,
        add_dirs=args.add_dir,
        images=args.image,
        disable_fallback=args.disable_fallback,
    )

    result = normalize_envelope(result, requested_runner="codex", requested_model=args.model)

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
                    },
                    ensure_ascii=False,
                )
            )
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result["success"]:
            print("=== CODEX OUTPUT ===")
            print(result.get("agent_message") or result["stdout"])
            if result.get("session_id"):
                print(f"\n=== SESSION ===\n{result['session_id']}")
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
        if output_file:
            print(f"Result written to {output_file}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
