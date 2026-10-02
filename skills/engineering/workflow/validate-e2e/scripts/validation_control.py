#!/usr/bin/env python3
"""Reserve bounded validation attempts and assess captured evidence. Never dispatch work."""

import argparse
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BROWSER_MECHANISMS = {"playwright-test", "playwright-cli", "agent-browser", "playwright-mcp", "native"}


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
        if "browser_mechanism" in unit:
            require(unit["browser_mechanism"] in BROWSER_MECHANISMS, "unknown browser mechanism")
            require(unit.get("preflight_required") is True, "browser units require a driver preflight")
            require(isinstance(plan.get("working_dir"), str) and Path(plan["working_dir"]).is_absolute(),
                    "browser plan requires an absolute working_dir")
        if unit["required"]:
            covered.update(unit["requirements"])
    require(covered == set(reqs), "every requirement needs a required validation unit")
    routes = plan.get("routes", [])
    require(len({r["id"] for r in routes}) == len(routes), "duplicate route IDs")
    for route in routes:
        if "provider_routing" in route:
            from provider_routing import validate_provider_routing
            require(route.get("runner") == "pi" and route.get("mode", "runner") == "runner", "provider policy requires a Pi runner route")
            validate_provider_routing(route["provider_routing"])
        if "runner" in route and "model" in route:
            from model_routing import validate_selection
            validate_selection(route["runner"], route["model"], route.get("effort"))
        if "browser" in route:
            from browser_preflight import validate_browser_route
            require(route.get("runner") == "pi", "external browser route requires Pi")
            validate_browser_route(route["browser"])
    limits = plan.get("call_limits", {})
    require(positive(limits.get("total_role_calls")) and all(positive(limits.get(r["id"])) for r in routes), "positive role call ceilings required")
    refs = plan.get("inputs", [])
    require(refs, "bind the current acceptance source files")
    require(len({str(Path(r['path']).resolve()) for r in refs}) == len(refs), "duplicate input paths")
    verify_refs(refs)
    if "review_snapshot" in plan:
        snapshot = bound_snapshot(plan, current=False)
        required = {key for unit in units if unit["required"] for key in unit["checks"]}
        scope = snapshot["requirements"]["value"]
        check_ids, observation_ids = {row["id"] for row in scope["checks"]}, set(scope["observations"])
        require(not check_ids.intersection(observation_ids), "validation check and observation ids must be distinct")
        expected = check_ids | observation_ids
        require(required == expected, "required units must account for every shared check and observation")
        require(all(set(unit["checks"]) <= expected for unit in units), "unit contains unknown shared check or observation")
        require(not plan.get("working_dir") or str(Path(plan["working_dir"]).resolve()) == snapshot["source"]["root"],
                "validation workspace differs from the shared snapshot")


def bound_snapshot(plan, ref=None, current=True):
    from review_evidence import current_snapshot, load_record
    baseline_ref = plan["review_snapshot"]
    ref = baseline_ref if ref is None else ref
    require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, "invalid shared snapshot reference")
    verify_refs([ref])
    snapshot = current_snapshot(ref["path"]) if current else load_record(ref["path"])
    identity = snapshot["requirements"]["value"]["context"].get("identity", snapshot["requirements"]["value"]["context"])
    require({"runtime", "dependencies"} <= set(identity) and bool({"external_state", "services"} & set(identity)),
            "validation needs runtime, dependency, and external state identity")
    if ref != baseline_ref:
        verify_refs([baseline_ref])
        baseline = load_record(baseline_ref["path"])
        require(snapshot["source"]["root"] == baseline["source"]["root"] and snapshot["source"]["base"] == baseline["source"]["base"],
                "validation source root or intended base changed")
        require(snapshot["contract"]["sha256"] == baseline["contract"]["sha256"], "validation acceptance contract changed")
        expected, observed = baseline["requirements"]["value"], snapshot["requirements"]["value"]
        require({key: value for key, value in expected.items() if key != "context"}
                == {key: value for key, value in observed.items() if key != "context"}, "validation required scope changed")
    return snapshot


