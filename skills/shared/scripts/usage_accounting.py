"""Account observed usage and evaluate optional limits before future dispatches."""

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from execution_metrics import FIELDS, normalize_metrics, number

METRICS = ("response_count",) + FIELDS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    require(isinstance(value, str), "usage timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "usage timestamp needs a timezone")
    return result


def text(value, name):
    require(isinstance(value, str) and value.strip(), f"{name} must be a nonempty string")
    return value


def check_metric_subsets(metrics):
    inputs = number(metrics.get("input_tokens"))
    cached = [number(metrics.get(key)) for key in ("cached_input_tokens", "cache_write_input_tokens")]
    if inputs is not None:
        require(sum(value for value in cached if value is not None) <= inputs,
                "reported cache subsets exceed total input")
    output, reasoning = (number(metrics.get(key)) for key in ("output_tokens", "reasoning_output_tokens"))
    require(output is None or reasoning is None or reasoning <= output,
            "reported reasoning subset exceeds total output")


def normalize_usage(receipt):
    """Count only reported responses; a dispatch can contain several responses."""
    metrics = normalize_metrics(receipt)
    supplied = receipt.get("metrics") if isinstance(receipt.get("metrics"), dict) else receipt
    responses = supplied.get("response_count", receipt.get("response_count"))
    if responses is None and isinstance(receipt.get("usage"), dict):
        responses = receipt["usage"].get("response_count")
    metrics["response_count"] = responses if type(responses) is int and responses >= 0 else None
    check_metric_subsets(metrics)
    return metrics


def receipt_usage(receipt):
    execution = receipt.get("native_execution", receipt)
    if "dispatch_metadata" in receipt:
        execution = {**receipt["dispatch_metadata"], **receipt}
    identity = receipt.get("usage_identity", {})
    require(isinstance(identity, dict) and set(identity) <= {"source_id", "context_id"}, "invalid usage identity")
    context = execution.get("context_id") or receipt.get("session_id")
    if identity.get("context_id") and context:
        require(identity["context_id"] == context, "usage context differs from execution context")
    for key, value in identity.items():
        text(value, key)
    return {"metrics": normalize_usage(receipt), "source_id": identity.get("source_id"),
            "context_id": identity.get("context_id", context)}


def validate_policy(policy):
    require(isinstance(policy, dict) and set(policy) <= {"limits", "require_known", "subscription_limits"},
            "invalid usage policy fields")
    limits = policy.get("limits", {})
    require(isinstance(limits, dict) and set(limits) <= set(METRICS), "invalid usage limit metric")
    for metric, limit in limits.items():
        require(number(limit) is not None and limit > 0, f"positive usage limit required for {metric}")
    known = policy.get("require_known", [])
    require(isinstance(known, list) and all(isinstance(key, str) and key in METRICS for key in known)
            and len(set(known)) == len(known), "invalid required usage metrics")
    windows = policy.get("subscription_limits", [])
    require(isinstance(windows, list), "subscription limits must be a list")
    identities = set()
    for window in windows:
        require(isinstance(window, dict) and set(window) == {
            "source_id", "window_id", "max_used_percent", "max_age_seconds"}, "invalid subscription limit")
        identity = (text(window["source_id"], "source_id"), text(window["window_id"], "window_id"))
        require(identity not in identities, "duplicate subscription limit")
        identities.add(identity)
        require(number(window["max_used_percent"]) is not None and 0 < window["max_used_percent"] <= 100,
                "subscription limit must be in (0, 100]")
        if "max_age_seconds" in window:
            require(number(window["max_age_seconds"]) is not None and window["max_age_seconds"] > 0,
                    "subscription maximum age must be positive")
    require(limits or known or windows, "usage policy must contain a limit or required metric")
    return copy.deepcopy(policy)


def bind_policy(plan, policy_path):
    """Use the existing approved scope digest to bind the optional policy file."""
    from task_queue import canonical_text_sha256
    path = Path(policy_path).resolve()
    inputs = plan.get("scope", {}).get("inputs", [])
    require(isinstance(inputs, list) and inputs, "usage policy requires approved scope inputs")
    encoded = json.dumps(sorted(inputs, key=lambda item: item["path"]), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    require(hashlib.sha256(encoded.encode()).hexdigest() == plan.get("approval", {}).get("scope_digest"),
            "usage policy scope digest differs from approval")
    matches = [item for item in inputs if Path(item["path"]).resolve() == path]
    require(len(matches) == 1, "usage policy file must be one approved scope input")
    require(canonical_text_sha256(path.read_text()) == matches[0]["content_sha256"],
            "usage policy file changed after approval")
    payload = json.loads(path.read_text())
    require(isinstance(payload, dict) and set(payload) == {"usage_policy"}, "usage policy file needs usage_policy only")
    policy = validate_policy(payload["usage_policy"])
    return {"usage_policy": policy, "usage_policy_ref": {"path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}


def check_policy_binding(state):
    ledger = state.get("call_ledger", {})
    if "usage_policy" not in ledger and "usage_policy_ref" not in ledger:
        return
    ref = ledger.get("usage_policy_ref", {})
    require(ref and "usage_policy" in ledger, "usage policy binding is missing")
    require(hashlib.sha256(Path(ref["path"]).read_bytes()).hexdigest() == ref["sha256"],
            "bound usage policy file changed")
    plan_ref = ledger["plan"]
    require(hashlib.sha256(Path(plan_ref["path"]).read_bytes()).hexdigest() == plan_ref["sha256"],
            "bound usage plan changed")
    bound = bind_policy(json.loads(Path(plan_ref["path"]).read_text()), ref["path"])
    require(bound == {"usage_policy": ledger["usage_policy"], "usage_policy_ref": ref},
            "stored usage policy differs from approved policy")


def _records(state):
    records, hashes = {}, set()
    groups = [("worker", "worker", state.get("call_ledger", {}).get("calls", {}))]
    measurement = state.get("workflow_measurement", {})
    groups.append(("coordinator", "coordinator", measurement.get("coordinator_calls", {})))
    def stages(values, parent=""):
        for stage, value in values.items():
            prefix = parent + "stage:" + stage
            groups.append((prefix, "worker", value.get("calls", {})))
            coordinators = value.get("coordinator_calls", {})
            snapshots = value.get("usage_accounting", {}).get("snapshots", {})
            if not coordinators and not any(item["scope"] == "coordinator" for item in snapshots.values()) and (
                    "coordinator" not in value.get("coverage", [])):
                coordinators = {"unknown": {}}
            groups.append((prefix + ":coordinator", "coordinator", coordinators))
            stages(value.get("stage_ledgers", {}), prefix + ":")
    stages(measurement.get("stage_ledgers", {}))
    for prefix, scope, calls in groups:
        for call_id, call in calls.items():
            digest = call.get("receipt_ref", {}).get("sha256")
            if digest and digest in hashes:
                continue
            if digest:
                hashes.add(digest)
            usage = call.get("observed_usage")
            if not isinstance(usage, dict):
                usage = {"metrics": normalize_usage(call.get("receipt", {}))}
            route = call.get("intent", {}).get("route", {}).get("id")
            records[prefix + ":" + call_id] = {
                "scope": scope,
                "metrics": {key: usage.get("metrics", {}).get(key) for key in METRICS},
                "source_id": usage.get("source_id"),
                "context_id": usage.get("context_id") or state.get("call_ledger", {}).get("contexts", {}).get(route)}
    return records


def _snapshot_rows(state):
    records = _records(state)
    snapshots = dict(state.get("usage_accounting", {}).get("snapshots", {}))
    def stage_snapshots(values, parent=""):
        for stage, record in values.items():
            prefix = parent + "stage:" + stage + ":"
            for key, snapshot in record.get("usage_accounting", {}).get("snapshots", {}).items():
                value = copy.deepcopy(snapshot)
                value["covers"] = [prefix + (item.removeprefix("worker:") if item.startswith("worker:") else item)
                                   for item in snapshot["covers"]]
                snapshots[prefix + key] = value
            stage_snapshots(record.get("stage_ledgers", {}), prefix)
    stage_snapshots(state.get("workflow_measurement", {}).get("stage_ledgers", {}))
    covered, identities, anomalies = set(), {}, []
    for key, snapshot in sorted(snapshots.items()):
        identity = (snapshot["source_id"], snapshot["context_id"], snapshot["epoch_id"])
        if identity in identities:
            anomalies.append({"code": "duplicate_snapshot_identity", "snapshot": key})
        identities[identity] = key
        for record_id in snapshot["covers"]:
            record = records.get(record_id)
            if record is None:
                anomalies.append({"code": "unknown_snapshot_record", "record": record_id})
            elif record["scope"] != snapshot["scope"] or record.get("context_id") != snapshot["context_id"] or (
                    record.get("source_id") and record["source_id"] != snapshot["source_id"]):
                anomalies.append({"code": "snapshot_identity_mismatch", "record": record_id})
            if record_id in covered:
                anomalies.append({"code": "overlapping_snapshots", "record": record_id})
            covered.add(record_id)
        # Explicit identity prevents a later receipt from silently duplicating a snapshot.
        for record_id, record in records.items():
            if (record.get("context_id") == identity[1] and record["scope"] == snapshot["scope"]
                    and record.get("source_id") in (None, identity[0])) and record_id not in covered:
                if not any(record_id in item["covers"] for item in snapshots.values()):
                    anomalies.append({"code": "snapshot_coverage_mismatch", "record": record_id})
    rows = [value for key, value in records.items() if key not in covered]
    rows.extend({"scope": item["scope"], "metrics": item["metrics"]} for item in snapshots.values())
    if not any(row["scope"] == "coordinator" for row in rows) and "coordinator" not in state.get(
            "workflow_measurement", {}).get("coverage", []):
        rows.append({"scope": "coordinator", "metrics": {key: None for key in METRICS}})
    return rows, anomalies


def _aggregate(rows):
    result = {}
    for key in METRICS:
        values = [number(row["metrics"].get(key)) for row in rows]
        measured = sum(value for value in values if value is not None)
        unknown = sum(value is None for value in values)
        result[key] = {"measured_sum": measured, "measured_records": len(values) - unknown,
                       "unknown_records": unknown, "total": None if unknown else measured}
    return result


def summarize_usage(state):
    """Return observed sums, known totals, and identity conflicts without mutation."""
    rows, anomalies = _snapshot_rows(state)
    return {"records": len(rows), "metrics": _aggregate(rows),
            "scopes": {scope: _aggregate([row for row in rows if row["scope"] == scope])
                       for scope in ("worker", "coordinator")}, "anomalies": anomalies,
            "subscriptions": copy.deepcopy(list(state.get("usage_accounting", {}).get("subscriptions", {}).values()))}


def ingest_snapshot(state, snapshot):
    """Replace a cumulative source snapshot once; reject resets and overlap."""
    required = {"source_id", "context_id", "epoch_id", "scope", "sequence", "covers", "metrics"}
    require(isinstance(snapshot, dict) and required <= snapshot.keys() <= required | {"observed_at", "baseline_sha256"},
            "invalid usage snapshot fields")
    for key in ("source_id", "context_id", "epoch_id"):
        text(snapshot[key], key)
    require(snapshot["scope"] in {"worker", "coordinator"}, "invalid usage snapshot scope")
    require(type(snapshot["sequence"]) is int and snapshot["sequence"] >= 0, "snapshot sequence must be nonnegative")
    covers = snapshot["covers"]
    require(isinstance(covers, list) and all(isinstance(item, str) and item for item in covers)
            and len(set(covers)) == len(covers), "snapshot covers must contain unique record IDs")
    require(snapshot["scope"] != "worker" or covers, "worker snapshot must cover recorded calls")
    metrics = snapshot["metrics"]
    require(isinstance(metrics, dict) and set(metrics) <= set(METRICS), "invalid snapshot metrics")
    for key, value in metrics.items():
        require(value is None or number(value) is not None, f"invalid snapshot metric: {key}")
        if key == "response_count":
            require(value is None or type(value) is int, "response count must be an integer")
    check_metric_subsets(metrics)
    if "observed_at" in snapshot:
        timestamp(snapshot["observed_at"])
    value = copy.deepcopy(snapshot)
    value["covers"] = sorted(covers)
    value["metrics"] = {key: metrics.get(key) for key in METRICS}
    key = json.dumps([snapshot[field] for field in ("source_id", "context_id", "epoch_id")], separators=(",", ":"))
    candidate = copy.deepcopy(state)
    snapshots = candidate.setdefault("usage_accounting", {}).setdefault("snapshots", {})
    old = snapshots.get(key)
    if old:
        if value["sequence"] == old["sequence"]:
            require(value == old, "same snapshot sequence has different facts")
            return {"ingestion": "existing", "snapshot_id": key}
        require(value["sequence"] > old["sequence"], "stale usage snapshot sequence")
        require(value.get("baseline_sha256") == old.get("baseline_sha256"), "snapshot baseline differs")
        require(value["scope"] == old["scope"] and set(old["covers"]) <= set(value["covers"]),
                "snapshot coverage or scope changed")
        if old.get("observed_at") and value.get("observed_at"):
            require(timestamp(value["observed_at"]) >= timestamp(old["observed_at"]), "snapshot time moved backwards")
        for metric in METRICS:
            before, after = old["metrics"][metric], value["metrics"][metric]
            require(before is None or (after is not None and after >= before),
                    f"usage counter reset or lost measurement: {metric}; use a distinct observed epoch")
    snapshots[key] = value
    anomalies = summarize_usage(candidate)["anomalies"]
    require(not anomalies, "usage snapshot identity or coverage mismatch: " + json.dumps(anomalies))
    state.clear()
    state.update(candidate)
    return {"ingestion": "updated" if old else "new", "snapshot_id": key}


def token_log_snapshot(log_path, metadata, baseline):
    """Read cumulative token_count fields only, with an explicit context baseline."""
    require(isinstance(metadata, dict) and "metrics" not in metadata, "token log metadata must omit metrics")
    require(isinstance(baseline, dict) and set(baseline) == {"source_id", "context_id", "epoch_id", "metrics"},
            "token baseline needs source, context, epoch, and metrics")
    require(all(baseline[key] == metadata.get(key) for key in ("source_id", "context_id", "epoch_id")),
            "token baseline identity differs from snapshot")
    base = baseline["metrics"]
    require(isinstance(base, dict) and set(base) <= set(METRICS), "invalid baseline metrics")
    require(all(value is None or number(value) is not None for value in base.values()), "invalid token baseline value")
    last = None
    with Path(log_path).open() as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError("saved token log contains invalid JSON") from error
            if not isinstance(event, dict):
                continue
            payload = event.get("payload")
            if not isinstance(payload, dict):
                continue
            if event.get("type") == "session_meta":
                require(payload.get("id") == metadata.get("context_id"), "token log context differs")
            if event.get("type") != "event_msg" or payload.get("type") != "token_count":
                continue
            info = payload.get("info")
            total = info.get("total_token_usage") if isinstance(info, dict) else None
            if not isinstance(total, dict):
                continue
            current = {key: number(total.get(key)) for key in (
                "input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens",
                "reasoning_output_tokens", "response_count")}
            check_metric_subsets(current)
            if last:
                require(all(before is None or (current[key] is not None and current[key] >= before)
                            for key, before in last.items()), "token log counter reset or lost measurement")
            last = current
    require(last is not None, "saved token log has no cumulative token usage")
    metrics = {key: None for key in METRICS}
    for key, value in last.items():
        before = number(base.get(key))
        if value is not None and before is not None:
            require(value >= before, f"token baseline exceeds observed {key}")
            metrics[key] = value - before
    check_metric_subsets(metrics)
    digest = hashlib.sha256(json.dumps(baseline, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**copy.deepcopy(metadata), "metrics": metrics, "baseline_sha256": digest}


def ingest_subscription(state, snapshot):
    """Store account window observations separately from provider currency costs."""
    required = {"source_id", "window_id", "sequence", "used_percent", "observed_at", "resets_at"}
    require(isinstance(snapshot, dict) and set(snapshot) == required, "invalid subscription snapshot fields")
    key = json.dumps([text(snapshot[name], name) for name in ("source_id", "window_id", "resets_at")], separators=(",", ":"))
    require(type(snapshot["sequence"]) is int and snapshot["sequence"] >= 0, "subscription sequence must be nonnegative")
    require(snapshot["used_percent"] is None or (number(snapshot["used_percent"]) is not None
            and snapshot["used_percent"] <= 100), "subscription percent must be in [0, 100] or null")
    observed, resets = timestamp(snapshot["observed_at"]), timestamp(snapshot["resets_at"])
    require(resets > observed, "subscription reset must follow observation")
    records = state.get("usage_accounting", {}).get("subscriptions", {})
    old = records.get(key)
    if old and snapshot["sequence"] == old["sequence"]:
        require(snapshot == old, "same subscription sequence has different facts")
        return {"ingestion": "existing"}
    previous = [item for item in records.values() if all(item[name] == snapshot[name]
                for name in ("source_id", "window_id")) and item["resets_at"] != snapshot["resets_at"]]
    if previous:
        latest = max(previous, key=lambda item: timestamp(item["observed_at"]))
        require(observed >= timestamp(latest["resets_at"]) and resets > timestamp(latest["resets_at"]),
                "subscription reset differs before the previous window ended")
    if old:
        require(snapshot["sequence"] > old["sequence"] and observed >= timestamp(old["observed_at"]),
                "stale subscription snapshot")
        require(old["used_percent"] is None or (snapshot["used_percent"] is not None
                and snapshot["used_percent"] >= old["used_percent"]), "subscription counter reset within a window")
    state.setdefault("usage_accounting", {}).setdefault("subscriptions", {})[key] = copy.deepcopy(snapshot)
    return {"ingestion": "updated" if old else "new"}


def evaluate_budget(state, policy=None, now=None):
    """Gate future dispatch only; callers can always reconcile existing work."""
    if policy is None:
        policy = state.get("call_ledger", {}).get("usage_policy")
        try:
            check_policy_binding(state)
        except (ValueError, OSError, KeyError, TypeError) as error:
            return {"decision": "block", "dispatch_allowed": False,
                    "reasons": [{"code": "invalid_usage_binding", "detail": str(error)}], "resume_at": None}
    if policy is None:
        return {"decision": "allow", "dispatch_allowed": True, "reasons": [], "resume_at": None}
    reasons, resume = [], []
    try:
        policy = validate_policy(policy)
    except ValueError as error:
        return {"decision": "block", "dispatch_allowed": False,
                "reasons": [{"code": "invalid_usage_policy", "detail": str(error)}], "resume_at": None}
    summary = summarize_usage(state)
    reasons.extend(summary["anomalies"])
    limits = policy.get("limits", {})
    for metric in sorted(set(limits) | set(policy.get("require_known", []))):
        usage = summary["metrics"][metric]
        if usage["unknown_records"]:
            reasons.append({"code": "usage_unknown", "metric": metric, "unknown_records": usage["unknown_records"]})
        if metric in limits and usage["measured_sum"] >= limits[metric]:
            reasons.append({"code": "budget_exhausted", "metric": metric,
                            "used": usage["measured_sum"], "limit": limits[metric]})
    current = timestamp(now) if isinstance(now, str) else now or datetime.now(timezone.utc)
    for window in policy.get("subscription_limits", []):
        candidates = [item for item in summary["subscriptions"] if all(
            item[key] == window[key] for key in ("source_id", "window_id"))]
        snapshot = max(candidates, key=lambda item: timestamp(item["observed_at"])) if candidates else None
        reason = None
        if snapshot is None or snapshot["used_percent"] is None:
            reason = "subscription_usage_unknown"
        elif current < timestamp(snapshot["observed_at"]):
            reason = "subscription_observation_in_future"
        elif current >= timestamp(snapshot["resets_at"]):
            reason = "subscription_window_expired"
        elif "max_age_seconds" in window and (current - timestamp(snapshot["observed_at"])).total_seconds() > window["max_age_seconds"]:
            reason = "subscription_snapshot_stale"
        elif snapshot["used_percent"] >= window["max_used_percent"]:
            reason = "subscription_budget_exhausted"
            resume.append(snapshot["resets_at"])
        if reason:
            reasons.append({"code": reason, "source_id": window["source_id"], "window_id": window["window_id"]})
    return {"decision": "block" if reasons else "allow", "dispatch_allowed": not reasons,
            "reasons": reasons, "resume_at": max(resume, key=timestamp) if resume else None}
