#!/usr/bin/env python3
"""Validate an approved routing plan and calculate its approval digests.

A routing plan binds task contracts (``scope.inputs``) and exact model routes
(``routes``) to one recorded user approval. This module only reads and checks;
it never approves, writes, or dispatches.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

_SHARED_SCRIPTS = str(Path(__file__).resolve().parent)
if _SHARED_SCRIPTS not in sys.path:
    sys.path.insert(0, _SHARED_SCRIPTS)
from model_routing import load_config, runner_efforts, validate_selection
from context_packet import validate_budget

RUNNERS = {"codex", "claude", "pi", "grok", "gemini", "muse"}
NATIVE_TRANSPORTS = {"subagent", "thread"}
STATUS_LINE = re.compile(r"\*\*Status:\*\* (?:ready-for-agent|in-progress|done|blocked)\Z")
ROUTING_CONFIG = load_config()
EFFORT_FLAGS = {name: value["effort_flag"] for name, value in ROUTING_CONFIG["runners"].items() if value["effort_flag"]}
RUNNER_CONTROLLED_EFFORTS = set(ROUTING_CONFIG["effort_levels"])
RUNNER_EFFORTS = {name: set(runner_efforts(name, config=ROUTING_CONFIG)) for name in EFFORT_FLAGS}


def require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"route.{field} must be a nonempty string")
    return value


def canonical_digest(value: Any) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_task_text(text: str) -> str:
    """Normalize task text while ignoring its exact standalone workflow status."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(
        line
        for line in normalized.splitlines(keepends=True)
        if not STATUS_LINE.fullmatch(line.removesuffix("\n"))
    )


def content_digest(path: Path) -> str:
    return hashlib.sha256(canonical_task_text(path.read_text(encoding="utf-8")).encode("utf-8")).hexdigest()


def scope_path(value: str, root: Path) -> Path:
    if "://" in value:
        raise ValueError("scope input paths must be local files, not URLs")
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def normalized_scope_inputs(inputs: list[Any]) -> list[Any]:
    return sorted(inputs, key=lambda item: item["path"])


def normalized_routes(routes: list[Any]) -> list[Any]:
    return sorted(routes, key=lambda route: (route["id"], route["task_id"]))


def route_variants(route: dict[str, Any]) -> list[dict[str, Any]]:
    variants = [route]
    fallback = fallback_route(route)
    if fallback is not None:
        variants.append(fallback)
    return variants


def validate_native_spec(route: dict[str, Any]) -> dict[str, Any] | None:
    """Validate checked host capability data without inventing a host adapter."""
    native = route.get("native")
    if native is None:
        return None
    if not isinstance(native, dict):
        raise ValueError("route.native must be an object")
    for field in ("host", "transport", "capability_source"):
        require_string(native.get(field), f"native.{field}")
    if native["transport"] not in NATIVE_TRANSPORTS:
        raise ValueError("route.native.transport must be subagent or thread")
    efforts = native.get("supported_efforts")
    if not isinstance(efforts, list) or not efforts:
        raise ValueError("route.native.supported_efforts must be a nonempty list")
    if (
        any(not isinstance(effort, str) for effort in efforts)
        or len(set(efforts)) != len(efforts)
        or any(effort not in RUNNER_CONTROLLED_EFFORTS for effort in efforts)
    ):
        raise ValueError("route.native.supported_efforts contains an unsupported effort")
    return native


