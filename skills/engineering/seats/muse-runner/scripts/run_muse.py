#!/usr/bin/env python3
"""Run one Muse CLI turn with bounded file tools and an explicit model."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

for _root in Path(__file__).resolve().parents:
    if (_root / "shared" / "scripts" / "runner_prompt.py").is_file():
        sys.path.insert(0, str(_root / "shared" / "scripts"))
        break

from model_receipt import attach_model_receipt
from model_routing import load_config, model_efforts, subscription_privacy
from runner_prompt import measured_run, prompt_context, record_input

ROUTING_CONFIG = load_config()
MODEL = ROUTING_CONFIG["models"]["muse-wonder-full"]["model"]
EFFORTS = model_efforts("muse", ROUTING_CONFIG)[MODEL]
VERSION = "1.4.7 (1.4.7-R6101.1)"
READ_TOOLS = ["read_file", "search"]
WRITE_TOOLS = [*READ_TOOLS, "write_file", "edit_file"]
ROLES = ("planner", "codereviewer", "implementer", "synthesizer", "adversarial", "challenger", "researcher")
OVERRIDES = {
    "agents.execution_capacity": 1,
    "run.subagent_delegation_mode": "off",
    "local_session_messaging.enabled": False,
    "feature_config.enabled": False,
    "tools.artifact.enabled": False,
    "telemetry.enabled": False,
}


def normalize_envelope(result, requested_runner="muse", requested_model=MODEL):
    result.setdefault("runner", requested_runner)
    result.setdefault("effective_runner", "muse")
    result.setdefault("effective_provider", "meta")
    result.setdefault("return_code", -3)
    result.setdefault("success", False)
    result.setdefault("auth_ok", None)
    result.setdefault("fallback_reason", None)
    result.setdefault("stdout", "")
    result.setdefault("stderr", "")
    result.setdefault("agent_message", "")
    result.setdefault("model_forwarded", False)
    attach_model_receipt(result, requested_model, observed_source="provider_event")
    return result


STARTUP_SETTING_KEYS = ("hooks", "managed_hooks_path", "managed_plugins_path", "plugins", "mcpServers", "mcp_servers")
# Muse runtime state that a trusted project may hold without adding startup code.
TRUSTED_PROJECT_STATE = {"settings.json", "worktrees", "projects", "lock.json", "feedback"}


def check_startup_settings(settings: Path):
    if not settings.exists():
        return
    value = json.loads(settings.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Muse settings must be a JSON object: {settings}")
    for key in STARTUP_SETTING_KEYS:
        if value.get(key):
            raise ValueError(f"Startup setting {key} in {settings} requires a separate audited configuration.")


def trusted_project(workspace: Path, root: Path):
    """Return the saved trust root that Muse applies to this workspace, if any.

    Muse 1.4.14 checks showed that a trusted workspace, or a folder below one,
    loads project hooks and `.mcp.json` servers at startup; an untrusted one loads
    neither. Any trusted ancestor counts, so a nearer non-trusted entry cannot
    hide one.
    """
    store = root / "trust.json"
    if not store.exists():
        return None
    value = json.loads(store.read_text(encoding="utf-8"))
    projects = value.get("projects") if isinstance(value, dict) else None
    if not isinstance(projects, dict):
        raise ValueError("Muse trust store must hold a projects object.")
    for candidate in dict.fromkeys((workspace, workspace.resolve())):
        for parent in (candidate, *candidate.parents):
            entry = projects.get(str(parent))
            if isinstance(entry, dict) and entry.get("decision") == "trusted":
                return parent
    return None


def check_startup_configuration(workspace: Path):
    """Refuse startup extensions that can run outside the selected tool list."""
    root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "muse"
    check_startup_settings(root / "settings.json")
    trusted = trusted_project(workspace, root)
    for parent in (workspace, *workspace.parents):
        project = parent / ".muse"
        if (project / "hooks.json").exists():
            raise ValueError("Project hooks require a separate audited configuration.")
        if trusted:
            if (parent / ".mcp.json").exists():
                raise ValueError(f"Trusted Muse project {trusted} would start the MCP servers in "
                                 f"{parent / '.mcp.json'}; they require a separate audited configuration.")
            check_startup_settings(project / "settings.json")
            if project.is_dir():
                unknown = sorted(entry.name for entry in project.iterdir() if entry.name not in TRUSTED_PROJECT_STATE)
                if unknown:
                    raise ValueError(f"Trusted Muse project {trusted} has unaudited project configuration in "
                                     f"{project}: {', '.join(unknown)}.")
        if (parent / ".git").exists():
            break
    if os.environ.get("MUSE_PERMISSION_PROFILE_FAIL_OPEN"):
        raise ValueError("Permission profile fail-open is not supported.")


def preflight(cli: str, workspace: Path, effort: str, deadline=None):
    def remaining():
        return min(5, max(0.001, deadline - time.monotonic())) if deadline else 5
    check_startup_configuration(workspace)
    version = subprocess.run([cli, "--version"], capture_output=True, text=True, timeout=remaining(), check=False)
    if version.returncode or version.stdout.strip().removeprefix("Muse Code ") != VERSION:
        raise ValueError(f"This adapter requires Muse CLI {VERSION}.")
    profile = subprocess.run(
        [cli, "model-profile", "show", MODEL, "--effort", effort],
        capture_output=True, text=True, timeout=remaining(), check=False,
    )
    if (profile.returncode
            or not re.search(rf"(?m)^model:\s+{re.escape(MODEL)}\s*$", profile.stdout)
            or not re.search(rf"(?m)^effort:\s+{re.escape(effort)}\s*$", profile.stdout)):
        raise ValueError("Exact model profile did not resolve.")
    return {
        "cli_version": version.stdout.strip(), "profile_resolved": True,
        "model_entitlement": "unknown", "serving_model": "unknown", "zdr": "user_confirmed",
        "privacy_evidence": subscription_privacy(ROUTING_CONFIG),
        "detail": "Local profile resolution does not prove current access. Subscription coverage is user confirmed, not independently verified.",
    }


def command_for(cli, workspace, prompt_file, provider, effort, max_steps, allow_write, allow_shell=False):
    tools = [*(WRITE_TOOLS if allow_write else READ_TOOLS), *(["bash", "bash_input"] if allow_shell else [])]
    command = [
        cli, "exec", "--json", "--provider", provider, "--workspace", str(workspace),
        "--prompt-file", str(prompt_file),
        "--max-model-steps", str(max_steps), "--max-tool-output-bytes", "32768",
        "--approval-mode", "never", "--approval-judge", "off",
        "--sandbox-network", "restricted",
        "--disable-web-tools", "--disable-reminders",
        "--no-foreign-personal-context", "--no-session-log", "--contributor-mode", "off",
        "--worktree", "off",
    ]
    if not allow_shell:
        command.append("--disable-shell")
    if not allow_write:
        command.append("--disable-write")
    if provider == "meta":
        command.extend(["--model", MODEL, "--reasoning-effort", effort, "--no-parallel-tool-calls"])
    for key, value in {**OVERRIDES, "run.toolset": tools, "permissions.schema_version": 1,
                       "permissions.default_profile": ":ask-me" if allow_write else ":read-only"}.items():
        command.extend(["-c", f"{key}={json.dumps(value, separators=(',', ':'))}"])
    return command


def provider_receipts(events, terminal):
    """Bind provider completion evidence to a completed root model task."""
    coverage = {"completed_task_ids": [], "missing_task_ids": [], "complete": False}
    run = terminal.get("run_stream")
    command = terminal.get("command_id")
    if not isinstance(run, dict) or run.get("kind") != "run" or not run.get("id") or not command:
        return [], coverage
    records = [event for event in events if (
        event.get("record_type") == "event" and event.get("durability") == "durable"
        and event.get("payload_schema_version") == 1
        and event["payload"].get("run_stream") == run
        and event["payload"].get("command_id") == command
        and event.get("causation_id") == command
    )]
    if not any(event["payload_type"] == "run.lifecycle.started"
               and event["payload"].get("kind") == "run_started" for event in records):
        return [], coverage
    tasks = {}
    for record in records:
        payload = record["payload"]
        task_id = payload.get("task_id")
        if not isinstance(task_id, str) or payload.get("task_stream") != {"kind": "task", "id": task_id}:
            continue
        task = tasks.setdefault(task_id, {"linked": False, "model": None, "root": False,
                                         "operation": None, "completed": False, "receipts": []})
        if record["payload_type"] == "task.stream.linked" and payload.get("kind") == "task_stream_linked":
            task["linked"] = True
            continue
        event = payload.get("event")
        if (payload.get("kind") != "task_lifecycle" or not isinstance(event, dict)
                or event.get("task_id") != task_id
                or record["payload_type"] != "task.lifecycle." + str(event.get("kind"))):
            continue
        kind = event["kind"]
        if kind == "proposed":
            name = event.get("task_kind")
            task["model"] = name if isinstance(name, str) and name.startswith("model.") and name.endswith(".response") else None
        elif kind == "side_effect_intent":
            task["operation"] = event.get("operation")
            task["root"] = "parent_task_id" in event and event["parent_task_id"] is None
        elif kind == "completed":
            task["completed"] = True
        elif kind == "status":
            details = event.get("details")
            if not isinstance(details, dict) or details.get("phase") != "stream_succeeded":
                continue
            facets = details.get("facets")
            if not isinstance(facets, list):
                raise ValueError("Invalid provider completion facets.")
            for facet in facets:
                if not isinstance(facet, dict) or facet.get("kind") != "producer":
                    continue
                detail = facet.get("detail")
                if not isinstance(detail, dict) or detail.get("kind") != "provider":
                    continue
                stream = detail.get("stream")
                if (detail.get("provider") != "meta" or not isinstance(stream, dict)
                        or stream.get("last_wire_event_type") != "response.completed"):
                    continue
                if not all(isinstance(detail.get(key), str) and detail[key].strip()
                           for key in ("model", "request_id", "response_id")):
                    raise ValueError("Incomplete provider completion identity.")
                if detail["model"] == "<synthetic>":
                    raise ValueError("Synthetic provider model is not serving evidence.")
                task["receipts"].append({"task_id": task_id, "run_id": run["id"],
                                         **{key: detail[key] for key in ("provider", "model", "request_id", "response_id")}})
    completed = {task_id: task for task_id, task in tasks.items()
                 if all(task[key] for key in ("model", "root", "completed"))
                 and task["operation"] == task["model"]}
    for task in completed.values():
        if task["model"] != "model.meta.response":
            task["receipts"] = []
    coverage["completed_task_ids"] = sorted(completed)
    coverage["missing_task_ids"] = sorted(task_id for task_id, task in completed.items()
                                           if not task["linked"] or not task["receipts"])
    coverage["complete"] = bool(completed) and not coverage["missing_task_ids"]
    return ([receipt for task in completed.values() if task["linked"]
             for receipt in task["receipts"]], coverage)


def parse_records(stdout):
    """Accept one completed root turn; never promote labels into model proof."""
    terminals, sessions, events = [], set(), []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict) or event.get("schema_version") != 1:
            raise ValueError("Unsupported Muse record schema.")
        stream, payload = event.get("stream"), event.get("payload")
        if not isinstance(stream, dict) or stream.get("kind") != "session" or not isinstance(payload, dict):
            raise ValueError("Expected a session record with an object payload.")
        if not isinstance(stream.get("id"), str) or not stream["id"]:
            raise ValueError("Missing session identity.")
        sessions.add(stream["id"])
        payload_type = event.get("payload_type")
        if not isinstance(payload_type, str):
            raise ValueError("Missing payload type.")
        events.append(event)
        if payload_type.startswith("run.terminal."):
            if payload.get("kind") != "run_terminal":
                raise ValueError("Invalid terminal record.")
            if payload_type != "run.terminal." + str(payload.get("terminal")):
                raise ValueError("Conflicting terminal status.")
            terminals.append(payload)
    if len(sessions) != 1 or len(terminals) != 1:
        raise ValueError("Expected one session and one terminal record.")
    terminal = terminals[0]
    message = terminal.get("text")
    if message is not None and not isinstance(message, str):
        raise ValueError("Invalid terminal text.")
    receipts, coverage = provider_receipts(events, terminal)
    models = sorted({receipt["model"] for receipt in receipts})
    result = {"session_id": sessions.pop(), "agent_message": message or "",
              "terminal": terminal.get("terminal"), "terminal_reason": terminal.get("reason"),
              "provider_model_receipts": receipts, "primary_model_ids": models,
              "model_receipt_coverage": coverage}
    if len(models) == 1 and coverage["complete"]:
        result["native_model_id"] = models[0]
    return result


def capture(command, workspace, timeout):
    """Stop the process group on timeout or interruption."""
    def terminate(signum, frame):
        raise SystemExit(128 + signum)

    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        return _capture(command, workspace, timeout)
    finally:
        signal.signal(signal.SIGTERM, previous)


def _capture(command, workspace, timeout):
    with subprocess.Popen(command, cwd=workspace, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, start_new_session=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout, stderr, process.returncode
        except BaseException:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            raise


@measured_run
def run_muse(prompt="", *, working_dir=None, prompt_files=None, model=MODEL, effort="high",
             provider="meta", allow_write=False, allow_shell=False, restrict_tools=False, role=None,
             timeout=300, max_steps=20, metadata_json=None, preflight_only=False, require_model_receipt=False):
    result = normalize_envelope({"effective_provider": provider}, requested_model=model)
    deadline = time.monotonic() + timeout
    try:
        if model != MODEL or effort not in EFFORTS:
            raise ValueError("Unsupported exact model or effort.")
        if provider not in ("meta", "echo") or role not in (None, *ROLES):
            raise ValueError("Unsupported provider or role.")
        if timeout <= 0 or max_steps <= 0 or allow_write and restrict_tools or allow_shell and not allow_write:
            raise ValueError("Use positive limits and one tool mode.")
        metadata = json.loads(metadata_json) if metadata_json else {}
        if isinstance(metadata, dict) and "privacy_evidence" in metadata:
            if provider != "meta" or metadata["privacy_evidence"] != subscription_privacy(ROUTING_CONFIG):
                raise ValueError("Approved subscription evidence differs from the loaded account scope.")
        workspace = Path(working_dir or Path.cwd()).expanduser().resolve(strict=True)
        if not workspace.is_dir():
            raise ValueError("Working directory must be a directory.")
        sections = [f"Role: {role}"] if role else []
        if allow_shell:
            sections.append("Complete this task as one worker. Do not start child workers or other model CLIs.")
        context = prompt_context(metadata_json)
        if context:
            sections.append(context)
        if prompt_files:
            for filename in prompt_files:
                path = Path(filename).expanduser()
                sections.append((path if path.is_absolute() else workspace / path).read_text(encoding="utf-8"))
        else:
            sections.append(prompt)
        rendered = "\n\n".join(sections)
        record_input(rendered)
        if not rendered.strip() and not preflight_only:
            raise ValueError("A prompt is required.")
        cli = shutil.which(os.environ.get("MUSE_CLI_PATH", "muse"))
        if not cli:
            result.update(status="seat_unavailable", return_code=-2, stderr="Muse CLI not found.")
            return result
        result["preflight"] = preflight(cli, workspace, effort, deadline)
        result.update(effective_provider=provider, effort=effort if provider == "meta" else None,
                      effort_control="runner" if provider == "meta" else "runtime",
                      configured_model=None,
                      tool_profile="write" if allow_write else "repo_read_only",
                      tool_allowlist=[*(WRITE_TOOLS if allow_write else READ_TOOLS), *(["bash", "bash_input"] if allow_shell else [])],
                      contributor_mode="off", privacy_status="user_confirmed" if provider == "meta" else "not_applicable",
                      privacy_evidence=subscription_privacy(ROUTING_CONFIG) if provider == "meta" else None,
                      resumable=False)
        if preflight_only:
            result.update(success=True, return_code=0, status="preflight_only")
            return normalize_envelope(result, requested_model=model)
        with tempfile.TemporaryDirectory(prefix="muse-runner-") as temporary:
            prompt_file = Path(temporary) / "prompt.txt"
            prompt_file.write_text(rendered, encoding="utf-8")
            command = command_for(cli, workspace, prompt_file, provider, effort, max_steps, allow_write, allow_shell)
            result["model_forwarded"] = provider == "meta"
            result["configured_model"] = MODEL if provider == "meta" else None
            stdout, stderr, return_code = capture(command, workspace, max(0.001, deadline - time.monotonic()))
        result.update(stdout=stdout, stderr=stderr, return_code=return_code)
        if stdout.strip():
            result.update(parse_records(stdout))
        result["success"] = return_code == 0 and result.get("terminal") == "completed"
        result["status"] = "completed" if result["success"] else "failed"
        if result["success"] and provider == "meta":
            result["auth_ok"] = True
        models = result.get("primary_model_ids", [])
        identity_error = ("Multiple primary serving models observed." if len(models) > 1 else
                          "Serving model differs from the requested model." if models and models[0] != model else
                          "Unexpected provider receipt in echo mode." if models and provider == "echo" else None)
        result["model_identity_error"] = identity_error
        if identity_error:
            result.update(success=False, return_code=-3, status="model_mismatch", stderr=identity_error)
        if return_code == 0 and not result["success"] and not identity_error:
            result["return_code"] = -3
            result["stderr"] += "\nMissing successful terminal record."
    except subprocess.TimeoutExpired:
        result.update(success=False, return_code=-1, status="timeout", stderr="Muse operation timed out.")
    except (ValueError, OSError, TypeError) as error:
        result.update(success=False, return_code=-3, status="blocked", stderr=str(error))
    result = normalize_envelope(result, requested_model=model)
    if (require_model_receipt or provider == "meta") and not preflight_only and result["success"] and (
            result["model_receipt"]["status"] != "verified" or result["effective_model"] != model):
        result.update(success=False, return_code=-3, status="model_unverified",
                      stderr="A matching verified serving-model receipt is required.")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt", nargs="?", default="")
    parser.add_argument("--prompt-file", action="append", dest="prompt_files")
    parser.add_argument("--working-dir")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--effort", default="high")
    parser.add_argument("--provider", choices=("meta", "echo"), default="meta")
    parser.add_argument("--role", choices=ROLES)
    parser.add_argument("--allow-write", action="store_true")
    parser.add_argument("--allow-shell", action="store_true", help="Allow sandboxed test commands; requires --allow-write.")
    parser.add_argument("--restrict-tools", action="store_true")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--metadata-json")
    parser.add_argument("--preflight", action="store_true", dest="preflight_only")
    parser.add_argument("--require-model-receipt", action="store_true")
    parser.add_argument("--background", action="store_true")
    parser.add_argument("--disable-fallback", action="store_true", help="Compatibility flag; fallback is always disabled.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output-file")
    args = vars(parser.parse_args())
    background = args.pop("background")
    as_json, output_file = args.pop("json"), args.pop("output_file")
    args.pop("disable_fallback")
    if background:
        from runner_jobs import launch_background
        try:
            if args["preflight_only"]:
                raise ValueError("Preflight must run in the foreground.")
            summary = launch_background("muse", Path(__file__), sys.argv[1:],
                                        working_dir=args["working_dir"], prompt_excerpt=args["prompt"],
                                        manifest_extra={"model": args["model"], "resumable": False})
        except (ValueError, OSError) as error:
            result = normalize_envelope({"stderr": str(error), "print_invocation_started": False})
            print(json.dumps(result))
            return 1
        print(json.dumps(summary))
        return 0
    result = run_muse(**args)
    if output_file:
        target = Path(output_file).expanduser().absolute()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, encoding="utf-8") as handle:
                json.dump(result, handle, indent=2)
                temporary = Path(handle.name)
            temporary.replace(target)
            result = {key: result.get(key) for key in (
                "success", "return_code", "runner", "effective_runner", "effective_provider", "fallback_from", "status")}
            result["output_file"] = str(target)
        except OSError as error:
            result.update(success=False, return_code=-3, stderr=str(error))
    print(json.dumps(result, indent=2) if as_json else result.get("agent_message") or result.get("stderr") or result.get("status"))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
