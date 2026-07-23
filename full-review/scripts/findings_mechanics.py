#!/usr/bin/env python3
"""Deterministic Phase 5 pre-pass for full-review findings.

Owns, mechanically: seat-return and finding validation, exact fingerprint
dedup, discrete confidence anchoring, the quote-the-line evidence gate,
conservative route merging, cross-model promotion for exact duplicates,
triage grouping (apply-queue vs decision-gate), and stable finding numbering.
The Phase 5 synthesizer consumes this script's output and never re-does any
of it in prose.

Input: a JSON array of seat returns, each `{"source": "<seat>", "comments": [...]}`
with comments shaped per references/review_output_schema.json. Read from stdin,
or from every `*.json` file in `--dir` (source defaults to the file stem).

Adapted from EveryInc/compound-engineering-plugin (MIT). See NOTICE at repo root.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
ANCHORS = (0.0, 0.25, 0.5, 0.75, 1.0)
# Ordered least to most conservative; merges only ever move rightward.
AUTOFIX_CLASSES = ("gated_auto", "manual", "advisory")
REQUIRED_COMMENT = {
    "severity": str,
    "confidence": (int, float),
    "category": str,
    "path": str,
    "line_start": int,
    "line_end": int,
    "title": str,
    "evidence": list,
}


def anchor(confidence: float) -> float:
    """Snap a raw confidence down to the nearest discrete anchor (conservative)."""
    clamped = min(max(float(confidence), 0.0), 1.0)
    return max(value for value in ANCHORS if value <= clamped + 1e-9)


def promote(confidence: float) -> float:
    return {0.5: 0.75, 0.75: 1.0, 1.0: 1.0}.get(confidence, confidence)


def has_evidence(comment: dict[str, Any]) -> bool:
    evidence = comment.get("evidence")
    return isinstance(evidence, list) and any(
        isinstance(item, str) and item.strip() for item in evidence
    )


def valid_comment(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not all(
        isinstance(value.get(key), expected) for key, expected in REQUIRED_COMMENT.items()
    ):
        return False
    if isinstance(value["confidence"], bool):
        return False
    return (
        value["severity"] in SEVERITIES
        and value["line_start"] > 0
        and value["line_end"] > 0
        and bool(value["path"].strip())
        and bool(value["title"].strip())
    )


def normalize(comment: dict[str, Any], source: str) -> dict[str, Any]:
    comment = dict(comment)
    path = comment["path"].strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    comment["path"] = path.lstrip("/")
    if comment["line_end"] < comment["line_start"]:
        comment["line_start"], comment["line_end"] = (
            comment["line_end"],
            comment["line_start"],
        )
    comment["category"] = comment["category"].strip().lower()
    raw = float(comment["confidence"])
    comment["confidence_raw"] = round(raw, 2)
    comment["confidence"] = anchor(raw)
    # Quote-the-line evidence gate: a hot finding without a quoted indicator
    # cannot stay hot on assertion alone.
    if comment["confidence"] >= 0.75 and not has_evidence(comment):
        comment["confidence"] = 0.5
    autofix = comment.get("autofix_class")
    if autofix == "safe_auto":
        autofix = "gated_auto"  # full-review never grants silent apply on code.
    if autofix not in AUTOFIX_CLASSES:
        autofix = "manual"
    comment["autofix_class"] = autofix
    comment.setdefault("source", source)
    return comment


def fingerprint(comment: dict[str, Any]) -> tuple[str, str, str]:
    return (
        comment["path"].lower(),
        f'{comment["line_start"]}-{comment["line_end"]}',
        comment["category"],
    )


def external_seat(source: str) -> bool:
    return source.startswith("external_")


def merge_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    # Start with the most urgent/high-confidence representation, then merge
    # conservatively: routes only narrow, evidence only accumulates.
    group.sort(key=lambda item: (SEVERITIES.index(item["severity"]), -item["confidence"]))
    merged = dict(group[0])
    sources: list[str] = []
    evidence: list[str] = []
    for comment in group:
        for name in [comment.get("source", "")] + list(comment.get("corroborated_by") or []):
            if isinstance(name, str) and name and name not in sources:
                sources.append(name)
        for item in comment.get("evidence") or []:
            if isinstance(item, str) and item.strip() and item not in evidence:
                evidence.append(item)
        if AUTOFIX_CLASSES.index(comment["autofix_class"]) > AUTOFIX_CLASSES.index(
            merged["autofix_class"]
        ):
            merged["autofix_class"] = comment["autofix_class"]
        if not merged.get("suggested_fix") and comment.get("suggested_fix"):
            merged["suggested_fix"] = comment["suggested_fix"]
        if comment.get("verified") is True:
            merged["verified"] = True
    merged["evidence"] = evidence
    merged["corroborated_by"] = sources
    externals = {name for name in sources if external_seat(name)}
    in_house = any(not external_seat(name) for name in sources)
    merged["corroborated_models"] = len(externals) + (1 if in_house else 0)
    # Cross-model promotion for exact duplicates: distinct external seats plus
    # quoted evidence step the anchor up once. In-house seats share one
    # orchestrator context and never promote on their own.
    confidence = max(item["confidence"] for item in group)
    if merged["corroborated_models"] >= 2 and has_evidence(merged):
        confidence = promote(confidence)
    merged["confidence"] = confidence
    return merged


def triage(comment: dict[str, Any]) -> str:
    """Apply queue = an automated fixer may act; everything else is human's."""
    if (
        comment["severity"] != "CRITICAL"
        and comment["category"] != "security"
        and comment["autofix_class"] == "gated_auto"
        and isinstance(comment.get("suggested_fix"), str)
        and comment["suggested_fix"].strip()
        and comment["confidence"] >= 0.75
        and comment.get("verified") is not False
    ):
        return "apply_queue"
    return "decision_gate"