def validate_route(route: Any) -> dict[str, Any]:
    if not isinstance(route, dict):
        raise ValueError("each route must be an object")
    for field in (
        "id",
        "task_id",
        "input_path",
        "track",
        "role",
        "seat",
        "runner",
        "model",
        "model_verification",
        "mode",
        "effort_control",
    ):
        require_string(route.get(field), field)
    if route["role"] not in {"implementer", "reviewer"}:
        raise ValueError(f"route.role must be implementer or reviewer, got {route['role']!r}")
    if route["runner"] not in RUNNERS:
        raise ValueError(f"route.runner is not supported: {route['runner']!r}")
    if route["mode"] not in {"runner", "native"}:
        raise ValueError(f"route.mode must be runner or native, got {route['mode']!r}")
    if route["model_verification"] not in {"required", "allow_unverified"}:
        raise ValueError("route.model_verification must be required or allow_unverified")
    if route["runner"] == "muse":
        from model_routing import subscription_privacy
        if (route["seat"] != "muse-wonder-full" or route["role"] != "implementer"
                or route["mode"] != "runner" or route["model_verification"] != "required"
                or route.get("unavailable") != {"action": "block"}
                or route.get("privacy_evidence") != subscription_privacy(ROUTING_CONFIG)):
            raise ValueError("Muse requires an implementation runner route, exact receipt, no fallback, and scoped subscription evidence")
    if "provider_routing" in route:
        from provider_routing import validate_provider_routing
        if route["runner"] != "pi" or route["mode"] != "runner":
            raise ValueError("provider_routing requires a Pi runner route")
        validate_provider_routing(route["provider_routing"])
    if "capabilities" in route or "required_capabilities" in route:
        capabilities = route.get("capabilities", {})
        required = route.get("required_capabilities", [])
        if not isinstance(capabilities, dict) or set(capabilities) - {"tools", "images"} or any(type(v) is not bool for v in capabilities.values()):
            raise ValueError("route.capabilities must contain tools or images booleans")
        if not isinstance(required, list) or any(v not in {"tools", "images"} for v in required) or len(set(required)) != len(required):
            raise ValueError("invalid route.required_capabilities")
        if any(capabilities.get(v) is not True for v in required):
            raise ValueError("route lacks a required model capability")
    if "browser" in route:
        from browser_preflight import validate_browser_route
        if route["runner"] != "pi" or route["mode"] != "runner":
            raise ValueError("browser command policy requires a Pi runner route")
        validate_browser_route(route["browser"])
    if "source_sharing" in route:
        sharing = route["source_sharing"]
        fields = {"provider", "scope", "follow_ups", "exclusions", "reference"}
        if not isinstance(sharing, dict) or set(sharing) != fields:
            raise ValueError("source_sharing needs provider, scope, follow_ups, exclusions and approval reference")
        for key in fields:
            require_string(sharing[key], "source_sharing." + key)
    if "recovery" in route:
        recovery = route["recovery"]
        if not isinstance(recovery, dict) or set(recovery) != {"review_cycles", "evidence_recoveries"} or any(type(v) is not int or v < 1 for v in recovery.values()):
            raise ValueError("route.recovery needs positive review_cycles and evidence_recoveries")
    validate_budget(route.get("context_budget"))
    effort_control = route["effort_control"]
    effort = route.get("effort")
    native = validate_native_spec(route)
    if effort_control == "runner":
        if route["runner"] not in EFFORT_FLAGS:
            raise ValueError(f"route.runner {route['runner']!r} cannot enforce a selected effort")
        validate_selection(route["runner"], route["model"], effort, ROUTING_CONFIG)
    elif effort_control == "runtime":
        known = next((m for m in ROUTING_CONFIG["models"].values()
                      if m["runner"] == route["runner"] and m["model"] == route["model"]), None)
        runtime_pi = route["runner"] == "pi" and known and known.get("effort_profile") == "runtime"
        if route["mode"] != "runner" or not (route["runner"] == "gemini" or runtime_pi):
            raise ValueError("runtime controlled effort requires a verified runtime model route")
        if effort is not None:
            raise ValueError("route.effort must be null when effort_control is runtime")
    elif effort_control == "native":
        if route["mode"] != "native":
            raise ValueError("native controlled effort is only valid for a native route")
        if native is None:
            raise ValueError("native controlled effort requires route.native capability data")
        if effort not in native["supported_efforts"]:
            raise ValueError("route.effort is not supported by the approved native host capability")
    else:
        raise ValueError("route.effort_control must be runner, runtime, or native")
    unavailable = route.get("unavailable")
    if not isinstance(unavailable, dict) or unavailable.get("action") not in {"block", "use"}:
        raise ValueError("route.unavailable must be {action: block} or an explicit approved fallback")
    if unavailable["action"] == "use":
        fallback = merge_fallback(route, unavailable)
        for field in ("seat", "runner", "model", "model_verification", "effort", "mode", "effort_control"):
            if field not in unavailable:
                raise ValueError(f"route.unavailable.{field} is required for an approved fallback")
        if fallback["mode"] == "native" and fallback["effort_control"] == "native" and "native" not in unavailable:
            raise ValueError("route.unavailable.native is required for a native controlled fallback")
        validate_route(fallback)
    return route


