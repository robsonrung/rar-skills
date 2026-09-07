#!/usr/bin/env python3
"""Validate, normalize, deduplicate, and filter full-review findings.

This helper does not choose routes, change a finding's severity, increase
confidence from agreement, or authorize fixes.

Input is a JSON array of route returns. Each return has a source and comments
array. Read from stdin, or from every JSON file in --dir.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
COMMENT_FIELDS = (
    "severity",
    "confidence",
    "category",
    "path",
    "line_start",
    "line_end",
    "title",
    "problem",
    "evidence",
    "suggested_fix",
    "tests_to_run",
    "verification",
)


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_comment(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(field in value for field in COMMENT_FIELDS):
        return False
    if not all(
        nonempty_string(value[field])
        for field in (
            "category",
            "path",
            "title",
            "problem",
            "suggested_fix",
            "tests_to_run",
            "verification",
        )
    ):
        return False
    if not isinstance(value["confidence"], (int, float)) or isinstance(
        value["confidence"], bool
    ):
        return False
    if not 0 <= float(value["confidence"]) <= 1:
        return False
    if value["severity"] not in SEVERITIES:
        return False
    if any(type(value[field]) is not int for field in ("line_start", "line_end")):
        return False
    if value["line_start"] <= 0 or value["line_end"] <= 0:
        return False
    return isinstance(value["evidence"], list) and any(
        nonempty_string(item) for item in value["evidence"]
    )


def normalize(comment: dict[str, Any], source: str) -> dict[str, Any]:
    value = {field: comment[field] for field in COMMENT_FIELDS}
    value["path"] = value["path"].strip().replace("\\", "/")
    while value["path"].startswith("./"):
        value["path"] = value["path"][2:]
    value["path"] = value["path"].lstrip("/")
    value["category"] = value["category"].strip().lower()
    value["confidence"] = round(float(value["confidence"]), 2)
    if value["line_end"] < value["line_start"]:
        value["line_start"], value["line_end"] = (
            value["line_end"],
            value["line_start"],
        )
    value["evidence"] = list(
        dict.fromkeys(item.strip() for item in value["evidence"] if nonempty_string(item))
    )
    value["source"] = source
    return value


def fingerprint(comment: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        comment["path"],
        f'{comment["line_start"]}-{comment["line_end"]}',
        comment["category"],
        comment["problem"].strip(),
        comment["severity"],
    )


def order(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        SEVERITIES.index(item["severity"]),
        -item["confidence"],
        item["path"].lower(),
        item["line_start"],
        item["title"].lower(),
    )


def merge_exact_duplicates(group: list[dict[str, Any]]) -> dict[str, Any]:
    group.sort(key=order)
    merged = dict(group[0])
    merged["confidence"] = max(item["confidence"] for item in group)
    sources: list[str] = []
    evidence: list[str] = []
    for item in group:
        for source in [item["source"], *item.get("corroborated_by", [])]:
            if source not in sources:
                sources.append(source)
        for proof in item["evidence"]:
            if proof not in evidence:
                evidence.append(proof)
    merged["evidence"] = evidence
    merged["source"] = sources[0]
    if len(sources) > 1:
        merged["corroborated_by"] = sources[1:]
    return merged


def load_payload(directory: str | None) -> Any:
    if directory is None:
        return json.load(sys.stdin)
    payload: list[Any] = []
    for file in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            payload.append({"source": file.stem, "comments": None})
            continue
        if isinstance(data, dict) and "source" not in data:
            data = dict(data, source=file.stem)
        payload.append(data)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", help="Directory containing route result JSON files")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Confidence threshold. Default: 0.75.",
    )
    parser.add_argument(
        "--max-non-blockers",
        type=int,
        default=5,
        help="Maximum MEDIUM and LOW findings. Default: 5.",
    )
    args = parser.parse_args()

    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    if args.max_non_blockers < 0:
        parser.error("--max-non-blockers must be zero or greater")

    try:
        payload = load_payload(args.dir)
    except (json.JSONDecodeError, OSError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}))
        return 2

    if not isinstance(payload, list):
        print(json.dumps({"status": "failed", "reason": "expected an array of route returns"}))
        return 2

    malformed_returns = 0
    malformed_findings = 0
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}

    for route in payload:
        if not (
            isinstance(route, dict)
            and nonempty_string(route.get("source"))
            and isinstance(route.get("comments"), list)
        ):
            malformed_returns += 1
            continue
        source = route["source"].strip()
        for comment in route["comments"]:
            if not valid_comment(comment):
                malformed_findings += 1
                continue
            normalized = normalize(comment, source)
            grouped.setdefault(fingerprint(normalized), []).append(normalized)

    merged = [merge_exact_duplicates(group) for group in grouped.values()]
    below_threshold = [item for item in merged if item["confidence"] < args.threshold]
    eligible = [item for item in merged if item["confidence"] >= args.threshold]
    blockers = [item for item in eligible if item["severity"] in ("CRITICAL", "HIGH")]
    non_blockers = [
        item for item in eligible if item["severity"] in ("MEDIUM", "LOW")
    ]
    blockers.sort(key=order)
    non_blockers.sort(key=lambda item: (-item["confidence"], *order(item)))
    retained = blockers + non_blockers[: args.max_non_blockers]
    suppressed_by_cap = non_blockers[args.max_non_blockers :]
    retained.sort(key=order)
    for number, comment in enumerate(retained, 1):
        comment["id"] = f"F{number}"

    print(
        json.dumps(
            {
                "status": "complete",
                "findings": retained,
                "suppressed_findings": sorted(
                    below_threshold + suppressed_by_cap, key=order
                ),
                "suppressed_by_confidence": len(below_threshold),
                "suppressed_by_cap": len(suppressed_by_cap),
                "malformed_returns": malformed_returns,
                "malformed_findings": malformed_findings,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
