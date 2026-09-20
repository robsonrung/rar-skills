#!/usr/bin/env python3
"""Reserve and reconcile role calls in the caller's existing run ledger. Never dispatch work."""

import argparse
import copy
import contextlib
import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from execution_metrics import aggregate_metrics, normalize_metrics


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_write(path, data, *, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if exclusive:
            # Publish a complete file only if this run has no owner yet.
            os.link(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def locked(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        state = json.loads(path.read_text()) if path.exists() else {}
        yield state
        state["updated_at"] = now()
        atomic_write(path, state)


def require(value, message):
    if not value:
        raise ValueError(message)


def initialize(state, plan_path, run_id, limits):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    require(plan.get("approval", {}).get("status") == "approved", "an approved route plan is required")
    require(limits and all(type(v) is int and v > 0 for v in limits.values()), "positive call ceilings are required")
    reference = {"path": str(plan_path), "sha256": sha(plan_path)}
    require(state.get("run_id", run_id) == run_id, "run ID differs")
    if "call_ledger" in state:
        require(state["call_ledger"]["plan"] == reference and state["call_ledger"]["limits"] == limits,
                "existing ledger has different plan or ceilings")
        return
    # Extend an existing run; never replace its steps, counters, gates or authority.
    state.setdefault("run_id", run_id)
    require(state["run_id"] == run_id, "run ID differs")
    for key, value in {"skill": "implement-tasks", "status": "running", "phase": "prepared",
                       "started_at": now(), "attempts": {}, "ceilings": {}, "gates": [],
                       "steps": [], "side_effects": []}.items():
        state.setdefault(key, value)
    state["call_ledger"] = {"plan": reference, "limits": limits, "calls": {}, "contexts": {}}


def reserve(state, route_id, call_id, brief, phase, setup_reference=None, review_snapshot=None):
    ledger = state["call_ledger"]
    reference = ledger["plan"]
    require(sha(reference["path"]) == reference["sha256"], "plan changed; reconcile authority before reservation")
    plan = json.loads(Path(reference["path"]).read_text())
    routes = [r for r in plan["routes"] if r["id"] == route_id]
    require(len(routes) == 1, "route is missing or ambiguous")
    brief = Path(brief).resolve()
    intent = {"route": routes[0], "input": {"path": str(brief), "sha256": sha(brief)},
              "phase": phase, "setup_reference": setup_reference}
    if review_snapshot is not None:
        import review_evidence
        snapshot = review_evidence.current_snapshot(review_snapshot)
        require(routes[0].get("role") == "reviewer", "only a reviewer can bind review evidence")
        if routes[0].get("input_path"):
            route_input = Path(routes[0]["input_path"])
            if not route_input.is_absolute():
                route_input = Path(snapshot["source"]["root"]) / route_input
            require(route_input.resolve() == Path(snapshot["contract"]["path"]).resolve(), "review contract differs from route input")
        intent["review_snapshot"] = {"path": str(Path(review_snapshot).resolve()), "sha256": sha(review_snapshot)}
    calls = ledger["calls"]
    if call_id in calls:
        require(calls[call_id]["intent"] == intent, "call ID already has different inputs")
        return calls[call_id]  # Reconciliation is required; this is not permission to dispatch again.
    require(not any(c["intent"]["route"]["id"] == route_id and c["status"] == "pending" for c in calls.values()),
            "route has a pending call; reconcile it before another reservation")
    attempts = state["attempts"]
    for key in ("total_role_calls", route_id):
        limit = ledger["limits"].get(key)
        require(limit is not None, f"missing approved ceiling for {key}")
        require(attempts.get(key, 0) < limit, f"call ceiling reached: {key}")
    for key in ("total_role_calls", route_id):
        attempts[key] = attempts.get(key, 0) + 1
    call = {"intent": intent, "status": "pending", "reserved_at": now()}
    calls[call_id] = call
    return call


def resolve_context(state, call_id, event_path):
    """Bind a host adapter's exact creation result; a setup token is never a task ID."""
    ledger = state["call_ledger"]
    call = ledger["calls"][call_id]
    event = json.loads(Path(event_path).read_text())
    require(call["status"] == "pending", "only a pending call can resolve setup")
    require(call["intent"]["setup_reference"] and event.get("setup_reference") == call["intent"]["setup_reference"],
            "host event does not match the queued setup reference")
    require(event.get("call_id") == call_id, "host event belongs to another call")
    context = event.get("context_id")
    require(isinstance(context, str) and context and not context.startswith("client-new-thread:"), "actual host context ID required")
    require(context != call["intent"]["setup_reference"], "setup token is not an actual context ID")
    evidence = event.get("evidence")
    require(isinstance(evidence, dict) and set(evidence) == {"path", "sha256"}
            and sha(evidence["path"]) == evidence["sha256"], "host event needs intact raw evidence")
    route = call["intent"]["route"]
    expected_host = route.get("native", {}).get("host")
    require(not expected_host or event.get("host") == expected_host, "host differs from approved route")
    require(all(key == route["id"] or value != context for key, value in ledger["contexts"].items()),
            "context belongs to another role")
    existing = ledger["contexts"].get(route["id"])
    require(existing is None or existing == context, "route already has another context")
    ledger["contexts"][route["id"]] = context
    call["context_event"] = {"path": str(Path(event_path).resolve()), "sha256": sha(event_path)}
    return context


def reconcile(state, call_id, receipt_path):
    ledger = state["call_ledger"]
    call = ledger["calls"][call_id]
    reference = {"path": str(Path(receipt_path).resolve()), "sha256": sha(receipt_path)}
    if call["status"] != "pending":
        require(call.get("receipt_ref") == reference, "completed call has a different receipt")
        return call
    receipt = json.loads(Path(receipt_path).read_text())
    execution = receipt.get("native_execution", receipt)
    if "dispatch_metadata" in receipt:
        execution = {**receipt["dispatch_metadata"], **receipt}
    route = call["intent"]["route"]
    require(execution.get("call_id") == call_id, "receipt belongs to another call")
    require(execution.get("input_revision") == call["intent"]["input"]["sha256"], "receipt input revision differs")
    require(execution.get("configured_model") == route["model"] and execution.get("configured_effort") == route.get("effort"),
            "receipt route differs")
    require(type(receipt.get("success")) is bool, "receipt needs explicit execution outcome")
    context = execution.get("context_id") or receipt.get("session_id")
    existing = ledger["contexts"].get(route["id"])
    require(not context or not existing or context == existing, "receipt does not resume the recorded role context")
    require(context or not receipt["success"], "successful receipt context is missing")
    if context:
        require(all(key == route["id"] or value != context for key, value in ledger["contexts"].items()),
                "receipt context belongs to another role")
        if receipt["success"]:
            ledger["contexts"][route["id"]] = context
    call.update(status="completed" if receipt["success"] else "failed", receipt_ref=reference,
                receipt={"metrics": normalize_metrics(receipt)}, completed_at=now())
    state["steps"].append({"step": call_id, "result": call["status"], "artifact": reference["path"]})
    return call


def complete(state, call_id, receipt_path):
    """Reconcile the actual receipt and its bound review in one retry-safe operation."""
    candidate = copy.deepcopy(state)
    call = reconcile(candidate, call_id, receipt_path)
    result = {"call_id": call_id, "execution_status": call["status"], "receipt": call["receipt_ref"]}
    receipt = json.loads(Path(receipt_path).read_text())
    if receipt["success"] and call["intent"]["route"].get("role") == "reviewer":
        import review_evidence
        binding = call["intent"].get("review_snapshot")
        require(binding and sha(binding["path"]) == binding["sha256"], "completion needs the snapshot bound before dispatch")
        snapshot = review_evidence.current_snapshot(binding["path"])
        review = review_evidence.record_review(binding["path"], json.loads(receipt.get("agent_message", "")), receipt)
        assessment = review_evidence.assess(binding["path"], snapshot["base_ref"])
        result.update(review={"path": str(review), "sha256": sha(review)}, review_status=assessment["status"], assessment=assessment)
        call["review"] = result["review"]
        call["review_status"] = assessment["status"]
    state.clear()
    state.update(candidate)
    return result


def status(state):
    ledger = state["call_ledger"]
    calls = ledger["calls"]
    tasks = {}
    for call in calls.values():
        task = call["intent"]["route"]["task_id"]
        tasks.setdefault(task, []).append(call)
    return {"run_id": state["run_id"], "phase": state["phase"], "status": state["status"],
            "attempts": state["attempts"],
            "calls": {key: {"status": value["status"], "route": value["intent"]["route"]["id"]} for key, value in calls.items()},
            "metrics_by_task": {key: aggregate_metrics(value) for key, value in tasks.items()}}


def summary(state):
    ledger = state["call_ledger"]
    counts = {"pending": 0, "completed": 0, "failed": 0, "other": 0}
    tasks = set()
    for call in ledger["calls"].values():
        value = call["status"]
        counts[value if value in counts else "other"] += 1
        tasks.add(call["intent"]["route"]["task_id"])
    used = state["attempts"].get("total_role_calls", 0)
    limit = ledger["limits"]["total_role_calls"]
    return {"run_id": state["run_id"], "phase": state["phase"], "status": state["status"],
            "task_count": len(tasks), "call_count": len(ledger["calls"]), "calls": counts,
            "total_role_calls": {"used": used, "limit": limit, "remaining": max(0, limit - used)}}


def call_summary(state, call_id):
    call = state["call_ledger"]["calls"][call_id]
    route = call["intent"]["route"]["id"]
    used = state["attempts"].get(route, 0)
    limit = state["call_ledger"]["limits"][route]
    return {"call_id": call_id, "route": route, "execution_status": call["status"],
            "remaining_route_calls": max(0, limit - used),
            "remaining_total_calls": max(0, state["call_ledger"]["limits"]["total_role_calls"]
                                         - state["attempts"].get("total_role_calls", 0))}


def status_query(state, args):
    if args.call:
        return {"call_id": args.call, "detail": state["call_ledger"]["calls"][args.call]}
    if args.details or args.task:
        require(1 <= args.limit <= 100 and args.offset >= 0, "use limit 1..100 and a nonnegative offset")
        calls = [(key, value) for key, value in state["call_ledger"]["calls"].items()
                 if not args.task or value["intent"]["route"]["task_id"] == args.task]
        page = calls[args.offset:args.offset + args.limit]
        result = {"total": len(calls), "offset": args.offset,
                  "next_offset": args.offset + len(page) if args.offset + len(page) < len(calls) else None,
                  "calls": [call_summary(state, key) for key, _ in page]}
        if args.metrics:
            result["metrics"] = aggregate_metrics([value for _, value in calls])
        return result
    if args.metrics:
        return {"metrics_by_task": status(state)["metrics_by_task"]}
    return summary(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="existing run-state.json location")
    parser.add_argument("--dry-run", action="store_true", help="validate without saving")
    commands = parser.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("--plan", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--limits", required=True, help="JSON file: total_role_calls and ceilings by route ID")
    reserve_parser = commands.add_parser("reserve")
    for name in ("route", "call", "brief", "phase"):
        reserve_parser.add_argument("--" + name, required=True)
    reserve_parser.add_argument("--setup-reference")
    reserve_parser.add_argument("--review-snapshot", help="bind a prepared snapshot for atomic review completion")
    for name, option in (("reconcile", "receipt"), ("complete", "receipt"), ("resolve-context", "event")):
        sub = commands.add_parser(name)
        sub.add_argument("--call", required=True)
        sub.add_argument("--" + option, required=True)
    query = commands.add_parser("status")
    selection = query.add_mutually_exclusive_group()
    selection.add_argument("--call", help="read one complete call record")
    selection.add_argument("--task", help="list calls for one task")
    selection.add_argument("--details", action="store_true", help="list a page of calls")
    query.add_argument("--offset", type=int, default=0)
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--metrics", action="store_true", help="aggregate stored usage only when requested")
    args = parser.parse_args()
    try:
        path = Path(args.state)
        def apply(state):
            if args.action == "status":
                return status_query(state, args)
            if args.action == "init":
                initialize(state, args.plan, args.run_id, json.loads(Path(args.limits).read_text()))
            elif args.action == "reserve":
                existed = args.call in state["call_ledger"]["calls"]
                reserve(state, args.route, args.call, args.brief, args.phase, args.setup_reference, args.review_snapshot)
                return {**call_summary(state, args.call), "reservation": "existing" if existed else "new"}
            elif args.action == "complete":
                require(not args.dry_run, "complete writes evidence; use receipt validation for a dry run")
                result = complete(state, args.call, args.receipt)
                result.pop("assessment", None)
                return {**call_summary(state, args.call), **result}
            elif args.action == "reconcile":
                reconcile(state, args.call, args.receipt)
            elif args.action == "resolve-context":
                resolve_context(state, args.call, args.event)
            return summary(state) if args.action == "init" else call_summary(state, args.call)
        if args.dry_run or args.action == "status":
            result = apply(json.loads(path.read_text()) if path.exists() else {})
        else:
            with locked(path) as state:
                result = apply(state)
        print(json.dumps({**result, "state_path": str(path.resolve())}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
