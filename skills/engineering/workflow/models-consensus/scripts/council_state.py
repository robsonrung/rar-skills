#!/usr/bin/env python3
"""Reserve and reconcile an approved council. This CLI never dispatches model calls."""

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

for ancestor in Path(__file__).resolve().parents:
    shared_scripts = ancestor / "shared" / "scripts"
    if (shared_scripts / "run_state.py").is_file():
        sys.path.insert(0, str(shared_scripts))
        break
else:
    raise SystemExit("shared/scripts/run_state.py is required beside the installed skills")
import run_state as ledger
import runner_jobs
import native_completion
from review_evidence import load_record
from execution_metrics import aggregate_metrics, normalize_metrics, FIELDS
from model_receipt import attach_model_receipt
from output_contract import _decode_exactly_one_json, validate_document, validate_schema
from cmux_council import validate_role_scope, require_token

SCHEMAS = {
    "poll": {"opening": "opening-answer", "organizer": "organizer-analysis",
             "gap_repair": "disagreement-round", "judge": "judge", "synthesis": "synthesis"},
    "debate": {"opening": "round1-response", "later_round": "later-round-response", "synthesis": "synthesis"},
    "personas": {"advisor": "opening-answer", "reviewer": "persona-review", "chairman": "persona-chairman"},
}
require = ledger.require


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def scope(document):
    require(isinstance(document, dict), "approval state must be an object")
    require_token(document.get("session_id"), "session id")
    require(isinstance(document.get("question"), str) and document["question"].strip(), "question is required")
    require(document.get("mode") in SCHEMAS, "unknown council mode")
    preview = copy.deepcopy(document.get("preview"))
    require(isinstance(preview, dict), "preview is required")
    preview.pop("scope_fingerprint", None)
    return {"session_id": document["session_id"], "question": document["question"],
            "mode": document["mode"], "preview": preview}


def fingerprint(document):
    return digest(scope(document))


def positive(value, label, zero=False):
    require(type(value) is int and value >= (0 if zero else 1), f"{label} must be a positive integer" if not zero else f"{label} must be a nonnegative integer")
    return value


