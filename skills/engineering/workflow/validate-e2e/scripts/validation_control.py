#!/usr/bin/env python3
"""Reserve bounded validation attempts and assess captured evidence. Never dispatch work."""

import argparse
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def utc():
    return datetime.now(timezone.utc)


def deadline(plan):
    value = datetime.fromisoformat(plan["budgets"]["deadline"].replace("Z", "+00:00"))
    require(value.tzinfo is not None, "deadline needs a timezone")
    return value


def positive(value):
    return type(value) is int and value > 0


def validate_plan(plan):
    require(plan.get("version") == 1, "unsupported validation plan")
    require(plan.get("approval", {}).get("status") == "approved" and
            plan["approval"].get("reference"), "record actual user approval before initialization")
    require(plan.get("mode") in ("assess", "repair"), "mode must be assess or repair")
    require(isinstance(plan.get("run_id"), str) and plan["run_id"], "run_id is required")
    scope = plan["scope"]
    require(type(scope.get("discovery_closed")) is bool, "explicit discovery_closed is required")
    reqs = scope["requirements"]
    require(reqs and all(isinstance(r, str) and r for r in reqs) and len(set(reqs)) == len(reqs),
            "requirement IDs must be nonempty and unique")
    budgets = plan["budgets"]
    require(all(positive(budgets.get(k)) for k in ("total_attempts", "max_parallel")), "positive budgets required")
    require(positive(budgets.get("max_preflights", budgets["total_attempts"])), "positive preflight ceiling required")
    deadline(plan)
    units = plan["units"]
    require(units and len({u["id"] for u in units}) == len(units), "unit IDs must be unique")
    covered = set()
    for unit in units:
        require(isinstance(unit["id"], str) and unit["id"], "unit ID is required")
        require(unit["requirements"] and set(unit["requirements"]) <= set(reqs), "unknown or empty requirement mapping")
        require(type(unit.get("required")) is bool, "explicit required flag is required")
        require(unit["checks"] and all(isinstance(c, str) and c for c in unit["checks"])
                and len(set(unit["checks"])) == len(unit["checks"]), "check IDs must be nonempty and unique")
        require(positive(unit.get("max_attempts")), "positive unit attempt limit required")
        recovery = unit.get("recovery_attempts", {})
        require(isinstance(recovery, dict) and set(recovery) <= {"test_repair", "evidence_repair", "product_repair"}
                and all(positive(v) for v in recovery.values()), "invalid recovery allowance")
        require("product_repair" not in recovery or plan["mode"] == "repair", "product repair requires repair authority")
        require(type(unit.get("preflight_required", False)) is bool, "invalid preflight requirement")
        if unit["required"]:
            covered.update(unit["requirements"])
    require(covered == set(reqs), "every requirement needs a required validation unit")
    routes = plan.get("routes", [])
    require(len({r["id"] for r in routes}) == len(routes), "duplicate route IDs")
    limits = plan.get("call_limits", {})
    require(positive(limits.get("total_role_calls")) and all(positive(limits.get(r["id"])) for r in routes), "positive role call ceilings required")
    refs = plan.get("inputs", [])
    require(refs, "bind the current acceptance source files")
    require(len({str(Path(r['path']).resolve()) for r in refs}) == len(refs), "duplicate input paths")
    verify_refs(refs)


def verify_refs(refs):
    for ref in refs:
        require(Path(ref["path"]).is_absolute(), "evidence paths must be absolute")
        require(digest(ref["path"]) == ref["sha256"], f"input or evidence changed: {ref['path']}")


def load_plan(state):
    ref = state["validation"]["plan"]
    require(digest(ref["path"]) == ref["sha256"], "approved plan changed; preserve the run and reconcile scope")
    plan = read(ref["path"])
    validate_plan(plan)
    return plan


def initialize(state, path, ledger):
    plan = read(path)
    validate_plan(plan)
    ref = {"path": str(Path(path).resolve()), "sha256": digest(path)}
    if "validation" in state:
        require(state["validation"]["plan"] == ref, "existing run has a different plan")
        return
    require(not state, "use an empty state or resume the existing validation run")
    state.update(skill="validate-e2e", run_id=plan["run_id"])
    ledger.initialize(state, path, plan["run_id"], plan["call_limits"])
    state["validation"] = {"plan": ref, "attempts": {}}
    state["ceilings"].update(plan["budgets"])