def bound_review_policy(plan, root, scope_inputs):
    """Load the explicit feature policy only when its approved inputs are present."""
    if "review_policy" not in plan:
        return None
    from feature_review import validate_policy, policy_inputs
    policy_path = scope_path(require_string(plan["review_policy"], "review_policy"), root)
    policy = validate_policy(policy_path, root)
    inputs = {item["path"].resolve() for item in scope_inputs.values()}
    for locator in policy_inputs(policy_path, root):
        if scope_path(str(locator), root) not in inputs:
            raise ValueError(f"review policy input is not in scope.inputs: {locator}")
    for task_id, task_policy in policy["tasks"].items():
        grouped = {}
        for route in plan.get("routes", []):
            if route.get("task_id") == task_id:
                roles = grouped.setdefault(route["track"], {})
                if route["role"] in roles:
                    raise ValueError(f"feature task has a duplicate role: {task_id}/{route['track']}")
                roles[route["role"]] = route
                if scope_path(route["input_path"], root) != scope_path(task_policy["contract"], root):
                    raise ValueError("feature task route does not bind the policy task contract")
        expected = {"implementer"} if task_policy["review"] == "deferred" else {"implementer", "reviewer"}
        if not grouped or any(set(roles) != expected for roles in grouped.values()):
            raise ValueError(f"routing plan needs roles {sorted(expected)} for feature task {task_id}")
        if task_policy["review"] == "critical":
            for roles in grouped.values():
                if any(writer["model"] == reader["model"] for writer in route_variants(roles["implementer"])
                       for reader in route_variants(roles["reviewer"])):
                    raise ValueError(f"routing plan cannot assign self-review for {task_id}")
    final_route = policy["final_review"]["route"]
    validate_route(final_route)
    if final_route not in plan.get("routes", []):
        raise ValueError("feature reviewer route is not in approved routes")
    if final_route.get("role") != "reviewer":
        raise ValueError("feature final route must be a reviewer")
    for route in plan["routes"]:
        if route.get("role") == "implementer":
            if route.get("task_id") not in policy["tasks"]:
                raise ValueError("feature implementer route is absent from the policy task set")
            for writer in route_variants(route):
                for reader in route_variants(final_route):
                    if writer["model"] == reader["model"]:
                        raise ValueError("feature reviewer cannot review its own implementation model")
    return {"path": str(policy_path), "sha256": file_digest(policy_path), "value": policy}


