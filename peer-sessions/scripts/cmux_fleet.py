#!/usr/bin/env python3
"""Launch peer sessions in cmux from a validated manifest."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


UUID = re.compile(r"^[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$")
TERMINAL_STATE_SCHEMA = 1
TERMINAL_STATE_OWNER = "peer-sessions.cmux_fleet"


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


def surface_ids(raw: str) -> list[str]:
    """Parse `cmux list-pane-surfaces --id-format uuids` rows into surface ids.

    Rows look like `* <uuid>  <title>  [selected]`; the leading marker flags the
    selected tab and is not part of the id.
    """
    found: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip().lstrip("*").strip()
        if not stripped:
            continue
        token = stripped.split()[0]
        if UUID.fullmatch(token):
            found.append(token)
    return found


def created_surface(before: list[str], after: list[str]) -> str:
    created = [surface for surface in after if surface not in before]
    if len(created) != 1:
        raise UsageError("cmux new-surface did not create exactly one visible tab")
    return created[0]


def caller_surface(cmux_bin: str, explicit: str | None) -> str:
    """Resolve the surface the fleet splits away from — the caller's own pane."""
    if explicit:
        return explicit
    env = os.environ.get("CMUX_SURFACE_ID")
    if env:
        return env
    identify = json.loads(invoke([cmux_bin, "identify", "--json"]).stdout)
    ref = identify.get("caller", {}).get("surface_ref")
    if not isinstance(ref, str):
        raise UsageError("cmux identify did not report a caller surface to split from")
    return ref


def split_plan(count: int, direction: str) -> list[str]:
    """Directions for each successive split.

    `auto` alternates right/down so panes tile toward a grid instead of
    shaving ever-thinner columns off one edge.
    """
    if direction != "auto":
        return [direction] * count
    return ["right" if index % 2 == 0 else "down" for index in range(count)]


def target_workspace(explicit: str | None) -> str:
    """Resolve the workspace that will hold the peer tabs.

    Defaults to the caller's own workspace so the fleet appears as tabs beside
    the coordinator rather than scattered across new workspaces.
    """
    workspace = explicit or os.environ.get("CMUX_WORKSPACE_ID")
    if not workspace:
        raise UsageError("no target workspace: pass --workspace or run inside a cmux workspace")
    return workspace


def plan(
    peers: list[dict[str, Any]],
    cmux_bin: str,
    surface_mode: str,
    workspace: str | None,
    direction: str = "auto",
) -> list[list[str]]:
    result: list[list[str]] = []
    headings = split_plan(len(peers), direction)
    for index, peer in enumerate(peers):
        if surface_mode == "split":
            target = workspace or "<current-workspace>"
            anchor = "<caller-surface>" if index == 0 else "<previous-split>"
            result.extend([
                [cmux_bin, "list-pane-surfaces", "--workspace", target, "--id-format", "uuids"],
                [cmux_bin, "new-split", headings[index], "--workspace", target, "--surface", anchor, "--focus", "false"],
                [cmux_bin, "list-pane-surfaces", "--workspace", target, "--id-format", "uuids"],
                [cmux_bin, "rename-tab", "--surface", "<new-split>", peer["id"]],
                [cmux_bin, "send", "--surface", "<new-split>", launch_command(peer)],
                [cmux_bin, "send-key", "--surface", "<new-split>", "enter"],
                [cmux_bin, "send", "--surface", "<new-split>", f"Read the brief file for {peer['id']} and follow it."],
                [cmux_bin, "send-key", "--surface", "<new-split>", "enter"],
            ])
            continue
        if surface_mode == "tab":
            target = workspace or "<current-workspace>"
            result.extend([
                [cmux_bin, "list-pane-surfaces", "--workspace", target, "--id-format", "uuids"],
                [cmux_bin, "new-surface", "--type", "terminal", "--workspace", target, "--focus", "false"],
                [cmux_bin, "list-pane-surfaces", "--workspace", target, "--id-format", "uuids"],
                [cmux_bin, "rename-tab", "--surface", "<new-surface>", peer["id"]],
                [cmux_bin, "send", "--surface", "<new-surface>", launch_command(peer)],
                [cmux_bin, "send-key", "--surface", "<new-surface>", "enter"],
                [cmux_bin, "send", "--surface", "<new-surface>", f"Read the brief file for {peer['id']} and follow it."],
                [cmux_bin, "send-key", "--surface", "<new-surface>", "enter"],
            ])
            continue
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


def terminal_state(surface_mode: str, run_dir: Path, terminals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": TERMINAL_STATE_SCHEMA,
        "created_by": TERMINAL_STATE_OWNER,
        "run_dir": str(run_dir),
        "transport": "cmux",
        "surface_mode": surface_mode,
        "terminals": terminals,
    }