def plan_from(document):
    frozen = scope(document)
    preview = frozen["preview"]
    approved_digest = fingerprint(document)
    require(document.get("approval", {}).get("status") == "approved", "explicit council approval is required")
    require(document["approval"].get("scope_fingerprint") == approved_digest
            and document["preview"].get("scope_fingerprint") == approved_digest, "approval fingerprint differs")
    validate_role_scope(preview)
    require(preview.get("transport") == "per_call", "use the terminal adapter for cmux plans")
    require(preview.get("tool_profile") in {"no_tools", "repo_read_only", "research_read_only"}, "read-only tool profile is required")
    positive(preview.get("output_cap_tokens"), "output cap")
    roles = preview["roles"]
    base = positive(preview.get("base_calls"), "base calls")
    conditional = positive(preview.get("conditional_calls"), "conditional calls", zero=True)
    retries = positive(preview.get("validation_retry_ceiling"), "validation retry ceiling", zero=True)
    maximum = positive(preview.get("maximum_calls"), "maximum calls")
    require(base + conditional == len(roles), "base and conditional calls must cover every planned step")
    require(retries <= len(roles) and maximum == len(roles) + retries, "maximum calls must include the exact retry ceiling")
    limits = preview.get("reported_limits", {})
    require(isinstance(limits, dict) and not set(limits) - set(FIELDS), "unknown reported usage limit")
    for key, value in limits.items():
        require(type(value) in (int, float) and value > 0 and value < float("inf"), f"positive reported limit required: {key}")
    if "elapsed_seconds" in preview:
        positive(preview["elapsed_seconds"], "elapsed seconds")
    seats = preview["seats"]
    models = {s["requested_model"] for s in seats}
    require((frozen["mode"] == "personas" and len(seats) == len(models) == 1)
            or (frozen["mode"] != "personas" and len(seats) == len(models) == 3), "mode requires the approved seat count and model diversity")
    execution = preview.get("execution", [])
    require(isinstance(execution, list) and all(isinstance(x, dict) for x in execution), "execution entries are required")
    executions = {e["call"]: e for e in execution}
    require(len(executions) == len(execution) and set(executions) == {r["call"] for r in roles}, "execution entries must exactly match planned steps")
    routes, steps = {}, {}
    for role in roles:
        step_id = role["call"]
        stage = role["role"]
        require(stage in SCHEMAS[frozen["mode"]], f"unsupported stage: {stage}")
        context_key = require_token(role.get("continuity_key"), "continuity key")
        route_execution = executions[step_id]
        require(route_execution.get("continuity_key") == context_key, "execution continuity key differs")
        require(route_execution.get("transport") in {"native", "runner"}, "native or runner transport is required")
        if route_execution["transport"] == "runner":
            require(isinstance(route_execution.get("runner"), str) and route_execution["runner"], "runner execution needs its exact runner")
            require(route_execution.get("runner_role") in {"planner", "codereviewer", "synthesizer", "adversarial", "challenger", "researcher"}, "runner execution needs a read-only runner role")
        require(route_execution.get("session_policy") == "persistent_same_role"
                and route_execution.get("resume_policy") == "recorded_context_only", "persistent same-role resume is required")
        require(all(isinstance(route_execution.get(k), str) and route_execution[k] for k in ("host", "execution_path")), "host and execution path are required")
        if route_execution["transport"] == "runner":
            allowed = route_execution.get("allowed_tools", [] if preview["tool_profile"] == "no_tools" else None)
            servers = route_execution.get("allowed_mcp_servers", [])
            require(isinstance(allowed, list) and all(isinstance(t, str) for t in allowed), "approved runner tool names are required")
            require(isinstance(servers, list) and all(isinstance(t, str) for t in servers), "approved server names must be a list")
            require(preview["tool_profile"] != "no_tools" or not allowed and not servers, "no_tools cannot allow tools or servers")
        route = {"id": context_key, "task_id": frozen["session_id"], "model": role["requested_model"],
                 "effort": role["effort"], "effort_control": role["effort_control"], "seat": role["seat"],
                 "role": role.get("context_role", stage), "execution": {k: v for k, v in route_execution.items() if k != "call"},
                 "tool_policy": preview["tool_profile"]}
        if context_key in routes:
            # Only the opening seat may continue into its gap repair or debate round.
            require(stage in {"gap_repair", "later_round"} and routes[context_key]["role"] == "opening", "independent roles need separate continuity keys")
            route["role"] = "opening"
            require(route == routes[context_key], "same context has different route controls")
        else:
            require(stage not in {"gap_repair", "later_round"}, "later stages must resume an opening context")
            require(route["role"] == stage, "context role must match its first stage")
            routes[context_key] = route
        schema_name = SCHEMAS[frozen["mode"]][stage]
        schema = _decode_exactly_one_json((Path(__file__).resolve().parents[1] / "schemas" / (schema_name + ".schema.json")).read_text())
        validate_schema(schema)
        steps[step_id] = {"route_id": context_key, "stage": stage, "schema": schema,
                          "output_cap_tokens": positive(role.get("output_cap_tokens", preview["output_cap_tokens"]), "step output cap")}
    conditional_count = 0
    for role in roles:
        step = steps[role["call"]]
        dependencies = role.get("depends_on")
        require(isinstance(dependencies, list) and all(isinstance(d, str) and d in steps and d != role["call"] for d in dependencies)
                and len(dependencies) == len(set(dependencies)), "step dependencies must name other approved steps")
        require(not dependencies if step["stage"] in {"opening", "advisor"} else bool(dependencies), "stage dependencies are missing or break opening isolation")
        is_conditional = role.get("conditional", False)
        require(type(is_conditional) is bool, "conditional must be boolean")
        conditional_count += is_conditional
        step.update(depends_on=dependencies, conditional=is_conditional)
    require(conditional_count == conditional, "conditional call count differs from planned steps")
    visited, active = set(), set()
    def visit(step_id):
        require(step_id not in active, "step dependency cycle")
        if step_id not in visited:
            active.add(step_id)
            for dependency in steps[step_id]["depends_on"]:
                visit(dependency)
            active.remove(step_id)
            visited.add(step_id)
    for step_id in steps:
        visit(step_id)
    ceilings = {"total_role_calls": maximum}
    for route_id in routes:
        ceilings[route_id] = sum(s["route_id"] == route_id for s in steps.values()) * (2 if retries else 1)
    return {"approval": copy.deepcopy(document["approval"]), "scope": frozen, "scope_fingerprint": approved_digest,
            "routes": list(routes.values()), "steps": steps, "limits": ceilings}