def load_payload(directory: str | None) -> Any:
    if directory is None:
        return json.load(sys.stdin)
    payload = []
    for file in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(file.read_text())
        except (json.JSONDecodeError, OSError):
            payload.append({"source": file.stem, "comments": None})  # counted malformed
            continue
        if isinstance(data, dict) and "source" not in data:
            data = dict(data, source=file.stem)
        payload.append(data)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", help="Findings directory of per-seat *.json files")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.75,
        help="Active confidence filter; anchored findings below it are suppressed "
        "(CRITICAL findings are exempt and never suppressed).",
    )
    args = parser.parse_args()

    try:
        payload = load_payload(args.dir)
    except (json.JSONDecodeError, OSError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}))
        return 2

    if not isinstance(payload, list):
        print(json.dumps({"status": "failed", "reason": "expected an array of seat returns"}))
        return 2

    malformed_returns = 0
    malformed_findings = 0
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}

    for seat in payload:
        if not (
            isinstance(seat, dict)
            and isinstance(seat.get("source"), str)
            and isinstance(seat.get("comments"), list)
        ):
            malformed_returns += 1
            continue
        for comment in seat["comments"]:
            if not valid_comment(comment):
                malformed_findings += 1
                continue
            normalized = normalize(comment, seat["source"])
            grouped.setdefault(fingerprint(normalized), []).append(normalized)

    merged = [merge_group(group) for group in grouped.values()]
    suppressed_by_confidence: Counter[str] = Counter()
    suppressed: list[dict[str, Any]] = []
    survivors: list[dict[str, Any]] = []
    for comment in merged:
        if comment["confidence"] < args.threshold and comment["severity"] != "CRITICAL":
            suppressed_by_confidence[str(comment["confidence"])] += 1
            suppressed.append(comment)
            continue
        comment["triage"] = triage(comment)
        survivors.append(comment)

    def order(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            SEVERITIES.index(item["severity"]),
            -item["confidence"],
            item["path"].lower(),
            item["line_start"],
            item["title"].lower(),
        )

    suppressed.sort(key=order)
    survivors.sort(key=order)
    for number, comment in enumerate(survivors, 1):
        comment["id"] = f"F{number}"

    print(
        json.dumps(
            {
                "status": "complete",
                "findings": survivors,
                "suppressed_findings": suppressed,
                "apply_queue": [c["id"] for c in survivors if c["triage"] == "apply_queue"],
                "decision_gate": [c["id"] for c in survivors if c["triage"] == "decision_gate"],
                "suppressed_by_confidence": dict(sorted(suppressed_by_confidence.items())),
                "malformed_returns": malformed_returns,
                "malformed_findings": malformed_findings,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
