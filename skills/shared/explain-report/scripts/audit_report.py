#!/usr/bin/env python3
"""Cross check report structure against a collected snapshot and original plan.

This validates supplied artifacts, not narrative truth or source correctness.
It reads local JSON and an optional plan, and performs no repository writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from render_report import validate_report


def audit(data, snapshot=None, source_plan=None):
    errors = validate_report(data)
    warnings = []
    if errors:
        return errors, warnings
    if snapshot is not None:
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            return ["Unsupported repository snapshot."], warnings
        if not snapshot.get("capture_complete"):
            warnings.append("The snapshot is incomplete; freshness and coverage remain qualified.")
        if data["snapshot"]["head"] != snapshot.get("head_revision"):
            errors.append("Report head does not match the collected repository revision.")
        comparison_base = snapshot.get("comparison_base")
        if comparison_base and data["snapshot"]["base"] != comparison_base:
            errors.append("Report base does not match the collected comparison base.")
        if data["kind"] == "implementation":
            if snapshot.get("scope", {}).get("mode") == "snapshot":
                errors.append("Implementation coverage needs a comparison snapshot with an explicit base.")
            else:
                actual = set()
                for item in snapshot.get("changes", []):
                    for key in ("path", "original_path"):
                        if item.get(key):
                            actual.add(item[key])
                claimed = set(data.get("coverage", {}).get("changed_paths", []))
                for path in sorted(actual - claimed):
                    errors.append("Changed path missing from report manifest: " + path)
                for path in sorted(claimed - actual):
                    errors.append("Report claims a changed path outside the snapshot: " + path)
    if source_plan is not None:
        recorded = data.get("plan", {}).get("sha256")
        actual_hash = hashlib.sha256(source_plan).hexdigest()
        if recorded != actual_hash:
            errors.append("Original plan SHA256 does not match the supplied plan bytes.")
    checks = {c["id"]: c for c in data.get("checks", [])}
    evidence = {e["id"]: e for e in data.get("evidence", [])}
    for requirement in data.get("requirements", []):
        if requirement["status"] == "met":
            passed = any(checks[c]["status"] == "passed" for c in requirement.get("checks", []))
            observed = any(evidence[e]["status"] == "observed" for e in requirement.get("evidence", []))
            if not passed and not observed:
                errors.append(requirement["id"] + ": a met requirement needs an observed basis or a passed check.")
    explained = {a["path"] for a in data.get("areas", [])}
    excluded = {p["path"] for p in data.get("coverage", {}).get("excluded", [])}
    declared_unknown = set(data.get("coverage", {}).get("unexplained", []))
    for path in sorted(set(data.get("coverage", {}).get("changed_paths", []))):
        if path in declared_unknown or path not in explained | excluded:
            warnings.append("Changed path still unexplained: " + path)
    if snapshot is None:
        warnings.append("No repository snapshot supplied; manifest completeness was not independently compared.")
    return errors, warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--snapshot")
    parser.add_argument("--source-plan")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.report).read_text(encoding="utf-8"))
        snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8")) if args.snapshot else None
        plan = Path(args.source_plan).read_bytes() if args.source_plan else None
        errors, warnings = audit(data, snapshot, plan)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "invalid", "errors": ["Could not read or validate the supplied artifacts."], "warnings": []}))
        return 2
    print(json.dumps({"status": "invalid" if errors else "valid_with_limits" if warnings else "valid", "errors": errors, "warnings": warnings, "meaning": "Artifact consistency only. Narrative truth and implementation correctness require separate evidence."}, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