def checked_result(plan, unit, result, snapshot_ref=None):
    """Validate captured facts without replacing independent review judgment."""
    from review_evidence import load_packet, validate_check, check_definition
    snapshot_ref = snapshot_ref or plan["review_snapshot"]
    snapshot = bound_snapshot(plan, snapshot_ref)
    require(result.get("evidence_packet"), "shared captured evidence packet is required")
    packet = load_packet(result["evidence_packet"], snapshot, snapshot_ref["path"], allow_partial=True)
    observations = {row["id"]: row for row in packet["observations"]}
    require(set(unit["checks"]) <= set(packet["checks"]) | set(observations), "unit packet is missing planned check or observation ids")
    statuses = {}
    for key in unit["checks"]:
        if key in packet["checks"]:
            passed = validate_check(packet["checks"][key], snapshot, check_definition(snapshot, key))
            statuses[key] = "passed" if passed else "failed"
        else:
            statuses[key] = {"pass": "passed", "fail": "failed", "skipped": "skipped"}[observations[key]["result"]]
    require(result["checks"] == statuses, "declared statuses differ from captured command or browser results")
    return packet


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
    if "review_snapshot" in plan:
        bound_snapshot(plan)
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
    if "review_snapshot" in plan:
        bound_snapshot(plan, intent["input"])
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
        if "browser_mechanism" in unit:
            check_browser_preflight(plan, unit, read(latest["record"]["path"]))
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
    unit = next(u for u in plan["units"] if u["id"] == unit_id)
    if "browser_mechanism" in unit:
        check_browser_preflight(plan, unit, result)
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


def check_browser_preflight(plan, unit, result):
    require(result.get("mechanism") == unit["browser_mechanism"], "preflight browser mechanism differs from the approved unit")
    require(result.get("working_dir") == str(Path(plan["working_dir"]).resolve()), "preflight browser workspace differs")
    if result["status"] == "ready" and unit["browser_mechanism"] in {"playwright-cli", "agent-browser"}:
        from browser_preflight import validate_preflight
        validate_preflight(result, unit["browser_mechanism"], plan["working_dir"])


def reserve_role(state, ledger, route_id, call_id, brief, phase):
    plan = load_plan(state)
    calls = state["call_ledger"]["calls"]
    existed = call_id in calls
    if not existed:
        require(utc() < deadline(plan), "deadline reached")
        require(sum(c["status"] == "pending" for c in calls.values()) < plan["budgets"]["max_parallel"], "parallel role ceiling reached")
        route = next(r for r in plan["routes"] if r["id"] == route_id)
        if "browser" in route:
            from browser_preflight import load_bound_preflight
            require(plan.get("working_dir"), "browser route requires working_dir")
            load_bound_preflight(route["browser"], plan["working_dir"])
    ledger.reserve(state, route_id, call_id, brief, phase)
    return {"reservation": "existing" if existed else "new", "call_id": call_id}


def finish(state, attempt_id, path):
    plan = load_plan(state)
    attempt = state["validation"]["attempts"][attempt_id]
    ref = {"path": str(Path(path).resolve()), "sha256": digest(path)}
    completed = attempt["status"] != "pending"
    if completed:
        require(attempt.get("result") == ref, "completed attempt has a different result")
    result = read(path)
    require(result["attempt_id"] == attempt_id, "result belongs to another attempt")
    require(result["input_sha256"] == attempt["intent"]["input"]["sha256"], "result input does not match reserved snapshot")
    unit = next(u for u in plan["units"] if u["id"] == attempt["intent"]["unit"])
    if "browser_mechanism" in unit:
        require(result.get("browser_mechanism") == unit["browser_mechanism"], "result browser mechanism differs from the approved unit")
    checks = result["checks"]
    require(isinstance(checks, dict) and set(checks) == set(unit["checks"]), "result must account for every planned check")
    require(all(v in ("passed", "failed", "blocked", "skipped") for v in checks.values()), "invalid check status")
    if "review_snapshot" in plan:
        checked_result(plan, unit, result, attempt["intent"]["input"])
    require(result.get("evidence") or result.get("evidence_packet") and "review_snapshot" in plan, "captured evidence required")
    verify_refs(result.get("evidence", []))
    if any(v != "passed" for v in checks.values()):
        require(result.get("reason"), "nonpass result needs a reason")
    status = next((s for s in ("failed", "blocked", "skipped") if s in checks.values()), "passed")
    if completed:
        require(attempt["status"] == status, "completed status differs from captured evidence")
        return
    attempt.update(status=status, result=ref, finished_at=utc().isoformat())
    state["steps"].append({"step": attempt_id, "result": status, "artifact": ref["path"]})