def validate_terminal_state(value: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    if value.get("schema_version") != TERMINAL_STATE_SCHEMA or value.get("created_by") != TERMINAL_STATE_OWNER:
        raise UsageError("terminal state was not created by this peer-sessions launcher")
    if value.get("transport") != "cmux":
        raise UsageError("terminal state must use cmux transport")
    surface_mode = value.get("surface_mode")
    if surface_mode not in {"split", "tab", "workspace"}:
        raise UsageError("terminal state has an unsupported surface mode")
    raw_terminals = value.get("terminals")
    if not isinstance(raw_terminals, list) or not raw_terminals:
        raise UsageError("terminal state has no peer terminals")
    terminals: list[dict[str, str]] = []
    seen_surfaces: set[str] = set()
    for raw in raw_terminals:
        if not isinstance(raw, dict):
            raise UsageError("each terminal state entry must be an object")
        peer = raw.get("peer")
        workspace = raw.get("workspace_id")
        surface = raw.get("surface_id")
        if not all(isinstance(value, str) and value for value in (peer, workspace, surface)):
            raise UsageError("each terminal state entry needs peer, workspace_id, and surface_id")
        if surface in seen_surfaces:
            raise UsageError("terminal state surface ids must be unique")
        seen_surfaces.add(surface)
        terminals.append({"peer": peer, "workspace_id": workspace, "surface_id": surface})
    return surface_mode, terminals


def teardown_plan(state: dict[str, Any], cmux_bin: str = "cmux") -> list[list[str]]:
    surface_mode, terminals = validate_terminal_state(state)
    if surface_mode == "workspace":
        workspaces = list(dict.fromkeys(terminal["workspace_id"] for terminal in terminals))
        return [[cmux_bin, "close-workspace", "--workspace", workspace] for workspace in workspaces]
    return [
        [cmux_bin, "close-surface", "--workspace", terminal["workspace_id"], "--surface", terminal["surface_id"]]
        for terminal in terminals
    ]


def run_teardown_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise UsageError(f"cmux executable not found: {command[0]}") from exc


def remaining_terminals(state: dict[str, Any], cmux_bin: str) -> list[dict[str, str]]:
    surface_mode, terminals = validate_terminal_state(state)
    if surface_mode == "workspace":
        live_workspaces = workspace_ids(invoke([cmux_bin, "list-workspaces", "--json"]).stdout)
        return [terminal for terminal in terminals if terminal["workspace_id"] in live_workspaces]
    remaining: list[dict[str, str]] = []
    for workspace in dict.fromkeys(terminal["workspace_id"] for terminal in terminals):
        live_surfaces = set(
            surface_ids(invoke([cmux_bin, "list-pane-surfaces", "--workspace", workspace, "--id-format", "uuids"]).stdout)
        )
        remaining.extend(
            terminal for terminal in terminals
            if terminal["workspace_id"] == workspace and terminal["surface_id"] in live_surfaces
        )
    return remaining


def teardown(state: dict[str, Any], cmux_bin: str = "cmux") -> dict[str, Any]:
    commands = teardown_plan(state, cmux_bin)
    attempts = []
    for command in commands:
        result = run_teardown_command(command)
        attempts.append(
            {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            }
        )
    remaining = remaining_terminals(state, cmux_bin)
    closed = all(attempt["return_code"] == 0 for attempt in attempts) and not remaining
    state["teardown"] = {"success": closed, "attempts": attempts, "remaining": remaining}
    return state


def start_splits(
    run_dir: Path,
    peers: list[dict[str, Any]],
    cmux_bin: str,
    workspace: str,
    anchor: str,
    direction: str,
) -> dict[str, Any]:
    """Split the caller's pane once per peer so the whole fleet shares one screen.

    Each split anchors on the previously created pane, so the panes tile instead
    of repeatedly halving the coordinator's own pane. As in tab mode, every send
    is addressed with an explicit `--surface`.
    """
    listing = [cmux_bin, "list-pane-surfaces", "--workspace", workspace, "--id-format", "uuids"]
    terminals = []
    for peer, heading in zip(peers, split_plan(len(peers), direction)):
        before = surface_ids(invoke(listing).stdout)
        invoke([cmux_bin, "new-split", heading, "--workspace", workspace, "--surface", anchor, "--focus", "false"])
        surface = created_surface(before, surface_ids(invoke(listing).stdout))
        invoke([cmux_bin, "rename-tab", "--surface", surface, peer["id"]])
        invoke([cmux_bin, "send", "--surface", surface, launch_command(peer)])
        invoke([cmux_bin, "send-key", "--surface", surface, "enter"])
        prompt = f"Read {run_dir / 'briefs' / (peer['id'] + '.md')} and follow it."
        invoke([cmux_bin, "send", "--surface", surface, prompt])
        invoke([cmux_bin, "send-key", "--surface", surface, "enter"])
        terminals.append({"peer": peer["id"], "workspace_id": workspace, "surface_id": surface, "split": heading})
        anchor = surface
    return terminal_state("split", run_dir, terminals)


def start_tabs(run_dir: Path, peers: list[dict[str, Any]], cmux_bin: str, workspace: str) -> dict[str, Any]:
    """Open one tab per peer inside an existing workspace.

    Every send is addressed with an explicit `--surface`, so a peer's brief can
    never land in the coordinator's own tab if focus moves mid-launch.
    """
    listing = [cmux_bin, "list-pane-surfaces", "--workspace", workspace, "--id-format", "uuids"]
    terminals = []
    for peer in peers:
        before = surface_ids(invoke(listing).stdout)
        invoke([cmux_bin, "new-surface", "--type", "terminal", "--workspace", workspace, "--focus", "false"])
        surface = created_surface(before, surface_ids(invoke(listing).stdout))
        invoke([cmux_bin, "rename-tab", "--surface", surface, peer["id"]])
        invoke([cmux_bin, "send", "--surface", surface, launch_command(peer)])
        invoke([cmux_bin, "send-key", "--surface", surface, "enter"])
        prompt = f"Read {run_dir / 'briefs' / (peer['id'] + '.md')} and follow it."
        invoke([cmux_bin, "send", "--surface", surface, prompt])
        invoke([cmux_bin, "send-key", "--surface", surface, "enter"])
        terminals.append({"peer": peer["id"], "workspace_id": workspace, "surface_id": surface})
    return terminal_state("tab", run_dir, terminals)


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
    return terminal_state("workspace", run_dir, terminals)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmux-bin", default="cmux")
    subparsers = parser.add_subparsers(dest="command", required=True)
    launch = subparsers.add_parser("start", help="open one cmux terminal for each peer")
    launch.add_argument("--manifest", required=True)
    launch.add_argument("--state-file")
    launch.add_argument(
        "--surface-mode",
        choices=("split", "tab", "workspace"),
        default="split",
        help="split: tile every peer beside the caller on one screen (default); tab: one tab per peer; workspace: one new workspace per peer",
    )
    launch.add_argument("--workspace", help="split/tab modes; defaults to the caller's CMUX_WORKSPACE_ID")
    launch.add_argument("--anchor-surface", help="split mode only; the surface to split from, defaults to CMUX_SURFACE_ID")
    launch.add_argument(
        "--split-direction",
        choices=("auto", "left", "right", "up", "down"),
        default="auto",
        help="split mode only; auto alternates right/down so panes tile toward a grid",
    )
    launch.add_argument("--dry-run", action="store_true")
    close = subparsers.add_parser("teardown", help="close only the peer surfaces or workspaces in a launcher state file")
    close.add_argument("--state-file", required=True)
    close.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])
        if args.command == "teardown":
            state_path = absolute_path(args.state_file, "state file")
            state = load_json(state_path, "terminal state")
            if args.dry_run:
                result: dict[str, Any] = {"dry_run": True, "plan": teardown_plan(state, args.cmux_bin)}
                exit_code = 0
            else:
                result = teardown(state, args.cmux_bin)
                write_json(state_path, result)
                exit_code = 0 if result["teardown"]["success"] else 1
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return exit_code
        if not args.dry_run and not args.state_file:
            raise UsageError("--state-file is required so the peer fleet can close only its own terminals")
        manifest = load_json(Path(args.manifest).expanduser(), "manifest")
        run_dir, peers = validate_manifest(manifest)
        in_workspace = args.surface_mode in ("split", "tab")
        workspace = target_workspace(args.workspace) if in_workspace and not args.dry_run else args.workspace
        if args.dry_run:
            result = {
                "run_dir": str(run_dir),
                "transport": "cmux",
                "surface_mode": args.surface_mode,
                "dry_run": True,
                "plan": plan(peers, args.cmux_bin, args.surface_mode, workspace, args.split_direction),
            }
        elif args.surface_mode == "split":
            anchor = caller_surface(args.cmux_bin, args.anchor_surface)
            result = start_splits(run_dir, peers, args.cmux_bin, workspace, anchor, args.split_direction)
        elif args.surface_mode == "tab":
            result = start_tabs(run_dir, peers, args.cmux_bin, workspace)
        else:
            result = start(run_dir, peers, args.cmux_bin)
        if args.state_file and not args.dry_run:
            write_json(absolute_path(args.state_file, "state file"), result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (UsageError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