def store_json(directory, value, label):
    path = Path(directory) / f"{label}-{digest(value)}.json"
    if path.exists():
        require(json.loads(path.read_text()) == value, "stored artifact changed")
    else:
        try:
            ledger.atomic_write(path, value, exclusive=True)
        except FileExistsError:
            require(json.loads(path.read_text()) == value, "stored artifact changed")
    return {"path": str(path.resolve()), "sha256": ledger.sha(path)}


def store_raw(directory, raw, label="receipt"):
    """Publish exact receipt bytes once, including during interrupted recovery."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (label + "-" + hashlib.sha256(raw).hexdigest() + ".json")
    fd, temporary = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            require(path.read_bytes() == raw, "stored receipt changed")
    finally:
        os.unlink(temporary)
    return path


def initialize(state, state_path, approval_path):
    document = json.loads(Path(approval_path).read_text())
    if "council" in state:
        frozen = read_plan(state)
        require(scope(document) == frozen["scope"] and document.get("approval") == frozen["approval"]
                and document["preview"].get("scope_fingerprint") == frozen["scope_fingerprint"], "existing council has different approval")
        return
    require(not state, "existing non-council state cannot be replaced")
    # If publication completed before a crash, reuse the original schemas after an upgrade.
    directory = Path(str(Path(state_path).resolve()) + ".artifacts")
    plan_path = directory / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        require(plan["scope"] == scope(document) and plan["approval"] == document.get("approval")
                and plan["scope_fingerprint"] == fingerprint(document)
                and document["preview"].get("scope_fingerprint") == plan["scope_fingerprint"], "saved plan differs from approval")
    else:
        plan = plan_from(document)
        ledger.atomic_write(plan_path, plan, exclusive=True)
    state.update(skill="models-consensus", council={"version": 1, "artifacts": str(directory), "steps": {}, "skipped": {}, "retries": 0})
    ledger.initialize(state, plan_path, plan["scope"]["session_id"], plan["limits"])


def read_plan(state):
    require(state.get("council", {}).get("version") == 1, "unsupported council state version; preserve this file")
    reference = state["call_ledger"]["plan"]
    require(ledger.sha(reference["path"]) == reference["sha256"], "immutable council plan changed")
    return json.loads(Path(reference["path"]).read_text())


def step_status(state, step_id):
    if step_id in state["council"].get("skipped", {}):
        return "skipped"
    calls = state["council"]["steps"].get(step_id, [])
    return state["call_ledger"]["calls"][calls[-1]]["council"]["response_status"] if calls else "not_started"


def refresh_status(state, plan):
    statuses = [step_status(state, step) for step in plan["steps"]]
    if all(s in {"valid", "skipped"} for s in statuses):
        state.update(status="completed", phase="completed")
    elif "pending" in statuses:
        state.update(status="running", phase="awaiting_results")
    elif "blocked_receipt" in statuses:
        state.update(status="failed", phase="receipt_blocked")
    elif any(step_status(state, step) in {"malformed", "execution_failed"}
             and (len(state["council"]["steps"].get(step, [])) >= 2
                  or state["council"]["retries"] >= plan["scope"]["preview"]["validation_retry_ceiling"]
                  or (not state["call_ledger"]["contexts"].get(plan["steps"][step]["route_id"])
                      and not first_context_recovery(state, plan["steps"][step]["route_id"])))
             for step in plan["steps"]):
        state.update(status="failed", phase="recovery_exhausted")
    else:
        state.update(status="running", phase="prepared")


def skip(state, step_id, reason):
    plan = read_plan(state)
    require(step_id in plan["steps"] and plan["steps"][step_id]["conditional"], "only an approved conditional step can be skipped")
    require(isinstance(reason, str) and reason.strip(), "skip reason is required")
    require(not state["council"]["steps"].get(step_id), "an attempted step cannot be skipped")
    skipped = state["council"].setdefault("skipped", {})
    require(step_id not in skipped or skipped[step_id] == reason, "skip reason already recorded")
    skipped[step_id] = reason
    refresh_status(state, plan)
    return {"step": step_id, "status": "skipped", "reason": reason}


def budget_status(state, plan):
    measurements = aggregate_metrics(list(state["call_ledger"]["calls"].values()))
    preview = plan["scope"]["preview"]
    return {"response_cap": {"tokens": preview["output_cap_tokens"], "enforcement": "advisory"},
            "reported_limits": preview.get("reported_limits", {}), "measurements": measurements,
            "elapsed_seconds": (datetime.now(timezone.utc) - datetime.fromisoformat(state["started_at"])).total_seconds()}


def budget_gate(state, plan):
    budget = budget_status(state, plan)
    for key, limit in budget["reported_limits"].items():
        metric = budget["measurements"][key]
        require(metric["measured_sum"] < limit, f"reported budget exhausted: {key}")
        require(metric["unknown_calls"] == 0, f"reported budget has unknown usage: {key}")
    elapsed_limit = plan["scope"]["preview"].get("elapsed_seconds")
    require(elapsed_limit is None or budget["elapsed_seconds"] < elapsed_limit, "elapsed time budget exhausted")


def proven_no_dispatch(receipt, call):
    """A dedicated prelaunch marker plus consistent actual evidence permits first setup."""
    route = call["intent"]["route"]
    execution = route["execution"]
    if (execution["transport"] != "runner" or receipt.get("print_invocation_started") is not False
            or receipt.get("success") is not False or receipt.get("terminal_status") != "preflight_blocked"
            or not isinstance(receipt.get("preflight"), dict) or receipt["preflight"].get("blocked") is not True):
        return False
    if type(receipt.get("return_code")) is not int or receipt["return_code"] == 0:
        return False
    evidence = receipt["preflight"].get("evidence")
    if not isinstance(evidence, dict) or type(evidence.get("provider_calls")) is not int or evidence["provider_calls"] != 0:
        return False
    expected = {"configured_model": route["model"], "effort": execution.get("effort_value", route["effort"]),
                "effective_runner": execution["runner"], "role": execution["runner_role"], "tool_profile": route["tool_policy"]}
    if any(key not in receipt or receipt[key] != value for key, value in expected.items()):
        return False
    if any(receipt.get(key) for key in ("session_id", "context_id", "session_file", "resume", "agent_message", "stdout",
                                         "fallback_reason", "effective_model", "native_model_id", "primary_model_ids", "event_log")):
        return False
    if call["council"].get("context_id") or call.get("context_event"):
        return False
    for name in ("model_receipt", "tool_profile_receipt"):
        proof = receipt.get(name) or {}
        if not isinstance(proof, dict) or proof.get("status") not in {None, "unverified"}:
            return False
        if name == "model_receipt" and proof.get("observed_model"):
            return False
        if name == "tool_profile_receipt" and (proof.get("observed_tools") is not None or proof.get("observed_mcp_servers") is not None):
            return False
    for metrics in (normalize_metrics(receipt), normalize_metrics({k: v for k, v in receipt.items() if k != "metrics"})):
        if any(value is not None and value != 0 for key, value in metrics.items() if key != "duration_ms"):
            return False
    return True


def first_context_recovery(state, route_id):
    calls = [call for call in state["call_ledger"]["calls"].values() if call["intent"]["route"]["id"] == route_id]
    if not calls or state["call_ledger"]["contexts"].get(route_id):
        return False
    for call in calls:
        if call["status"] != "failed" or call["council"].get("response_status") != "execution_failed":
            return False
        reference = call["council"].get("raw_receipt")
        intact(reference)
        receipt = json.loads(Path(reference["path"]).read_text())
        if not proven_no_dispatch(receipt, call):
            return False
    return True


def reserve(state, step_id, call_id, brief):
    plan = read_plan(state)
    require_token(call_id, "call id")
    require(step_id in plan["steps"], "step is absent from approved plan")
    step = plan["steps"][step_id]
    calls = state["call_ledger"]["calls"]
    brief = store_raw(state["council"]["artifacts"], Path(brief).read_bytes(), "input")
    existing = calls.get(call_id)
    if existing:
        require(existing["council"]["step"] == step_id, "call belongs to another step")
        ledger.reserve(state, step["route_id"], call_id, brief, step["stage"], "council:" + call_id)
        return {"reservation": "existing", "dispatch_allowed": False, "call_id": call_id, "status": existing["status"]}
    require(step_id not in state["council"].get("skipped", {}), "step was skipped")
    require(all(step_status(state, dependency) in {"valid", "skipped"} for dependency in step["depends_on"]), "step prerequisites are not complete")
    budget_gate(state, plan)
    history = state["council"]["steps"].get(step_id, [])
    require(not history or calls[history[-1]]["council"].get("response_status") in {"malformed", "execution_failed"}, "step is completed or pending")
    context = state["call_ledger"]["contexts"].get(step["route_id"])
    route_history = [c for c in calls.values() if c["intent"]["route"]["id"] == step["route_id"]]
    require(not route_history or context or first_context_recovery(state, step["route_id"]),
            "recorded role context is unavailable; do not start a replacement")
    if history:
        require(len(history) == 1 and state["council"]["retries"] < plan["scope"]["preview"]["validation_retry_ceiling"], "validation retry ceiling reached")
    call = ledger.reserve(state, step["route_id"], call_id, brief, step["stage"], "council:" + call_id)
    if history:
        state["council"]["retries"] += 1
    state["council"]["steps"].setdefault(step_id, []).append(call_id)
    route = call["intent"]["route"]
    execution = route["execution"]
    dispatch = {"call_id": call_id, "input_revision": call["intent"]["input"]["sha256"],
                "configured_model": route["model"], "configured_effort": route["effort"],
                "role": route["role"], "task_id": route["task_id"], "tool_policy": route["tool_policy"],
                "host": execution["host"], "transport": execution["transport"],
                "execution_path": execution["execution_path"], "context_id": context,
                "scope_fingerprint": plan["scope_fingerprint"], "step": step_id,
                "response_cap": {"tokens": step["output_cap_tokens"], "enforcement": "advisory"}}
    dispatch_ref = store_json(state["council"]["artifacts"], dispatch, "dispatch")
    call["council"] = {"step": step_id, "schema_digest": digest(step["schema"]), "dispatch": dispatch_ref,
                       "response_status": "pending", "context_id": context}
    refresh_status(state, plan)
    return {"reservation": "new", "dispatch_allowed": True, "call_id": call_id, "dispatch": dispatch_ref,
            "context_id": context, "response_cap": dispatch["response_cap"]}


def intact(reference):
    require(isinstance(reference, dict) and ledger.sha(reference["path"]) == reference["sha256"], "evidence changed or is missing")


def bind(state, call_id, event_path):
    read_plan(state)
    call = state["call_ledger"]["calls"][call_id]
    event = json.loads(Path(event_path).read_text())
    route = call["intent"]["route"]
    require(event.get("input_revision") == call["intent"]["input"]["sha256"], "event input revision differs")
    require(event.get("host") == route["execution"]["host"] and event.get("transport") == route["execution"]["transport"], "event execution path differs")
    context = ledger.resolve_context(state, call_id, event_path)
    if "job_id" in event:
        require(route["execution"]["transport"] == "runner" and isinstance(event.get("working_dir"), str), "runner job needs its working directory")
        job = {"working_dir": str(Path(event["working_dir"]).resolve()), "job_id": require_token(event["job_id"], "job id")}
        require(not call["council"].get("job") or call["council"]["job"] == job, "bound runner job differs")
        call["council"]["job"] = job
    call["council"]["context_id"] = context
    return {"call_id": call_id, "context_id": context}


def runner_tool_error(receipt, route):
    proof = receipt.get("tool_profile_receipt")
    if not isinstance(proof, dict) or proof.get("status") != "verified":
        return "runner tool policy lacks verified startup evidence"
    if proof.get("profile") != route["tool_policy"] or proof.get("errors") != []:
        return "runner tool proof differs from approved profile"
    allowed = route["execution"].get("allowed_tools", [])
    servers = route["execution"].get("allowed_mcp_servers", [])
    for key, approved in (("observed_tools", allowed), ("observed_mcp_servers", servers)):
        observed = proof.get(key)
        if not isinstance(observed, list) or any(not isinstance(item, str) or item not in approved for item in observed):
            return "runner exposed an unapproved tool or server"
    return None


def reconcile(state, call_id, receipt_path):
    plan = read_plan(state)
    call = state["call_ledger"]["calls"][call_id]
    raw = Path(receipt_path).read_bytes()
    receipt = json.loads(raw)
    if isinstance(receipt, dict) and set(receipt) == {"payload", "sha256"}:
        receipt = load_record(receipt_path)
    require(isinstance(receipt, dict), "receipt must be an object")
    if call["status"] != "pending":
        require(hashlib.sha256(raw).hexdigest() == call["council"]["raw_receipt"]["sha256"], "completed call has a different receipt")
        for key in ("raw_receipt", "artifact"):
            if key in call["council"]:
                intact(call["council"][key])
        return {"call_id": call_id, "status": call["council"]["response_status"], "reconciled": "existing"}
    intact(call["intent"]["input"])
    intact(call["council"]["dispatch"])
    require(call["council"]["schema_digest"] == digest(plan["steps"][call["council"]["step"]]["schema"]), "schema snapshot differs")
    dispatch = json.loads(Path(call["council"]["dispatch"]["path"]).read_text())
    execution = receipt.get("native_execution", receipt.get("dispatch_metadata", receipt))
    require(isinstance(execution, dict), "receipt execution must be an object")
    required = ("call_id", "input_revision", "configured_model", "configured_effort", "host", "transport", "role", "task_id", "tool_policy")
    require(all(k in execution and execution[k] == dispatch[k] for k in required), "receipt dispatch binding differs")
    if dispatch["transport"] == "runner":
        route_execution = call["intent"]["route"]["execution"]
        for key in ("call_id", "input_revision", "configured_model", "configured_effort", "host", "transport", "tool_policy"):
            require(key not in receipt or receipt[key] == dispatch[key], "receipt dispatch binding differs")
        if receipt.get("success") is True:
            require(receipt.get("configured_model") == dispatch["configured_model"], "actual configured model is missing or differs")
            require(receipt.get("effective_runner") == route_execution["runner"], "actual runner differs")
            effort = receipt.get("effort", receipt.get("thinking", receipt.get("configured_effort")))
            expected_effort = route_execution.get("effort_value", dispatch["configured_effort"])
            require(effort == expected_effort, "actual effort differs")
            require(receipt.get("tool_profile") == dispatch["tool_policy"], "actual tool profile differs")
            require(receipt.get("role") == route_execution["runner_role"], "actual runner role differs")
    if dispatch["transport"] == "native":
        evidence = receipt.get("evidence", {})
        require("raw" in evidence and "dispatch" in evidence, "native completion needs raw host and dispatch evidence")
        for reference in evidence.values():
            intact(reference)
        require(evidence["dispatch"] == call["council"]["dispatch"], "native dispatch evidence differs")
        require(execution.get("host_id") == dispatch["host"], "native host id differs")
        if receipt.get("success") is True:
            with tempfile.TemporaryDirectory() as temporary:
                captured = native_completion.capture(evidence["raw"]["path"], evidence["dispatch"]["path"],
                                                    execution.get("context_id"), execution.get("host_id"),
                                                    execution.get("turn_id"), execution.get("completed_turn"),
                                                    Path(temporary) / "capture.json")
                observed = load_record(captured)
            prior = [c["council"] for key, c in state["call_ledger"]["calls"].items()
                     if key != call_id and c["intent"]["route"]["id"] == call["intent"]["route"]["id"]]
            require(all(c.get("turn_id") != execution.get("turn_id") for c in prior), "native turn was already consumed")
            require(all(c.get("completed_turn", 0) < execution["completed_turn"] for c in prior), "native completed turn did not advance")
            require(all(receipt.get(k) == observed[k] for k in ("success", "agent_message", "native_execution", "metrics")),
                    "native receipt differs from exact host completion")
    if dispatch["transport"] == "native":
        context = execution.get("context_id")
    else:
        context = receipt.get("session_id") or receipt.get("context_id")
        require(not receipt.get("session_id") or not receipt.get("context_id")
                or receipt["session_id"] == receipt["context_id"], "actual session and context evidence differ")
    known_context = state["call_ledger"]["contexts"].get(call["intent"]["route"]["id"])
    require(not known_context or context == known_context, "receipt does not resume the recorded role context")
    if context:
        require(isinstance(context, str) and not context.startswith("client-new-thread:"), "actual context id required")
    candidate = copy.deepcopy(state)
    saved_receipt = store_raw(state["council"]["artifacts"], raw)
    semantic = copy.deepcopy(receipt)
    if dispatch["transport"] == "runner":
        # Metadata describes intent. Only actual session evidence can bind continuity.
        semantic["context_id"] = context
    semantic_receipt = store_json(state["council"]["artifacts"], semantic, "envelope")
    ledger.reconcile(candidate, call_id, semantic_receipt["path"])
    stored = candidate["call_ledger"]["calls"][call_id]
    if context:
        # Keep the context even when the provider reports a failed turn.
        candidate["call_ledger"]["contexts"][call["intent"]["route"]["id"]] = context
    serving_receipt = receipt.get("model_receipt") or {}
    require(isinstance(serving_receipt, dict), "model receipt must be an object")
    source = serving_receipt.get("source", "not_observed")
    provenance = attach_model_receipt(copy.deepcopy(receipt), dispatch["configured_model"], observed_source=source)
    if dispatch["transport"] == "native":
        # The supported wait capture has no serving-model attestation.
        provenance["model_receipt"] = {"status": "unverified", "source": "not_observed", "observed_model": None}
    proof = provenance["model_receipt"]
    policy_error = "receipt used an unapproved fallback" if receipt.get("fallback_reason") else None
    if dispatch["transport"] == "runner" and receipt["success"]:
        policy_error = policy_error or runner_tool_error(receipt, call["intent"]["route"])
    tool_receipt = receipt.get("tool_profile_receipt")
    if isinstance(tool_receipt, dict) and tool_receipt.get("status") == "violated":
        policy_error = "receipt reports a tool policy violation"
    if proof["status"] == "verified" and proof["observed_model"] != dispatch["configured_model"]:
        policy_error = "observed model differs from approved model"
    if (plan["scope"]["preview"]["serving_receipt"] == "required" and proof["status"] != "verified"
            and not proven_no_dispatch(receipt, call)):
        policy_error = "required serving proof is missing"
    response_status, error, value = "execution_failed", receipt.get("error"), None
    if receipt["success"]:
        try:
            value = _decode_exactly_one_json(receipt.get("agent_message", ""), allow_prose_fence=True)
            require(isinstance(value, dict), "council response must be a JSON object")
            schema = plan["steps"][call["council"]["step"]]["schema"]
            validation = validate_document(value, schema)
            require(validation.valid, validation.error)
            response_status = "valid"
        except (ValueError, TypeError, AttributeError) as exc:
            response_status, error, value = "malformed", str(exc), None
    if policy_error:
        response_status, error = "blocked_receipt", policy_error
    artifact = {"call_id": call_id, "step": call["council"]["step"], "status": response_status,
                "response": value, "error": error, "model_receipt": proof,
                "schema_digest": call["council"]["schema_digest"],
                "raw_receipt": {"path": str(saved_receipt.resolve()), "sha256": ledger.sha(saved_receipt)}}
    stored["council"].update(response_status=response_status, context_id=context,
                              raw_receipt=artifact["raw_receipt"], model_receipt=proof,
                              artifact=store_json(state["council"]["artifacts"], artifact, "response"))
    if dispatch["transport"] == "native" and receipt["success"]:
        stored["council"].update(turn_id=execution["turn_id"], completed_turn=execution["completed_turn"])
    state.clear()
    state.update(candidate)
    refresh_status(state, plan)
    return {"call_id": call_id, "status": response_status, "artifact": stored["council"]["artifact"], "reconciled": "new"}


def observe(state):
    read_plan(state)
    pending = {key: value["council"]["job"] for key, value in state["call_ledger"]["calls"].items()
               if value["status"] == "pending" and value["council"].get("job")}
    observations = runner_jobs.observe_many([(j["working_dir"], j["job_id"]) for j in pending.values()])
    return {call: {"job_id": job["job_id"], "status": observations[(job["working_dir"], job["job_id"])]["status"],
                   "dispatch_allowed": False} for call, job in pending.items()}


def status(state):
    plan = read_plan(state)
    return {**ledger.summary(state), "budget": budget_status(state, plan),
            "skipped": state["council"].get("skipped", {}),
            "steps": {step: [{"call_id": call, "status": state["call_ledger"]["calls"][call]["council"]["response_status"]}
                             for call in calls] for step, calls in state["council"]["steps"].items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", help="persistent council state path")
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("fingerprint", "init"):
        sub = commands.add_parser(name)
        sub.add_argument("--approval-state", required=True)
    sub = commands.add_parser("reserve")
    for name in ("step", "call", "brief"):
        sub.add_argument("--" + name, required=True)
    for action, option in (("reconcile", "receipt"), ("bind", "event")):
        sub = commands.add_parser(action)
        sub.add_argument("--call", required=True)
        sub.add_argument("--" + option, required=True)
    sub = commands.add_parser("skip")
    sub.add_argument("--step", required=True)
    sub.add_argument("--reason", required=True)
    commands.add_parser("observe")
    commands.add_parser("status")
    args = parser.parse_args()
    try:
        if args.action == "fingerprint":
            result = {"scope_fingerprint": fingerprint(json.loads(Path(args.approval_state).read_text()))}
        else:
            require(args.state, "--state is required")
            if args.action in {"status", "observe"}:
                state = json.loads(Path(args.state).read_text())
                result = status(state) if args.action == "status" else observe(state)
            else:
                with ledger.locked(args.state) as state:
                    if args.action == "init":
                        initialize(state, args.state, args.approval_state)
                        result = status(state)
                    elif args.action == "reserve":
                        result = reserve(state, args.step, args.call, args.brief)
                    elif args.action == "skip":
                        result = skip(state, args.step, args.reason)
                    elif args.action == "bind":
                        result = bind(state, args.call, args.event)
                    else:
                        result = reconcile(state, args.call, args.receipt)
        print(json.dumps(result))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
