#!/usr/bin/env python3
"""Consume local workflow events and propose host actions without dispatching work.

Examples:
  workflow_controller.py preview --root PROJECT --queue queue.json \
    --routing-plan plan.json --ledger run-state.json --checkpoint controller.json --events events.jsonl
  workflow_controller.py apply [same arguments]
  workflow_controller.py wait [same arguments] --timeout 30
  workflow_controller.py ack --checkpoint controller.json --id ACTION_ID

Preview and wait are read only. Apply reconciles receipts and saves an action outbox.
Acknowledge delivered actions with ack after their host effect or receipt delivery.
All results are JSON. Event data never becomes a command or a host tool call.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
import run_state
import task_queue
import usage_accounting

VERSION = 1
MAX_LINE = 65536
TASK = re.compile(r"T[1-9][0-9]*\Z")


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_object(path):
    value = json.loads(Path(path).read_text())
    require(isinstance(value, dict), f"expected a JSON object: {path}")
    return value


def load_checkpoint(path):
    value = read_object(path) if Path(path).exists() else {}
    require(not value or value.get("schema_version") == VERSION, "unsupported controller checkpoint version")
    return value


def text(value, field):
    require(isinstance(value, str) and bool(value.strip()), f"{field} must be a nonempty string")


def normalize_event(event):
    require(isinstance(event, dict), "event must be an object")
    kind = event.get("kind")
    common = {"id", "kind", "source", "cursor"}
    fields = {"status": {"call_id", "status"}, "receipt": {"call_id", "receipt"},
              "decision": {"task_id", "status"}, "wake": set()}
    require(isinstance(kind, str) and kind in fields, "unsupported event kind")
    require(set(event) == common | fields[kind], "event fields differ from the normalized event schema")
    for field in ("id", "source", "cursor"):
        text(event[field], field)
    if kind in {"status", "receipt"}:
        text(event["call_id"], "call_id")
    if kind == "status":
        require(event["status"] in {"running", "completed", "failed", "cancelled", "waiting_user"}, "unsupported worker status")
    elif kind == "decision":
        require(isinstance(event["task_id"], str) and TASK.fullmatch(event["task_id"]), "invalid decision task_id")
        require(event["status"] in {"waiting", "resolved"}, "unsupported decision status")
    elif kind == "receipt":
        ref = event["receipt"]
        require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "receipt needs path and sha256")
        text(ref["path"], "receipt.path")
        require(isinstance(ref["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", ref["sha256"]), "invalid receipt sha256")
    return event


def read_events(path, checkpoint, limit=100):
    """Read complete appended lines. Keep an anchor to detect source replacement."""
    require(type(limit) is int and 1 <= limit <= 1000, "event limit must be 1..1000")
    path = Path(path).resolve()
    source = checkpoint.get("event_source", {})
    if source:
        require(source["path"] == str(path), "checkpoint belongs to another event source")
    if not path.exists():
        require(not source.get("offset", 0), "event source is missing after checkpoint")
        return [], [{"path": str(path), "offset": 0}], False
    with path.open("rb") as stream:
        stat = os.fstat(stream.fileno())
        identity = [stat.st_dev, stat.st_ino]
        require(not source.get("identity") or source["identity"] == identity, "event source was replaced; restore its append-only history")
        offset = source.get("offset", 0)
        require(type(offset) is int and 0 <= offset <= stat.st_size, "event source was truncated")
        if source.get("anchor"):
            anchor = source["anchor"]
            stream.seek(anchor["start"])
            require(hashlib.sha256(stream.read(offset - anchor["start"])).hexdigest() == anchor["sha256"], "event source checkpoint anchor changed")
        stream.seek(offset)
        result = []
        next_source = {**source, "path": str(path), "identity": identity, "offset": offset}
        positions = [copy.deepcopy(next_source)]
        while len(result) < limit:
            start = stream.tell()
            line = stream.readline(MAX_LINE + 1)
            require(len(line) <= MAX_LINE, "event line exceeds 64 KiB")
            if not line or not line.endswith(b"\n"):
                break
            event = normalize_event(json.loads(line))
            result.append(event)
            next_source.update(offset=stream.tell(), anchor={"start": start, "sha256": hashlib.sha256(line).hexdigest()})
            positions.append(copy.deepcopy(next_source))
        more = next_source["offset"] < stat.st_size and len(result) == limit
        return result, positions, more


def consume(state, checkpoint, events, root):
    """Reconcile into copies. Receipt checks remain owned by run_state."""
    state = copy.deepcopy(state)
    checkpoint = copy.deepcopy(checkpoint)
    checkpoint.setdefault("schema_version", VERSION)
    seen = checkpoint.setdefault("seen", {})
    cursors = checkpoint.setdefault("cursors", {})
    observed = checkpoint.setdefault("observed", {})
    decisions = checkpoint.setdefault("decisions", {})
    issues = checkpoint.setdefault("receipt_issues", {})
    reconciled = []
    consumed = 0
    calls = state.get("call_ledger", {}).get("calls", {})
    require(isinstance(calls, dict), "ledger calls must be an object")
    for event in events:
        normalize_event(event)
        key = json.dumps([event["source"], event["id"]], separators=(",", ":"))
        fingerprint = digest(event)
        if key in seen:
            require(seen[key] == fingerprint, "event ID was reused with different facts")
            consumed += 1
            continue
        kind = event["kind"]
        if kind in {"status", "receipt"}:
            call_id = event["call_id"]
            require(call_id in calls, f"event call is absent from the approved ledger: {call_id}")
            if kind == "status":
                observed[call_id] = event["status"]
            else:
                reference = event["receipt"]
                receipt = Path(reference["path"])
                receipt = (receipt if receipt.is_absolute() else Path(root) / receipt).resolve()
                try:
                    require(run_state.sha(receipt) == reference["sha256"], "receipt checksum differs")
                    candidate = copy.deepcopy(state)
                    prior = copy.deepcopy(calls[call_id])
                    run_state.reconcile(candidate, call_id, receipt)
                    state = candidate
                    calls = state["call_ledger"]["calls"]
                    issues.pop(call_id, None)
                    if calls[call_id] != prior:
                        reconciled.append(call_id)
                except (ValueError, OSError, KeyError, TypeError) as error:
                    issues[call_id] = str(error)
                    break
        elif kind == "decision":
            decisions[event["task_id"]] = event["status"]
        seen[key] = fingerprint
        cursors[event["source"]] = event["cursor"]
        consumed += 1
    return state, checkpoint, reconciled, consumed


def task_id(call):
    return call.get("intent", {}).get("route", {}).get("task_id")


def project(state, checkpoint, schedule, *, unapplied=False):
    """Return changed host proposals. Queue acceptance is used without substitution."""
    budget = usage_accounting.evaluate_budget(state)
    current = {}
    calls = state.get("call_ledger", {}).get("calls", {})
    waiting = {key for key, value in checkpoint.get("decisions", {}).items() if value == "waiting"}
    for call_id, observed in checkpoint.get("observed", {}).items():
        call = calls[call_id]
        if observed == "waiting_user" and call.get("status") == "pending":
            if task_id(call):
                waiting.add(task_id(call))
        if call.get("status") == "pending" and observed in {"completed", "failed", "cancelled"}:
            current["receipt:" + call_id] = {"kind": "receipt_required", "call_id": call_id,
                                            "observed_status": observed, "retry_allowed": False}
    for call_id, reason in checkpoint.get("receipt_issues", {}).items():
        current["invalid:" + call_id] = {"kind": "receipt_invalid", "call_id": call_id, "reason": reason, "retry_allowed": False}
    for call_id, call in calls.items():
        if call.get("status") in {"completed", "failed"}:
            current["call:" + call_id] = {"kind": "call_completed" if call["status"] == "completed" else "call_failed",
                                         "call_id": call_id, "task_id": task_id(call)}
            route = call.get("intent", {}).get("route", {})
            if call["status"] == "completed" and route.get("role") == "reviewer" and not call.get("review"):
                current["review:" + call_id] = {"kind": "review_completion_required", "call_id": call_id}
    for identity in sorted(waiting, key=task_queue.task_sort_key):
        current["decision:" + identity] = {"kind": "user_decision", "task_id": identity}
    budget_signature = {key: budget.get(key) for key in ("decision", "dispatch_allowed", "reasons", "resume_at")}
    current["budget"] = {"kind": "usage_budget", **budget_signature}
    if budget["dispatch_allowed"] and not unapplied:
        for task in schedule.get("ready", []):
            if task["id"] not in waiting:
                current["ready:" + task["id"]] = {"kind": "ready", "task_id": task["id"]}
    if schedule.get("required_integration"):
        current["integration"] = {"kind": "integration_required", "tasks": schedule["required_integration"]}
    if schedule.get("blocked"):
        current["blocked"] = {"kind": "queue_blocked", "tasks": schedule["blocked"]}
    if schedule.get("error"):
        current["queue_error"] = {"kind": "queue_error", "reason": schedule["error"]}
    for identity in schedule.get("integrated", []):
        current["integrated:" + identity] = {"kind": "task_integrated", "task_id": identity}
    previous = checkpoint.get("projection", {})
    proposals = [("actions", "action:" + key, digest(current[key]), copy.deepcopy(current[key]))
                 for key in sorted(current) if previous.get(key) != current[key]]
    for key in sorted(set(previous) - set(current)):
        proposals.append(("actions", "action:" + key, None, {"kind": "cleared", "key": key}))
    sidebar = sidebar_projection(schedule, waiting)
    previous_sidebar = checkpoint.get("sidebar", {})
    for identity in sidebar["order"]:
        if previous_sidebar.get("tasks", {}).get(identity) != sidebar["tasks"][identity]:
            proposals.append(("sidebar_actions", "sidebar:status:" + identity, digest(sidebar["tasks"][identity]),
                              {"kind": "set_task_status", "task_id": identity, **sidebar["tasks"][identity]}))
    if previous_sidebar.get("order") != sidebar["order"]:
        proposals.append(("sidebar_actions", "sidebar:order", digest(sidebar["order"]),
                          {"kind": "reorder_tasks", "task_ids": sidebar["order"]}))
    validity = {"action:" + key: digest(value) for key, value in current.items()}
    validity.update({"sidebar:status:" + key: digest(value) for key, value in sidebar["tasks"].items()})
    validity["sidebar:order"] = digest(sidebar["order"])
    delivery = update_outbox(checkpoint, proposals, validity)
    checkpoint["projection"] = current
    checkpoint["sidebar"] = sidebar
    return {**delivery, "dispatch_allowed": budget["dispatch_allowed"] and not unapplied,
            "budget": budget_signature}


def update_outbox(checkpoint, proposals, validity):
    """Keep unacknowledged occurrences; retire stale proposals without executing them."""
    outbox = checkpoint.setdefault("outbox", {})
    for channel, slot, expected, action in proposals:
        sequence = checkpoint.get("action_sequence", 0) + 1
        checkpoint["action_sequence"] = sequence
        action["id"] = digest({"binding": checkpoint.get("binding"), "sequence": sequence,
                               "channel": channel, "action": action})[:24]
        outbox[action["id"]] = {"channel": channel, "slot": slot, "expected": expected,
                                "action": action, "superseded": False}
    delivery = {"actions": [], "sidebar_actions": [], "superseded_action_ids": []}
    for identity, entry in outbox.items():
        if validity.get(entry["slot"]) != entry["expected"]:
            entry["superseded"] = True
        if entry["superseded"]:
            delivery["superseded_action_ids"].append(identity)
        else:
            delivery[entry["channel"]].append(copy.deepcopy(entry["action"]))
    return delivery


def acknowledge(checkpoint_path, identities):
    """Acknowledge only explicit IDs after delivery; repeating an acknowledgement is safe."""
    require(isinstance(identities, list) and identities and all(isinstance(value, str) and value for value in identities),
            "acknowledgement requires nonempty action IDs")
    with lock(checkpoint_path):
        checkpoint = load_checkpoint(checkpoint_path)
        require(bool(checkpoint), "controller checkpoint is missing")
        outbox = checkpoint.get("outbox", {})
        acknowledged = checkpoint.setdefault("acknowledged_actions", [])
        require(all(value in outbox or value in acknowledged for value in identities), "unknown action acknowledgement ID")
        newly = []
        for identity in dict.fromkeys(identities):
            if identity in outbox:
                del outbox[identity]
                acknowledged.append(identity)
                newly.append(identity)
        if newly:
            run_state.atomic_write(checkpoint_path, checkpoint)
        return {"schema_version": VERSION, "status": "acknowledged", "acknowledged": list(dict.fromkeys(identities)),
                "new_acknowledgements": len(newly), "pending_actions": len(outbox)}


def sidebar_projection(schedule, waiting):
    tasks = {}
    for group in ("ready", "active", "blocked"):
        for row in schedule.get(group, []):
            tasks[row["id"]] = {"status": "active", "icon": "🧑‍💻"}
    for identity in schedule.get("integrated", []):
        tasks[identity] = {"status": "complete", "icon": "✅"}
    for identity in waiting:
        if identity in tasks and tasks[identity]["status"] != "complete":
            tasks[identity] = {"status": "waiting", "icon": "❓"}
    rank = {"waiting": 0, "active": 1, "complete": 2}
    order = sorted(tasks, key=lambda key: (rank[tasks[key]["status"]], task_queue.task_sort_key(key)))
    return {"tasks": tasks, "order": order}


@contextlib.contextmanager
def lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def cycle(args, apply=False):
    root = Path(args.root).resolve()
    checkpoint_path = Path(args.checkpoint).resolve()
    ledger_path = Path(args.ledger).resolve()
    require(checkpoint_path not in {ledger_path, Path(args.events).resolve(), Path(args.queue).resolve(), Path(args.routing_plan).resolve()},
            "checkpoint must be separate from inputs")
    checkpoint = load_checkpoint(checkpoint_path)
    binding = {"root": str(root), "ledger": str(ledger_path), "queue": str(Path(args.queue).resolve()),
               "routing_plan": str(Path(args.routing_plan).resolve())}
    require(not checkpoint.get("binding") or checkpoint["binding"] == binding, "checkpoint belongs to another workflow")
    checkpoint["binding"] = binding
    before = read_object(ledger_path)
    events, positions, more = read_events(args.events, checkpoint, args.limit)
    state, candidate, reconciled, consumed = consume(before, checkpoint, events, root)
    source = positions[consumed]
    candidate["event_source"] = source
    stalled = consumed < len(events)
    if apply and state != before:
        run_state.atomic_write(ledger_path, state)
    try:
        schedule = task_queue.schedule(args.queue, args.routing_plan, args.ledger, args.root)
    except (ValueError, OSError, KeyError, TypeError) as error:
        schedule = {"error": str(error)}
    result = project(state, candidate, schedule, unapplied=not apply and state != before)
    for action in [*result["actions"], *result["sidebar_actions"]]:
        action["persisted"] = apply or action["id"] in checkpoint.get("outbox", {})
    if apply:
        run_state.atomic_write(checkpoint_path, candidate)
    changed = bool(result["actions"] or result["sidebar_actions"] or result["superseded_action_ids"])
    return {"schema_version": VERSION, "status": "actionable" if changed else "unchanged", "mode": "apply" if apply else "preview",
            "cursor": source["offset"], "cursors": candidate.get("cursors", {}), "more": more and not stalled, "event_blocked": stalled,
            "reconciled_calls": reconciled, "checkpoint_saved": apply, **result}


def input_signature(args):
    values = []
    for name in ("events", "ledger", "queue", "routing_plan"):
        path = Path(getattr(args, name))
        try:
            stat = path.stat()
            values.append((stat.st_ino, stat.st_size, stat.st_mtime_ns))
        except FileNotFoundError:
            values.append(None)
    return values


def wait(args):
    require(0 <= args.timeout <= 60, "timeout must be 0..60 seconds")
    require(0.05 <= args.interval <= 5, "interval must be 0.05..5 seconds")
    deadline = time.monotonic() + args.timeout
    result = cycle(args)
    if result["status"] == "actionable" or result["more"]:
        return result
    signature = input_signature(args)
    while time.monotonic() < deadline:
        time.sleep(min(args.interval, max(0, deadline - time.monotonic())))
        observed = input_signature(args)
        if observed != signature:
            result = cycle(args)
            if result["status"] == "actionable" or result["more"]:
                return result
            signature = observed
    budget = usage_accounting.evaluate_budget(read_object(args.ledger))
    if any(budget.get(key) != result["budget"].get(key) for key in ("decision", "dispatch_allowed", "reasons", "resume_at")):
        result = cycle(args)
        if result["status"] == "actionable":
            return result
    return {"schema_version": VERSION, "status": "timeout", "mode": "preview", "cursor": result["cursor"],
            "cursors": result["cursors"], "actions": [], "sidebar_actions": [], "superseded_action_ids": [], "checkpoint_saved": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "apply", "wait"):
        sub = commands.add_parser(name)
        for flag in ("root", "queue", "routing-plan", "ledger", "checkpoint", "events"):
            sub.add_argument("--" + flag, required=True)
        sub.add_argument("--limit", type=int, default=100, help="maximum complete event lines, 1..1000")
        if name == "wait":
            sub.add_argument("--timeout", type=float, default=30, help="local wait, 0..60 seconds")
            sub.add_argument("--interval", type=float, default=0.25, help="local file check interval, 0.05..5 seconds")
    ack_parser = commands.add_parser("ack", help="acknowledge delivered action occurrence IDs")
    ack_parser.add_argument("--checkpoint", required=True)
    ack_parser.add_argument("--id", dest="action_ids", action="append", required=True, help="repeat for each delivered or superseded action")
    args = parser.parse_args(argv)
    if args.command == "ack":
        try:
            result = acknowledge(Path(args.checkpoint).resolve(), args.action_ids)
            print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
            return 0
        except (ValueError, OSError, KeyError, TypeError) as error:
            print(json.dumps({"schema_version": VERSION, "status": "blocked", "error": str(error)}, ensure_ascii=False))
            return 2
    args.root = str(Path(args.root).resolve())
    for name in ("queue", "routing_plan", "ledger", "checkpoint", "events"):
        path = Path(getattr(args, name))
        setattr(args, name, str((path if path.is_absolute() else Path(args.root) / path).resolve()))
    try:
        if args.command == "apply":
            require(Path(args.checkpoint).resolve() != Path(args.ledger).resolve(), "checkpoint must be separate from ledger")
            with lock(args.checkpoint), lock(args.ledger):
                result = cycle(args, apply=True)
        elif args.command == "wait":
            result = wait(args)
        else:
            result = cycle(args)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"schema_version": VERSION, "status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
