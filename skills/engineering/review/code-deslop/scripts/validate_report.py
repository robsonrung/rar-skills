#!/usr/bin/env python3
"""Check report structure and consistency; never execute commands or verify source claims."""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any


def validate(report: Any) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    def text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def one_of(value: Any, choices: set[str]) -> bool:
        return isinstance(value, str) and value in choices

    def relative(value: Any) -> bool:
        return text(value) and not PurePosixPath(value).is_absolute() and ".." not in PurePosixPath(value).parts

    if not isinstance(report, dict):
        return ["Report must be a JSON object"]
    require(report.get("schema_version") == "1.0", "schema_version must be 1.0")
    require(one_of(report.get("mode"), {"audit", "fix"}), "mode must be audit or fix")
    require(text(report.get("scope")), "scope must state the reviewed scope and baseline")
    require(text(report.get("summary")), "summary must be non-empty")
    for key in ("changed_files", "exclusions", "findings", "checks", "unresolved"):
        require(isinstance(report.get(key), list), f"{key} must be an array")
    if errors:
        return errors
    require(all(relative(path) for path in report["changed_files"]), "changed_files must be relative paths without '..'")
    require(all(text(item) for item in report["exclusions"] + report["unresolved"]),
            "exclusions and unresolved must contain non-empty strings")
    if report["mode"] == "audit":
        require(not report["changed_files"], "audit must not report changed files")
    checks: dict[str, dict[str, Any]] = {}
    outcomes = {"passed", "failed", "not-run", "blocked"}
    for index, check in enumerate(report["checks"]):
        label = f"checks[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = check.get("id")
        require(text(identifier), f"{label}.id is required")
        if not text(identifier):
            continue
        require(identifier not in checks, f"Duplicate check id {identifier}")
        checks[identifier] = check
        require(one_of(check.get("kind"), {"static", "test", "typecheck", "build", "differential", "mutation", "browser", "manual"}),
                f"{label}.kind is invalid")
        require(one_of(check.get("baseline"), outcomes) and one_of(check.get("after"), outcomes),
                f"{label} must record baseline and after outcomes")
        require(text(check.get("evidence")), f"{label}.evidence is required")
        if not one_of(check.get("kind"), {"static", "manual"}) and any(one_of(check.get(key), {"passed", "failed"}) for key in ("baseline", "after")):
            require(text(check.get("command")), f"{label}.command is required for executed checks")
    ids: set[str] = set()
    statuses = {"fixed", "proposed", "kept", "blocked", "separate-change"}
    categories = {"noise", "dead-code", "dependency", "abstraction", "duplication", "control-flow",
                  "error-handling", "types", "tests", "react", "architecture", "correctness", "convention"}
    for index, finding in enumerate(report["findings"]):
        label = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{label} must be an object")
            continue
        identifier = finding.get("id")
        require(text(identifier), f"{label}.id is required")
        if text(identifier):
            require(identifier not in ids, f"Duplicate finding id {identifier}")
            ids.add(identifier)
        require(one_of(finding.get("status"), statuses), f"{label}.status is invalid")
        require(one_of(finding.get("category"), categories), f"{label}.category is invalid")
        require(relative(finding.get("path")), f"{label}.path must be repository-relative")
        require(type(finding.get("line")) is int and finding["line"] > 0, f"{label}.line must be a positive integer")
        require(one_of(finding.get("risk"), {"low", "medium", "high"}), f"{label}.risk is invalid")
        for key in ("evidence", "cost", "counterevidence", "action", "reason"):
            require(text(finding.get(key)), f"{label}.{key} is required")
        check_ids = finding.get("check_ids")
        require(isinstance(check_ids, list) and all(text(item) for item in check_ids),
                f"{label}.check_ids must be an array of check identifiers")
        if not isinstance(check_ids, list) or not all(text(item) for item in check_ids):
            continue
        require(all(item in checks for item in check_ids), f"{label} references an unknown check")
        if finding.get("status") == "fixed":
            require(report["mode"] == "fix", f"{label}: fixed finding requires fix mode")
            require(bool(report["changed_files"]), f"{label}: fixed finding requires changed_files")
            require(finding.get("risk") != "high", f"{label}: high-risk change must be a separate task")
            linked = [checks[item] for item in check_ids if item in checks]
            require(any(item.get("after") == "passed" for item in linked), f"{label}: fixed finding needs a passed after-check")
            require(not any(item.get("after") == "failed" for item in linked), f"{label}: fixed finding has a failing linked check")
            if finding.get("category") != "noise":
                require(any(not one_of(item.get("kind"), {"static", "manual"})
                            and item.get("baseline") == "passed" and item.get("after") == "passed"
                            for item in linked), f"{label}: executable cleanup needs a passing baseline/after check pair")
    review = report.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
    else:
        require(one_of(review.get("independence"), {"fresh-context", "self-review", "none"}), "review.independence is invalid")
        require(one_of(review.get("result"), {"passed", "failed", "not-run"}), "review.result is invalid")
        require(text(review.get("evidence")), "review.evidence is required")
        if review.get("independence") == "none":
            require(review.get("result") == "not-run", "An unperformed review cannot pass or fail")
    return errors


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
        errors = validate(report)
    except (OSError, ValueError, TypeError) as exc:
        print(f"report: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Report is structurally consistent. Source claims and evidence have not been verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