def reserve(state, unit_id, attempt_id, input_path, reason, kind="validation"):
    plan = load_plan(state)
    units = [u for u in plan["units"] if u["id"] == unit_id]
    require(len(units) == 1, "unknown unit")
    unit = units[0]
    attempts = state["validation"]["attempts"]
    intent = {"unit": unit_id, "input": {"path": str(Path(input_path).resolve()), "sha256": digest(input_path)}, "reason": reason}
    if kind != "validation":
        intent["kind"] = kind
    if attempt_id in attempts:
        require(attempts[attempt_id]["intent"] == intent, "attempt ID has different inputs")
        return {"reservation": "existing", "attempt": attempts[attempt_id]}
    require(utc() < deadline(plan), "deadline reached")
    prior = [a for a in attempts.values() if a["intent"]["unit"] == unit_id]
    require(not any(a["status"] == "pending" for a in prior), "reconcile pending unit before another attempt")
    allowed = unit["max_attempts"] if kind == "validation" else unit.get("recovery_attempts", {}).get(kind, 0)
    require(allowed > 0, "recovery category is not approved")
    require(sum(a["intent"].get("kind", "validation") == kind for a in prior) < allowed, "unit attempt ceiling reached")
    require(kind == "validation" or reason.strip(), "recovery needs a reason")
    preflights = [p for p in state["validation"].get("preflights", {}).values() if p["unit"] == unit_id]
    if unit.get("preflight_required") or preflights:
        require(preflights, "preflight is required before execution")
        latest = preflights[-1]
        verify_refs([latest["input"], latest["record"]])
        verify_refs(read(latest["record"]["path"])["evidence"])
        require(latest["input"] == intent["input"], "preflight input changed")
        require(latest["status"] == "ready", "preflight is blocked; no business attempt reserved")
    require(len(attempts) < plan["budgets"]["total_attempts"], "total attempt ceiling reached")
    require(sum(a["status"] == "pending" for a in attempts.values()) < plan["budgets"]["max_parallel"], "parallel ceiling reached")
    if prior:
        require(reason.strip(), "retry needs a new hypothesis or changed input reason")
        require(prior[-1]["status"] != "passed" or prior[-1]["intent"]["input"]["sha256"] != intent["input"]["sha256"],
                "unchanged passed unit must reuse evidence")
    attempts[attempt_id] = {"intent": intent, "status": "pending", "reserved_at": utc().isoformat()}
    state["attempts"]["validation_attempts"] = len(attempts)
    state["phase"] = unit_id
    return {"reservation": "new", "attempt": attempts[attempt_id]}


def record_preflight(state, unit_id, preflight_id, input_path, result_path):
    plan = load_plan(state)
    require(any(u["id"] == unit_id for u in plan["units"]), "unknown preflight unit")
    result = read(result_path)
    require(result.get("status") in {"ready", "blocked"} and result.get("evidence"), "preflight needs status and evidence")
    require(result.get("reason"), "preflight needs a reason")
    verify_refs(result["evidence"])
    entry = {"unit": unit_id, "status": result["status"],
             "input": {"path": str(Path(input_path).resolve()), "sha256": digest(input_path)},
             "record": {"path": str(Path(result_path).resolve()), "sha256": digest(result_path)}}
    records = state["validation"].setdefault("preflights", {})
    if preflight_id in records:
        require(records[preflight_id] == entry, "preflight id has different evidence")
        return {"reservation": "existing", **entry}
    require(utc() < deadline(plan), "deadline reached")
    require(len(records) < plan["budgets"].get("max_preflights", plan["budgets"]["total_attempts"]), "preflight ceiling reached")
    records[preflight_id] = entry
    return {"reservation": "new", **entry}


def reserve_role(state, ledger, route_id, call_id, brief, phase):
    plan = load_plan(state)
    calls = state["call_ledger"]["calls"]
    existed = call_id in calls
    if not existed:
        require(utc() < deadline(plan), "deadline reached")
        require(sum(c["status"] == "pending" for c in calls.values()) < plan["budgets"]["max_parallel"], "parallel role ceiling reached")
    ledger.reserve(state, route_id, call_id, brief, phase)
    return {"reservation": "existing" if existed else "new", "call_id": call_id}


