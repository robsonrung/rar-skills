#!/usr/bin/env python3
"""Validate, normalize, deduplicate, and filter full-review findings.

This helper does not choose routes, change a finding's severity, increase
confidence from agreement, or authorize fixes.

Input is a JSON array of route returns. Each return has a source and comments
array. Read from stdin, or from every JSON file in --dir.
"""

from __future__ import annotations

import argparse
import hashlib
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
    if "id" in value and not nonempty_string(value["id"]):
        return False
    if "related_ids" in value and (not isinstance(value["related_ids"], list) or not all(nonempty_string(item) for item in value["related_ids"])):
        return False
    if value.get("status", "confirmed") not in ("confirmed", "unverified", "refuted"):
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
    value["status"] = comment.get("status", "confirmed")
    if comment.get("related_ids"):
        value["related_ids"] = list(dict.fromkeys(comment["related_ids"]))
    if "id" in comment:
        value["id"] = comment["id"]
    else:
        identity = json.dumps(fingerprint(value), ensure_ascii=False).encode("utf-8")
        value["id"] = "F-" + hashlib.sha256(identity).hexdigest()[:16]
    return value


def fingerprint(comment: dict[str, Any]) -> tuple[str, ...]:
    return (
        comment["path"],
        f'{comment["line_start"]}-{comment["line_end"]}',
        comment["category"],
        comment["problem"].strip(),
        comment["severity"],
        comment.get("status", "confirmed"),
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
    identifiers = sorted({identifier for item in group for identifier in [item["id"], *item.get("related_ids", [])]})
    merged["id"] = identifiers[0]
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
    aliases = identifiers[1:]
    if aliases:
        merged["related_ids"] = aliases
    else:
        merged.pop("related_ids", None)
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
        help="Maximum non-security MEDIUM and LOW findings in the human summary only. Default: 5.",
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
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    identities: dict[str, tuple[tuple[str, ...], str]] = {}

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
            key = fingerprint(normalized)
            for identifier in [normalized["id"], *normalized.get("related_ids", [])]:
                previous = identities.get(identifier)
                if previous is not None and previous[0] != key:
                    print(json.dumps({
                        "status": "failed",
                        "reason": "finding ID or alias refers to distinct findings; supply unique IDs and retain the source mapping",
                        "conflicting_id": identifier,
                        "sources": [previous[1], source],
                    }))
                    return 2
                identities[identifier] = (key, source)
            grouped.setdefault(key, []).append(normalized)

    merged = [merge_exact_duplicates(group) for group in grouped.values()]
    below_threshold = [item for item in merged if item["confidence"] < args.threshold]
    eligible = [item for item in merged if item["confidence"] >= args.threshold and item["status"] == "confirmed"]
    excluded = [item for item in merged if item["confidence"] < args.threshold or item["status"] != "confirmed"]
    always_shown = [item for item in eligible if item["severity"] in ("CRITICAL", "HIGH") or item["category"] == "security"]
    bounded_summary = [item for item in eligible if item not in always_shown]
    bounded_summary.sort(key=lambda item: (-item["confidence"], *order(item)))
    summary = sorted(always_shown + bounded_summary[: args.max_non_blockers], key=order)
    omitted = bounded_summary[args.max_non_blockers :]
    retained = sorted(eligible, key=order)

    print(
        json.dumps(
            {
                "status": "complete",
                "findings": retained,
                "summary_findings": summary,
                "summary_omitted_ids": [item["id"] for item in omitted],
                "suppressed_findings": sorted(excluded, key=order),
                "suppressed_by_confidence": len(below_threshold),
                "suppressed_by_cap": 0,
                "summary_omitted_count": len(omitted),
                "malformed_returns": malformed_returns,
                "malformed_findings": malformed_findings,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
