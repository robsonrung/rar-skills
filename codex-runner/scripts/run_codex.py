#!/usr/bin/env python3
"""Execute prompts in Codex CLI exec mode with role and continuation support."""

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


ROLE_INSTRUCTIONS = {
    "planner": "Act as a planning specialist. Break work into phases, call out risks, and keep the output actionable.",
    "codereviewer": "Act as a rigorous code reviewer. Prioritize correctness, regressions, missing tests, and concrete evidence.",
    "implementer": "Act as an implementation specialist. Make forward progress, explain assumptions briefly, and verify changes where possible.",
    "synthesizer": "Act as a synthesis specialist. Reconcile competing ideas, preserve nuance, and recommend a clear next step.",
    "adversarial": "Act as an adversarial reviewer. Pressure-test assumptions, attack weak reasoning, and surface concrete failure modes with evidence.",
    "challenger": "Act as a constructive challenger. Argue against the leading option, name viable alternatives, and force explicit tradeoff handling.",
    "researcher": "Act as a research specialist. Distinguish facts from inference, gather evidence, and cite sources or concrete artifacts when available.",
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


def invoke_fallback(
    runner_script: Path,
    prompt: str,
    timeout: int,
    working_dir: Optional[str],
    prompt_file: Optional[str],
    role: Optional[str],
    session_file: Optional[str],
    metadata_json: Optional[str],
    restrict_tools: bool,
) -> dict[str, Any]:
    command = [sys.executable, str(runner_script), "--json", "--disable-fallback"]

    if prompt_file:
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
    sandbox: Optional[str] = None,
    approval_policy: Optional[str] = None,
    skip_git_repo_check: bool = False,
    prompt_file: Optional[str] = None,
    role: Optional[str] = None,
    session_file: Optional[str] = None,
    metadata_json: Optional[str] = None,
    ephemeral: bool = False,
    output_schema: Optional[str] = None,
    restrict_tools: bool = False,
    full_auto: bool = False,
    disable_fallback: bool = False,
) -> dict[str, Any]:
    command = ["codex", "exec"]
    command_display = "codex exec"

    if working_dir and not Path(working_dir).is_dir():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Working directory does not exist: {working_dir}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir,
        }

    if prompt_file and not Path(prompt_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Prompt file does not exist: {prompt_file}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
        }

    if session_file and not Path(session_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Session file does not exist: {session_file}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
        }

    if output_schema and not Path(output_schema).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Output schema file does not exist: {output_schema}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or os.getcwd(),
        }

    final_prompt = build_prompt(prompt, prompt_file, role, session_file, metadata_json)
    if working_dir:
        command.extend(["--cd", working_dir])

    if model:
        command.extend(["--model", model])

    resolved_sandbox = sandbox or ("read-only" if restrict_tools else None)
    if resolved_sandbox:
        command.extend(["--sandbox", resolved_sandbox])
    elif full_auto:
        command.append("--full-auto")

    if approval_policy:
        command.extend(["--ask-for-approval", approval_policy])

    if skip_git_repo_check:
        command.append("--skip-git-repo-check")

    if ephemeral:
        command.append("--ephemeral")

    if output_schema:
        command.extend(["--output-schema", output_schema])

    command.append(final_prompt)

    command_display = " ".join(shlex.quote(part) for part in command)

    if shutil.which("codex") is None:
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
                    prompt_file,
                    role,
                    session_file,
                    metadata_json,
                    restrict_tools,
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
            "command": command_display,
            "working_dir": working_dir or "current directory",
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
            "return_code": result.returncode,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "codex",
            "effective_runner": "codex",
            "role": role,
            "session_file": session_file,
            "prompt_file": prompt_file,
            "sandbox": resolved_sandbox,
            "ephemeral": ephemeral,
            "output_schema": output_schema,
            "restrict_tools": restrict_tools,
            "full_auto": full_auto,
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
            "return_code": -1,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "codex",
            "effective_runner": "codex",
            "role": role,
            "sandbox": resolved_sandbox,
            "ephemeral": ephemeral,
            "output_schema": output_schema,
            "restrict_tools": restrict_tools,
            "full_auto": full_auto,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Codex CLI not found. Check if it is installed and in PATH.",
            "return_code": -2,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "codex",
            "effective_runner": "codex",
            "role": role,
            "sandbox": resolved_sandbox,
            "ephemeral": ephemeral,
            "output_schema": output_schema,
            "restrict_tools": restrict_tools,
            "full_auto": full_auto,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Unexpected error: {str(e)}",
            "return_code": -3,
            "command": command_display,
            "working_dir": working_dir or "current directory",
            "runner": "codex",
            "effective_runner": "codex",
            "role": role,
            "sandbox": resolved_sandbox,
            "ephemeral": ephemeral,
            "output_schema": output_schema,
            "restrict_tools": restrict_tools,
            "full_auto": full_auto,
        }


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
        help="Codex model alias",
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
        help="Use Codex read-only sandbox for analysis seats",
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
        type=str,
        default=None,
        help="Read the prompt body from a file instead of the positional argument",
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

    if not args.prompt and not args.prompt_file:
        parser.error("Provide a prompt argument or --prompt-file")

    result = run_codex(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model,
        sandbox=args.sandbox,
        approval_policy=args.approval_policy,
        skip_git_repo_check=args.skip_git_repo_check,
        prompt_file=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        ephemeral=args.ephemeral,
        output_schema=args.output_schema,
        restrict_tools=args.restrict_tools,
        full_auto=args.full_auto,
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
        if output_file:
            print(f"Result written to {output_file}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