def load_routing_plan(path: str, task_id: str, active_tracks: set[str], require_approved: bool, root: Path) -> dict[str, Any]:
    plan_candidate = Path(path).expanduser()
    plan_path = (plan_candidate if plan_candidate.is_absolute() else root / plan_candidate).resolve()
    if not plan_path.is_file():
        raise ValueError(f"routing plan not found: {plan_path}")
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"routing plan is not valid JSON: {error}") from error
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ValueError("routing plan must have schema_version 1")
    approval = plan.get("approval")
    if not isinstance(approval, dict) or not isinstance(approval.get("status"), str):
        raise ValueError("routing plan must include approval.status")
    if require_approved and approval.get("status") != "approved":
        raise ValueError("routing plan is not user approved")
    for field in ("decided_at", "reference", "scope_digest", "routes_digest"):
        require_string(approval.get(field), f"approval.{field}")
    if not re.fullmatch(r"[a-f0-9]{64}", approval["scope_digest"]):
        raise ValueError("approval.scope_digest must be a 64 character SHA-256")
    if not re.fullmatch(r"[a-f0-9]{64}", approval["routes_digest"]):
        raise ValueError("approval.routes_digest must be a 64 character SHA-256")
    scope = plan.get("scope")
    if not isinstance(scope, dict) or not isinstance(scope.get("inputs"), list) or not scope["inputs"]:
        raise ValueError("routing plan must include scope.inputs")
    scope_inputs: dict[str, dict[str, Any]] = {}
    for item in scope["inputs"]:
        if not isinstance(item, dict):
            raise ValueError("each scope input must be an object")
        input_path = require_string(item.get("path"), "scope.inputs.path")
        expected_digest = require_string(item.get("content_sha256"), "scope.inputs.content_sha256")
        if not re.fullmatch(r"[a-f0-9]{64}", expected_digest):
            raise ValueError(f"scope input digest is invalid for {input_path!r}")
        resolved = scope_path(input_path, root)
        if not resolved.is_file():
            raise ValueError(f"scope input is missing or not a file: {input_path}")
        if content_digest(resolved) != expected_digest:
            raise ValueError(f"scope input changed after approval: {input_path}")
        if input_path in scope_inputs:
            raise ValueError(f"duplicate scope input path: {input_path}")
        scope_inputs[input_path] = {"path": resolved, "content_sha256": expected_digest}
    if canonical_digest(normalized_scope_inputs(scope["inputs"])) != approval["scope_digest"]:
        raise ValueError("approval.scope_digest does not match scope.inputs")
    routes = plan.get("routes")
    if not isinstance(routes, list):
        raise ValueError("routing plan must include routes[]")
    all_route_ids: set[str] = set()
    for route in routes:
        validated = validate_route(route)
        if validated["id"] in all_route_ids:
            raise ValueError(f"duplicate route id: {validated['id']}")
        all_route_ids.add(validated["id"])
    if canonical_digest(normalized_routes(routes)) != approval["routes_digest"]:
        raise ValueError("approval.routes_digest does not match routes")
    review_policy = bound_review_policy(plan, root, scope_inputs)
    selected = [validate_route(route) for route in routes if isinstance(route, dict) and route.get("task_id") == task_id]
    if not selected:
        raise ValueError(f"routing plan has no routes for task {task_id!r}")
    by_track: dict[str, dict[str, dict[str, Any]]] = {}
    for route in selected:
        track = route["track"]
        if track not in active_tracks:
            continue
        roles = by_track.setdefault(track, {})
        if route["role"] in roles:
            raise ValueError(f"routing plan has duplicate {route['role']} route for {task_id}/{track}")
        roles[route["role"]] = route
    if set(by_track) != active_tracks:
        missing = ", ".join(sorted(active_tracks - set(by_track)))
        raise ValueError(f"routing plan is missing active track routes: {missing}")
    for track, roles in by_track.items():
        task_policy = review_policy["value"]["tasks"].get(task_id) if review_policy else None
        deferred = task_policy is not None and task_policy["review"] == "deferred"
        expected_roles = {"implementer"} if deferred else {"implementer", "reviewer"}
        if set(roles) != expected_roles:
            raise ValueError(f"routing plan needs roles {sorted(expected_roles)} for {task_id}/{track}")
        implementer = roles["implementer"]
        if task_policy and scope_path(implementer["input_path"], root) != scope_path(task_policy["contract"], root):
            raise ValueError("feature task route does not bind the policy task contract")
        if not deferred:
            for writer in route_variants(implementer):
                for reader in route_variants(roles["reviewer"]):
                    if writer["model"] == reader["model"]:
                        raise ValueError(f"routing plan cannot assign self-review for {task_id}/{track}")
        for route in roles.values():
            if route["input_path"] not in scope_inputs:
                raise ValueError(f"route input_path is not in scope.inputs: {route['input_path']}")
    return {"path": str(plan_path), "approval": approval, "scope_inputs": scope_inputs, "routes": by_track,
            **({"review_policy": review_policy} if review_policy is not None else {})}