def finish(state, attempt_id, path):
    plan = load_plan(state)
    attempt = state["validation"]["attempts"][attempt_id]
    ref = {"path": str(Path(path).resolve()), "sha256": digest(path)}
    if attempt["status"] != "pending":
        require(attempt.get("result") == ref, "completed attempt has a different result")
        return
    result = read(path)
    require(result["attempt_id"] == attempt_id, "result belongs to another attempt")
    require(result["input_sha256"] == attempt["intent"]["input"]["sha256"], "result input does not match reserved snapshot")
    unit = next(u for u in plan["units"] if u["id"] == attempt["intent"]["unit"])
    checks = result["checks"]
    require(isinstance(checks, dict) and set(checks) == set(unit["checks"]), "result must account for every planned check")
    require(all(v in ("passed", "failed", "blocked", "skipped") for v in checks.values()), "invalid check status")
    require(result.get("evidence"), "captured evidence required")
    verify_refs(result["evidence"])
    if any(v != "passed" for v in checks.values()):
        require(result.get("reason"), "nonpass result needs a reason")
    status = next((s for s in ("failed", "blocked", "skipped") if s in checks.values()), "passed")
    attempt.update(status=status, result=ref, finished_at=utc().isoformat())
    state["steps"].append({"step": attempt_id, "result": status, "artifact": ref["path"]})


def summarize(state):
    plan = load_plan(state)
    attempts = state["validation"]["attempts"]
    last = {a["intent"]["unit"]: a for a in attempts.values()}
    units = {}
    for unit in plan["units"]:
        entry = last.get(unit["id"])
        status = entry["status"] if entry else "pending"
        if entry and entry.get("result"):
            verify_refs([entry["intent"]["input"], entry["result"]])
            verify_refs(read(entry["result"]["path"])["evidence"])
        preflights = [p for p in state["validation"].get("preflights", {}).values() if p["unit"] == unit["id"]]
        if preflights:
            verify_refs([preflights[-1]["input"], preflights[-1]["record"]])
            verify_refs(read(preflights[-1]["record"]["path"])["evidence"])
            if preflights[-1]["status"] == "blocked":
                status = "blocked"
        units[unit["id"]] = {"status": status, "required": unit["required"]}
    required = [v["status"] for v in units.values() if v["required"]]
    calls = state["call_ledger"]["calls"].values()
    pending_calls = sum(c["status"] == "pending" for c in calls)
    pending_attempts = sum(a["status"] == "pending" for a in attempts.values())
    if all(s == "passed" for s in required) and plan["scope"]["discovery_closed"] and not pending_calls and not pending_attempts:
        status = "passed"
    elif "failed" in required:
        status = "failed"
    elif "blocked" in required or not plan["scope"]["discovery_closed"]:
        status = "blocked"
    elif utc() >= deadline(plan) or len(attempts) >= plan["budgets"]["total_attempts"]:
        status = "ceiling_hit"
    else:
        status = "partial"
    return {"status": status, "units": units, "required_passed": required.count("passed"),
            "required_total": len(required), "attempts_used": len(attempts), "pending_role_calls": pending_calls,
            "deadline": plan["budgets"]["deadline"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true", help="check without saving")
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init"); init.add_argument("--plan", required=True)
    start = sub.add_parser("reserve")
    for name in ("unit", "attempt", "input"):
        start.add_argument("--" + name, required=True)
    start.add_argument("--reason", default="")
    start.add_argument("--kind", choices=("validation", "test_repair", "evidence_repair", "product_repair"), default="validation")
    preflight = sub.add_parser("preflight", help="record driver or service readiness without consuming a business attempt")
    for name in ("unit", "id", "input", "result"):
        preflight.add_argument("--" + name, required=True)
    end = sub.add_parser("finish"); end.add_argument("--attempt", required=True); end.add_argument("--result", required=True)
    role = sub.add_parser("reserve-role")
    for name in ("route", "call", "brief", "phase"):
        role.add_argument("--" + name, required=True)
    sub.add_parser("summary")
    args = parser.parse_args()
    sys.path.insert(0, str(args.shared_dir / "scripts"))
    ledger = importlib.import_module("run_state")
    def apply(state):
        if args.action == "init":
            initialize(state, args.plan, ledger)
        elif args.action == "reserve":
            return reserve(state, args.unit, args.attempt, args.input, args.reason, args.kind)
        elif args.action == "preflight":
            return record_preflight(state, args.unit, args.id, args.input, args.result)
        elif args.action == "reserve-role":
            return reserve_role(state, ledger, args.route, args.call, args.brief, args.phase)
        elif args.action == "finish":
            finish(state, args.attempt, args.result)
        return summarize(state)
    try:
        if args.dry_run or args.action == "summary":
            output = apply(read(args.state) if args.state.exists() else {})
        else:
            with ledger.locked(args.state) as state:
                output = apply(state)
        print(json.dumps(output))
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
