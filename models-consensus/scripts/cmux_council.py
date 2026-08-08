#!/usr/bin/env python3
"""Interactive cmux transport for models-consensus.

Creates one cmux workspace per terminal agent, sends literal input to the
recorded surface, and collects the agent's JSON artifact. cmux does not expose
terminal output capture, so artifacts are the response channel.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


SESSION_PREFIX = "consensus-"
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")


class UsageError(ValueError):
    """Raised for an invalid or unsafe cmux council operation."""


def require_token(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_TOKEN.fullmatch(value):
        raise UsageError(f"{label} must contain only letters, numbers, dot, underscore, colon, or hyphen")
    return value


def session_name(session_id: str) -> str:
    return f"{SESSION_PREFIX}{require_token(session_id, 'session id')}"


def require_interactive_command(command: Sequence[str]) -> None:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise UsageError("each seat command must be a non-empty argv array")
    binary = Path(command[0]).name
    args = set(command[1:])
    if binary == "claude" and ({"-p", "--print"} & args):
        raise UsageError("claude command must be interactive, not --print")
    if binary == "codex" and "exec" in args:
        raise UsageError("codex command must be interactive, not codex exec")
    if binary == "grok" and ({"-p", "--single", "agent"} & args):
        raise UsageError("grok command must be interactive, not single-turn or agent mode")
    if binary == "cline":
        if "--tui" not in args:
            raise UsageError("cline command must include --tui for interactive mode")
        if {"--json", "--acp", "--zen"} & args:
            raise UsageError("cline command must be interactive, not JSON, ACP, or Zen mode")
    if binary == "agy":
        if "--prompt-interactive" not in args:
            raise UsageError("agy command must include --prompt-interactive")
        if {"-p", "--print", "--prompt"} & args:
            raise UsageError("agy command must be interactive, not print mode")


def validate_manifest(manifest: dict[str, Any]) -> tuple[str, Path, list[dict[str, Any]]]:
    if not isinstance(manifest, dict):
        raise UsageError("manifest must be a JSON object")
    session_id = manifest.get("session_id")
    workspace = manifest.get("workspace")
    seats = manifest.get("seats")
    session_name(session_id)
    if not isinstance(workspace, str) or not workspace:
        raise UsageError("manifest.workspace must be a non-empty path")
    if not isinstance(seats, list) or not seats:
        raise UsageError("manifest.seats must be a non-empty array")
    normalized: list[dict[str, Any]] = []
    seat_ids: set[str] = set()
    for seat in seats:
        if not isinstance(seat, dict):
            raise UsageError("each manifest seat must be an object")
        seat_id = require_token(seat.get("id"), "seat id")
        if seat_id in seat_ids:
            raise UsageError("manifest seat ids must be unique")
        seat_ids.add(seat_id)
        command = seat.get("command")
        if not isinstance(command, list):
            raise UsageError(f"seat {seat_id} command must be an argv array")
        require_interactive_command(command)
        normalized.append({"id": seat_id, "command": list(command)})
    return session_id, Path(workspace).expanduser(), normalized


def build_start_plan(manifest: dict[str, Any], cmux_bin: str = "cmux") -> list[list[str]]:
    _, _, seats = validate_manifest(manifest)
    plan: list[list[str]] = []
    for seat in seats:
        plan.extend(
            [
                [cmux_bin, "list-workspaces", "--json"],
                [cmux_bin, "new-workspace"],
                [cmux_bin, "list-workspaces", "--json"],
                [cmux_bin, "select-workspace", "--workspace", "<new-workspace>"],
                [cmux_bin, "identify", "--json"],
                [cmux_bin, "send", shlex.join(seat["command"])],
                [cmux_bin, "send-key", "enter"],
            ]
        )
    return plan


def build_send_plan(surface_id: str, message: str, cmux_bin: str = "cmux") -> list[list[str]]:
    if not isinstance(message, str) or not message:
        raise UsageError("message must be non-empty")
    surface = require_token(surface_id, "surface id")
    return [
        [cmux_bin, "send", "--surface", surface, message],
        [cmux_bin, "send-key", "--surface", surface, "enter"],
    ]


def run_cmux(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, capture_output=True, text=True, check=check)
    except FileNotFoundError as exc:
        raise UsageError(f"cmux executable not found: {command[0]}") from exc


def parse_identify(raw: str) -> dict[str, str | None]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"cmux identify did not return valid JSON: {exc}") from exc

    def entity_id(entity: str) -> str | None:
        direct = payload.get(f"{entity}_id") if isinstance(payload, dict) else None
        if isinstance(direct, str):
            return direct
        nested = payload.get(entity) if isinstance(payload, dict) else None
        if isinstance(nested, dict) and isinstance(nested.get("id"), str):
            return nested["id"]
        return None

    return {"workspace_id": entity_id("workspace"), "surface_id": entity_id("surface")}


def workspace_ids(raw: str) -> set[str]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"cmux list-workspaces did not return valid JSON: {exc}") from exc
    entries = payload.get("workspaces") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise UsageError("cmux list-workspaces JSON has no workspaces array")
    ids = {entry.get("id") for entry in entries if isinstance(entry, dict) and isinstance(entry.get("id"), str)}
    if len(ids) != len(entries):
        raise UsageError("cmux list-workspaces JSON contains a workspace without an id")
    return ids


def new_workspace_id(before: str, after: str) -> str:
    created = workspace_ids(after) - workspace_ids(before)
    if len(created) != 1:
        raise UsageError("cmux new-workspace must create exactly one discoverable workspace")
    return created.pop()


def start_session(manifest: dict[str, Any], cmux_bin: str = "cmux") -> dict[str, Any]:
    session_id, workspace, seats = validate_manifest(manifest)
    if not workspace.is_dir():
        raise UsageError(f"workspace does not exist or is not a directory: {workspace}")
    state: dict[str, Any] = {
        "session_id": session_id,
        "transport": "cmux_interactive",
        "workspace": str(workspace),
        "seats": [],
    }
    for seat in seats:
        before = run_cmux([cmux_bin, "list-workspaces", "--json"], check=True)
        run_cmux([cmux_bin, "new-workspace"], check=True)
        after = run_cmux([cmux_bin, "list-workspaces", "--json"], check=True)
        workspace_id = new_workspace_id(before.stdout, after.stdout)
        run_cmux([cmux_bin, "select-workspace", "--workspace", workspace_id], check=True)
        identify = run_cmux([cmux_bin, "identify", "--json"], check=True)
        context = parse_identify(identify.stdout)
        if not context["surface_id"]:
            raise UsageError("cmux identify did not provide a focused surface id")
        if context["workspace_id"] != workspace_id:
            raise UsageError("cmux focused workspace differs from the newly created workspace")
        run_cmux([cmux_bin, "send", shlex.join(seat["command"])], check=True)
        run_cmux([cmux_bin, "send-key", "enter"], check=True)
        state["seats"].append({"id": seat["id"], **context})
    return state


def send_message(surface_id: str, message: str, cmux_bin: str = "cmux") -> list[list[str]]:
    plan = build_send_plan(surface_id, message, cmux_bin=cmux_bin)
    for command in plan:
        run_cmux(command, check=True)
    return plan


def collect_artifact(seat: str, round_number: int, output_path: Path) -> dict[str, Any]:
    if round_number < 1:
        raise UsageError("round must be at least 1")
    path = Path(output_path).expanduser()
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise UsageError(f"terminal response artifact not found: {path}") from exc
    try:
        json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"terminal response artifact is not valid JSON: {exc}") from exc
    return {
        "runner": "terminal",
        "effective_runner": "cmux",
        "effective_provider": None,
        "effective_model": None,
        "auth_ok": None,
        "fallback_reason": None,
        "success": True,
        "return_code": 0,
        "status": "artifact_captured",
        "execution_path": "cmux_interactive",
        "receipt_status": "unverified_terminal",
        "seat": require_token(seat, "seat id"),
        "round": round_number,
        "agent_message": raw,
        "artifact_path": str(path),
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    try:
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def load_json(path: str, label: str) -> Any:
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UsageError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UsageError(f"{label} is not valid JSON: {exc}") from exc


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmux-bin", default="cmux")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start", help="create a cmux workspace for each interactive seat")
    start.add_argument("--manifest", required=True)
    start.add_argument("--state-file")
    start.add_argument("--dry-run", action="store_true")
    send = subparsers.add_parser("send", help="send one literal message to a recorded surface")
    send.add_argument("--surface", required=True)
    send.add_argument("--message-file", required=True)
    send.add_argument("--dry-run", action="store_true")
    collect = subparsers.add_parser("collect", help="read one JSON response artifact")
    collect.add_argument("--seat", required=True)
    collect.add_argument("--round", type=int, required=True)
    collect.add_argument("--output-file", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])
        if args.command == "start":
            manifest = load_json(args.manifest, "manifest")
            plan = build_start_plan(manifest, args.cmux_bin)
            if args.dry_run:
                result: dict[str, Any] = {"session": session_name(manifest["session_id"]), "plan": plan}
            else:
                result = start_session(manifest, args.cmux_bin)
                result["session"] = session_name(manifest["session_id"])
                if args.state_file:
                    atomic_write_json(Path(args.state_file).expanduser(), result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.command == "send":
            try:
                message = Path(args.message_file).expanduser().read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise UsageError(f"message file not found: {args.message_file}") from exc
            plan = build_send_plan(args.surface, message, args.cmux_bin)
            if not args.dry_run:
                send_message(args.surface, message, args.cmux_bin)
            print(json.dumps({"surface": args.surface, "plan": plan}, indent=2, ensure_ascii=False))
        elif args.command == "collect":
            print(json.dumps(collect_artifact(args.seat, args.round, Path(args.output_file)), indent=2, ensure_ascii=False))
        return 0
    except (UsageError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