def fallback_route(route: dict[str, Any]) -> dict[str, Any] | None:
    unavailable = route["unavailable"]
    if unavailable["action"] != "use":
        return None
    fallback = merge_fallback(route, unavailable)
    validate_route(fallback)
    return fallback


def merge_fallback(route: dict[str, Any], alternate: dict[str, Any]) -> dict[str, Any]:
    if "provider_routing" in route and alternate.get("runner") != route["runner"] and "provider_routing" not in alternate:
        raise ValueError("a different fallback runner needs an explicit provider_routing decision")
    fallback = {**route, **alternate, "unavailable": {"action": "block"}}
    if route.get("provider_routing") and fallback.get("runner") == "pi":
        from provider_routing import validate_provider_routing
        parent_policy = route["provider_routing"]
        policy = fallback.get("provider_routing")
        if policy is None:
            raise ValueError("Pi fallback cannot remove provider_routing")
        validate_provider_routing(policy)
        if "only" in parent_policy and ("only" not in policy or not set(policy["only"]) <= set(parent_policy["only"])):
            raise ValueError("Pi fallback cannot expand the provider allowlist")
        if parent_policy.get("allow_fallbacks") is False and policy.get("allow_fallbacks") is not False:
            raise ValueError("Pi fallback cannot enable provider fallbacks")
    for field in ("provider_routing", "browser", "capabilities", "required_capabilities"):
        if field in fallback and fallback[field] is None:
            del fallback[field]
    return fallback


def receipt_error(route: dict[str, Any], result: dict[str, Any]) -> str | None:
    if route["runner"] == "muse":
        if (result.get("privacy_status") != "user_confirmed"
                or result.get("privacy_evidence") != route.get("privacy_evidence")
                or result.get("contributor_mode") != "off"):
            return "Muse result does not match the approved subscription evidence or contributor setting"
    if "provider_routing" in route:
        from provider_routing import provider_receipt_error
        policy_error = provider_receipt_error(route["provider_routing"], result)
        if policy_error:
            return policy_error
    if "browser" in route:
        if result.get("tool_policy") != "browser" or result.get("browser_mechanism") != route["browser"]["mechanism"]:
            return "browser receipt does not match the approved mechanism and tool policy"
    if result.get("effective_runner") != route["runner"]:
        return f"effective runner {result.get('effective_runner')!r} does not match approved runner {route['runner']!r}"
    if result.get("configured_model") != route["model"]:
        return f"configured model {result.get('configured_model')!r} does not match approved model {route['model']!r}"
    receipt = result.get("model_receipt")
    if not isinstance(receipt, dict):
        return "runner result is missing model_receipt"
    receipt_status = receipt.get("status")
    if route["model_verification"] == "required":
        if receipt_status != "verified":
            return "approved route requires a verified serving-model receipt"
        if receipt.get("source") not in {"native_event", "provider_event"}:
            return "verified serving-model receipt has no trusted observation source"
        if receipt.get("observed_model") != route["model"]:
            return f"observed model {receipt.get('observed_model')!r} does not match approved model {route['model']!r}"
        if result.get("effective_model") != route["model"]:
            return f"effective model {result.get('effective_model')!r} does not match observed approved model {route['model']!r}"
    elif receipt_status == "verified":
        if receipt.get("source") not in {"native_event", "provider_event"}:
            return "verified serving-model receipt has no trusted observation source"
        if receipt.get("observed_model") != route["model"] or result.get("effective_model") != route["model"]:
            return "verified serving-model receipt does not match the approved model"
    elif receipt_status == "unverified":
        if receipt.get("observed_model") is not None or result.get("effective_model") is not None:
            return "unverified route receipt must not claim an observed serving model"
    else:
        return "runner result has an invalid model_receipt status"
    if route["effort_control"] == "runner":
        if result.get("effort_clamped") is True:
            return "runner clamped the approved effort"
        observed = result.get("effective_effort", result.get("requested_effort", result.get("effort", result.get("thinking"))))
        if observed != route["effort"]:
            return f"effective effort {observed!r} does not match approved effort {route['effort']!r}"
    elif route["effort_control"] == "native":
        if result.get("configured_effort") != route["effort"]:
            return f"configured native effort {result.get('configured_effort')!r} does not match approved effort {route['effort']!r}"
        if result.get("effective_effort") != route["effort"]:
            return f"effective native effort {result.get('effective_effort')!r} does not match approved effort {route['effort']!r}"
    elif route["effort_control"] == "runtime" and route["runner"] == "pi":
        if result.get("effective_effort", result.get("thinking")) is not None:
            return "runtime model receipt must not claim a selected effort"
    return None


