#!/usr/bin/env python3
"""Create a compact architecture decision record draft."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path


# Canonical template source. references/adrtemplate.md owns the template text;
# this script loads and fills it at runtime so the two never drift.
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "references" / "adrtemplate.md"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "architecture_decision"


def load_template() -> str:
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    match = re.search(r"```markdown\n(.*?)```", text, re.DOTALL)
    if not match:
        raise ValueError(f"Expected a fenced markdown template block in {TEMPLATE_PATH}.")
    return match.group(1)


def build_markdown(title: str, status: str, today: str) -> str:
    # Callable replacements keep the substituted text literal, so titles with
    # backslashes or group references like \1 do not break re.sub.
    template = load_template()
    template = re.sub(
        r"^# ADR: .*$", lambda _: f"# ADR: {title}", template, count=1, flags=re.MULTILINE
    )
    template = re.sub(
        r"^Status: .*$", lambda _: f"Status: {status}", template, count=1, flags=re.MULTILINE
    )
    template = re.sub(
        r"^Date: .*$", lambda _: f"Date: {today}", template, count=1, flags=re.MULTILINE
    )
    return template


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
    try:
        content = build_markdown(args.title, args.status, args.date)
    except (OSError, ValueError) as error:
        print(f"Expected a readable ADR template. {error}", file=sys.stderr)
        return 2

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
