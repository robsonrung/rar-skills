#!/usr/bin/env python3
"""Measure a rendered worker prompt against its byte budget."""

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_MAX_BYTES = 24000


def require(condition, message):
    if not condition:
        raise ValueError(message)


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    measure = sub.add_parser("measure", help="check the complete rendered input without dispatching or writing files")
    measure.add_argument("--input", required=True, help="UTF-8 file containing the exact final worker prompt")
    measure.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    measure.add_argument("--reason", help="required when the limit exceeds the default")
    args = parser.parse_args()
    try:
        if args.action == "measure":
            budget = {"max_bytes": args.max_bytes}
            if args.reason is not None:
                budget["reason"] = args.reason
            # Preserve newlines because this measures a rendered artifact, not canonical task text.
            with Path(args.input).open(encoding="utf-8", newline="") as stream:
                result = {"status": "within_limit", "input_measurement": measure_rendered(stream.read(), budget)}
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
