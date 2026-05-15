#!/usr/bin/env python3
"""Execute prompts via Qwen Code CLI in headless mode."""

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


DEFAULT_MODEL = "qwen3.6-plus"
DEFAULT_RUNNER = "qwen"
DEFAULT_OUTPUT_FORMAT = "stream-json"
DEFAULT_INPUT_FORMAT = "text"
DEFAULT_APPROVAL_MODE = "yolo"

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


def normalize_prompt_files(prompt_files: list[str] | None) -> list[str]:
    return [str(Path(path).expanduser()) for path in (prompt_files or [])]


def parse_sandbox_flag(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None

    value = raw_value.strip().lower()
    if value in {"", "false", "0", "off", "no", "none"}:
        return "false"

    # Preserve headless execution while allowing callers to pass Codex-style
    # sandbox names such as read-only or workspace-write.
    return "true"


def inspect_native_stream(stdout: str) -> tuple[Any, str | None]:
    result_payload = None
    native_error = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(event, dict):
            continue

        if event.get("type") == "assistant":
            message = event.get("message") or {}
            for item in message.get("content", []):
                if item.get("type") == "text":
                    text = item.get("text", "")
                    if isinstance(text, str) and text.startswith("[API Error:"):
                        native_error = text

        if event.get("type") == "result":
            result_payload = event.get("result")
            if event.get("is_error") is True and native_error is None:
                native_error = (
                    result_payload
                    if isinstance(result_payload, str)
                    else json.dumps(result_payload, ensure_ascii=False)
                )

    if native_error is None and isinstance(result_payload, str) and result_payload.startswith("[API Error:"):
        native_error = result_payload

    return result_payload, native_error


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


def run_qwen(
    prompt: str,
    timeout: int = 3600,
    working_dir: str | None = None,
    model: str | None = None,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    input_format: str = DEFAULT_INPUT_FORMAT,
    approval_mode: str = DEFAULT_APPROVAL_MODE,
    prompt_files: list[str] | None = None,
    role: str | None = None,
    session_file: str | None = None,
    metadata_json: str | None = None,
    output_schema: str | None = None,
    sandbox: str | None = None,
    restrict_tools: bool = False,
    disable_fallback: bool = False,
    no_session_persistence: bool = False,
    ephemeral: bool = False,
    safe: bool = False,
    bare: bool = False,
    runner_name: str = DEFAULT_RUNNER,
) -> dict[str, Any]:
    del disable_fallback
    del safe
    del bare

    prompt_files = normalize_prompt_files(prompt_files)
    model = model or DEFAULT_MODEL
    cwd = working_dir or os.getcwd()

    if working_dir and not Path(working_dir).is_dir():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Working directory does not exist: {working_dir}",
            "return_code": -3,
            "command": "qwen",
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": runner_name,
        }

    for prompt_file in prompt_files:
        if not Path(prompt_file).is_file():
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Prompt file does not exist: {prompt_file}",
                "return_code": -3,
                "command": "qwen",
                "working_dir": cwd,
                "model": model,
                "runner": runner_name,
                "effective_runner": runner_name,
            }

    if session_file and not Path(session_file).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Session file does not exist: {session_file}",
            "return_code": -3,
            "command": "qwen",
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": runner_name,
        }

    if output_schema and not Path(output_schema).is_file():
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Output schema file does not exist: {output_schema}",
            "return_code": -3,
            "command": "qwen",
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": runner_name,
        }

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
        return {
            "success": False,
            "stdout": "",
            "stderr": "Provide a prompt argument or at least one --prompt-file",
            "return_code": -3,
            "command": "qwen",
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": runner_name,
        }

    command = [
        "qwen",
        "--model",
        model,
        "--output-format",
        output_format,
        "--input-format",
        input_format,
        "--approval-mode",
        approval_mode,
        "--channel",
        "CI",
        "--chat-recording=false",
    ]

    sandbox_flag = parse_sandbox_flag(sandbox)
    if sandbox_flag is not None:
        command.append(f"--sandbox={sandbox_flag}")

    command.append(final_prompt)
    command_display = " ".join(shlex.quote(part) for part in command)

    if shutil.which("qwen") is None:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Qwen CLI not found. Check if it is installed and in PATH.",
            "return_code": -2,
            "command": command_display,
            "working_dir": cwd,
            "model": model,
            "runner": runner_name,
            "effective_runner": runner_name,
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
        "input_format": input_format,
        "approval_mode": approval_mode,
        "runner": runner_name,
        "effective_runner": runner_name,
        "role": role,
        "session_file": session_file,
        "restrict_tools": restrict_tools,
        "ephemeral": ephemeral,
        "chat_recording": False,
    }

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
            timeout=timeout,
        )
        result["stdout"] = process.stdout
        result["stderr"] = process.stderr
        result["return_code"] = process.returncode
        result["success"] = process.returncode == 0
        native_result, native_error = inspect_native_stream(process.stdout)
        if native_result is not None:
            result["native_result"] = native_result
        if native_error:
            result["success"] = False
            result["stderr"] = (
                f"{process.stderr.rstrip()}\n{native_error}".strip()
                if process.stderr
                else native_error
            )
            if result["return_code"] == 0:
                result["return_code"] = -3

    except subprocess.TimeoutExpired as exc:
        result["stderr"] = f"Timeout expired after {timeout} seconds"
        result["stdout"] = (
            exc.stdout
            if isinstance(exc.stdout, str)
            else (exc.stdout.decode("utf-8", errors="replace") if exc.stdout else "")
        )
        result["return_code"] = -1

    except FileNotFoundError:
        result["stderr"] = "Qwen CLI not found. Check if it is installed and in PATH."
        result["return_code"] = -2

    except Exception as exc:
        result["stderr"] = f"Unexpected error: {exc}"
        result["return_code"] = -3

    return result


