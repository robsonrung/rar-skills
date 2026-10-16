#!/usr/bin/env python3
"""Refresh focused feature evidence without changing plans or accepting a feature."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import sys
import tempfile

import feature_review as feature
import review_evidence as evidence


def atomic_record(path, payload):
    """Publish a complete immutable result without exposing a partial JSON record."""
    path = Path(path)
    value = {"payload": payload, "sha256": evidence.digest(payload)}
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.link(temporary, path)
    finally:
        temporary.unlink()
    return path


def original_capture(snapshot_path, check_path):
    """Follow coverage and transfer links to the original passing execution."""
    check = evidence.load_record(check_path)
    evidence.require(evidence.validate_check(check_path, evidence.snapshot_record(snapshot_path), check["definition"]),
                     "capture is not passing")
    if check.get("kind") == "coverage":
        check_path = evidence.checked_link(check["aggregate"], "covered aggregate")
        check = evidence.load_record(check_path)
    if "transfer" in check:
        check_path = evidence.checked_link(check["transfer"]["check"], "original check")
        check = evidence.load_record(check_path)
    snapshot_path = check["snapshot_path"]
    old = evidence.snapshot_record(snapshot_path)
    evidence.require("transfer" not in check and check.get("kind") != "coverage"
                     and evidence.validate_check(check_path, old, check["definition"]),
                     "capture is not a passing original execution")
    return Path(snapshot_path).resolve(), Path(check_path).resolve()


def candidates(entries, root, prior=None):
    found = []
    for entry in entries.values():
        try:
            snapshot_path = evidence.checked_link(entry["snapshot"], "prior snapshot")
            packet = evidence.load_packet(entry["evidence_packet"], evidence.snapshot_record(snapshot_path), snapshot_path)
            for check_path in packet["checks"].values():
                try:
                    found.append(original_capture(snapshot_path, check_path))
                except (ValueError, OSError, KeyError, TypeError):
                    pass
        except (ValueError, OSError, KeyError, TypeError):
            continue
    if prior:
        for link in prior.get("captures", []):
            try:
                check_path = evidence.checked_link(link, "resume capture")
                check = evidence.load_record(check_path)
                found.append(original_capture(check["snapshot_path"], check_path))
            except (ValueError, OSError, KeyError, TypeError):
                continue
    return list(dict.fromkeys(found))


def ledger_plan(ledger, root):
    link = ledger.get("plan")
    evidence.require(isinstance(link, dict) and isinstance(link.get("path"), str), "ledger plan is missing")
    return evidence.checked_link({**link, "path": str((Path(root) / link["path"]).resolve())}, "ledger plan")


def critical_binding(entry, ledger):
    if "critical_review" in entry:
        return copy.deepcopy(entry["critical_review"])
    snapshot = entry.get("snapshot")
    evidence.require(isinstance(snapshot, dict), "critical review needs an original snapshot")
    review = evidence.evidence_link(Path(snapshot["path"]).parent / "review.json")
    matches = [key for key, call in ledger.get("calls", {}).items()
               if call.get("status") == "completed" and call.get("review_status") == "ready"
               and call.get("intent", {}).get("review_snapshot") == snapshot and call.get("review") == review]
    evidence.require(len(matches) == 1, "critical review needs one actual completed original reviewer call")
    return {"snapshot": snapshot, "call_id": matches[0]}


def environment_record(path, source, context):
    value = evidence.read_json(path)
    evidence.validate_environment_assessment(value)
    evidence.require(value.get("to_source_id") == evidence.digest(source)
                     and value.get("context_id") == evidence.digest(evidence.context_identity(context)),
                     "environment assessment belongs to another current source or context")
    return value


def refresh(policy_path, root, base, ledger_path, output, environment_path, *, execute=False,
            tasks=None, resume_from=None):
    root = Path(root).resolve()
    output = (root / Path(output)).resolve()
    policy_path, ledger_path = (root / Path(policy_path)).resolve(), (root / Path(ledger_path)).resolve()
    evidence.require(not execute or environment_path is not None, "execution requires an explicit environment assessment")
    environment_path = (root / Path(environment_path)).resolve() if environment_path is not None else None
    policy = feature.validate_policy(policy_path, root)
    state = evidence.read_json(ledger_path)
    ledger = state.get("call_ledger", state)
    evidence.require(isinstance(ledger, dict) and isinstance(ledger.get("calls"), dict)
                     and all(isinstance(call, dict) and call.get("status") in {"completed", "failed", "cancelled"}
                             for call in ledger["calls"].values()), "pending or unknown calls block refresh")
    plan_path = ledger_plan(ledger, root)
    plan = evidence.read_json(plan_path)
    feature.validate_plan_policy(plan, root)
    evidence.require((root / plan["review_policy"]).resolve() == policy_path, "ledger selects another policy")
    entries = state.get("integration_evidence", {})
    evidence.require(isinstance(entries, dict), "integration evidence must be an object")
    selected = tasks if tasks is not None else sorted(entries)
    evidence.require(isinstance(selected, list) and 0 < len(selected) <= 100 and len(set(selected)) == len(selected)
                     and set(selected) <= set(policy["tasks"]) and set(selected) <= set(entries),
                     "select 1 to 100 distinct feature tasks with existing evidence")
    requirements = {key: feature.requirements(policy_path, root, key) for key in selected}
    evidence.require(sum(len(value["checks"]) for value in requirements.values()) <= 1000,
                     "refresh exceeds the 1000 check bound")
    artifact_roots = {evidence.snapshot_record(evidence.checked_link(entries[key]["snapshot"], "task snapshot"))["artifact_dir"]
                      for key in selected}
    evidence.require(len(artifact_roots) == 1, "selected tasks must share one artifact directory")
    artifact_dir = Path(artifact_roots.pop()).resolve()
    evidence.require(output.is_relative_to(artifact_dir) and output != artifact_dir,
                     "output must be a new child of the original artifact directory")
    for key in selected:
        if policy["tasks"][key]["review"] == "critical":
            evidence.require("reuse_scope" in policy["tasks"][key],
                             f"{key} requires a new independent review; scoped reuse was not approved")
            reference = critical_binding(entries[key], ledger)
            old_path = evidence.checked_link(reference["snapshot"], "original critical snapshot")
            old = evidence.snapshot_record(old_path)
            evidence.require(evidence.assess_record(old_path, old)["status"] == "ready", "original critical review is not ready")
            feature.reviewer_binding(policy, old_path, ledger["calls"][reference["call_id"]], ledger, root, critical_task=key)
    source = evidence.source_state(root, base, artifact_dir)
    context = next(iter(requirements.values()))["context"]
    environment = environment_record(environment_path, source, context) if environment_path is not None else None
    identity = {"policy": evidence.evidence_link(policy_path), "ledger": evidence.evidence_link(ledger_path),
                "environment": evidence.evidence_link(environment_path) if environment_path else None,
                "source_id": evidence.digest(source), "context_id": evidence.digest(evidence.context_identity(context)),
                "tasks": selected, "base": base, "output": str(output), "artifact_dir": str(artifact_dir)}
    result_path = output / "result.json"
    if execute and result_path.exists():
        previous = evidence.load_record(result_path)
        evidence.require(previous["request"] == identity, "published batch belongs to another request or source")
        if previous["status"] == "ready":
            validate_patch(previous, root, policy_path, ledger)
        return previous
    prior = evidence.load_record((root / Path(resume_from)).resolve()) if resume_from else None
    if prior:
        evidence.require(prior["request"]["policy"] == identity["policy"]
                         and prior["request"]["ledger"] == identity["ledger"],
                         "resume batch belongs to another policy or ledger")
    originals = candidates({key: entries[key] for key in selected}, root, prior)
    evidence.require(len(originals) <= 2000, "refresh exceeds the original capture bound")
    pool = {}
    for old_path, capture in originals:
        signature = evidence.digest(evidence.load_record(capture)["definition"])
        pool.setdefault(signature, []).append((old_path, capture))
    result = {"schema_version": 1, "status": "preview", "request": identity,
              "feature_accepted": False, "integration_evidence_patch": {}, "captures": [], "tasks": {}, "reasons": []}
    if not execute:
        result["tasks"] = {key: {"checks": [{"id": row["id"], "action": "fresh" if row.get("fresh") else "select-or-run"}
                                           for row in requirements[key]["checks"]],
                               "critical_review_required": policy["tasks"][key]["review"] == "critical"}
                           for key in selected}
        result["available_original_captures"] = len(originals)
        result["environment_required"] = environment is None
        return result
    evidence.require(not output.exists(), "use a new output directory for an incomplete or failed batch")
    output.mkdir(parents=True)
    proposed, prepared, critical = {}, {}, {}
    try:
        for key in selected:
            directory = output / key
            directory.mkdir()
            req_path = directory / "requirements.json"
            req_path.write_text(json.dumps(requirements[key], indent=2) + "\n")
            snapshot_path = evidence.prepare(root, base, root / policy["tasks"][key]["contract"], req_path,
                                             directory, artifact_dir=artifact_dir)
            prepared[key] = snapshot_path
            if policy["tasks"][key]["review"] == "critical":
                reference = critical_binding(entries[key], ledger)
                assessment = {**environment, "from_snapshot_sha256": reference["snapshot"]["sha256"]}
                assessment_path = directory / "critical.environment.json"
                assessment_path.write_text(json.dumps(assessment, indent=2) + "\n")
                reference["assessment"] = evidence.evidence_link(assessment_path)
                feature.assess_critical_reuse(policy_path, key, snapshot_path, reference, ledger, root)
                critical[key] = reference
        for key in selected:
            snapshot_path = prepared[key]
            directory = snapshot_path.parent
            checks, actions, available = {}, [], {}
            snapshot = evidence.current_snapshot(snapshot_path)
            rows = []
            for definition in requirements[key]["checks"]:
                check_id = definition["id"]
                row = {"id": check_id, "action": "run", "reason": "no passing captured check supplied"}
                for old_path, capture in pool.get(evidence.digest(definition), []):
                    try:
                        selection = evidence.select_checks(snapshot_path, old_path, {check_id: str(capture)},
                                                           selected=[check_id])
                        candidate = selection["checks"][0]
                        if candidate["action"] in {"reuse", "transfer"}:
                            row = candidate
                            available[check_id] = (old_path, capture)
                            break
                    except (ValueError, OSError, KeyError, TypeError):
                        continue
                rows.append(row)
            rows = evidence.apply_check_coverage(snapshot, rows)
            definitions = {row["id"]: row for row in requirements[key]["checks"]}
            # Capture aggregate commands before deriving their covered check records.
            ordered = [row for row in rows if row["action"] != "covered"]
            ordered.extend(row for row in rows if row["action"] == "covered")
            for row in ordered:
                check_id, action = row["id"], row["action"]
                definition = definitions[check_id]
                if action == "covered":
                    capture = evidence.cover_check(snapshot_path, check_id, checks[row["covered_by"]])
                elif action in {"reuse", "transfer"}:
                    old_path, capture = available[check_id]
                    if action == "transfer":
                        assessment = {**environment, "from_snapshot_sha256": evidence.file_hash(old_path)}
                        assessment_path = directory / (check_id + ".environment.json")
                        assessment_path.write_text(json.dumps(assessment, indent=2) + "\n")
                        capture = evidence.transfer_check(old_path, snapshot_path, capture, assessment_path)
                else:
                    capture = evidence.run_check(snapshot_path, check_id)
                    result["captures"].append(evidence.evidence_link(capture))
                    evidence.require(evidence.validate_check(capture, evidence.current_snapshot(snapshot_path), definition),
                                     f"{key} check {check_id} failed")
                    pool.setdefault(evidence.digest(definition), []).append((snapshot_path, capture))
                checks[check_id] = str(capture)
                actions.append({"id": check_id, "action": action, "capture": evidence.evidence_link(capture),
                                **({"covered_by": row["covered_by"]} if action == "covered" else {})})
            packet = evidence.prepare_packet(snapshot_path, directory / "packet.json", checks=checks, observations=[])
            entry = copy.deepcopy(entries[key])
            for stale_field in ("carry_forward", "batch_review"):
                entry.pop(stale_field, None)
            entry.update(snapshot=evidence.evidence_link(snapshot_path), evidence_packet=evidence.evidence_link(packet), base=base)
            if policy["tasks"][key]["review"] == "critical":
                entry["critical_review"] = critical[key]
            else:
                entry.pop("critical_review", None)
            proposed[key] = entry
            result["tasks"][key] = {"checks": actions, "snapshot": entry["snapshot"], "evidence_packet": entry["evidence_packet"]}
        result["integration_evidence_patch"] = proposed
        validate_patch(result, root, policy_path, ledger)
        evidence.require(evidence.evidence_link(ledger_path) == identity["ledger"], "ledger changed during refresh")
        evidence.require(evidence.evidence_link(environment_path) == identity["environment"], "environment changed during refresh")
        environment_record(environment_path, evidence.source_state(root, base, artifact_dir), next(iter(requirements.values()))["context"])
        result["status"] = "ready"
    except (ValueError, OSError, KeyError, TypeError) as error:
        result.update(status="blocked", integration_evidence_patch={})
        result["reasons"].append(str(error))
    atomic_record(result_path, result)
    return result


def validate_patch(result, root, policy_path, ledger):
    """Validate focused gates only; actual receipt and final acceptance stay with the queue."""
    evidence.require(isinstance(ledger.get("calls"), dict)
                     and all(isinstance(call, dict) and call.get("status") in {"completed", "failed", "cancelled"} for call in ledger["calls"].values()),
                     "pending or unknown calls block evidence publication")
    plan_path = ledger_plan(ledger, root)
    plan = evidence.read_json(plan_path)
    feature.validate_plan_policy(plan, root)
    evidence.require((Path(root) / plan["review_policy"]).resolve() == Path(policy_path).resolve(), "ledger selects another policy")
    evidence.require(set(result["integration_evidence_patch"]) == set(result["request"]["tasks"])
                     and bool(result["integration_evidence_patch"]), "patch task set differs from requested tasks")
    for key, entry in result["integration_evidence_patch"].items():
        snapshot = evidence.checked_link(entry["snapshot"], "refreshed snapshot")
        kwargs = {"critical_review": entry["critical_review"], "call_ledger": ledger} if "critical_review" in entry else {}
        assessment = feature.assess_task(policy_path, key, snapshot, entry["evidence_packet"], entry["base"], root, **kwargs)
        evidence.require(assessment["dependency_release"], f"{key}: " + "; ".join(assessment["reasons"]))


def apply_result(result_path, root):
    """Apply a validated patch under the existing ledger lock and exact hash guard."""
    import run_state
    import task_queue

    root = Path(root).resolve()
    result_path = Path(result_path).resolve()
    result = evidence.load_record(result_path)
    evidence.require(result.get("status") == "ready" and result.get("feature_accepted") is False,
                     "only a complete focused evidence refresh can be applied")
    request = result["request"]
    ledger_path = Path(request["ledger"]["path"])
    policy_path = evidence.checked_link(request["policy"], "refresh policy")
    marker = evidence.evidence_link(result_path)
    # Read-only replay does not touch timestamps or acquire a write lock.
    existing = evidence.read_json(ledger_path)
    if existing.get("evidence_refreshes", {}).get(request["output"]) == marker:
        evidence.require(all(existing.get("integration_evidence", {}).get(key) == value
                             for key, value in result["integration_evidence_patch"].items()),
                         "applied evidence has since changed")
        source = evidence.source_state(root, request["base"], request["artifact_dir"])
        evidence.require(evidence.digest(source) == request["source_id"], "source changed after refresh")
        env_path = evidence.checked_link(request["environment"], "refresh environment")
        environment_record(env_path, source, feature.requirements(policy_path, root)["context"])
        validate_patch(result, root, policy_path, existing.get("call_ledger", existing))
        return {"status": "already-applied", "feature_accepted": False}
    with run_state.locked(ledger_path) as state:
        evidence.require(evidence.evidence_link(ledger_path) == request["ledger"],
                         "ledger changed after refresh; regenerate the proposal")
        ledger = state.get("call_ledger", state)
        plan_path = ledger_plan(ledger, root)
        plan = evidence.read_json(plan_path)
        feature.validate_plan_policy(plan, root)
        source = evidence.source_state(root, request["base"], request["artifact_dir"])
        evidence.require(evidence.digest(source) == request["source_id"], "source changed after refresh")
        evidence.require(not ledger_path.is_relative_to(root) or ledger_path.relative_to(root).as_posix() not in source["files"],
                         "ledger must be outside captured source before applying evidence")
        env_path = evidence.checked_link(request["environment"], "refresh environment")
        context = feature.requirements(policy_path, root)["context"]
        environment_record(env_path, source, context)
        validate_patch(result, root, policy_path, ledger)
        prospective = copy.deepcopy(state)
        prospective.setdefault("integration_evidence", {}).update(result["integration_evidence_patch"])
        policy = feature.validate_policy(policy_path, root)
        queue = task_queue.load_queue(root / policy["queue"], root)
        routing = task_queue.routes_for_queue(queue, plan_path, root)
        states = task_queue.classify_tasks(queue, prospective, routing, plan_path, root)
        evidence.require(all(states[key].kind == "implemented" for key in request["tasks"]),
                         "queue rejected refreshed implementation or reviewer evidence")
        state.setdefault("integration_evidence", {}).update(result["integration_evidence_patch"])
        state.setdefault("evidence_refreshes", {})[request["output"]] = marker
    return {"status": "applied", "tasks": request["tasks"], "feature_accepted": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--apply-result")
    for name in ("policy", "base", "ledger", "output", "environment"):
        parser.add_argument("--" + name)
    parser.add_argument("--task", action="append", dest="tasks")
    parser.add_argument("--resume-from")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.apply_result:
            evidence.require(not args.execute and not any((args.policy, args.base, args.ledger, args.output, args.environment, args.tasks, args.resume_from)),
                             "apply-result cannot be combined with refresh arguments")
            result = apply_result(args.apply_result, args.root)
        else:
            evidence.require(all((args.policy, args.base, args.ledger, args.output)),
                             "refresh requires policy, base, ledger, and output")
            result = refresh(args.policy, args.root, args.base, args.ledger, args.output, args.environment,
                             execute=args.execute, tasks=args.tasks, resume_from=args.resume_from)
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "blocked" else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "invalid", "reasons": [str(error)]}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
