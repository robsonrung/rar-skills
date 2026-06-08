#!/usr/bin/env python3
"""Create a compact architecture decision record draft."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "architecture_decision"


def build_markdown(title: str, status: str, today: str) -> str:
    return f"""# ADR: {title}

Status: {status}

Date: {today}

## Context

Describe the problem, current code shape, data ownership, runtime workflow, constraints, and alternatives considered.

## Decision

State the choice and the implementation move that will enforce it.

## Consequences

Describe what gets easier, what gets harder, what coupling is introduced or removed, and what future change would make this worth revisiting.

## Fitness Functions

List tests, static checks, contract checks, monitors, migration checks, or review checks that protect the decision.

## Validation

List commands, runtime checks, or evidence used to verify the implementation.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft an architecture decision record markdown file."
    )
    parser.add_argument("--title", required=True, help="Decision title.")
    parser.add_argument(
        "--out-dir",
        default="docs/adr",
        help="Directory for the ADR. Defaults to docs/adr.",
    )
    parser.add_argument("--slug", help="Optional file slug. Defaults to title slug.")
    parser.add_argument("--status", default="proposed", help="ADR status.")
    parser.add_argument(
        "--date",
        default=dt.date.today().strftime("%Y%m%d"),
        help="Date in YYYYMMDD format. Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the target path and content without writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    slug = slugify(args.slug or args.title)
    out_dir = Path(args.out_dir)
    target = out_dir / f"{args.date}_{slug}.md"
    content = build_markdown(args.title, args.status, args.date)

    result = {"path": str(target), "dry_run": bool(args.dry_run)}

    if args.dry_run:
        result["content"] = content
        print(json.dumps(result, indent=2))
        return 0

    if target.exists():
        print(
            f"Expected no existing ADR at {target}. Choose another title or slug.",
            file=sys.stderr,
        )
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
