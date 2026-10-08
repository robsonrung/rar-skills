#!/usr/bin/env python3
"""Compare recorded workflow measurements without changing execution state."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from execution_metrics import FIELDS, aggregate_metrics

CASE_KINDS = {"bounded-fix", "routine-feature", "ui", "permissions", "migration-concurrency"}
IDENTITY_FIELDS = ("case_id", "case_kind", "source_start_revision", "requirements_sha256",
                   "checks_sha256", "environment_sha256")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), "timestamps must be ISO 8601 strings with a timezone")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("timestamps must be ISO 8601 strings with a timezone") from error
    require(result.tzinfo is not None, "timestamps need a timezone")
    return result


def elapsed_ms(start, end):
    duration = (timestamp(end) - timestamp(start)).total_seconds() * 1000
    require(duration >= 0, "completion precedes start")
    return duration


def call_timing(calls, start, end):
    lower = timestamp(start) if start is not None else None
    upper = timestamp(end) if end is not None else None
    checked, unknown = 0, 0
    for call_id, call in calls.items():
        events = {}
        for field in ("reserved_at", "completed_at"):
            value = call.get(field)
            if value is None:
                unknown += 1
                continue
            event = timestamp(value)
            require(lower is None or event >= lower, f"call {call_id} {field} precedes workflow start")
            require(upper is None or event <= upper, f"call {call_id} {field} follows workflow completion")
            events[field] = event
            checked += 1
        if len(events) == 2:
            require(events["reserved_at"] <= events["completed_at"], f"call {call_id} completion precedes reservation")
    return {"checked_events": checked, "unknown_events": unknown}


def approval_wait_ms(intervals, start, end):
    if intervals is None or start is None or end is None:
        return None
    require(isinstance(intervals, list), "approval_wait_intervals must be a list or null")
    lower, upper = timestamp(start), timestamp(end)
    spans = []
    for interval in intervals:
        require(isinstance(interval, dict), "approval wait interval must be an object")
        begin, finish = timestamp(interval.get("started_at")), timestamp(interval.get("completed_at"))
        require(lower <= begin <= finish <= upper, "approval wait falls outside workflow interval")
        spans.append((begin, finish))
    merged = []
    for begin, finish in sorted(spans):
        if merged and begin <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(finish, merged[-1][1]))
        else:
            merged.append((begin, finish))
    return sum((finish - begin).total_seconds() * 1000 for begin, finish in merged)


def string_list(value, name):
    require(isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value),
            f"{name} must be a list of nonempty strings")
    return value


def summarize(state):
    require(isinstance(state, dict), "run state must be an object")
    status = state.get("status")
    require(status is None or (isinstance(status, str) and status in {
        "running", "awaiting_human", "complete", "failed", "ceiling_hit", "cancelled"}), "invalid workflow status")
    measurement = state.get("workflow_measurement", {})
    require(isinstance(measurement, dict), "workflow_measurement must be an object")
    identity = measurement.get("identity", {})
    require(isinstance(identity, dict), "measurement identity must be an object")
    missing = []
    for key in IDENTITY_FIELDS:
        value = identity.get(key)
        if value is None:
            missing.append("identity." + key)
        else:
            require(isinstance(value, str) and value.strip(), f"invalid identity.{key}")
            if key.endswith("_sha256"):
                require(re.fullmatch(r"[0-9a-f]{64}", value), f"invalid identity.{key}")
            if key == "source_start_revision":
                require(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value), "use a full source start revision")
            if key == "case_kind":
                require(value in CASE_KINDS, "unsupported case_kind")
    ledger = state.get("call_ledger")
    require(ledger is None or isinstance(ledger, dict), "call_ledger must be an object")
    calls = ledger.get("calls") if ledger is not None else None
    require(calls is None or isinstance(calls, dict), "call ledger calls must be an object")
    if calls is None:
        missing.append("call_ledger.calls")
    ledger_known = calls is not None
    calls = calls or {}
    for call in calls.values():
        require(isinstance(call, dict), "call must be an object")
        require(isinstance(call.get("status"), str) and call["status"] in {"pending", "completed", "failed"},
                "invalid call status")
        require(call.get("receipt") is None or isinstance(call["receipt"], dict), "receipt must be an object")
    if measurement.get("worker_calls_complete") is not True:
        require(measurement.get("worker_calls_complete") is None or measurement.get("worker_calls_complete") is False,
                "worker_calls_complete must be boolean")
        missing.append("worker_calls_complete")
    workers = aggregate_metrics(list(calls.values()))
    coordinator = measurement.get("coordinator_receipts")
    require(coordinator is None or (isinstance(coordinator, list) and all(isinstance(r, dict) for r in coordinator)),
            "coordinator_receipts must be a list of receipts or null")
    coordinator_metrics = None if coordinator is None else aggregate_metrics([{"receipt": r} for r in coordinator])
    if coordinator is None:
        missing.append("coordinator_receipts")
    for name, metrics in (("workers", workers), ("coordinator", coordinator_metrics)):
        if metrics is not None:
            missing.extend(f"{name}.{key}" for key in FIELDS if metrics[key]["unknown_calls"])
    start, end = state.get("started_at"), state.get("completed_at")
    wall = elapsed_ms(start, end) if start is not None and end is not None else None
    timing = call_timing(calls, start, end)
    if timing["unknown_events"]:
        missing.append("call_timing")
    wait = approval_wait_ms(measurement.get("approval_wait_intervals"), start, end)
    for key, value in (("workflow_elapsed_ms", wall), ("approval_wait_ms", wait)):
        if value is None:
            missing.append(key)
    repairs = measurement.get("repair_call_ids")
    if repairs is not None:
        string_list(repairs, "repair_call_ids")
        require(len(set(repairs)) == len(repairs), "repair call IDs must be unique")
        require(not ledger_known or set(repairs) <= calls.keys(), "repair call IDs must be ledger calls")
    else:
        missing.append("repair_call_ids")
    commands = measurement.get("command_keys")
    if commands is not None:
        string_list(commands, "command_keys")
    else:
        missing.append("command_keys")
    acceptance = measurement.get("acceptance")
    defects = measurement.get("missed_defects")
    for name, value in (("acceptance", acceptance), ("missed_defects", defects)):
        if value is None:
            missing.append(name)
            continue
        require(isinstance(value, dict), f"{name} must be an object or null")
        require(isinstance(value.get("evidence"), str) and value["evidence"].strip(), f"{name} needs an evidence reference")
        if name == "acceptance":
            require(type(value.get("passed")) is bool, "acceptance.passed must be boolean")
        else:
            require(type(value.get("count")) is int and value["count"] >= 0, "missed_defects.count must be a nonnegative integer")
            require(isinstance(value.get("observation_window"), str) and value["observation_window"].strip(),
                    "missed defects need an observation_window")
    pending = sum(call["status"] == "pending" for call in calls.values())
    if state.get("status") not in {"complete", "failed", "ceiling_hit", "cancelled"} or pending:
        missing.append("terminal_workflow")
    counts_known = ledger_known and measurement.get("worker_calls_complete") is True
    failed = sum(call["status"] == "failed" for call in calls.values())
    cost_known = counts_known and "terminal_workflow" not in missing and coordinator_metrics is not None
    cost_known = cost_known and not workers["reported_cost_usd"]["unknown_calls"] and not coordinator_metrics["reported_cost_usd"]["unknown_calls"]
    total_cost = (workers["reported_cost_usd"]["measured_sum"] + coordinator_metrics["reported_cost_usd"]["measured_sum"]) if cost_known else None
    return {"identity": {key: identity.get(key) for key in IDENTITY_FIELDS},
            "workflow_elapsed_ms": wall, "approval_wait_ms": wait,
            "call_timing": timing if ledger_known else None,
            "workers": workers, "coordinator": coordinator_metrics, "total_reported_cost_usd": total_cost,
            "measured_worker_calls": len(calls), "worker_calls": len(calls) if counts_known else None,
            "pending_calls": pending if ledger_known else None, "measured_failed_calls": failed,
            "failed_calls": failed if counts_known and not pending else None,
            "repair_calls": None if repairs is None else len(repairs),
            "commands": None if commands is None else len(commands),
            "repeated_commands": None if commands is None else len(commands) - len(set(commands)),
            "acceptance": acceptance, "missed_defects": defects,
            "incomplete_fields": missing}


def compare(baseline, candidate):
    reports, errors = {}, []
    for name, state in (("baseline", baseline), ("candidate", candidate)):
        try:
            reports[name] = summarize(state)
        except ValueError as error:
            errors.append(f"{name}: {error}")
    if errors:
        return {"status": "invalid", "errors": errors, "deltas": None}
    before, after = reports["baseline"], reports["candidate"]
    mismatches = [key for key in IDENTITY_FIELDS if before["identity"][key] is not None
                  and after["identity"][key] is not None and before["identity"][key] != after["identity"][key]]
    if before["missed_defects"] and after["missed_defects"]:
        if before["missed_defects"]["observation_window"] != after["missed_defects"]["observation_window"]:
            mismatches.append("missed_defects.observation_window")
    if before["acceptance"] and after["acceptance"]:
        if not (before["acceptance"]["passed"] and after["acceptance"]["passed"]):
            mismatches.append("acceptance.passed")
    if before["missed_defects"] and after["missed_defects"]:
        if before["missed_defects"]["count"] != after["missed_defects"]["count"]:
            mismatches.append("missed_defects.count")
    if mismatches:
        return {"status": "mismatched", "mismatched_fields": mismatches, **reports, "deltas": None,
                "observed_acceptance_match": False, "quality_equivalence": "not-established"}
    missing_identity = any(value is None for report in reports.values() for value in report["identity"].values())
    outcomes = all(report["acceptance"] and report["missed_defects"] for report in reports.values())
    comparable = bool(outcomes) and not missing_identity and all(
        "terminal_workflow" not in report["incomplete_fields"] for report in reports.values())
    deltas = {}
    if comparable:
        for key in ("workflow_elapsed_ms", "approval_wait_ms", "total_reported_cost_usd", "worker_calls", "failed_calls",
                    "repair_calls", "commands", "repeated_commands"):
            deltas[key] = after[key] - before[key] if before[key] is not None and after[key] is not None else None
        for group in ("workers", "coordinator"):
            deltas[group] = {}
            for key in FIELDS:
                left, right = before[group], after[group]
                known = left is not None and right is not None and not left[key]["unknown_calls"] and not right[key]["unknown_calls"]
                if group == "workers":
                    known = known and all(not report["pending_calls"] and "worker_calls_complete" not in report["incomplete_fields"]
                                          and "call_ledger.calls" not in report["incomplete_fields"] for report in reports.values())
                deltas[group][key] = right[key]["measured_sum"] - left[key]["measured_sum"] if known else None
    return {"status": "incomplete" if any(report["incomplete_fields"] for report in reports.values()) else "matched",
            **reports, "deltas": deltas if comparable else None,
            "observed_acceptance_match": comparable,
            "quality_equivalence": "not-established",
            "limits": "Reported outcomes need independent evidence review. Matched observations do not establish general quality equivalence."}


def main():
    parser = argparse.ArgumentParser(description=__doc__, epilog="Example: workflow_comparison.py --baseline before.json --candidate after.json")
    parser.add_argument("--baseline", type=Path, required=True, help="baseline run-state JSON")
    parser.add_argument("--candidate", type=Path, required=True, help="candidate run-state JSON")
    args = parser.parse_args()
    try:
        result = compare(json.loads(args.baseline.read_text()), json.loads(args.candidate.read_text()))
        rendered = json.dumps(result, indent=2, allow_nan=False)
    except (OSError, ValueError) as error:
        print(f"Cannot read comparison inputs: {error}", file=sys.stderr)
        return 2
    print(rendered)
    return 0 if result["status"] == "matched" else 1


if __name__ == "__main__":
    sys.exit(main())
