#!/usr/bin/env python3
"""Adopt an approved cmux peer fleet and relay council artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SESSION_PREFIX = "consensus-"
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class UsageError(ValueError):
    """Raised for an invalid or unsafe cmux council operation."""


def require_token(value: str, label: str) -> str:
    if not isinstance(value, str) or not SAFE_TOKEN.fullmatch(value):
        raise UsageError(f"{label} must contain only letters, numbers, dot, underscore, colon, or hyphen")
    return value


def session_name(session_id: str) -> str:
    return f"{SESSION_PREFIX}{require_token(session_id, 'session id')}"


def require_fingerprint(value: str, label: str) -> str:
    if not isinstance(value, str) or not FINGERPRINT.fullmatch(value):
        raise UsageError(f"{label} must be a SHA-256 fingerprint")
    return value


def validate_model_receipt(value: Any, requested_model: str, label: str) -> str:
    if not isinstance(value, dict):
        raise UsageError(f"{label} must contain a model receipt")
    status = value.get("status")
    source = value.get("source")
    observed_model = value.get("observed_model")
    if status not in {"verified", "unverified"}:
        raise UsageError(f"{label} model receipt must state verified or unverified")
    if source not in {"native_event", "provider_event", "configured_model", "not_observed"}:
        raise UsageError(f"{label} model receipt has an unknown source")
    if status == "verified":
        if source not in {"native_event", "provider_event"}:
            raise UsageError(f"{label} verified receipt must use a native or provider source")
        if observed_model != requested_model:
            raise UsageError(f"{label} verified model differs from the approved requested model")
    elif source not in {"configured_model", "not_observed"} or observed_model is not None:
        raise UsageError(f"{label} unverified receipt must not claim an observed model")
    return status


def selected_seat_ids(preview: dict[str, Any]) -> list[str]:
    seats = preview.get("seats")
    if not isinstance(seats, list) or not seats:
        raise UsageError("approval preview must name at least one seat")
    selected: list[str] = []
    for entry in seats:
        if not isinstance(entry, dict):
            raise UsageError("each approved seat must be an object")
        seat_id = require_token(entry.get("id"), "approved seat id")
        requested_model = entry.get("requested_model")
        provider = entry.get("provider")
        if not isinstance(requested_model, str) or not requested_model:
            raise UsageError(f"approved seat {seat_id} must name its requested model")
        if not isinstance(provider, str) or not provider:
            raise UsageError(f"approved seat {seat_id} must name its provider")
        validate_model_receipt(entry.get("model_receipt"), requested_model, f"approved seat {seat_id}")
        if seat_id in selected:
            raise UsageError("approval preview seat ids must be unique")
        selected.append(seat_id)
    return selected


def approved_seat_models(preview: dict[str, Any]) -> dict[str, str]:
    selected_seat_ids(preview)
    return {entry["id"]: entry["requested_model"] for entry in preview["seats"]}


def validate_effort(value: Any, control: Any, label: str) -> tuple[str | None, str]:
    if control == "runtime":
        if value is not None:
            raise UsageError(f"{label} must be null when effort control is runtime")
        return None, control
    if control == "configured":
        if not isinstance(value, str) or not value:
            raise UsageError(f"{label} must name configured effort")
        return value, control
    raise UsageError(f"{label} must state configured or runtime effort control")


def validate_role_scope(preview: dict[str, Any]) -> None:
    seat_models = approved_seat_models(preview)
    receipt_requirement = preview.get("serving_receipt")
    if receipt_requirement not in {"required", "explicitly_allowed_unverified"}:
        raise UsageError("approval preview must state its serving-receipt requirement")
    if receipt_requirement == "required" and any(
        entry["model_receipt"]["status"] != "verified" for entry in preview["seats"]
    ):
        raise UsageError("approval preview requires verified serving-model receipts")
    roles = preview.get("roles")
    if not isinstance(roles, list) or not roles:
        raise UsageError("approval preview must contain at least one role")
    calls: dict[str, tuple[str | None, str]] = {}
    for entry in roles:
        if not isinstance(entry, dict):
            raise UsageError("each approved role must be an object")
        call = require_token(entry.get("call"), "approved role call")
        role = entry.get("role")
        seat = require_token(entry.get("seat"), "approved role seat")
        model = entry.get("requested_model")
        effort = entry.get("effort")
        effort_control = entry.get("effort_control")
        if not isinstance(role, str) or not role:
            raise UsageError(f"approved role {call} must name its role")
        if seat not in seat_models:
            raise UsageError(f"approved role {call} names an unselected seat")
        if model != seat_models[seat]:
            raise UsageError(f"approved role {call} requested model does not match its seat")
        if call in calls:
            raise UsageError("approved role calls must be unique")
        calls[call] = validate_effort(effort, effort_control, f"approved role {call} effort")

    effort_entries = preview.get("effort")
    if not isinstance(effort_entries, list) or not effort_entries:
        raise UsageError("approval preview must contain effort for every role call")
    recorded_effort: dict[str, tuple[str | None, str]] = {}
    for entry in effort_entries:
        if not isinstance(entry, dict):
            raise UsageError("each effort entry must be an object")
        call = require_token(entry.get("call"), "effort call")
        effort = entry.get("effort")
        effort_control = entry.get("effort_control")
        if call in recorded_effort:
            raise UsageError("effort calls must be unique")
        recorded_effort[call] = validate_effort(effort, effort_control, f"effort entry {call}")
    if recorded_effort != calls:
        raise UsageError("effort entries must exactly match the approved role calls")


def approval_scope_payload(state: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(state, dict):
        raise UsageError("approval state must be a JSON object")
    session_id = require_token(state.get("session_id"), "approval session id")
    question = state.get("question")
    mode = state.get("mode")
    preview = state.get("preview")
    if not isinstance(question, str) or not question:
        raise UsageError("approval state must contain a question")
    if not isinstance(mode, str) or not mode:
        raise UsageError("approval state must contain a mode")
    if not isinstance(preview, dict):
        raise UsageError("approval state must contain a preview object")
    if preview.get("transport") != "cmux":
        raise UsageError("approval preview transport must be cmux")
    validate_role_scope(preview)
    try:
        normalized_preview = json.loads(json.dumps(preview, ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise UsageError(f"approval preview is not JSON serializable: {exc}") from exc
    normalized_preview.pop("scope_fingerprint", None)
    return {
        "session_id": session_id,
        "question": question,
        "mode": mode,
        "preview": normalized_preview,
    }


def approval_scope_fingerprint(state: dict[str, Any]) -> str:
    payload = approval_scope_payload(state)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def approved_plan(state: dict[str, Any], expected_session_id: str | None = None) -> tuple[str, str, list[str]]:
    payload = approval_scope_payload(state)
    if expected_session_id is not None and payload["session_id"] != require_token(expected_session_id, "session id"):
        raise UsageError("approval state belongs to a different session")
    preview = state["preview"]
    expected = approval_scope_fingerprint(state)
    preview_fingerprint = require_fingerprint(preview.get("scope_fingerprint"), "approval preview fingerprint")
    if preview_fingerprint != expected:
        raise UsageError("approval preview fingerprint does not match its scope")
    approval = state.get("approval")
    if not isinstance(approval, dict) or approval.get("status") != "approved":
        raise UsageError("council plan is not approved")
    approval_fingerprint = require_fingerprint(approval.get("scope_fingerprint"), "approval fingerprint")
    if approval_fingerprint != expected:
        raise UsageError("approval fingerprint does not match the preview scope")
    return payload["session_id"], expected, selected_seat_ids(preview)


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


def dispatch_plan(plan: Sequence[list[str]]) -> None:
    for command in plan:
        run_cmux(command, check=True)


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
        "model_receipt": {
            "status": "unverified",
            "source": "not_observed",
            "observed_model": None,
        },
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


def load_approved_plan(path: str) -> tuple[dict[str, Any], str, str, list[str]]:
    state = load_json(path, "approval state")
    if not isinstance(state, dict):
        raise UsageError("approval state must be a JSON object")
    session_id, fingerprint, seats = approved_plan(state)
    return state, session_id, fingerprint, seats


def adopt_peer_fleet(
    session_id: str,
    peer_run: str,
    terminal_state: str,
    expected_seats: Sequence[str],
) -> dict[str, Any]:
    """Normalize a peer-sessions terminal record into council seat state."""
    session = session_name(session_id)
    run_dir = Path(peer_run).expanduser().resolve()
    fleet = load_json(str(run_dir / "state.json"), "peer fleet state")
    if not isinstance(fleet, dict) or fleet.get("schema_version") != 1:
        raise UsageError("peer fleet state has an unsupported schema")
    if fleet.get("delivery_mode") != "coordinator":
        raise UsageError("peer fleet must use delivery_mode coordinator")
    peers = fleet.get("peers")
    if not isinstance(peers, list) or not peers:
        raise UsageError("peer fleet state has no peer roster")
    roster = {require_token(peer.get("id"), "peer id") for peer in peers if isinstance(peer, dict)}
    if len(roster) != len(peers):
        raise UsageError("peer fleet state has an invalid peer roster")
    expected = {require_token(seat, "expected seat id") for seat in expected_seats}
    if not expected or len(expected) != len(expected_seats):
        raise UsageError("expected seat ids must be non-empty and unique")
    if roster != expected:
        raise UsageError("peer fleet roster does not match the selected council seats")

    terminals = load_json(terminal_state, "peer terminal state")
    if not isinstance(terminals, dict) or terminals.get("transport") != "cmux":
        raise UsageError("peer terminal state must use cmux transport")
    recorded_run = terminals.get("run_dir")
    if not isinstance(recorded_run, str) or Path(recorded_run).expanduser().resolve() != run_dir:
        raise UsageError("peer terminal state belongs to a different fleet run")
    records = terminals.get("terminals")
    if not isinstance(records, list) or not records:
        raise UsageError("peer terminal state has no terminal records")

    adopted: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise UsageError("each peer terminal record must be an object")
        peer = require_token(record.get("peer"), "peer id")
        if peer not in roster or peer in seen:
            raise UsageError("peer terminal records must map one-to-one to the fleet roster")
        seen.add(peer)
        adopted.append(
            {
                "id": peer,
                "workspace_id": require_token(record.get("workspace_id"), "workspace id"),
                "surface_id": require_token(record.get("surface_id"), "surface id"),
                "execution_path": "cmux_interactive",
                "receipt_status": "unverified_terminal",
            }
        )
    if seen != roster:
        raise UsageError("peer terminal records do not cover the complete fleet roster")
    return {
        "session": session,
        "session_id": session_id,
        "transport": "cmux_interactive",
        "fleet_run_dir": str(run_dir),
        "seats": sorted(adopted, key=lambda seat: seat["id"]),
    }


def adopt_approved_peer_fleet(
    approval_state: str,
    peer_run: str,
    terminal_state: str,
) -> dict[str, Any]:
    _, session_id, fingerprint, seats = load_approved_plan(approval_state)
    adopted = adopt_peer_fleet(session_id, peer_run, terminal_state, seats)
    adopted["approval_scope_fingerprint"] = fingerprint
    adopted["approved_seats"] = sorted(seats)
    return adopted


def approved_surface(approval_state: str, adopted_state: str, seat_id: str) -> str:
    _, session_id, fingerprint, selected_seats = load_approved_plan(approval_state)
    seat = require_token(seat_id, "approved seat id")
    if seat not in selected_seats:
        raise UsageError("seat is not in the approved council plan")

    adopted = load_json(adopted_state, "adopted state")
    if not isinstance(adopted, dict):
        raise UsageError("adopted state must be a JSON object")
    if adopted.get("session_id") != session_id:
        raise UsageError("adopted state belongs to a different council session")
    if adopted.get("transport") != "cmux_interactive":
        raise UsageError("adopted state must use cmux interactive transport")
    if adopted.get("approval_scope_fingerprint") != fingerprint:
        raise UsageError("adopted state does not match the approved council plan")

    approved_seats = adopted.get("approved_seats")
    if not isinstance(approved_seats, list):
        raise UsageError("adopted state has no approved seat roster")
    adopted_roster = sorted(require_token(value, "adopted approved seat id") for value in approved_seats)
    if adopted_roster != sorted(selected_seats):
        raise UsageError("adopted state roster does not match the approved council plan")

    records = adopted.get("seats")
    if not isinstance(records, list):
        raise UsageError("adopted state has no terminal records")
    recorded_ids = [require_token(record.get("id"), "adopted seat id") for record in records if isinstance(record, dict)]
    if len(recorded_ids) != len(records) or sorted(recorded_ids) != sorted(selected_seats):
        raise UsageError("adopted terminal records do not match the approved council roster")
    matches = [record for record in records if isinstance(record, dict) and record.get("id") == seat]
    if len(matches) != 1:
        raise UsageError("adopted state must record exactly one surface for the approved seat")
    return require_token(matches[0].get("surface_id"), "approved surface id")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cmux-bin", default="cmux")
    subparsers = parser.add_subparsers(dest="command", required=True)
    fingerprint = subparsers.add_parser("fingerprint", help="calculate an approval-preview scope fingerprint")
    fingerprint.add_argument("--approval-state", required=True)
    adopt = subparsers.add_parser("adopt", help="adopt a coordinator-mode peer-sessions cmux fleet")
    adopt.add_argument("--approval-state", required=True)
    adopt.add_argument("--peer-run", required=True)
    adopt.add_argument("--terminal-state", required=True)
    adopt.add_argument("--state-file", required=True)
    send = subparsers.add_parser("send", help="send one literal message to an approved recorded surface")
    send.add_argument("--approval-state", required=True)
    send.add_argument("--adopted-state", required=True)
    send.add_argument("--seat", required=True)
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
        if args.command == "fingerprint":
            state = load_json(args.approval_state, "approval state")
            if not isinstance(state, dict):
                raise UsageError("approval state must be a JSON object")
            print(json.dumps({"scope_fingerprint": approval_scope_fingerprint(state)}, indent=2, ensure_ascii=False))
        elif args.command == "adopt":
            result = adopt_approved_peer_fleet(args.approval_state, args.peer_run, args.terminal_state)
            atomic_write_json(Path(args.state_file).expanduser(), result)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif args.command == "send":
            try:
                message = Path(args.message_file).expanduser().read_text(encoding="utf-8")
            except FileNotFoundError as exc:
                raise UsageError(f"message file not found: {args.message_file}") from exc
            surface = approved_surface(args.approval_state, args.adopted_state, args.seat)
            plan = build_send_plan(surface, message, args.cmux_bin)
            if not args.dry_run:
                dispatch_plan(plan)
            print(json.dumps({"seat": args.seat, "surface": surface, "plan": plan}, indent=2, ensure_ascii=False))
        elif args.command == "collect":
            print(json.dumps(collect_artifact(args.seat, args.round, Path(args.output_file)), indent=2, ensure_ascii=False))
        return 0
    except (UsageError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
