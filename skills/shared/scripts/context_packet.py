#!/usr/bin/env python3
"""Bind a bounded role brief to its decision sources without embedding their contents."""

import argparse
import hashlib
import json
from pathlib import Path

from review_evidence import contract_hash, file_hash, load_record, require, write_record

DEFAULT_MAX_BYTES = 24000


def validate_budget(budget=None):
    """Use a byte ceiling; do not present byte counts as measured model tokens."""
    if budget is None:
        return {"max_bytes": DEFAULT_MAX_BYTES}
    require(isinstance(budget, dict) and {"max_bytes"} <= set(budget) <= {"max_bytes", "reason"},
            "context budget needs max_bytes and an optional reason")
    require(type(budget["max_bytes"]) is int and budget["max_bytes"] > 0, "positive context byte limit required")
    if "reason" in budget:
        require(isinstance(budget["reason"], str) and bool(budget["reason"].strip()), "context budget reason must be nonempty text")
    require(budget["max_bytes"] <= DEFAULT_MAX_BYTES or "reason" in budget,
            f"a context limit above {DEFAULT_MAX_BYTES} bytes needs a recorded reason")
    return dict(budget)


class ContextBudgetError(ValueError):
    def __init__(self, measurement):
        self.measurement = measurement
        super().__init__(f"complete rendered input is {measurement['utf8_bytes']} bytes; limit is {measurement['max_bytes']}. "
                         "Link supporting evidence or narrow derived notes without removing acceptance rules. "
                         "A larger limit needs a reason in the approved route's context_budget.")


def measure_rendered(text, budget=None):
    """Measure the exact launcher text, including contracts and appended instructions."""
    limit = validate_budget(budget)
    encoded = text.encode("utf-8")
    measurement = {"scope": "launcher_rendered_input", "utf8_bytes": len(encoded), **limit,
                   "sha256": hashlib.sha256(encoded).hexdigest(), "token_count": None,
                   "unmeasured": ["host_instructions", "tool_schemas", "adapter_text", "role_history", "later_reads"]}
    if len(encoded) > limit["max_bytes"]:
        raise ContextBudgetError(measurement)
    return measurement


def prepare(brief, sources, output, max_bytes=DEFAULT_MAX_BYTES):
    brief = Path(brief).resolve()
    require(type(max_bytes) is int and max_bytes > 0, "positive packet byte limit required")
    require(brief.stat().st_size <= max_bytes, "brief exceeds packet limit; link source sections instead of copying them")
    require(isinstance(sources, list) and sources, "packet requires source authority entries")
    entries = []
    seen = set()
    for source in sources:
        require(isinstance(source, dict) and set(source) == {"path", "authority", "locator"}, "source needs path, authority, locator")
        require(source["authority"] in {"decision", "evidence", "superseded"}, "invalid source authority")
        path = str(Path(source["path"]).resolve())
        require(path not in seen and isinstance(source["locator"], str) and source["locator"].strip(), "duplicate source or missing locator")
        seen.add(path)
        entries.append({**source, "path": path, "sha256": contract_hash(path) if source["authority"] == "decision" else file_hash(path)})
    require(any(e["authority"] == "decision" for e in entries), "name at least one current decision source")
    return write_record(output, {"brief": {"path": str(brief), "sha256": file_hash(brief)}, "sources": entries, "max_bytes": max_bytes})


def verify(path, brief=None):
    packet = load_record(path)
    entry = packet["brief"]
    require(brief is None or Path(brief).resolve() == Path(entry["path"]), "packet belongs to another brief")
    require(file_hash(entry["path"]) == entry["sha256"], "derived brief changed; rebuild packet")
    require(Path(entry["path"]).stat().st_size <= packet["max_bytes"], "brief exceeds packet limit")
    for entry in packet["sources"]:
        actual = contract_hash(entry["path"]) if entry["authority"] == "decision" else file_hash(entry["path"])
        require(actual == entry["sha256"], f"{entry['authority']} source changed; revise derived brief: {entry['path']}")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    make = sub.add_parser("prepare")
    for name in ("brief", "sources", "output"):
        make.add_argument("--" + name, required=True)
    make.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    check = sub.add_parser("verify")
    check.add_argument("--packet", required=True)
    measure = sub.add_parser("measure", help="check the complete rendered input without dispatching or writing files")
    measure.add_argument("--input", required=True, help="UTF-8 file containing the exact final worker prompt")
    measure.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    measure.add_argument("--reason", help="required when the limit exceeds the default")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = {"packet": str(prepare(args.brief, json.loads(Path(args.sources).read_text()), args.output, args.max_bytes))}
        elif args.action == "measure":
            budget = {"max_bytes": args.max_bytes}
            if args.reason is not None:
                budget["reason"] = args.reason
            # Preserve newlines because this measures a rendered artifact, not canonical task text.
            with Path(args.input).open(encoding="utf-8", newline="") as stream:
                result = {"status": "within_limit", "input_measurement": measure_rendered(stream.read(), budget)}
        else:
            verify(args.packet)
            result = {"status": "current"}
        print(json.dumps(result))
        return 0
    except ContextBudgetError as error:
        print(json.dumps({"status": "blocked", "error": str(error), "input_measurement": error.measurement}))
        return 2
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
