#!/usr/bin/env python3
"""Validate explicit feature review policies and captured acceptance evidence."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

import review_evidence as evidence


def local_file(root, value, label):
    evidence.require(isinstance(value, str), f"{label} must be a relative file path")
    path = evidence.safe_path(root, value)
    evidence.require(value == Path(value).as_posix() and value != "." and path.is_file()
                     and not path.is_symlink() and path.resolve().is_relative_to(root),
                     f"{label} must name a source file inside root")
    return path.resolve()


def check_plan(policy, root):
    plan = evidence.read_json(local_file(root, policy["check_plan"], "check_plan"))
    evidence.require(isinstance(plan, dict) and set(plan) == {"requirements", "required_checks", "interactions"},
                     "check_plan needs requirements, required_checks, and interactions")
    requirements = plan["requirements"]
    evidence.require(isinstance(requirements, dict) and "check_contract" not in requirements,
                     "feature check plan derives its check contract from policy")
    evidence.validate_requirements(requirements, root)
    evidence.require(not {"batch", "review_scope"}.intersection(requirements),
                     "feature check plan cannot contain a batch or prospective review scope")
    checks = {row["id"] for row in requirements["checks"]}
    flags = plan["required_checks"]
    evidence.require(isinstance(flags, dict) and set(flags) == checks
                     and all(type(flag) is bool for flag in flags.values()) and any(flags.values()),
                     "required_checks must give every check a boolean and require at least one check")
    interactions = plan["interactions"]
    evidence.require(isinstance(interactions, list) and bool(interactions)
                     and all(isinstance(key, str) for key in interactions)
                     and len(set(interactions)) == len(interactions)
                     and set(interactions) <= set(requirements["observations"]),
                     "interactions must name unique captured feature observations")
    return plan


@evidence.validation_session
def validate_policy(path, root, task_contracts=None):
    root = Path(root).resolve()
    path = (root / Path(path)).resolve()
    evidence.require(path.is_relative_to(root), "review policy must be inside source root")
    local_file(root, path.relative_to(root).as_posix(), "review policy")
    policy = evidence.read_json(path)
    fields = {"schema_version", "mode", "queue", "feature_contract", "check_plan", "tasks", "final_review"}
    evidence.require(isinstance(policy, dict) and set(policy) == fields
                     and type(policy["schema_version"]) is int and policy["schema_version"] == 1
                     and policy["mode"] == "feature", "invalid feature review policy")
    feature_contract = local_file(root, policy["feature_contract"], "feature_contract")
    plan = check_plan(policy, root)
    checks = set(plan["required_checks"])
    tasks = policy["tasks"]
    evidence.require(isinstance(tasks, dict) and bool(tasks)
                     and all(isinstance(key, str) and re.fullmatch(r"T[1-9][0-9]*", key) for key in tasks),
                     "feature policy needs explicit task IDs")
    for key, row in tasks.items():
        evidence.require(isinstance(row, dict) and set(row) == {"contract", "review", "reason", "focused_checks"},
                         f"{key} needs contract, review, reason, and focused_checks")
        contract = local_file(root, row["contract"], f"{key} contract")
        evidence.require(row["review"] in {"critical", "deferred"}
                         and isinstance(row["reason"], str) and row["reason"].strip(),
                         f"{key} needs an explicit review classification and reason")
        focused = row["focused_checks"]
        evidence.require(isinstance(focused, list) and bool(focused)
                         and all(isinstance(check, str) for check in focused)
                         and len(set(focused)) == len(focused) and set(focused) <= checks,
                         f"{key} focused checks must name unique feature check IDs")
        if task_contracts is not None:
            evidence.require(key in task_contracts and Path(task_contracts[key]).resolve() == contract,
                             f"{key} policy contract differs from canonical queue")
    if task_contracts is not None:
        evidence.require(set(tasks) == set(task_contracts), "policy task set differs from canonical queue")
    from task_queue import load_queue
    queue_path = local_file(root, policy["queue"], "policy queue")
    evidence.file_hash(queue_path)
    queue = load_queue(queue_path, root)
    evidence.require(not queue.legacy and queue.review_policy == path,
                     "policy queue must select this exact review policy")
    evidence.require({task.id: task.contract_path for task in queue.tasks}
                     == {key: root / row["contract"] for key, row in tasks.items()},
                     "policy tasks differ from canonical queue contracts")
    final = policy["final_review"]
    evidence.require(isinstance(final, dict) and set(final) == {"scope", "route"},
                     "final_review needs scope and route")
    evidence.require(local_file(root, final["scope"], "final review scope") == feature_contract,
                     "final review scope must be the feature acceptance contract")
    route = final["route"]
    evidence.require(isinstance(route, dict) and route.get("role") == "reviewer"
                     and route.get("task_id") not in tasks
                     and local_file(root, route.get("input_path"), "final reviewer input") == feature_contract,
                     "final reviewer route must bind the feature contract and a separate role")
    from task_queue import launcher_module
    launcher_module().validate_route(route)
    return policy


def policy_inputs(path, root):
    root = Path(root).resolve()
    policy = validate_policy(path, root)
    return list(dict.fromkeys([(root / Path(path)).resolve().relative_to(root).as_posix(), policy["queue"], policy["check_plan"],
                              policy["feature_contract"], *[row["contract"] for row in policy["tasks"].values()]]))


def check_contract(path, root):
    root = Path(root).resolve()
    policy = validate_policy(path, root)
    contract = root / policy["feature_contract"]
    return {"policy": str((root / Path(path)).resolve()), "path": str(contract), "sha256": evidence.contract_hash(contract),
            "inputs": [{"path": str(root / name), "content_sha256": evidence.scope_content_hash(root / name)}
                       for name in policy_inputs(path, root)]}


def validate_check_contract(binding, root):
    evidence.require(isinstance(binding, dict) and set(binding) == {"policy", "path", "sha256", "inputs"}
                     and isinstance(binding["policy"], str) and Path(binding["policy"]).is_absolute(),
                     "invalid feature check contract")
    evidence.require(binding == check_contract(binding["policy"], root),
                     "feature check contract omits or changes approved policy inputs")
    policy = validate_policy(binding["policy"], root)
    return {Path(root).resolve() / name for name in [policy["feature_contract"],
                                                   *[row["contract"] for row in policy["tasks"].values()]]}


@evidence.validation_session
def validate_plan_policy(plan, root):
    """Validate optional feature authority before a new role reservation."""
    if "review_policy" not in plan:
        return None
    root = Path(root).resolve()
    from task_queue import launcher_module
    launcher = launcher_module()
    evidence.require(plan.get("schema_version") == 1 and plan.get("approval", {}).get("status") == "approved",
                     "feature review requires an approved routing plan")
    inputs = plan.get("scope", {}).get("inputs")
    evidence.require(isinstance(inputs, list) and bool(inputs), "feature routing scope.inputs are missing")
    indexed = {}
    for row in inputs:
        evidence.require(isinstance(row, dict) and set(row) == {"path", "content_sha256"}, "invalid feature scope input")
        path = local_file(root, row["path"], "feature scope input")
        evidence.require(row["path"] not in indexed and launcher.content_digest(path) == row["content_sha256"],
                         "feature scope input changed or is duplicated")
        indexed[row["path"]] = {"path": path, "content_sha256": row["content_sha256"]}
    evidence.require(launcher.canonical_digest(launcher.normalized_scope_inputs(inputs))
                     == plan["approval"].get("scope_digest"), "feature routing scope digest differs")
    routes = plan.get("routes")
    evidence.require(isinstance(routes, list) and bool(routes), "feature routing routes are missing")
    ids = set()
    for route in routes:
        launcher.validate_route(route)
        evidence.require(route["id"] not in ids, "duplicate feature routing role ID")
        ids.add(route["id"])
    evidence.require(launcher.canonical_digest(launcher.normalized_routes(routes))
                     == plan["approval"].get("routes_digest"), "feature routing routes digest differs")
    return launcher.bound_review_policy(plan, root, indexed)


@evidence.validation_session
def requirements(path, root, task_id=None):
    """Derive exact snapshot requirements from the single feature check plan."""
    root = Path(root).resolve()
    policy = validate_policy(path, root)
    plan = check_plan(policy, root)
    value = copy.deepcopy(plan["requirements"])
    if task_id is None:
        ids = {key for key, required in plan["required_checks"].items() if required}
    else:
        evidence.require(task_id in policy["tasks"], "task is absent from feature policy")
        ids = set(policy["tasks"][task_id]["focused_checks"])
        value["observations"], value["exclusions"] = [], {}
        value.pop("observation_inputs", None)
    value["checks"] = [row for row in value["checks"] if row["id"] in ids]
    value["check_contract"] = check_contract(path, root)
    return value


def bound_snapshot(path, root, policy_path, policy, base, task_id=None):
    snapshot = evidence.current_snapshot(path, base)
    evidence.require(Path(snapshot["source"]["root"]).resolve() == root, "snapshot belongs to another source root")
    contract = policy["feature_contract"] if task_id is None else policy["tasks"][task_id]["contract"]
    evidence.require(Path(snapshot["contract"]["path"]).resolve() == root / contract,
                     "snapshot belongs to another acceptance contract")
    evidence.require(snapshot["requirements"]["value"] == requirements(policy_path, root, task_id),
                     "snapshot requirements differ from the feature check plan")
    evidence.check_acceptance(snapshot)
    return snapshot


@evidence.validation_session
def assess_task(path, task_id, snapshot_path, packet_link, base, root=None):
    result = {"dependency_release": False, "feature_accepted": False,
              "independent_review_required": True, "reasons": []}
    try:
        if root is None:
            root = evidence.snapshot_record(snapshot_path)["source"]["root"]
        root = Path(root).resolve()
        policy = validate_policy(path, root)
        evidence.require(task_id in policy["tasks"], "task is absent from feature policy")
        critical = policy["tasks"][task_id]["review"] == "critical"
        result["independent_review_required"] = critical
        snapshot = bound_snapshot(snapshot_path, root, path, policy, base, task_id)
        packet = evidence.load_packet(packet_link, snapshot, Path(snapshot_path).resolve())
        failed = [row["id"] for row in snapshot["requirements"]["value"]["checks"]
                  if not evidence.validate_check(packet["checks"][row["id"]], snapshot, row)]
        evidence.require(not failed, f"focused checks failed: {failed}")
        if critical:
            evidence.require(evidence.assess(snapshot_path, base)["status"] == "ready",
                             "critical task requires a ready independent review")
        result["dependency_release"] = True
    except (ValueError, OSError, KeyError, TypeError) as error:
        result["reasons"].append(str(error))
    return result


def reviewer_binding(policy, snapshot_path, receipt, ledger, root):
    """Read the captured receipt; call status alone is not review evidence."""
    evidence.require(isinstance(ledger, dict) and isinstance(ledger.get("calls"), dict),
                     "final acceptance requires the actual call ledger")
    calls = ledger["calls"]
    evidence.require(all(isinstance(call, dict) and call.get("status") in {"completed", "failed", "cancelled"}
                         for call in calls.values()), "pending calls block final acceptance")
    matches = [key for key, call in calls.items() if call == receipt]
    evidence.require(len(matches) == 1, "final reviewer receipt must identify one actual ledger call")
    call_id = matches[0]
    evidence.require(receipt.get("status") == "completed" and receipt.get("review_status") == "ready",
                     "final reviewer call is not completed and ready")
    route = policy["final_review"]["route"]
    intent = receipt.get("intent", {})
    evidence.require(intent.get("route") == route, "final reviewer route differs from policy")
    plan_link = ledger.get("plan")
    evidence.require(isinstance(plan_link, dict) and isinstance(plan_link.get("path"), str), "call ledger plan is missing")
    plan_path = Path(plan_link["path"])
    plan_path = evidence.checked_link({**plan_link, "path": str((root / plan_path).resolve())}, "call ledger plan")
    plan = evidence.read_json(plan_path)
    evidence.require(plan.get("approval", {}).get("status") == "approved" and route in plan.get("routes", []),
                     "final reviewer route is absent from the approved plan")
    policy_path = local_file(root, plan.get("review_policy"), "approved review_policy")
    evidence.require(validate_policy(policy_path, root) == policy, "call ledger plan binds another review policy")
    validate_plan_policy(plan, root)
    for candidate in plan["routes"]:
        if candidate.get("role") == "implementer":
            from task_queue import launcher_module
            evidence.require(all(variant.get("model") != route["model"]
                                 for variant in launcher_module().route_variants(candidate)),
                             "final reviewer model must differ from each implementer model")
    snapshot_path = Path(snapshot_path).resolve()
    evidence.require(intent.get("review_snapshot") == evidence.evidence_link(snapshot_path),
                     "final reviewer call belongs to another snapshot")
    review_path = snapshot_path.parent / "review.json"
    evidence.require(receipt.get("review") == evidence.evidence_link(review_path),
                     "final reviewer call belongs to another review")
    raw = evidence.read_json(evidence.checked_link(receipt.get("receipt_ref"), "final reviewer receipt"))
    execution = raw.get("native_execution", raw)
    if "dispatch_metadata" in raw:
        execution = {**raw["dispatch_metadata"], **raw}
    evidence.require(raw.get("success") is True and execution.get("call_id") == call_id
                     and execution.get("input_revision") == intent.get("input", {}).get("sha256")
                     and execution.get("configured_model") == route["model"]
                     and execution.get("configured_effort") == route.get("effort"),
                     "final reviewer execution differs from the reserved call")
    evidence.checked_link(intent.get("input"), "final reviewer input")
    from task_queue import launcher_module
    mismatch = launcher_module().receipt_error(route, raw)
    evidence.require(mismatch is None, f"final reviewer receipt is invalid: {mismatch}")
    context = execution.get("context_id") or raw.get("session_id")
    contexts = ledger.get("contexts", {})
    evidence.require(isinstance(context, str) and bool(context) and contexts.get(route["id"]) == context
                     and all(key == route["id"] or value != context for key, value in contexts.items()),
                     "final reviewer requires its own recorded context")
    evidence.require(evidence.load_record(review_path)["execution"] == raw,
                     "final review execution differs from the completed receipt")


@evidence.validation_session
def assess_feature(path, snapshot_path, base, reviewer_receipt, root=None, call_ledger=None):
    result = {"status": "needs-work", "final_review_ready": False, "reasons": []}
    try:
        if root is None:
            root = evidence.snapshot_record(snapshot_path)["source"]["root"]
        root = Path(root).resolve()
        policy = validate_policy(path, root)
        bound_snapshot(snapshot_path, root, path, policy, base)
        evidence.require(evidence.assess(snapshot_path, base)["status"] == "ready",
                         "combined feature review is not ready")
        reviewer_binding(policy, snapshot_path, reviewer_receipt, call_ledger, root)
        result.update(status="ready", final_review_ready=True)
    except (ValueError, OSError, KeyError, TypeError) as error:
        result["reasons"].append(str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "requirements", "assess-task", "assess-feature"])
    parser.add_argument("--policy", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--task")
    parser.add_argument("--snapshot")
    parser.add_argument("--packet", help="immutable packet record path")
    parser.add_argument("--base")
    parser.add_argument("--ledger", help="JSON call ledger file")
    parser.add_argument("--call", help="completed final reviewer call ID")
    args = parser.parse_args()
    try:
        if args.command == "validate":
            validate_policy(args.policy, args.root)
            result = {"status": "valid", "inputs": policy_inputs(args.policy, args.root)}
        elif args.command == "requirements":
            result = requirements(args.policy, args.root, args.task)
        else:
            evidence.require(args.snapshot and args.base, "assessment needs --snapshot and --base")
            if args.command == "assess-task":
                evidence.require(args.task and args.packet, "task assessment needs --task and --packet")
                result = assess_task(args.policy, args.task, args.snapshot, evidence.evidence_link(args.packet), args.base, args.root)
            else:
                evidence.require(args.ledger and args.call, "feature assessment needs --ledger and --call")
                ledger = evidence.read_json(args.ledger)
                result = assess_feature(args.policy, args.snapshot, args.base, ledger["calls"][args.call], args.root, ledger)
        print(json.dumps(result, indent=2))
        return 1 if result.get("reasons") else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "invalid", "reasons": [str(error)]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