def plan_digests(plan_path: Path, root: Path) -> dict[str, Any]:
    """Return current scope inputs and approval digests for a draft plan."""
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict) or not isinstance(plan.get("scope"), dict):
        raise ValueError("routing plan must contain scope.inputs")
    inputs = plan["scope"].get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise ValueError("routing plan must contain one or more scope inputs")
    actual_inputs: list[dict[str, str]] = []
    for item in inputs:
        if not isinstance(item, dict):
            raise ValueError("each scope input must be an object")
        input_path = require_string(item.get("path"), "scope.inputs.path")
        if any(row["path"] == input_path for row in actual_inputs):
            raise ValueError(f"duplicate scope input path: {input_path}")
        resolved = scope_path(input_path, root)
        if not resolved.is_file():
            raise ValueError(f"scope input is missing or not a file: {input_path}")
        actual_inputs.append({"path": input_path, "content_sha256": content_digest(resolved)})
    routes = plan.get("routes")
    if not isinstance(routes, list) or not routes:
        raise ValueError("routing plan must contain one or more routes")
    paths = {row["path"] for row in actual_inputs}
    ids: set[str] = set()
    for route in routes:
        validated = validate_route(route)
        if validated["id"] in ids:
            raise ValueError(f"duplicate route id: {validated['id']}")
        if validated["input_path"] not in paths:
            raise ValueError(f"route input_path is not in scope.inputs: {validated['input_path']}")
        ids.add(validated["id"])
    return {
        "scope": {"inputs": normalized_scope_inputs(actual_inputs)},
        "approval_digests": {
            "scope_digest": canonical_digest(normalized_scope_inputs(actual_inputs)),
            "routes_digest": canonical_digest(normalized_routes(routes)),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    digests = commands.add_parser("digests", help="calculate scope and route digests for a draft plan")
    digests.add_argument("--routing-plan", required=True)
    digests.add_argument("--working-dir", default=".")
    check = commands.add_parser("check", help="validate an approved plan for one task")
    check.add_argument("--routing-plan", required=True)
    check.add_argument("--task-id", required=True)
    check.add_argument("--track", action="append", required=True)
    check.add_argument("--working-dir", default=".")
    args = parser.parse_args(argv)
    root = Path(args.working_dir).expanduser().resolve()
    candidate = Path(args.routing_plan).expanduser()
    plan_path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        if args.command == "digests":
            result = plan_digests(plan_path, root)
        else:
            routed = load_routing_plan(str(plan_path), args.task_id, set(args.track), True, root)
            result = {"status": "approved", "routes": routed["routes"]}
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
