#!/usr/bin/env python3
"""Create a bounded peer-session ledger and individual brief files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PEER_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class UsageError(ValueError):
    """Raised for a recoverable input or filesystem contract violation."""


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_deadline(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise UsageError("deadline must be an ISO-8601 timestamp, for example 2026-08-08T18:00:00Z") from exc
    if parsed.tzinfo is None:
        raise UsageError("deadline must include a timezone, for example 2026-08-08T18:00:00Z")
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    temporary.replace(path)


def parse_peer(value: str) -> tuple[str, Path]:
    peer, separator, raw_path = value.partition(":")
    if not separator or not PEER_ID.fullmatch(peer):
        raise UsageError("peer must have the form lower-case-name:/absolute/working/directory")
    workdir = Path(raw_path).expanduser()
    if not workdir.is_absolute() or not workdir.is_dir():
        raise UsageError(f"peer {peer} working directory must be an existing absolute directory: {raw_path}")
    return peer, workdir.resolve()


def brief(
    run_dir: Path,
    peer: str,
    objective: str,
    workdir: Path,
    deadline: str | None,
    delivery_mode: str,
) -> str:
    deadline_text = deadline or "No deadline declared. Stop at the first blocking authority question."
    if delivery_mode == "mailbox":
        delivery = f"""Read `{run_dir / 'state.json'}` for the fleet record. Write exactly one reply through:

```bash
python3 <peer-sessions-dir>/scripts/peer_mailbox.py reply --run-dir {run_dir} --peer {peer} --status done --summary \"<result>\" --evidence \"<path or command>\" --next-step \"<next action>\"
```

Your reply path is `{run_dir / 'replies' / f'{peer}.json'}`. Report `blocked` or `failed` rather than guessing. Do not replace an existing reply unless your coordinator explicitly asks for a correction."""
    else:
        delivery = f"""Read `{run_dir / 'state.json'}` for the fleet record. This fleet uses coordinator-managed artifacts. Wait for the coordinator's terminal prompt and write only the artifact it names.

Do not write `{run_dir / 'replies' / f'{peer}.json'}` and do not send a result to another peer. Report a permission denial or blocking condition in the requested artifact rather than guessing."""
    return f"""# Brief for {peer}

## Objective

{objective}

## Scope

Work from `{workdir}`. Do not act outside the user authority available in your own session.

## Delivery

{delivery}

## Deadline

{deadline_text}
"""


def initialize(args: argparse.Namespace) -> dict[str, Any]:
    run_dir = Path(args.run_dir).expanduser()
    if not run_dir.is_absolute():
        run_dir = (Path.cwd() / run_dir).resolve()
    if run_dir.exists():
        raise UsageError(f"run directory already exists: {run_dir}")
    if not args.objective.strip():
        raise UsageError("objective must not be empty")
    parsed = [parse_peer(value) for value in args.peer]
    peer_ids = [peer for peer, _ in parsed]
    if len(peer_ids) != len(set(peer_ids)):
        raise UsageError("peer names must be unique")
    deadline = parse_deadline(args.deadline)
    state = {
        "schema_version": 1,
        "status": "active",
        "created_at": now(),
        "objective": args.objective,
        "deadline": deadline,
        "delivery_mode": args.delivery_mode,
        "peers": [
            {"id": peer, "workdir": str(workdir), "brief": f"briefs/{peer}.md", "reply": f"replies/{peer}.json"}
            for peer, workdir in parsed
        ],
    }
    result = {"run_dir": str(run_dir), "state_path": str(run_dir / "state.json"), "peers": peer_ids, "dry_run": args.dry_run}
    if args.dry_run:
        return result
    (run_dir / "briefs").mkdir(parents=True)
    (run_dir / "replies").mkdir()
    write_json(run_dir / "state.json", state)
    for peer, workdir in parsed:
        (run_dir / "briefs" / f"{peer}.md").write_text(
            brief(run_dir, peer, args.objective, workdir, deadline, args.delivery_mode), encoding="utf-8"
        )
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    init = subparsers.add_parser("init", help="create a new run directory and briefs")
    init.add_argument("--run-dir", required=True)
    init.add_argument("--objective", required=True)
    init.add_argument("--peer", action="append", required=True, help="lower-case-name:/absolute/working/directory")
    init.add_argument("--deadline", help="ISO-8601 timestamp with timezone")
    init.add_argument(
        "--delivery-mode",
        choices=("mailbox", "coordinator"),
        default="mailbox",
        help="mailbox: peer_mailbox.py reply; coordinator: a composing skill owns response artifacts",
    )
    init.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv if argv is not None else sys.argv[1:])
        print(json.dumps(initialize(args), indent=2, ensure_ascii=False))
        return 0
    except UsageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