def summarize(state):
    plan = load_plan(state)
    attempts = state["validation"]["attempts"]
    last = {a["intent"]["unit"]: a for a in attempts.values()}
    last_ids = {a["intent"]["unit"]: key for key, a in attempts.items()}
    units = {}
    for unit in plan["units"]:
        entry = last.get(unit["id"])
        status = entry["status"] if entry else "pending"
        if entry and entry.get("result"):
            verify_refs([entry["intent"]["input"], entry["result"]])
            result = read(entry["result"]["path"])
            require(result["attempt_id"] == last_ids[unit["id"]] and result["input_sha256"] == entry["intent"]["input"]["sha256"],
                    "validation result binding differs")
            require(entry["status"] == next((s for s in ("failed", "blocked", "skipped") if s in result["checks"].values()), "passed"),
                    "validation status differs from captured result")
            verify_refs(result.get("evidence", []))
            if "review_snapshot" in plan:
                checked_result(plan, unit, result, entry["intent"]["input"])
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
    if status == "passed" and "review_snapshot" not in plan:
        status = "blocked"
    return {"status": status, "units": units, "required_passed": required.count("passed"),
            "required_total": len(required), "attempts_used": len(attempts), "pending_role_calls": pending_calls,
            "evidence_kind": "shared-captured" if "review_snapshot" in plan else "context-only",
            "deadline": plan["budgets"]["deadline"]}


def export_evidence(state, output):
    """Bridge completed direct captures to shared review without promoting generic reports."""
    from review_evidence import prepare_packet, evidence_link
    plan = load_plan(state)
    require("review_snapshot" in plan, "historical generic evidence is context only; run fresh shared captures")
    require(summarize(state)["status"] == "passed", "validation is incomplete or has failed required evidence")
    last = {a["intent"]["unit"]: a for a in state["validation"]["attempts"].values()}
    checks, observations, snapshot_ref = {}, {}, None
    for unit in plan["units"]:
        if not unit["required"]:
            continue
        entry = last[unit["id"]]
        require(snapshot_ref is None or snapshot_ref == entry["intent"]["input"], "all required units must bind one current snapshot before export")
        snapshot_ref = entry["intent"]["input"]
        packet = checked_result(plan, unit, read(entry["result"]["path"]), snapshot_ref)
        for key, path in packet["checks"].items():
            if key not in unit["checks"]:
                continue
            require(key not in checks or checks[key] == path, "validation units reference different command captures")
            checks[key] = path
        for row in packet["observations"]:
            if row["id"] not in unit["checks"]:
                continue
            require(row["id"] not in observations or observations[row["id"]] == row, "validation units reference different browser captures")
            observations[row["id"]] = row
    path = prepare_packet(snapshot_ref["path"], output, checks, list(observations.values()))
    return {"snapshot": snapshot_ref, "evidence_packet": evidence_link(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shared-dir", required=True, type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="check without saving")
    sub = parser.add_subparsers(dest="action", required=True)
    preview = sub.add_parser("preview-models", help="resolve recommendations before checking execution availability")
    preview.add_argument("--route", action="append", required=True)
    preview.add_argument("--profile", default="default")
    preview.add_argument("--local-profile")
    preview.add_argument("--risk", choices=("normal", "high"), default="normal")
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
    bridge = sub.add_parser("evidence-packet", help="export checked direct captures for shared review; legacy reports remain context")
    bridge.add_argument("--output", required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.shared_dir / "scripts"))
    if args.action == "preview-models":
        try:
            routing = importlib.import_module("model_routing")
            config_path = (args.shared_dir / "model-routing.json").resolve()
            config = routing.load_config(config_path)
            names = list(dict.fromkeys(args.route))
            require(all(name.startswith("validation-") or name == "test-execution" for name in names),
                    "preview requires validation routes or test-execution")
            routes = [routing.resolve_profile(name, None if args.profile == "default" else args.profile, local_profile=args.local_profile,
                                              risk=args.risk, config=config) for name in names]
            print(json.dumps({"status": "resolved", "profile": routes[0]["profile"],
                              "config_path": str(config_path), "config_digest": routing.config_digest(config),
                              "skill_path": str(Path(__file__).resolve().parents[1]),
                              "availability_checked": False, "routes": routes}))
            return 0
        except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
            print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
            return 2
    if args.state is None:
        parser.error("--state is required except for preview-models")
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
        elif args.action == "evidence-packet":
            require(not args.dry_run, "evidence-packet writes an immutable artifact; omit --dry-run")
            return export_evidence(state, args.output)
        return summarize(state)
    try:
        if args.dry_run or args.action in {"summary", "evidence-packet"}:
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
