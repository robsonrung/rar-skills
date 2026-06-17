#!/usr/bin/env python3
"""Leitwörter regression guard.

Enforces the leitwörter convention (see LEITWORTER.md) against the registry in
leitworter.json. Two failure modes are gated (exit 1):

  - deletion: a `must_contain` leitwort disappeared from the skill that owns it.
  - drift:    a `must_not_contain` generic phrasing returned to a guarded file.

Two things are reported as warnings only (never fail the build):

  - canon drift_terms appearing anywhere outside the skill that owns the leitwort.
  - filler verbs ("carefully", "thoroughly", ...) in any SKILL.md.

Usage:
  python3 scripts/check_leitworter.py [--registry PATH] [--root DIR] [--json]

Exit codes: 0 = no gated violations, 1 = one or more gated violations,
2 = usage/registry error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_registry(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: registry not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    except json.JSONDecodeError as exc:
        print(f"error: registry is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2)


def check_guards(registry: dict, root: Path) -> list[str]:
    """Return a list of gated-violation messages (deletion + drift)."""
    errors: list[str] = []
    for guard in registry.get("guards", []):
        rel = guard["file"]
        path = root / rel
        if not path.exists():
            errors.append(f"{rel}: guarded file is missing")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for needle in guard.get("must_contain", []):
            if needle.lower() not in text:
                errors.append(
                    f"{rel}: deletion — required leitwort '{needle}' is gone "
                    f"(concept: {guard.get('concept', '?')})"
                )
        for needle in guard.get("must_not_contain", []):
            if needle.lower() in text:
                errors.append(
                    f"{rel}: drift — forbidden phrasing '{needle}' returned "
                    f"(concept: {guard.get('concept', '?')})"
                )
    return errors


def skill_files(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("*/SKILL.md"))


def owner_files(registry: dict, leitwort: str) -> set[str]:
    owners: set[str] = set()
    for guard in registry.get("guards", []):
        if any(leitwort.lower() == mc.lower() for mc in guard.get("must_contain", [])):
            owners.add(guard["file"])
    return owners


def check_warnings(registry: dict, root: Path) -> list[str]:
    warnings: list[str] = []
    files = skill_files(root)

    # Canon drift terms used outside the owning skill.
    for entry in registry.get("canon", []):
        leitwort = entry["leitwort"]
        owners = owner_files(registry, leitwort)
        for term in entry.get("drift_terms", []):
            for path in files:
                rel = str(path.relative_to(root))
                if rel in owners:
                    continue
                if term.lower() in path.read_text(encoding="utf-8").lower():
                    warnings.append(
                        f"{rel}: uses '{term}' — prefer canon leitwort "
                        f"'{leitwort}'"
                    )

    # Filler verbs in any SKILL.md.
    fillers = [f.lower() for f in registry.get("filler_verbs", [])]
    for path in files:
        rel = str(path.relative_to(root))
        low = path.read_text(encoding="utf-8").lower()
        hits = sorted({f for f in fillers if f in low})
        if hits:
            warnings.append(f"{rel}: filler verbs present ({', '.join(hits)})")
    return warnings


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", default=None,
                        help="path to leitworter.json (default: <root>/leitworter.json)")
    parser.add_argument("--root", default=None,
                        help="repo root (default: parent of this script's dir)")
    parser.add_argument("--json", action="store_true",
                        help="emit machine-readable JSON to stdout")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    registry_path = Path(args.registry) if args.registry else root / "leitworter.json"
    registry = load_registry(registry_path)

    errors = check_guards(registry, root)
    warnings = check_warnings(registry, root)

    if args.json:
        json.dump({"errors": errors, "warnings": warnings}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        if errors:
            print(f"\nFAIL: {len(errors)} leitwort regression(s):", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK: {len(registry.get('guards', []))} guarded skills intact "
                  f"({len(warnings)} warning(s)).")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