def build_parser(default_model: str, description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is 2+2?"
  %(prog)s --prompt-file /tmp/brief.md --prompt-file /tmp/stance.md --role codereviewer
  %(prog)s "Return JSON only" --output-format json --json
  %(prog)s "Read-only architecture review" --restrict-tools --model qwen3.6-plus
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
        help=f"Qwen CLI model to use (default: {default_model})",
    )
    parser.add_argument(
        "--output-format",
        "-o",
        type=str,
        choices=["text", "json", "stream-json"],
        default=DEFAULT_OUTPUT_FORMAT,
        help=f"Qwen CLI output format (default: {DEFAULT_OUTPUT_FORMAT})",
    )
    parser.add_argument(
        "--input-format",
        type=str,
        choices=["text", "stream-json"],
        default=DEFAULT_INPUT_FORMAT,
        help=f"Qwen CLI stdin format (default: {DEFAULT_INPUT_FORMAT})",
    )
    parser.add_argument(
        "--approval-mode",
        type=str,
        choices=["plan", "default", "auto-edit", "yolo"],
        default=DEFAULT_APPROVAL_MODE,
        help=f"Approval mode for headless execution (default: {DEFAULT_APPROVAL_MODE})",
    )
    parser.add_argument(
        "--sandbox",
        "-s",
        type=str,
        default=None,
        help="Pass a truthy or falsy sandbox hint through to Qwen CLI",
    )
    parser.add_argument(
        "--restrict-tools",
        action="store_true",
        help="Add a read-only analysis overlay to the prompt",
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
        help="Append a JSON Schema file to the prompt as an output contract",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Compatibility alias for disabling chat recording",
    )
    parser.add_argument(
        "--no-session-persistence",
        action="store_true",
        help="Disable chat recording for this run",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Compatibility flag accepted for runner parity",
    )
    parser.add_argument(
        "--bare",
        action="store_true",
        help="Compatibility flag accepted for runner parity",
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help="Accepted for runner parity. Qwen-backed runners never fall back to another provider.",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Write the wrapper JSON result to this file atomically",
    )

    return parser


def main(
    default_model: str = DEFAULT_MODEL,
    runner_name: str = DEFAULT_RUNNER,
    description: str | None = None,
) -> None:
    parser = build_parser(
        default_model=default_model,
        description=description or "Execute prompts using Qwen CLI in headless mode.",
    )
    args = parser.parse_args()

    result = run_qwen(
        prompt=args.prompt,
        timeout=args.timeout,
        working_dir=args.working_dir,
        model=args.model or default_model,
        output_format=args.output_format,
        input_format=args.input_format,
        approval_mode=args.approval_mode,
        prompt_files=args.prompt_file,
        role=args.role,
        session_file=args.session_file,
        metadata_json=args.metadata_json,
        output_schema=args.output_schema,
        sandbox=args.sandbox,
        restrict_tools=args.restrict_tools,
        disable_fallback=args.disable_fallback,
        no_session_persistence=args.no_session_persistence,
        ephemeral=args.ephemeral,
        safe=args.safe,
        bare=args.bare,
        runner_name=runner_name,
    )

    result = normalize_envelope(result, requested_runner=runner_name, requested_model=args.model or default_model)

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
        if result["stdout"]:
            print(result["stdout"], end="")
        if result["stderr"]:
            print(result["stderr"], file=sys.stderr)
        if output_file:
            print(f"Result written to {output_file}")

    sys.exit(result["return_code"] if result["return_code"] >= 0 else 1)


if __name__ == "__main__":
    main()
