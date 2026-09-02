#!/usr/bin/env python3
"""Write and inspect immutable structured replies for a peer-session fleet."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_STATUSES = {"done", "blocked", "failed"}
REQUIRED_REPLY_KEYS = {"peer", "status", "summary", "evidence", "next_step", "created_at", "authority_claim"}


class UsageError(ValueError):
    """Raised for a recoverable mailbox contract violation."""


def timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def run_directory(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    state = load_json(path / "state.json", "fleet state")
    if state.get("schema_version") != 1 or not isinstance(state.get("peers"), list):
        raise UsageError(f"fleet state has an unsupported schema: {path / 'state.json'}")
    return path


def peer_ids(run_dir: Path) -> set[str]:
    state = load_json(run_dir / "state.json", "fleet state")
    result = {item.get("id") for item in state["peers"] if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(result) != len(state["peers"]):
        raise UsageError("fleet state has an invalid peer roster")
    return result


def validate_reply(value: dict[str, Any], expected_peer: str) -> list[str]:
    errors: list[str] = []
    missing = REQUIRED_REPLY_KEYS - value.keys()
    if missing:
        errors.append(f"missing keys: {', '.join(sorted(missing))}")
    if value.get("peer") != expected_peer:
        errors.append(f"peer must equal {expected_peer!r}")
    if value.get("status") not in VALID_STATUSES:
        errors.append("status must be done, blocked, or failed")
    for key in ("summary", "next_step", "created_at", "authority_claim"):
        if not isinstance(value.get(key), str) or not value.get(key).strip():
            errors.append(f"{key} must be a non-empty string")
    if not isinstance(value.get("evidence"), list) or not value["evidence"] or not all(isinstance(item, str) and item for item in value["evidence"]):
        errors.append("evidence must be a non-empty list of strings")
    if value.get("authority_claim") != "none":
        errors.append("authority_claim must be none")
    return errors


def atomic_write(path: Path, value: dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary.replace(path)


def same_reply(existing: dict[str, Any], candidate: dict[str, Any]) -> bool:
    return all(existing.get(key) == candidate.get(key) for key in candidate if key != "created_at")


def deadline_expired(run_dir: Path) -> bool:
    state = load_json(run_dir / "state.json", "fleet state")
    raw = state.get("deadline")
    if raw is None:
        return False
    if not isinstance(raw, str):
        raise UsageError("fleet deadline must be a string or null")
    try:
        deadline = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UsageError("fleet deadline is not a valid ISO-8601 timestamp") from exc
    return datetime.now(UTC) >= deadline.astimezone(UTC)


def reply(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_directory(args.run_dir)
    if args.peer not in peer_ids(run_dir):
        raise UsageError(f"peer is not in this fleet: {args.peer}")
    value = {
        "peer": args.peer,
        "status": args.status,
        "summary": args.summary,
        "evidence": args.evidence,
        "next_step": args.next_step,
        "created_at": timestamp(),
        "authority_claim": "none",
    }
    errors = validate_reply(value, args.peer)
    if errors:
        raise UsageError("; ".join(errors))
    path = run_dir / "replies" / f"{args.peer}.json"
    if path.exists():
        current = load_json(path, "existing reply")
        if same_reply(current, value):
            return {"reply_path": str(path), "result": "unchanged"}
        if not args.replace:
            raise UsageError(f"reply already exists: {path}; use --replace only for an explicit correction")
    if args.dry_run:
        return {"reply_path": str(path), "result": "planned", "reply": value}
    atomic_write(path, value)
    return {"reply_path": str(path), "result": "written"}


def status(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = run_directory(args.run_dir)
    fleet = load_json(run_dir / "state.json", "fleet state")
    if fleet.get("delivery_mode") == "coordinator":
        raise UsageError("mailbox status is unavailable for delivery_mode coordinator; use the composing skill's artifact protocol")
    statuses = []
    for peer in sorted(peer_ids(run_dir)):
        path = run_dir / "replies" / f"{peer}.json"
        if not path.exists():
            statuses.append({"peer": peer, "status": "missing", "reply_path": str(path)})
            continue
        try:
            value = load_json(path, "reply")
            errors = validate_reply(value, peer)
        except UsageError as exc:
            statuses.append({"peer": peer, "status": "invalid", "reply_path": str(path), "errors": [str(exc)]})
            continue
        if errors:
            statuses.append({"peer": peer, "status": "invalid", "reply_path": str(path), "errors": errors})
        else:
            statuses.append({"peer": peer, "status": value["status"], "reply_path": str(path)})
    terminal = {item["status"] for item in statuses}
    expired = deadline_expired(run_dir)
    if expired:
        overall = "deadline_expired"
    elif terminal == {"done"}:
        overall = "complete"
    elif "blocked" in terminal or "failed" in terminal:
        overall = "needs_direction"
    else:
        overall = "waiting"
    return {"run_dir": str(run_dir), "overall_status": overall, "deadline_expired": expired, "peers": statuses}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    write = subparsers.add_parser("reply", help="write one peer reply")
    write.add_argument("--run-dir", required=True)
    write.add_argument("--peer", required=True)
    write.add_argument("--status", required=True, choices=sorted(VALID_STATUSES))
    write.add_argument("--summary", required=True)
    write.add_argument("--evidence", action="append", required=True)
    write.add_argument("--next-step", required=True)
    write.add_argument("--replace", action="store_true")
    write.add_argument("--dry-run", action="store_true")
    inspect = subparsers.add_parser("status", help="validate every expected peer reply")
    inspect.add_argument("--run-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])
        result = reply(args) if args.command == "reply" else status(args)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
