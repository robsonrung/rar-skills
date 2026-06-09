#!/usr/bin/env python3
"""Create a unique mission control workspace and ledger."""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:72] or "codex-mission"


def resolve_root(root: str, workspace: Path) -> Path:
    candidate = Path(root).expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate.resolve()


def ledger_template(title: str, mission_id: str, run_dir: Path) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    handoffs_dir = run_dir / "handoffs"
    reports_dir = run_dir / "worker-reports"
    return f"""# Codex Mission Control Ledger

## Mission

Title: {title}
Mission id: {mission_id}
Created at: {created_at}
Run directory: {run_dir}
Handoffs directory: {handoffs_dir}
Worker reports directory: {reports_dir}

## Goal

Capture the mission goal here in one sentence.

## Constraints

Record user instructions, repo instructions, safety boundaries, branch state, and non goals.

## Runtime Preflight

| Capability | Status | Evidence | Notes |
| --- | --- | --- | --- |
| native subagent tools | unknown | pending | record tool_search or direct tool visibility |
| thread creation tool | unknown | pending | record host capability or handoff fallback |

## Workstreams

| Workstream | Owner | Status | Scope | Notes |
| --- | --- | --- | --- | --- |
| manager | manager | active | coordination and integration | replace with actual workstreams |

## Thread Registry

| Workstream | Thread id | Environment | Prompt or handoff | Status |
| --- | --- | --- | --- | --- |

## Subagents

| Workstream | Agent id | Role | Scope | Status |
| --- | --- | --- | --- | --- |

## Handoffs

| Workstream | Path | Target | Status |
| --- | --- | --- | --- |

## Decisions

| Time | Decision | Reason |
| --- | --- | --- |

## Integration Notes

Track compact summaries from workers here. Link to reports instead of pasting long logs.

## Verification

| Check | Command or method | Result | Notes |
| --- | --- | --- | --- |

## Final Summary

Record the final user facing summary, unresolved risks, and follow up threads.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a unique Codex mission directory with a uniquely named ledger."
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Short human readable task title used to derive the run slug.",
    )
    parser.add_argument(
        "--root",
        default="work/codex-missions",
        help="Root directory for mission runs. Relative paths resolve from --workspace.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace used to resolve relative roots. Defaults to current directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the paths that would be created without writing files.",
    )
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    root = resolve_root(args.root, workspace)
    task_slug = slugify(args.title)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = secrets.token_hex(3)
    mission_id = f"{timestamp}-{task_slug}-{suffix}"
    run_dir = root / task_slug / mission_id
    handoffs_dir = run_dir / "handoffs"
    reports_dir = run_dir / "worker-reports"
    ledger_path = run_dir / f"mission-{mission_id}.md"

    result = {
        "mission_id": mission_id,
        "task_slug": task_slug,
        "run_dir": str(run_dir),
        "ledger_path": str(ledger_path),
        "handoffs_dir": str(handoffs_dir),
        "worker_reports_dir": str(reports_dir),
        "dry_run": args.dry_run,
    }

    if args.dry_run:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    try:
        handoffs_dir.mkdir(parents=True, exist_ok=False)
        reports_dir.mkdir(parents=True, exist_ok=False)
        ledger_path.write_text(
            ledger_template(args.title, mission_id, run_dir),
            encoding="utf-8",
        )
    except FileExistsError as exc:
        print(f"mission path already exists unexpectedly: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"failed to create mission workspace: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
