#!/usr/bin/env python3
"""Launch peer sessions in cmux from a validated manifest."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class UsageError(ValueError):
    """Raised for a recoverable terminal-fleet contract violation."""


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UsageError(f"{label} not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UsageError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise UsageError(f"{label} must be a JSON object: {path}")
    return value


def absolute_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise UsageError(f"{label} must be a non-empty absolute path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise UsageError(f"{label} must be absolute: {value}")
    return path.resolve()


def validate_manifest(value: dict[str, Any]) -> tuple[Path, list[dict[str, Any]]]:
    run_dir = absolute_path(value.get("run_dir", ""), "manifest.run_dir")
    state = load_json(run_dir / "state.json", "fleet state")
    roster = {item.get("id") for item in state.get("peers", []) if isinstance(item, dict)}
    peers = value.get("peers")
    if not isinstance(peers, list) or not peers:
        raise UsageError("manifest.peers must be a non-empty array")
    prepared = []
    ids = set()
    for item in peers:
        if not isinstance(item, dict):
            raise UsageError("each manifest peer must be an object")
        peer_id = item.get("id")
        command = item.get("command")
        cwd = item.get("cwd")
        if not isinstance(peer_id, str) or peer_id not in roster or peer_id in ids:
            raise UsageError("each manifest peer id must be a unique id from the fleet roster")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) and part for part in command):
            raise UsageError(f"peer {peer_id} command must be a non-empty argv array")
        if "--print" in command:
            raise UsageError(f"peer {peer_id} command must be interactive, not --print")
        workdir = absolute_path(cwd, f"peer {peer_id} cwd")
        if not workdir.is_dir():
            raise UsageError(f"peer {peer_id} cwd is not a directory: {workdir}")
        ids.add(peer_id)
        prepared.append({"id": peer_id, "cwd": str(workdir), "command": command})
    if ids != roster:
        raise UsageError("manifest must launch every peer in the fleet roster")
    return run_dir, prepared


def workspace_ids(raw: str) -> set[str]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"cmux list-workspaces did not return JSON: {exc}") from exc
    entries = value.get("workspaces") if isinstance(value, dict) else None
    if not isinstance(entries, list):
        raise UsageError("cmux list-workspaces JSON has no workspaces array")
    ids = {item.get("id") for item in entries if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(ids) != len(entries):
        raise UsageError("cmux list-workspaces JSON has an entry without an id")
    return ids


def new_workspace(before: str, after: str) -> str:
    created = workspace_ids(after) - workspace_ids(before)
    if len(created) != 1:
        raise UsageError("cmux new-workspace did not create exactly one visible workspace")
    return created.pop()


def surface_id(raw: str) -> str:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UsageError(f"cmux identify did not return JSON: {exc}") from exc
    surface = value.get("surface_id") if isinstance(value, dict) else None
    if not isinstance(surface, str):
        surface = value.get("surface", {}).get("id") if isinstance(value, dict) and isinstance(value.get("surface"), dict) else None
    if not isinstance(surface, str):
        raise UsageError("cmux identify did not provide a focused surface id")
    return surface


def plan(peers: list[dict[str, Any]], cmux_bin: str) -> list[list[str]]:
    result: list[list[str]] = []
    for peer in peers:
        result.extend([
            [cmux_bin, "list-workspaces", "--json"],
            [cmux_bin, "new-workspace"],
            [cmux_bin, "list-workspaces", "--json"],
            [cmux_bin, "select-workspace", "--workspace", "<new-workspace>"],
            [cmux_bin, "identify", "--json"],
            [cmux_bin, "send", launch_command(peer)],
            [cmux_bin, "send-key", "enter"],
            [cmux_bin, "send", f"Read the brief file for {peer['id']} and follow it."],
            [cmux_bin, "send-key", "enter"],
        ])
    return result


def launch_command(peer: dict[str, Any]) -> str:
    return f"cd {shlex.quote(peer['cwd'])} && {shlex.join(peer['command'])}"


def invoke(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise UsageError(f"cmux executable not found: {command[0]}") from exc


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary.replace(path)


def start(run_dir: Path, peers: list[dict[str, Any]], cmux_bin: str) -> dict[str, Any]:
    terminals = []
    for peer in peers:
        before = invoke([cmux_bin, "list-workspaces", "--json"])
        invoke([cmux_bin, "new-workspace"])
        after = invoke([cmux_bin, "list-workspaces", "--json"])
        workspace = new_workspace(before.stdout, after.stdout)
        invoke([cmux_bin, "select-workspace", "--workspace", workspace])
        identify = invoke([cmux_bin, "identify", "--json"])
        surface = surface_id(identify.stdout)
        invoke([cmux_bin, "send", launch_command(peer)])
        invoke([cmux_bin, "send-key", "enter"])
        prompt = f"Read {run_dir / 'briefs' / (peer['id'] + '.md')} and follow it."
        invoke([cmux_bin, "send", prompt])
        invoke([cmux_bin, "send-key", "enter"])
        terminals.append({"peer": peer["id"], "workspace_id": workspace, "surface_id": surface})
    return {"run_dir": str(run_dir), "transport": "cmux", "terminals": terminals}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmux-bin", default="cmux")
    subparsers = parser.add_subparsers(dest="command", required=True)
    launch = subparsers.add_parser("start", help="create one cmux workspace for each peer")
    launch.add_argument("--manifest", required=True)
    launch.add_argument("--state-file")
    launch.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])
        manifest = load_json(Path(args.manifest).expanduser(), "manifest")
        run_dir, peers = validate_manifest(manifest)
        if args.dry_run:
            result = {"run_dir": str(run_dir), "transport": "cmux", "dry_run": True, "plan": plan(peers, args.cmux_bin)}
        else:
            result = start(run_dir, peers, args.cmux_bin)
            if args.state_file:
                write_json(absolute_path(args.state_file, "state file"), result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (UsageError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
