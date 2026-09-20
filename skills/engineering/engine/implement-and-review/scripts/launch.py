#!/usr/bin/env python3
"""Launch approved implementation and review routes for one task.

The routing plan is the authority for model, runner, effort, and known fallback.
This helper never selects a default model, changes a route, commits, pushes, merges,
opens a pull request, or removes worktrees unless its explicit cleanup command is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NoReturn


SKILL_ROOT = Path(__file__).resolve().parents[1]
JOB_ID_RE = re.compile(r"\b([a-z]+-[0-9a-f]{8})\b")
RUNNERS = {"codex", "claude", "pi", "grok", "gemini", "cline"}
NATIVE_TRANSPORTS = {"subagent", "thread"}
RUNNER_RESUME_FLAGS = {
    "codex": "--resume",
    "claude": "--resume",
    "grok": "--resume",
    "pi": "--session",
    "cline": "--session",
}
TERMINAL_JOB_STATUSES = {"completed", "failed", "died", "cancelled", "missing"}
ACTIVE_REVIEW_STATUSES = {"starting", "running", "awaiting_native_dispatch", "orchestrator-managed"}
MAX_REVIEW_CYCLES = 3
MAX_EVIDENCE_RECOVERIES = 1
STATUS_LINE = re.compile(r"\*\*Status:\*\* (?:ready-for-agent|in-progress|done|blocked)\Z")
WRITE_BOUNDARY = """

Execution boundary
Implement only this approved task and its acceptance contract. Do not create a git
commit, push, merge, open or update a pull request, delete worktrees, change
deployment state, or send messages to external services. Report evidence and any
blocker to the orchestrator.
"""
REVIEW_BOUNDARY = """

Review boundary
Review only this approved task against its acceptance contract and evidence. Do
not edit files, change scope, choose a route, or send external messages. Report
findings and evidence to the orchestrator.
"""


def _skills_dir() -> Path:
    """Find the source or installed skills root that owns shared/scripts."""
    for parent in SKILL_ROOT.parents:
        if (parent / "shared" / "scripts" / "runner_jobs.py").is_file():
            return parent
    return SKILL_ROOT.parent


SKILLS_DIR = _skills_dir()
_SHARED_SCRIPTS = str(SKILLS_DIR / "shared" / "scripts")
if _SHARED_SCRIPTS not in sys.path:
    sys.path.insert(0, _SHARED_SCRIPTS)
from model_routing import load_config, model_efforts, runner_efforts, validate_selection
from context_packet import DEFAULT_MAX_BYTES, measure_rendered, validate_budget
import runner_jobs

ROUTING_CONFIG = load_config()
EFFORT_FLAGS = {name: value["effort_flag"] for name, value in ROUTING_CONFIG["runners"].items() if value["effort_flag"]}
RUNNER_CONTROLLED_EFFORTS = set(ROUTING_CONFIG["effort_levels"])
RUNNER_EFFORTS = {name: set(runner_efforts(name, config=ROUTING_CONFIG)) for name in EFFORT_FLAGS}
CODEX_MODEL_EFFORTS = model_efforts("codex", ROUTING_CONFIG)



def evidence_module():
    shared = str(SKILLS_DIR / "shared" / "scripts")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    import review_evidence
    return review_evidence


def review_source_binding(snapshot_path, working_dir, contract, base, previous=None):
    evidence = evidence_module()
    snapshot_path = Path(require_string(snapshot_path, "review snapshot")).expanduser().resolve()
    snapshot = evidence.current_snapshot(snapshot_path, base)
    evidence.require(snapshot["source"]["root"] == str(working_dir), "review snapshot belongs to another worktree")
    evidence.require(snapshot["contract"]["path"] == str(contract["path"]), "review snapshot uses another task contract")
    evidence.require(snapshot["contract"]["sha256"] == evidence.contract_hash(contract["path"]), "review contract changed")
    if previous is not None:
        evidence.require(previous in snapshot["previous_reviews"], "snapshot must reference the latest recorded review for this track")
    return {"path": str(snapshot_path), "sha256": file_digest(snapshot_path)}


def runner_script(name: str) -> Path:
    shared = str(SKILLS_DIR / "shared" / "scripts")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        from skill_paths import runner_script as resolve_runner_script
    except ImportError:
        return SKILLS_DIR / f"{name}-runner" / "scripts" / f"run_{name}.py"
    return resolve_runner_script(name, root=SKILLS_DIR)


def err(*message: object) -> None:
    print(*message, file=sys.stderr)


def fail(message: str, code: int = 1) -> NoReturn:
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False))
    err(f"error: {message}")
    raise SystemExit(code)


def git(args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        fail("not inside a git repository")
    return Path(result.stdout.strip())


def maybe_repo_root(working_dir: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=working_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunnerLaunchError(RuntimeError):
    pass


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


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        raise ValueError(f"route.runner is not supported by this launcher: {route['runner']!r}")
    if route["mode"] not in {"runner", "native"}:
        raise ValueError(f"route.mode must be runner or native, got {route['mode']!r}")
    if route["model_verification"] not in {"required", "allow_unverified"}:
        raise ValueError("route.model_verification must be required or allow_unverified")
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
        if route["mode"] != "runner" or route["runner"] != "gemini":
            raise ValueError("runtime controlled effort is only valid for a gemini runner route")
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
        fallback = {**route, **unavailable}
        fallback["unavailable"] = {"action": "block"}
        for field in ("seat", "runner", "model", "model_verification", "effort", "mode", "effort_control"):
            if field not in unavailable:
                raise ValueError(f"route.unavailable.{field} is required for an approved fallback")
        if fallback["mode"] == "native" and fallback["effort_control"] == "native" and "native" not in unavailable:
            raise ValueError("route.unavailable.native is required for a native controlled fallback")
        validate_route(fallback)
    return route


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
        if set(roles) != {"implementer", "reviewer"}:
            raise ValueError(f"routing plan needs one implementer and one reviewer for {task_id}/{track}")
        implementer = roles["implementer"]
        reviewer = roles["reviewer"]
        for writer in route_variants(implementer):
            for reader in route_variants(reviewer):
                if writer["model"] == reader["model"]:
                    raise ValueError(f"routing plan cannot assign self-review for {task_id}/{track}")
        for route in roles.values():
            if route["input_path"] not in scope_inputs:
                raise ValueError(f"route input_path is not in scope.inputs: {route['input_path']}")
    return {"path": str(plan_path), "approval": approval, "scope_inputs": scope_inputs, "routes": by_track}


def fallback_route(route: dict[str, Any]) -> dict[str, Any] | None:
    unavailable = route["unavailable"]
    if unavailable["action"] != "use":
        return None
    fallback = {**route, **unavailable, "unavailable": {"action": "block"}}
    validate_route(fallback)
    return fallback


def persistent_pi_session_id(route: dict[str, Any], brief: Path) -> str:
    """Give a first Pi turn a stable native session identifier without creating it."""
    route_key = hashlib.sha256(route["id"].encode("utf-8")).hexdigest()[:16]
    return str(brief.parent / f"pi-session-{route_key}.jsonl")


def route_arguments(
    route: dict[str, Any],
    brief: Path,
    working_dir: Path,
    role: str,
    timeout: int,
    metadata: dict[str, Any],
    read_only: bool,
    resume_context_id: str | None = None,
) -> list[str]:
    from execution_provenance import capture
    metadata = {**metadata, "execution_provenance": capture([Path(__file__), runner_script(route["runner"])])}
    arguments = [
        "--prompt-file", str(brief),
        "--working-dir", str(working_dir),
        "--model", route["model"],
        "--role", role,
        "--timeout", str(timeout),
        "--disable-fallback",
        "--metadata-json", json.dumps(metadata),
    ]
    if route["runner"] == "claude":
        arguments.extend(["--output-format", "stream-json"])
    if route["runner"] in {"pi", "cline"}:
        arguments.extend(["--seat", route["seat"]])
    if route["effort_control"] == "runner":
        arguments.extend([EFFORT_FLAGS[route["runner"]], route["effort"]])
    if resume_context_id:
        resume_flag = RUNNER_RESUME_FLAGS.get(route["runner"])
        if resume_flag is None:
            raise RunnerLaunchError(
                f"{route['runner']} has no exact persistent-session resume adapter for route {route['id']}"
            )
        arguments.extend([resume_flag, resume_context_id])
    elif route["runner"] == "pi":
        arguments.extend(["--session", persistent_pi_session_id(route, brief)])
    arguments.append("--restrict-tools" if read_only else "--allow-write")
    return arguments


def fire_runner(name: str, arguments: list[str], working_dir: Path, dry_run: bool) -> dict[str, Any]:
    command = [sys.executable, str(runner_script(name)), *arguments, "--background", "--json"]
    if dry_run:
        err(f"[dry-run] ({working_dir}) " + " ".join(shlex.quote(part) for part in command))
        return {"job_id": None, "job_dir": None, "result_file": None, "dry_run": True}
    result = subprocess.run(command, cwd=str(working_dir), capture_output=True, text=True, check=False)
    output = (result.stdout or "").strip()
    try:
        summary = json.loads(output)
        job_id = summary.get("job_id")
    except json.JSONDecodeError:
        summary = {}
        match = JOB_ID_RE.search(output)
        job_id = match.group(1) if match else None
    if not job_id:
        raise RunnerLaunchError(
            f"could not start {name} route. stdout={output[:400]!r} stderr={(result.stderr or '').strip()[:400]!r}"
        )
    return {
        "job_id": job_id,
        "job_dir": summary.get("job_dir"),
        "result_file": summary.get("result_file"),
        "pid": summary.get("pid"),
    }


def dispatch_route(
    route: dict[str, Any],
    brief: Path,
    working_dir: Path,
    role: str,
    timeout: int,
    metadata: dict[str, Any],
    read_only: bool,
    dry_run: bool,
    resume_context: dict[str, Any] | None = None,
    use_approved_fallback: bool = True,
) -> dict[str, Any]:
    measurement = metadata.get("input_measurement")
    if not dry_run or (measurement is None and brief.is_file()):
        with brief.open(encoding="utf-8", newline="") as stream:
            actual = measure_rendered(stream.read(), route.get("context_budget"))
        if measurement is not None and measurement != actual:
            raise ValueError("rendered input changed after budget preflight")
        measurement = actual
    if measurement is not None:
        metadata = {**metadata, "input_measurement": measurement}
    if route["mode"] == "native":
        native = validate_native_spec(route) or {}
        context_id = resume_context.get("context_id") if isinstance(resume_context, dict) else None
        context_action = "resume" if isinstance(context_id, str) and context_id else "start"
        if metadata.get("context_recovery"):
            context_action = "reconstruct"
        return {
            "mode": "native",
            "status": "awaiting_native_dispatch",
            "selected_route": route,
            "effective_route": route,
            "native_dispatch": {
                "route_id": route["id"],
                "host": native.get("host"),
                "transport": native.get("transport"),
                "capability_source": native.get("capability_source"),
                "context_action": context_action,
                "parent_history": "none",
                "input_path": str(brief),
                "input_measurement": measurement,
                "context_id": context_id,
                "context_recovery_reason": metadata.get("context_recovery_reason"),
                "call_id": metadata.get("call_id"),
                "task_id": metadata.get("task_id"),
                "role": route["role"],
                "configured_model": route["model"],
                "configured_effort": route.get("effort"),
                "effort_control": route["effort_control"],
                "tool_policy": "read-only" if read_only else "write",
                "input_revision": metadata.get("input_revision"),
            },
            "pending": "Dispatch this exact native route, preserve its role context, and record its receipt.",
        }
    try:
        result = fire_runner(
            route["runner"],
            route_arguments(route, brief, working_dir, role, timeout, metadata, read_only, resume_context_id=(
                resume_context.get("context_id") if isinstance(resume_context, dict) else None
            )),
            working_dir,
            dry_run,
        )
        return {
            "mode": "runner",
            "selected_route": route,
            "effective_route": route,
            "resume_context_id": resume_context.get("context_id") if isinstance(resume_context, dict) else None,
            "input_measurement": measurement,
            "parent_history": "none",
            "input_revision": metadata.get("input_revision"),
            "tool_policy": "read-only" if read_only else "write",
            **result,
        }
    except RunnerLaunchError as primary_error:
        fallback = fallback_route(route)
        if fallback is None or not use_approved_fallback or resume_context is not None:
            raise
        try:
            result = dispatch_route(
                fallback,
                brief,
                working_dir,
                role,
                timeout,
                metadata,
                read_only,
                dry_run,
                resume_context=None,
                use_approved_fallback=False,
            )
        except RunnerLaunchError as fallback_error:
            raise RunnerLaunchError(f"primary route failed: {primary_error}; approved fallback failed: {fallback_error}") from fallback_error
        return {
            **result,
            "selected_route": route,
            "effective_route": fallback,
            "fallback_reason": str(primary_error),
        }


def worktree_exists(root: Path, path: Path) -> bool:
    output = git(["worktree", "list", "--porcelain"], cwd=root).stdout
    target = str(path.resolve())
    return any(line.removeprefix("worktree ") == target for line in output.splitlines() if line.startswith("worktree "))


def branch_exists(root: Path, branch: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root, check=False).returncode == 0


def create_worktree(root: Path, path: Path, branch: str, base: str, force: bool, dry_run: bool) -> None:
    has_worktree = worktree_exists(root, path)
    has_branch = branch_exists(root, branch)
    if has_worktree or has_branch:
        if not force:
            raise RunnerLaunchError(
                f"worktree {path} or branch {branch} already exists. Use a new session id or explicit --force."
            )
        if not dry_run:
            if has_worktree:
                removed = git(["worktree", "remove", "--force", str(path)], cwd=root, check=False)
                if removed.returncode != 0:
                    raise RunnerLaunchError(removed.stderr.strip() or removed.stdout.strip() or f"could not remove {path}")
            if has_branch:
                deleted = git(["branch", "-D", branch], cwd=root, check=False)
                if deleted.returncode != 0:
                    raise RunnerLaunchError(deleted.stderr.strip() or deleted.stdout.strip() or f"could not delete {branch}")
    if dry_run:
        err(f"[dry-run] git worktree add -b {branch} {path} {base}")
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RunnerLaunchError(f"could not prepare worktree parent {path.parent}: {error}") from error
    created = git(["worktree", "add", "-b", branch, str(path), base], cwd=root, check=False)
    if created.returncode != 0:
        raise RunnerLaunchError(created.stderr.strip() or created.stdout.strip() or f"could not create {path}")


def render_bound_brief(
    contract: dict[str, Any],
    source: Path,
    boundary: str,
    note_label: str,
) -> tuple[str, dict[str, Any]]:
    """Bind derived worker notes to the approved task contract they cannot replace."""
    contract_path = contract["path"]
    contract_text = contract_path.read_text(encoding="utf-8")
    note_text = source.read_text(encoding="utf-8")
    packet_path = source.with_suffix(source.suffix + ".packet.json")
    if packet_path.exists():
        from context_packet import verify
        verify(packet_path, source)
    elif len(note_text.encode("utf-8")) > DEFAULT_MAX_BYTES:
        raise ValueError(f"derived brief exceeds {DEFAULT_MAX_BYTES} bytes; link evidence or supply a bounded context packet")
    rendered = f"""Approved task contract
Source: {contract_path}
Canonical content SHA-256: {contract['content_sha256']}

The task contract below controls scope and acceptance. The {note_label.lower()}
may add execution detail only. If it conflicts with the contract, stop and
report the conflict.

Task contract begins
{contract_text.rstrip()}
Task contract ends

{note_label}
Source: {source}
SHA-256: {file_digest(source)}

{note_text.rstrip()}
"""
    return rendered.rstrip() + boundary + "\n", {
        "contract_path": str(contract_path),
        "contract_content_sha256": contract["content_sha256"],
        "derived_path": str(source),
        "derived_sha256": file_digest(source),
        **({"context_packet": str(packet_path), "context_packet_sha256": file_digest(packet_path)} if packet_path.exists() else {}),
    }


def write_bound_brief(rendered: str, destination: Path, dry_run: bool) -> Path:
    if not dry_run:
        destination.write_text(rendered, encoding="utf-8")
    return destination


def native_call_id(route: dict[str, Any], phase: str, cycle: int, attempt: int) -> str:
    """Bind a host receipt to one recorded route invocation, not a global session."""
    return f"{route['id']}:{phase}:{cycle}:{attempt}"


def task_tracks(args: argparse.Namespace, root: Path) -> dict[str, Path]:
    tracks: dict[str, Path] = {}
    for track, brief in args.track_briefs:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", track):
            fail(f"invalid track name: {track!r}")
        if track in tracks:
            fail(f"duplicate track name: {track!r}")
        source_candidate = Path(brief).expanduser()
        source = (source_candidate if source_candidate.is_absolute() else root / source_candidate).resolve()
        if not source.is_file():
            fail(f"brief for track {track!r} is missing or not a file")
        tracks[track] = source
    if not tracks:
        fail("provide at least one --track NAME BRIEF pair")
    return tracks


def validate_path_component(value: str, field: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value):
        fail(f"invalid {field}: {value!r}")


def resolve_working_root(value: str | None) -> tuple[Path, Path | None]:
    candidate = Path(value).expanduser().resolve() if value else Path.cwd().resolve()
    if not candidate.is_dir():
        fail(f"working directory is missing or not a directory: {candidate}")
    git_root = maybe_repo_root(candidate)
    return (git_root or candidate), git_root


def initial_manifest(
    args: argparse.Namespace,
    working_root: Path,
    git_root: Path | None,
    base: str | None,
    artifact_dir: Path,
    worktrees_dir: Path | None,
    routing: dict[str, Any],
) -> dict[str, Any]:
    from execution_provenance import capture
    provenance = capture([Path(__file__), SKILL_ROOT / "SKILL.md",
                          SKILLS_DIR / "shared" / "model-routing.json",
                          SKILLS_DIR / "shared" / "scripts" / "review_evidence.py"])
    return {
        "schema_version": 1,
        "skill_provenance": provenance,
        "skill": "implement-and-review",
        "session_id": args.session_id,
        "task_id": args.task_id,
        "base": base,
        "working_root": str(working_root),
        "repo_root": str(git_root) if git_root else None,
        "isolation": args.isolation,
        "worktrees_dir": str(worktrees_dir) if worktrees_dir else None,
        "routing_plan": {"path": routing["path"], "approval": routing["approval"]},
        "artifact_dir": str(artifact_dir),
        "dry_run": args.dry_run,
        "status": "running",
        "phase": "launch",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "attempts": {"review_cycles": {}, "evidence_recoveries": {}},
        "ceilings": {
            "max_review_cycles": MAX_REVIEW_CYCLES,
            "max_evidence_recoveries": MAX_EVIDENCE_RECOVERIES,
        },
        "gates": ([
            {
                "gate": "model_plan_approval",
                "decision": "approved",
                "decided_at": routing["approval"]["decided_at"],
                "reference": routing["approval"]["reference"],
                "scope_digest": routing["approval"]["scope_digest"],
                "routes_digest": routing["approval"]["routes_digest"],
            }
        ] if routing["approval"].get("status") == "approved" else []),
        "side_effects": [],
        "steps": [],
        "native_contexts": {},
        "runner_contexts": {},
        "tracks": {},
        "reviews": [],
    }


def fail_track_launch(manifest: dict[str, Any], manifest_path_value: Path, track: str, message: str, dry_run: bool) -> NoReturn:
    record = manifest["tracks"][track]
    record["status"] = "failed"
    record["implementation"] = {
        "status": "failed",
        "selected_route": record["implementer_route"],
        "error": message,
    }
    manifest["status"] = "failed"
    manifest["phase"] = f"{track}_implementation"
    if not dry_run:
        save_manifest(manifest, manifest_path_value)
    fail(message)


def cmd_launch(args: argparse.Namespace) -> int:
    validate_path_component(args.session_id, "session id")
    validate_path_component(args.task_id, "task id")
    root, git_root = resolve_working_root(args.working_dir)
    briefs = task_tracks(args, root)
    tracks = set(briefs)
    try:
        routing = load_routing_plan(args.routing_plan, args.task_id, tracks, require_approved=not args.dry_run, root=root)
    except ValueError as error:
        fail(str(error))
    prepared: dict[str, dict[str, Any]] = {}
    try:
        for track, source in briefs.items():
            route = routing["routes"][track]["implementer"]
            contract = routing["scope_inputs"][route["input_path"]]
            rendered, binding = render_bound_brief(contract, source, WRITE_BOUNDARY, "Derived implementation notes")
            binding["input_measurement"] = measure_rendered(rendered, route.get("context_budget"))
            prepared[track] = {
                "rendered": rendered,
                "binding": binding,
                "source": source,
                "input_revision": text_digest(rendered),
            }
    except (ValueError, OSError, UnicodeError) as error:
        fail(f"could not prepare a bound implementation brief: {error}")
    if args.isolation == "working-tree" and len(tracks) > 1:
        fail("multiple implementation tracks require explicit worktree isolation")
    if args.isolation == "worktree" and git_root is None:
        fail("worktree isolation requires a git repository")
    if git_root and not args.allow_dirty and git(["status", "--porcelain", "--untracked-files=no"], cwd=git_root).stdout.strip():
        fail("working tree has uncommitted tracked changes; pass --allow-dirty only when the task scope is known")
    if args.base and git_root is None:
        fail("--base requires a git repository")
    base = args.base or (git(["rev-parse", "HEAD"], cwd=git_root).stdout.strip() if git_root else None)
    artifact_dir = root / ".ai-workflow" / "impl-review" / args.session_id / args.task_id
    worktrees_dir = (
        (Path(args.worktrees_dir).expanduser().resolve() if args.worktrees_dir else git_root.parent / ".worktrees" / f"impl-review-{args.session_id}" / args.task_id)
        if git_root
        else None
    )
    if not args.dry_run:
        artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest = initial_manifest(args, root, git_root, base, artifact_dir, worktrees_dir, routing)
    if args.dry_run and routing["approval"].get("status") != "approved":
        manifest["approval_preview"] = True
        manifest["status"] = "unapproved_preview"
    manifest_path_value = artifact_dir / "launch-manifest.json"
    if not args.dry_run:
        from run_state import atomic_write
        try:
            atomic_write(manifest_path_value, manifest, exclusive=True)
        except FileExistsError:
            fail(f"task manifest already exists: {manifest_path_value}; resume or reconcile the existing task")
    for track in sorted(tracks):
        if args.isolation == "worktree":
            branch = f"impl/{args.task_id}-{track}-{args.session_id}"
            assert worktrees_dir is not None and git_root is not None and base is not None
            working_dir = worktrees_dir / track
        else:
            branch = None
            working_dir = root
        routes = routing["routes"][track]
        metadata = {
            "session": args.session_id,
            "task_id": args.task_id,
            "track": track,
            "phase": "implement",
            "routing_plan": routing["path"],
            "input_revision": prepared[track]["input_revision"],
            "input_measurement": prepared[track]["binding"]["input_measurement"],
            "call_id": native_call_id(routes["implementer"], "implementation", 0, 1),
        }
        manifest["tracks"][track] = {
            "active": True,
            "status": "preparing",
            "branch": branch,
            "working_dir": str(working_dir),
            "brief": str(artifact_dir / f"{track}-implementation-brief.md"),
            "brief_binding": prepared[track]["binding"],
            "implementer_route": routes["implementer"],
            "reviewer_route": routes["reviewer"],
            "implementation": {"status": "pending", "selected_route": routes["implementer"]},
        }
        if not args.dry_run:
            save_manifest(manifest, manifest_path_value)
        try:
            if args.isolation == "worktree":
                create_worktree(git_root, working_dir, branch, base, args.force, args.dry_run)
                manifest["tracks"][track]["worktree"] = {"status": "created", "path": str(working_dir), "branch": branch}
                if not args.dry_run:
                    save_manifest(manifest, manifest_path_value)
            brief = write_bound_brief(
                prepared[track]["rendered"],
                artifact_dir / f"{track}-implementation-brief.md",
                args.dry_run,
            )
            manifest["tracks"][track]["brief"] = str(brief)
            manifest["tracks"][track]["implementation"] = {"status": "starting", "selected_route": routes["implementer"]}
            if not args.dry_run:
                save_manifest(manifest, manifest_path_value)
            launch = dispatch_route(
                routes["implementer"], brief, working_dir, "implementer", args.timeout, metadata, False, args.dry_run
            )
        except (RunnerLaunchError, ValueError, OSError, UnicodeError) as error:
            fail_track_launch(manifest, manifest_path_value, track, str(error), args.dry_run)
        manifest["tracks"][track]["implementation"] = {"status": "running", **launch}
        manifest["tracks"][track]["status"] = "implementation_running"
        if not args.dry_run:
            save_manifest(manifest, manifest_path_value)
    if not args.dry_run:
        save_manifest(manifest, manifest_path_value)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def manifest_path(args: argparse.Namespace) -> Path:
    if args.manifest:
        return Path(args.manifest).expanduser().resolve()
    validate_path_component(args.session_id, "session id")
    validate_path_component(args.task_id, "task id")
    root, _ = resolve_working_root(args.working_dir)
    return root / ".ai-workflow" / "impl-review" / args.session_id / args.task_id / "launch-manifest.json"


def validate_manifest(manifest: Any, path: Path, args: argparse.Namespace) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        fail("manifest must be a JSON object")
    if manifest.get("skill") != "implement-and-review" or manifest.get("schema_version") != 1:
        fail("manifest is not owned by implement-and-review")
    session_id = manifest.get("session_id")
    task_id = manifest.get("task_id")
    if not isinstance(session_id, str) or not isinstance(task_id, str):
        fail("manifest is missing a valid session id or task id")
    validate_path_component(session_id, "manifest session id")
    validate_path_component(task_id, "manifest task id")
    if args.session_id and args.session_id != session_id:
        fail("manifest session id does not match the requested session id")
    if args.task_id and args.task_id != task_id:
        fail("manifest task id does not match the requested task id")
    working_root_value = manifest.get("working_root")
    if not isinstance(working_root_value, str) or not working_root_value:
        fail("manifest is missing its working root")
    working_root = Path(working_root_value).resolve()
    expected = working_root / ".ai-workflow" / "impl-review" / session_id / task_id / "launch-manifest.json"
    if path.resolve() != expected:
        fail("manifest path is not the launcher-owned artifact path")
    if manifest.get("artifact_dir") != str(expected.parent):
        fail("manifest artifact directory does not match its launcher-owned path")
    return manifest


def load_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], Path]:
    path = manifest_path(args)
    if not path.is_file():
        fail(f"manifest not found: {path}")
    try:
        return validate_manifest(json.loads(path.read_text(encoding="utf-8")), path, args), path
    except json.JSONDecodeError as error:
        fail(f"manifest is not valid JSON: {error}")


def save_manifest(manifest: dict[str, Any], path: Path) -> None:
    manifest["updated_at"] = utc_now()
    from run_state import atomic_write
    atomic_write(path, manifest)


def context_identity_error(context: Any, route: dict[str, Any], task_id: str, kind: str) -> str | None:
    if not isinstance(context, dict):
        return f"{kind} context is not an object"
    expected = {
        "role": route["role"],
        "task_id": task_id,
        "configured_model": route["model"],
        "configured_effort": route.get("effort"),
    }
    if kind == "native":
        native = validate_native_spec(route)
        if native is not None:
            expected.update({"host": native["host"], "transport": native["transport"]})
    else:
        expected["runner"] = route["runner"]
    for field, value in expected.items():
        if context.get(field) != value:
            return f"{kind} context {field} does not match the approved route"
    context_id = context.get("context_id")
    if not isinstance(context_id, str) or not context_id:
        return f"{kind} context has no persistent context id"
    return None


def stored_context(manifest: dict[str, Any], key: str, route: dict[str, Any], kind: str) -> dict[str, Any] | None:
    contexts = manifest.setdefault(key, {})
    if not isinstance(contexts, dict):
        raise ValueError(f"manifest {key} must be an object")
    context = contexts.get(route["id"])
    if context is None:
        return None
    mismatch = context_identity_error(context, route, manifest["task_id"], kind)
    if mismatch:
        raise ValueError(mismatch)
    return context


def persistent_effective_route(manifest: dict[str, Any], approved_route: dict[str, Any]) -> dict[str, Any]:
    """Keep an approved fallback route when it owns the role's stored context."""
    matches: list[dict[str, Any]] = []
    matched_contexts: set[str] = set()
    conflicts: dict[str, str] = {}
    for candidate in route_variants(approved_route):
        key = "native_contexts" if candidate["mode"] == "native" else "runner_contexts"
        contexts = manifest.get(key, {})
        if not isinstance(contexts, dict):
            raise ValueError(f"manifest {key} must be an object")
        context = contexts.get(candidate["id"])
        if context is None:
            continue
        context_key = f"{key}:{candidate['id']}"
        mismatch = context_identity_error(context, candidate, manifest["task_id"], "native" if candidate["mode"] == "native" else "runner")
        if mismatch is None:
            matches.append(candidate)
            matched_contexts.add(context_key)
        else:
            conflicts[context_key] = mismatch
    if len(matches) > 1 and len(matched_contexts) > 1:
        raise ValueError(f"route {approved_route['id']} has conflicting persistent contexts")
    if matches:
        unmatched_conflicts = [
            mismatch for context_key, mismatch in conflicts.items() if context_key not in matched_contexts
        ]
        if unmatched_conflicts:
            raise ValueError(f"route {approved_route['id']} has a conflicting persistent context")
        return matches[0]
    if conflicts:
        raise ValueError(next(iter(conflicts.values())))
    return approved_route


def resumable_context(manifest: dict[str, Any], route: dict[str, Any]) -> dict[str, Any] | None:
    if route["mode"] == "native":
        context = stored_context(manifest, "native_contexts", route, "native")
    else:
        if route["runner"] not in RUNNER_RESUME_FLAGS:
            return None
        context = stored_context(manifest, "runner_contexts", route, "runner")
    if context is None:
        return None
    if context.get("status") != "completed":
        raise ValueError(f"route {route['id']} has a {context.get('status')!r} context and cannot resume it")
    return context


def reject_context_owned_by_another_route(
    contexts: dict[str, Any],
    route: dict[str, Any],
    context_id: str,
    kind: str,
    host_or_runner: str,
) -> None:
    for other_route_id, other_context in contexts.items():
        if other_route_id == route["id"] or not isinstance(other_context, dict):
            continue
        owner = other_context.get("host") if kind == "native" else other_context.get("runner")
        if owner == host_or_runner and other_context.get("context_id") == context_id:
            raise ValueError(
                f"{kind} context id is already owned by route {other_route_id}; roles cannot share a persistent context"
            )


def native_execution_error(
    route: dict[str, Any],
    receipt: dict[str, Any],
    task_id: str,
    expected_dispatch: dict[str, Any] | None,
) -> str | None:
    execution = receipt.get("native_execution")
    if not isinstance(execution, dict):
        return "native receipt is missing native_execution"
    for field in ("host", "transport", "context_id", "role", "task_id", "configured_model", "configured_effort", "tool_policy", "completed_turn"):
        if field not in execution:
            return f"native receipt is missing native_execution.{field}"
    if not isinstance(execution["host"], str) or not execution["host"]:
        return "native receipt has an invalid native_execution.host"
    if execution["transport"] not in NATIVE_TRANSPORTS:
        return "native receipt has an invalid native_execution.transport"
    if not isinstance(execution["context_id"], str) or not execution["context_id"]:
        return "native receipt has no persistent native context id"
    if not isinstance(execution["completed_turn"], int) or execution["completed_turn"] < 1:
        return "native receipt has an invalid native_execution.completed_turn"
    if execution["role"] != route["role"] or execution["task_id"] != task_id:
        return "native receipt role or task does not match the approved route"
    if execution["configured_model"] != route["model"]:
        return "native receipt configured model does not match the approved route"
    if execution["configured_effort"] != route.get("effort"):
        return "native receipt configured effort does not match the approved route"
    native = validate_native_spec(route)
    if native is not None and (execution["host"] != native["host"] or execution["transport"] != native["transport"]):
        return "native receipt host or transport does not match the approved route"
    if expected_dispatch is not None:
        for field in ("call_id", "input_revision", "tool_policy", "parent_history"):
            expected = expected_dispatch.get(field)
            if expected is not None and execution.get(field) != expected:
                return f"native receipt {field} does not match the dispatched route call"
    return None


def native_receipt_path(manifest: dict[str, Any], route: dict[str, Any], phase: str, cycle: int | None, receipt: dict[str, Any]) -> Path:
    artifact_dir = Path(manifest["artifact_dir"]).resolve()
    key = hashlib.sha256(route["id"].encode("utf-8")).hexdigest()[:16]
    execution = receipt.get("native_execution")
    turn = execution.get("completed_turn", "unknown") if isinstance(execution, dict) else "unknown"
    context_id = execution.get("context_id", "unknown") if isinstance(execution, dict) else "unknown"
    call_id = execution.get("call_id", "unknown") if isinstance(execution, dict) else "unknown"
    context_key = hashlib.sha256(str(context_id).encode("utf-8")).hexdigest()[:12]
    call_key = hashlib.sha256(str(call_id).encode("utf-8")).hexdigest()[:12]
    candidate = artifact_dir / "native-receipts" / (
        f"{phase}-{cycle or 0}-{key}-context-{context_key}-call-{call_key}-turn-{turn}.json"
    )
    resolved = candidate.resolve()
    if artifact_dir not in resolved.parents:
        raise ValueError("native receipt path escapes the launcher artifact directory")
    return resolved


def write_native_receipt(destination: Path, receipt: dict[str, Any]) -> dict[str, str]:
    if destination.exists():
        if not destination.is_file():
            raise ValueError("native receipt artifact path is not a file")
        try:
            existing = json.loads(destination.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError(f"native receipt artifact cannot be verified: {error}") from error
        if canonical_digest(existing) != canonical_digest(receipt):
            raise ValueError("native receipt artifact already exists with different content")
        return {"path": str(destination), "sha256": file_digest(destination)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"path": str(destination), "sha256": file_digest(destination)}


def persist_native_receipt(
    manifest: dict[str, Any],
    route: dict[str, Any],
    phase: str,
    cycle: int | None,
    receipt: dict[str, Any],
    context_recovery_reason: str | None,
) -> dict[str, Any] | None:
    """Persist one host receipt and bind it to the route's own context only."""
    destination = native_receipt_path(manifest, route, phase, cycle, receipt)
    if receipt.get("success") is not True:
        return {"receipt": write_native_receipt(destination, receipt), "context": None}
    execution = receipt.get("native_execution")
    if not isinstance(execution, dict):
        return {"receipt": write_native_receipt(destination, receipt), "context": None}
    contexts = manifest.setdefault("native_contexts", {})
    if not isinstance(contexts, dict):
        raise ValueError("manifest native_contexts must be an object")
    current = contexts.get(route["id"])
    context_id = execution["context_id"]
    if current is not None:
        mismatch = context_identity_error(current, route, manifest["task_id"], "native")
        if mismatch:
            raise ValueError(mismatch)
        if current["context_id"] != context_id:
            if not context_recovery_reason:
                raise ValueError("native receipt changed the persistent context; use an explicit context recovery record")
            manifest.setdefault("native_context_breaks", []).append({
                "route_id": route["id"],
                "previous_context_id": current["context_id"],
                "replacement_context_id": context_id,
                "reason": context_recovery_reason,
                "recorded_at": utc_now(),
            })
            current = None
        else:
            pending_call_id = current.get("pending_call_id")
            if pending_call_id is not None and execution.get("call_id") != pending_call_id:
                raise ValueError("native receipt call id does not match the pending persistent context call")
            if execution["completed_turn"] <= current.get("last_completed_turn", 0):
                raise ValueError("native receipt completed_turn does not advance its persistent context")
    reject_context_owned_by_another_route(contexts, route, context_id, "native", execution["host"])
    native = validate_native_spec(route)
    reference = write_native_receipt(destination, receipt)
    context = {
        "host": execution["host"],
        "transport": execution["transport"],
        "context_id": context_id,
        "role": route["role"],
        "task_id": manifest["task_id"],
        "configured_model": route["model"],
        "configured_effort": route.get("effort"),
        "tool_policy": execution["tool_policy"],
        "receipt_ref": reference["path"],
        "receipt_sha256": reference["sha256"],
        "last_input_revision": execution.get("input_revision"),
        "last_completed_turn": execution["completed_turn"],
        "pending_call_id": None,
        "status": "completed" if receipt.get("success") is True else "failed",
    }
    if native is None:
        context["legacy_transport_unverified"] = True
    if current is not None:
        context["started_at"] = current.get("started_at", utc_now())
    else:
        context["started_at"] = utc_now()
    contexts[route["id"]] = context
    return {"receipt": reference, "context": context}


def persist_runner_context(manifest: dict[str, Any], entry: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    """Store a route-specific runner session without using a global latest session."""
    if snapshot.get("success") is not True:
        return False
    route = entry.get("effective_route") or entry.get("selected_route")
    session_id = snapshot.get("runner_session_id")
    if not isinstance(route, dict) or not isinstance(session_id, str) or not session_id:
        return False
    try:
        validate_route(route)
    except ValueError:
        return False
    contexts = manifest.setdefault("runner_contexts", {})
    if not isinstance(contexts, dict):
        raise ValueError("manifest runner_contexts must be an object")
    current = contexts.get(route["id"])
    receipt_ref = entry.get("result_file") or entry.get("job_id")
    if current is not None:
        mismatch = context_identity_error(current, route, manifest["task_id"], "runner")
        if mismatch:
            raise ValueError(mismatch)
        processed = current.get("processed_receipt_refs", [])
        if not isinstance(processed, list):
            raise ValueError("runner context processed_receipt_refs must be a list")
        if receipt_ref in processed:
            return False
        if current.get("status") == "broken":
            return False
        if entry.get("resume_context_id") != current["context_id"]:
            current["status"] = "broken"
            current["break_reason"] = "runner continuation did not use the recorded role session"
            current["processed_receipt_refs"] = [*processed, receipt_ref]
            return True
        if session_id != current["context_id"]:
            current["status"] = "broken"
            current["break_reason"] = "runner returned a different session after exact resume"
            current["processed_receipt_refs"] = [*processed, receipt_ref]
            return True
    reject_context_owned_by_another_route(contexts, route, session_id, "runner", route["runner"])
    contexts[route["id"]] = {
        "runner": route["runner"],
        "context_id": session_id,
        "role": route["role"],
        "task_id": manifest["task_id"],
        "configured_model": route["model"],
        "configured_effort": route.get("effort"),
        "tool_policy": entry.get("tool_policy"),
        "receipt_ref": receipt_ref,
        "processed_receipt_refs": ([*current.get("processed_receipt_refs", []), receipt_ref] if isinstance(current, dict) else [receipt_ref]),
        "last_input_revision": entry.get("input_revision"),
        "last_completed_turn": (current.get("last_completed_turn", 0) + 1) if isinstance(current, dict) else 1,
        "status": "completed",
    }
    return True


def persist_terminal_runner_contexts(manifest: dict[str, Any], snapshot: dict[str, Any]) -> bool:
    changed = False
    for track_name, track_snapshot in snapshot.get("tracks", {}).items():
        track = manifest.get("tracks", {}).get(track_name)
        if isinstance(track, dict) and isinstance(track_snapshot, dict):
            changed = persist_runner_context(manifest, track.get("implementation", {}), track_snapshot) or changed
    for review in manifest.get("reviews", []):
        if not isinstance(review, dict):
            continue
        key = f"{review.get('track', 'unknown')}:{review.get('cycle', '0')}"
        review_snapshot = snapshot.get("reviews", {}).get(key)
        if isinstance(review_snapshot, dict):
            changed = persist_runner_context(manifest, review.get("launch", {}), review_snapshot) or changed
    return changed


def jobs_query(subcommand: str, job_id: str, working_dir: str) -> dict[str, Any]:
    observation = runner_jobs.observe_many([(working_dir, job_id)])[(working_dir, job_id)]
    return observation["result"] if subcommand == "result" else {"status": observation["status"]}


def receipt_error(route: dict[str, Any], result: dict[str, Any]) -> str | None:
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
    return None


def job_snapshot(entry: dict[str, Any], working_dir: str, observation=None) -> tuple[dict[str, Any], bool]:
    if entry.get("mode") == "native":
        receipt = entry.get("completion_receipt")
        if not isinstance(receipt, dict):
            return {"mode": "native", "status": "orchestrator-managed", "route": entry.get("selected_route")}, False
        route = entry.get("effective_route") or entry.get("selected_route")
        snapshot: dict[str, Any] = {"mode": "native", "status": "completed", "success": receipt.get("success") is True}
        if snapshot["success"] and isinstance(route, dict):
            mismatch = receipt_error(route, receipt)
            if mismatch:
                snapshot["success"] = False
                snapshot["route_error"] = mismatch
        if not snapshot["success"]:
            snapshot["status"] = "failed"
            snapshot["error"] = receipt.get("error") or snapshot.get("route_error") or "native route did not report success"
        snapshot["model_receipt"] = receipt.get("model_receipt")
        return snapshot, True
    job_id = entry.get("job_id")
    if not job_id:
        if entry.get("status") in {"failed", "ceiling_hit"}:
            return {
                "mode": entry.get("mode"),
                "status": entry.get("status"),
                "success": False,
                "error": entry.get("error") or "route did not start",
            }, True
        return {"mode": entry.get("mode"), "status": "not-started"}, False
    status = observation["status"] if observation is not None else jobs_query("status", job_id, working_dir).get("status", "unknown")
    snapshot: dict[str, Any] = {"mode": "runner", "job_id": job_id, "status": status}
    if status in TERMINAL_JOB_STATUSES:
        result = observation["result"] if observation is not None else jobs_query("result", job_id, working_dir)
        snapshot["success"] = status == "completed" and result.get("success") is True
        snapshot["runner_session_id"] = result.get("session_id")
        snapshot["model_receipt"] = result.get("model_receipt")
        snapshot["result_file"] = entry.get("result_file")
        if status != "completed":
            snapshot["error"] = result.get("error") or f"runner job ended with status {status}"
        route = entry.get("effective_route")
        if snapshot["success"] and isinstance(route, dict):
            mismatch = receipt_error(route, result)
            if mismatch:
                snapshot["success"] = False
                snapshot["route_error"] = mismatch
        elif status == "completed" and result.get("success") is not True:
            snapshot["error"] = result.get("error") or "completed runner job has no successful result"
        return snapshot, True
    return snapshot, False


def poll_once(manifest: dict[str, Any], cache=None) -> dict[str, Any]:
    result: dict[str, Any] = {"session_id": manifest.get("session_id"), "task_id": manifest.get("task_id"), "tracks": {}, "reviews": {}}
    terminal = True
    entries = [(info.get("implementation", {}), info.get("working_dir", "."))
               for info in manifest.get("tracks", {}).values()]
    entries += [(review.get("launch", {}), review.get("working_dir", "."))
                for review in manifest.get("reviews", [])]
    observations = runner_jobs.observe_many(
        [(directory, entry["job_id"]) for entry, directory in entries
         if entry.get("mode") != "native" and entry.get("job_id")], cache)
    for track, info in manifest.get("tracks", {}).items():
        entry, directory = info.get("implementation", {}), info.get("working_dir", ".")
        snapshot, done = job_snapshot(entry, directory, observations.get((directory, entry.get("job_id"))))
        result["tracks"][track] = snapshot
        terminal = terminal and done
    for review in manifest.get("reviews", []):
        key = f"{review.get('track', 'unknown')}:{review.get('cycle', '0')}"
        entry, directory = review.get("launch", {}), review.get("working_dir", ".")
        snapshot, done = job_snapshot(entry, directory, observations.get((directory, entry.get("job_id"))))
        result["reviews"][key] = snapshot
        terminal = terminal and done
    result["all_terminal"] = terminal
    return result


def cmd_poll(args: argparse.Namespace) -> int:
    deadline = time.monotonic() + args.wait_timeout
    delay = max(1, min(args.interval, 60))
    previous = None
    cache = {}
    while True:
        manifest, path = load_manifest(args)
        snapshot = poll_once(manifest, cache)
        try:
            context_changed = persist_terminal_runner_contexts(manifest, snapshot)
        except ValueError as error:
            fail(str(error))
        if context_changed:
            save_manifest(manifest, path)
        if not args.wait or snapshot["all_terminal"] or time.monotonic() >= deadline:
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))
            failures = [entry for group in (snapshot["tracks"], snapshot["reviews"]) for entry in group.values() if entry.get("success") is False]
            return 1 if failures else 0
        marker = canonical_digest(snapshot)
        delay = min(delay * 2, 60) if marker == previous else max(1, min(args.interval, 60))
        previous = marker
        time.sleep(min(delay, max(0, deadline - time.monotonic())))


def track_working_dir(manifest: dict[str, Any], track_name: str, track: dict[str, Any]) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", track_name):
        raise ValueError(f"invalid track name: {track_name!r}")
    working_root = Path(manifest["working_root"]).resolve()
    working_dir_value = track.get("working_dir")
    if not isinstance(working_dir_value, str) or not working_dir_value:
        raise ValueError(f"track {track_name!r} has no working directory")
    working_dir = Path(working_dir_value).resolve()
    isolation = manifest.get("isolation")
    if isolation == "working-tree":
        if track.get("branch") is not None or working_dir != working_root:
            raise ValueError(f"track {track_name!r} is not a launcher-owned working-tree track")
    elif isolation == "worktree":
        worktrees_dir_value = manifest.get("worktrees_dir")
        expected_branch = f"impl/{manifest['task_id']}-{track_name}-{manifest['session_id']}"
        if not isinstance(worktrees_dir_value, str) or not worktrees_dir_value:
            raise ValueError("worktree manifest is missing its worktree root")
        expected_dir = Path(worktrees_dir_value).resolve() / track_name
        if working_dir != expected_dir or track.get("branch") != expected_branch:
            raise ValueError(f"track {track_name!r} is not a launcher-owned worktree track")
    else:
        raise ValueError("manifest has an invalid isolation mode")
    return working_dir


def implementation_ready(track: dict[str, Any], working_dir: Path) -> None:
    snapshot, terminal = job_snapshot(track.get("implementation", {}), str(working_dir))
    if not terminal:
        fail("implementation is not complete; review cannot start yet")
    if snapshot.get("success") is not True:
        reason = snapshot.get("route_error") or snapshot.get("error") or "implementation did not succeed"
        fail(f"implementation is not eligible for review: {reason}")


def recovery_limits(manifest, track):
    defaults = {"review_cycles": MAX_REVIEW_CYCLES, "evidence_recoveries": MAX_EVIDENCE_RECOVERIES}
    if "routing_plan" not in manifest:
        return defaults
    routing = load_routing_plan(manifest["routing_plan"]["path"], manifest["task_id"], {track}, True, Path(manifest["working_root"]))
    if routing["approval"] != manifest["routing_plan"]["approval"]:
        raise ValueError("recovery plan approval changed")
    return routing["routes"][track]["reviewer"].get("recovery", defaults)


def next_review_cycle(manifest: dict[str, Any], track_name: str, requested_cycle: int | None, dry_run: bool, path: Path) -> int:
    attempts = manifest.setdefault("attempts", {}).setdefault("review_cycles", {})
    previous = attempts.get(track_name, 0)
    if not isinstance(previous, int) or previous < 0:
        fail(f"manifest has an invalid review cycle count for {track_name}")
    ceiling = recovery_limits(manifest, track_name)["review_cycles"]
    if previous >= ceiling:
        manifest["status"] = "ceiling_hit"
        manifest["phase"] = f"{track_name}_review"
        if not dry_run:
            save_manifest(manifest, path)
        fail(f"review/fix cycle ceiling reached for {track_name}: {ceiling}")
    cycle = previous + 1
    if requested_cycle is not None and requested_cycle != cycle:
        fail(f"next review cycle for {track_name} is {cycle}, not {requested_cycle}")
    if not dry_run:
        attempts[track_name] = cycle
        save_manifest(manifest, path)
    return cycle


def active_review_record(manifest: dict[str, Any], track_name: str, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Return an unfinished same-track review so its role context stays exclusive."""
    reviews = manifest.get("reviews", [])
    if not isinstance(reviews, list):
        raise ValueError("manifest reviews must be a list")
    snapshots = snapshot.get("reviews", {})
    if not isinstance(snapshots, dict):
        raise ValueError("review snapshot must contain an object")
    for review in reviews:
        if not isinstance(review, dict) or review.get("track") != track_name:
            continue
        launch = review.get("launch")
        launch_status = launch.get("status") if isinstance(launch, dict) else None
        if review.get("status") not in ACTIVE_REVIEW_STATUSES and launch_status not in ACTIVE_REVIEW_STATUSES:
            continue
        key = f"{track_name}:{review.get('cycle', '0')}"
        observed = snapshots.get(key)
        if isinstance(observed, dict) and observed.get("status") in TERMINAL_JOB_STATUSES:
            continue
        return review
    return None


def cmd_review(args: argparse.Namespace) -> int:
    manifest, path = load_manifest(args)
    track = manifest.get("tracks", {}).get(args.track)
    if not isinstance(track, dict):
        fail(f"track not found in manifest: {args.track}")
    root = Path(manifest["working_root"]).resolve()
    routing_plan = manifest.get("routing_plan", {}).get("path")
    task_id = manifest.get("task_id")
    if not isinstance(routing_plan, str) or not isinstance(task_id, str):
        fail("manifest has no approved routing plan reference")
    try:
        routing = load_routing_plan(routing_plan, task_id, {args.track}, require_approved=True, root=root)
    except ValueError as error:
        fail(f"routing plan is no longer valid: {error}")
    approved_route = routing["routes"][args.track]["reviewer"]
    try:
        saved_route = track.get("reviewer_route")
        validate_route(saved_route)
    except ValueError as error:
        fail(f"invalid reviewer route in manifest: {error}")
    if canonical_digest(saved_route) != canonical_digest(approved_route):
        fail("manifest reviewer route no longer matches the approved routing plan")
    if manifest.get("routing_plan", {}).get("approval") != routing["approval"]:
        fail("manifest approval record no longer matches the approved routing plan")
    try:
        working_dir = track_working_dir(manifest, args.track, track)
    except ValueError as error:
        fail(str(error))
    implementation_ready(track, working_dir)
    try:
        prior_snapshot = poll_once(manifest)
        if persist_terminal_runner_contexts(manifest, prior_snapshot) and not args.dry_run:
            save_manifest(manifest, path)
        route = persistent_effective_route(manifest, approved_route)
        resume_context = resumable_context(manifest, route)
    except ValueError as error:
        fail(str(error))
    active_review = active_review_record(manifest, args.track, prior_snapshot)
    if active_review is not None:
        cycle = active_review.get("cycle", "unknown")
        fail(f"review cycle {cycle} for {args.track} is still active")
    brief_candidate = Path(args.review_brief).expanduser()
    brief = (brief_candidate if brief_candidate.is_absolute() else root / brief_candidate).resolve()
    if not brief.is_file():
        fail("review brief is missing or not a file")
    try:
        rendered, binding = render_bound_brief(
            routing["scope_inputs"][route["input_path"]], brief, REVIEW_BOUNDARY, "Derived review notes"
        )
    except (ValueError, OSError, UnicodeError) as error:
        fail(f"could not prepare a bound review brief: {error}")
    try:
        prior_records = [r for r in manifest.get("reviews", []) if r.get("track") == args.track and r.get("review_evidence")]
        previous = max(prior_records, key=lambda r: r["cycle"])["review_evidence"] if prior_records else None
        source_binding = review_source_binding(
            getattr(args, "review_snapshot", None), working_dir,
            routing["scope_inputs"][route["input_path"]], manifest.get("base"),
            previous,
        )
    except (ValueError, OSError, KeyError, TypeError) as error:
        fail(f"review evidence cannot be bound: {error}")
    try:
        evidence = evidence_module()
        contract = evidence.response_contract(source_binding["path"])
        packet_path = getattr(args, "evidence_packet", None)
        packet_link = evidence.evidence_link(packet_path) if packet_path else None
        if packet_link:
            evidence.load_packet(packet_link, evidence.current_snapshot(source_binding["path"]), source_binding["path"])
    except (ValueError, OSError, KeyError, TypeError) as error:
        fail(f"review evidence preflight failed: {error}")
    rendered += (
        "\nStructured review evidence\n"
        f"Snapshot: {source_binding['path']}\n"
        f"Snapshot file SHA-256: {source_binding['sha256']}\n"
        "Read shared/references/review-evidence.md for the result contract. "
        "Return the result JSON as your entire final response. Cover every snapshot "
        "changed path and use only captured check results. Do not write evidence files; "
        "the coordinator records your response.\n"
    )
    rendered += "Required response coverage: " + json.dumps(contract, sort_keys=True) + "\n"
    if packet_link:
        rendered += "Captured evidence packet: " + json.dumps(packet_link, sort_keys=True) + "\n"
        rendered += "After inspecting the captures, use this evidence_packet reference instead of checks and observations.\n"
    try:
        binding["input_measurement"] = measure_rendered(rendered, route.get("context_budget"))
    except ValueError as error:
        fail(str(error))
    cycle = next_review_cycle(manifest, args.track, args.cycle, args.dry_run, path)
    bound_brief = Path(manifest["artifact_dir"]) / f"{args.track}-review-{cycle}-brief.md"
    input_revision = text_digest(rendered)
    metadata = {
        "input_measurement": binding["input_measurement"],
        "session": manifest.get("session_id"),
        "task_id": manifest.get("task_id"),
        "track": args.track,
        "cycle": cycle,
        "phase": "review",
        "routing_plan": manifest.get("routing_plan", {}).get("path"),
        "input_revision": input_revision,
        "call_id": native_call_id(route, "review", cycle, 1),
    }
    record = {
        "track": args.track,
        "cycle": cycle,
        "status": "starting",
        "working_dir": str(working_dir),
        "brief": str(bound_brief),
        "brief_binding": binding,
        "input_revision": input_revision,
        "reviewer_route": approved_route,
        "source_snapshot": source_binding,
        "launch": {"status": "pending", "selected_route": approved_route},
    }
    context_before_launch: dict[str, Any] | None = None
    if resume_context is not None and not args.dry_run:
        context_before_launch = dict(resume_context)
        resume_context["status"] = "pending"
        resume_context["pending_call_id"] = metadata["call_id"]
        resume_context["last_input_revision"] = input_revision
        save_manifest(manifest, path)
    if not args.dry_run:
        manifest.setdefault("reviews", []).append(record)
        save_manifest(manifest, path)
    try:
        written = write_bound_brief(rendered, bound_brief, args.dry_run)
        record["brief"] = str(written)
        record["launch"] = {"status": "starting", "selected_route": approved_route}
        if not args.dry_run:
            save_manifest(manifest, path)
        launch = dispatch_route(
            route,
            written,
            working_dir,
            "codereviewer",
            args.timeout,
            metadata,
            True,
            args.dry_run,
            resume_context=resume_context,
        )
    except (RunnerLaunchError, ValueError, OSError, UnicodeError) as error:
        if context_before_launch is not None and resume_context is not None:
            resume_context.clear()
            resume_context.update(context_before_launch)
        record["status"] = "failed"
        record["launch"] = {"status": "failed", "selected_route": route, "error": str(error)}
        manifest["status"] = "failed"
        manifest["phase"] = f"{args.track}_review"
        if not args.dry_run:
            save_manifest(manifest, path)
        fail(str(error))
    if canonical_digest(route) != canonical_digest(approved_route):
        launch["selected_route"] = approved_route
        launch["effective_route"] = route
        launch["persistent_effective_route"] = True
    record["status"] = "running"
    record["launch"] = {"status": "running", **launch}
    if launch["mode"] == "native" and resume_context is not None:
        resume_context["status"] = "pending"
        resume_context["pending_call_id"] = launch["native_dispatch"].get("call_id")
        resume_context["last_input_revision"] = input_revision
    elif launch["mode"] == "runner" and resume_context is not None:
        resume_context["pending_job_id"] = launch.get("job_id")
    if not args.dry_run:
        save_manifest(manifest, path)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def selected_review(manifest, track, cycle=None):
    records = [r for r in manifest.get("reviews", []) if r.get("track") == track]
    if cycle is not None:
        records = [r for r in records if r.get("cycle") == cycle]
    if not records:
        raise ValueError("no matching review record")
    return max(records, key=lambda r: r["cycle"])


def bound_snapshot(record):
    binding = record.get("source_snapshot")
    if not isinstance(binding, dict) or file_digest(Path(binding["path"])) != binding["sha256"]:
        raise ValueError("source snapshot is missing or its checksum changed")
    return binding["path"]


def cmd_record_review(args):
    manifest, path = load_manifest(args)
    try:
        record = selected_review(manifest, args.track, args.cycle)
        snapshot_path = bound_snapshot(record)
        entry = record["launch"]
        route = entry.get("effective_route") or entry["selected_route"]
        routing = load_routing_plan(manifest["routing_plan"]["path"], manifest["task_id"], {args.track}, True, Path(manifest["working_root"]))
        approved = routing["routes"][args.track]["reviewer"]
        if canonical_digest(record["reviewer_route"]) != canonical_digest(approved) or not any(canonical_digest(route) == canonical_digest(x) for x in route_variants(approved)):
            raise ValueError("review route no longer matches the approved plan")
        review_source_binding(snapshot_path, Path(record["working_dir"]), routing["scope_inputs"][approved["input_path"]], manifest["base"])
        snapshot, terminal = job_snapshot(entry, record["working_dir"])
        if not terminal or snapshot.get("success") is not True:
            raise ValueError("review execution has no successful terminal result")
        execution = entry["completion_receipt"] if entry["mode"] == "native" else jobs_query("result", entry["job_id"], record["working_dir"])
        mismatch = receipt_error(route, execution)
        if mismatch:
            raise ValueError(mismatch)
        if entry["mode"] == "native":
            mismatch = native_execution_error(route, execution, manifest["task_id"], entry.get("native_dispatch"))
            if mismatch:
                raise ValueError(mismatch)
        evidence = evidence_module()
        result_path = evidence.record_review(snapshot_path, json.loads(execution.get("agent_message", "")), execution)
        record["review_evidence"] = {"path": str(result_path), "sha256": file_digest(result_path)}
        save_manifest(manifest, path)
        result = evidence.assess(snapshot_path, manifest["base"])
        print(json.dumps(result))
        return 0 if result["status"] == "ready" else 1
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


def cmd_verify_review(args):
    manifest, _ = load_manifest(args)
    try:
        record = selected_review(manifest, args.track)
        snapshot_path = bound_snapshot(record)
        routing = load_routing_plan(manifest["routing_plan"]["path"], manifest["task_id"], {args.track}, True, Path(manifest["working_root"]))
        approved = routing["routes"][args.track]["reviewer"]
        if canonical_digest(record["reviewer_route"]) != canonical_digest(approved):
            raise ValueError("review route no longer matches the approved plan")
        review_source_binding(snapshot_path, Path(record["working_dir"]), routing["scope_inputs"][approved["input_path"]], args.base)
        link = record.get("review_evidence")
        if not isinstance(link, dict) or Path(link["path"]).resolve() != Path(snapshot_path).parent / "review.json" or file_digest(Path(link["path"])) != link["sha256"]:
            raise ValueError("recorded review evidence is missing or changed")
        result = evidence_module().assess(snapshot_path, args.base)
        print(json.dumps(result))
        return 0 if result["status"] == "ready" else 1
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}))
        return 2


def cmd_record_native(args: argparse.Namespace) -> int:
    manifest, path = load_manifest(args)
    track = manifest.get("tracks", {}).get(args.track)
    if not isinstance(track, dict):
        fail(f"track not found in manifest: {args.track}")
    root = Path(manifest["working_root"]).resolve()
    routing_plan = manifest.get("routing_plan", {}).get("path")
    if not isinstance(routing_plan, str):
        fail("manifest has no approved routing plan reference")
    try:
        routing = load_routing_plan(routing_plan, manifest["task_id"], {args.track}, require_approved=True, root=root)
    except ValueError as error:
        fail(f"routing plan is no longer valid: {error}")
    if args.phase == "implementation":
        if args.cycle is not None:
            fail("--cycle is only valid for a native review receipt")
        entry = track.get("implementation")
        approved_route = routing["routes"][args.track]["implementer"]
    else:
        if args.cycle is None:
            fail("--cycle is required for a native review receipt")
        candidates = [
            item for item in manifest.get("reviews", [])
            if item.get("track") == args.track and item.get("cycle") == args.cycle
        ]
        if len(candidates) != 1:
            fail("native review record was not found")
        entry = candidates[0].get("launch")
        approved_route = routing["routes"][args.track]["reviewer"]
    if not isinstance(entry, dict) or entry.get("mode") != "native":
        fail("selected route is not a pending native route")
    if entry.get("status") not in {"awaiting_native_dispatch", "orchestrator-managed", "running"}:
        fail("native route is not awaiting a receipt")
    selected_route = entry.get("selected_route")
    effective_route = entry.get("effective_route") or selected_route
    try:
        validate_route(effective_route)
    except ValueError as error:
        fail(f"native route record is invalid: {error}")
    if not any(canonical_digest(effective_route) == canonical_digest(candidate) for candidate in route_variants(approved_route)):
        fail("native route record no longer matches the approved routing plan or an approved fallback")
    receipt_candidate = Path(args.receipt).expanduser()
    receipt_path = (receipt_candidate if receipt_candidate.is_absolute() else root / receipt_candidate).resolve()
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"native receipt is not readable JSON: {error}")
    if not isinstance(receipt, dict):
        fail("native receipt must be a JSON object")
    dispatch = entry.get("native_dispatch") if isinstance(entry.get("native_dispatch"), dict) else None
    recovery_reason = args.context_recovery_reason or (dispatch.get("context_recovery_reason") if dispatch else None)
    if receipt.get("success") is True:
        mismatch = receipt_error(effective_route, receipt)
        if mismatch:
            fail(f"native receipt does not match the approved route: {mismatch}")
        mismatch = native_execution_error(effective_route, receipt, manifest["task_id"], dispatch)
        if mismatch:
            fail(f"native receipt does not match the dispatched native call: {mismatch}")
    try:
        persisted = persist_native_receipt(
            manifest,
            effective_route,
            args.phase,
            args.cycle,
            receipt,
            recovery_reason,
        )
    except (OSError, UnicodeError, ValueError) as error:
        fail(f"could not persist the native receipt: {error}")
    entry["completion_receipt"] = receipt
    entry["receipt_artifact"] = persisted["receipt"] if persisted else None
    entry.setdefault("receipt_history", []).append(entry["receipt_artifact"])
    if dispatch is not None:
        dispatch["status"] = "completed" if receipt.get("success") is True else "failed"
    entry["status"] = "completed" if receipt.get("success") is True else "failed"
    save_manifest(manifest, path)
    print(json.dumps({
        "track": args.track,
        "phase": args.phase,
        "status": entry["status"],
        "model_receipt": receipt.get("model_receipt"),
        "receipt_artifact": entry["receipt_artifact"],
    }, indent=2, ensure_ascii=False))
    return 0 if receipt.get("success") is True else 1


def cmd_resume_native(args: argparse.Namespace) -> int:
    """Prepare the next implementer turn in its recorded native context."""
    manifest, path = load_manifest(args)
    track = manifest.get("tracks", {}).get(args.track)
    if not isinstance(track, dict):
        fail(f"track not found in manifest: {args.track}")
    root = Path(manifest["working_root"]).resolve()
    routing_plan = manifest.get("routing_plan", {}).get("path")
    task_id = manifest.get("task_id")
    if not isinstance(routing_plan, str) or not isinstance(task_id, str):
        fail("manifest has no approved routing plan reference")
    try:
        routing = load_routing_plan(routing_plan, task_id, {args.track}, require_approved=True, root=root)
    except ValueError as error:
        fail(f"routing plan is no longer valid: {error}")
    entry = track.get("implementation")
    approved_route = routing["routes"][args.track]["implementer"]
    if not isinstance(entry, dict) or entry.get("mode") != "native":
        fail("implementation route is not a completed native route")
    effective_route = entry.get("effective_route") or entry.get("selected_route")
    try:
        validate_route(effective_route)
    except ValueError as error:
        fail(f"native route record is invalid: {error}")
    if effective_route["mode"] != "native" or not any(
        canonical_digest(effective_route) == canonical_digest(candidate) for candidate in route_variants(approved_route)
    ):
        fail("native route record no longer matches the approved implementation route or fallback")
    if entry.get("status") != "completed" or not isinstance(entry.get("completion_receipt"), dict):
        fail("implementation has no completed native receipt to resume")
    try:
        working_dir = track_working_dir(manifest, args.track, track)
        context = stored_context(manifest, "native_contexts", effective_route, "native")
    except ValueError as error:
        fail(str(error))
    recovery_reason = args.context_recovery_reason
    if context is None and not recovery_reason:
        fail("implementation has no persistent native context; provide a recorded context recovery reason")
    if context is not None and context.get("status") != "completed" and not recovery_reason:
        fail("implementation native context is not complete; provide a recovery reason only after confirming it is lost")
    source_candidate = Path(args.follow_up).expanduser()
    source = (source_candidate if source_candidate.is_absolute() else root / source_candidate).resolve()
    if not source.is_file():
        fail("implementation follow-up is missing or not a file")
    try:
        rendered, binding = render_bound_brief(
            routing["scope_inputs"][effective_route["input_path"]],
            source,
            WRITE_BOUNDARY,
            "Derived implementation follow-up",
        )
        binding["input_measurement"] = measure_rendered(rendered, effective_route.get("context_budget"))
    except (ValueError, OSError, UnicodeError) as error:
        fail(f"could not prepare a bound implementation follow-up: {error}")
    previous_attempts = entry.get("resume_attempts", 0)
    if not isinstance(previous_attempts, int) or previous_attempts < 0:
        fail("implementation record has an invalid native resume count")
    if previous_attempts >= MAX_REVIEW_CYCLES + MAX_EVIDENCE_RECOVERIES:
        manifest["status"] = "ceiling_hit"
        manifest["phase"] = f"{args.track}_implementation_followup"
        save_manifest(manifest, path)
        fail(
            "native implementation follow-up ceiling reached for "
            f"{args.track}: {MAX_REVIEW_CYCLES + MAX_EVIDENCE_RECOVERIES}"
        )
    attempt = previous_attempts + 1
    bound_brief = Path(manifest["artifact_dir"]) / f"{args.track}-implementation-resume-{attempt}-brief.md"
    input_revision = text_digest(rendered)
    metadata = {
        "input_measurement": binding["input_measurement"],
        "session": manifest["session_id"],
        "task_id": task_id,
        "track": args.track,
        "phase": "implementation_followup",
        "routing_plan": routing_plan,
        "input_revision": input_revision,
        "call_id": native_call_id(effective_route, "implementation", 0, attempt + 1),
        "context_recovery": bool(recovery_reason),
        "context_recovery_reason": recovery_reason,
    }
    try:
        written = write_bound_brief(rendered, bound_brief, False)
        launch = dispatch_route(
            effective_route,
            written,
            working_dir,
            "implementer",
            args.timeout,
            metadata,
            False,
            False,
            resume_context=None if recovery_reason else context,
        )
    except (RunnerLaunchError, ValueError, OSError, UnicodeError) as error:
        fail(str(error))
    previous_dispatch = entry.get("native_dispatch")
    if isinstance(previous_dispatch, dict):
        entry.setdefault("native_dispatch_history", []).append(previous_dispatch)
    entry.setdefault("completion_receipt_history", []).append({
        "receipt_artifact": entry.get("receipt_artifact"),
        "status": "completed",
    })
    entry["brief"] = str(written)
    entry["brief_binding"] = binding
    entry["input_revision"] = input_revision
    entry["resume_attempts"] = attempt
    entry["native_dispatch"] = launch["native_dispatch"]
    entry["completion_receipt"] = None
    entry["status"] = launch["status"]
    entry["pending"] = launch["pending"]
    if context is not None:
        if recovery_reason:
            context["status"] = "lost"
            context["pending_call_id"] = None
        else:
            context["status"] = "pending"
            context["pending_call_id"] = launch["native_dispatch"].get("call_id")
            context["last_input_revision"] = input_revision
    if recovery_reason:
        manifest.setdefault("steps", []).append({
            "step": f"{args.track}_native_context_recovery",
            "result": "requested",
            "route_id": effective_route["id"],
            "reason": recovery_reason,
        })
    save_manifest(manifest, path)
    print(json.dumps({
        "track": args.track,
        "status": entry["status"],
        "native_dispatch": entry["native_dispatch"],
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_evidence_recovery(args: argparse.Namespace) -> int:
    manifest, path = load_manifest(args)
    track = manifest.get("tracks", {}).get(args.track)
    if not isinstance(track, dict):
        fail(f"track not found in manifest: {args.track}")
    attempts = manifest.setdefault("attempts", {}).setdefault("evidence_recoveries", {})
    previous = attempts.get(args.track, 0)
    if not isinstance(previous, int) or previous < 0:
        fail(f"manifest has an invalid evidence recovery count for {args.track}")
    ceiling = recovery_limits(manifest, args.track)["evidence_recoveries"]
    if previous >= ceiling:
        manifest["status"] = "ceiling_hit"
        manifest["phase"] = f"{args.track}_evidence_recovery"
        save_manifest(manifest, path)
        fail(f"evidence recovery ceiling reached for {args.track}: {ceiling}")
    attempt = previous + 1
    attempts[args.track] = attempt
    record = {
        "step": f"{args.track}_evidence_recovery",
        "result": "reserved",
        "attempt": attempt,
        "reason": args.reason,
    }
    manifest.setdefault("steps", []).append(record)
    manifest["phase"] = f"{args.track}_evidence_recovery"
    save_manifest(manifest, path)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def cmd_plan_digests(args: argparse.Namespace) -> int:
    """Calculate approval digests without recording approval or starting work."""
    root, _ = resolve_working_root(args.working_dir)
    candidate = Path(args.routing_plan).expanduser()
    plan_path = (candidate if candidate.is_absolute() else root / candidate).resolve()
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"routing plan is not readable JSON: {error}")
    if not isinstance(plan, dict) or not isinstance(plan.get("scope"), dict):
        fail("routing plan must contain scope.inputs")
    inputs = plan["scope"].get("inputs")
    if not isinstance(inputs, list) or not inputs:
        fail("routing plan must contain one or more scope inputs")
    actual_inputs: list[dict[str, str]] = []
    paths: set[str] = set()
    try:
        for item in inputs:
            if not isinstance(item, dict):
                raise ValueError("each scope input must be an object")
            input_path = require_string(item.get("path"), "scope.inputs.path")
            if input_path in paths:
                raise ValueError(f"duplicate scope input path: {input_path}")
            resolved = scope_path(input_path, root)
            if not resolved.is_file():
                raise ValueError(f"scope input is missing or not a file: {input_path}")
            paths.add(input_path)
            actual_inputs.append({"path": input_path, "content_sha256": content_digest(resolved)})
        routes = plan.get("routes")
        if not isinstance(routes, list) or not routes:
            raise ValueError("routing plan must contain one or more routes")
        ids: set[str] = set()
        for route in routes:
            validated = validate_route(route)
            if validated["id"] in ids:
                raise ValueError(f"duplicate route id: {validated['id']}")
            if validated["input_path"] not in paths:
                raise ValueError(f"route input_path is not in scope.inputs: {validated['input_path']}")
            ids.add(validated["id"])
    except (OSError, UnicodeError, ValueError) as error:
        fail(str(error))
    print(json.dumps({
        "scope": {"inputs": normalized_scope_inputs(actual_inputs)},
        "approval_digests": {
            "scope_digest": canonical_digest(normalized_scope_inputs(actual_inputs)),
            "routes_digest": canonical_digest(normalized_routes(routes)),
        },
        "dispatch": "not-approved",
    }, indent=2, ensure_ascii=False))
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    manifest, _ = load_manifest(args)
    repo_root_value = manifest.get("repo_root")
    if not isinstance(repo_root_value, str) or not repo_root_value:
        fail("this manifest has no launcher-created worktrees to clean up")
    root = Path(repo_root_value).resolve()
    if maybe_repo_root(root) != root:
        fail("manifest repository root is no longer a git repository")
    if Path(manifest["working_root"]).resolve() != root:
        fail("worktree cleanup requires the launcher's repository root")
    requested_root, _ = resolve_working_root(args.working_dir)
    if requested_root != root:
        fail("cleanup must run from the manifest project root or use matching --working-dir")
    removed: list[str] = []
    planned: list[str] = []
    errors: list[str] = []
    for track_name, info in manifest.get("tracks", {}).items():
        if not isinstance(info, dict):
            errors.append(f"invalid track record: {track_name}")
            continue
        branch = info.get("branch")
        if not branch:
            continue
        worktree_record = info.get("worktree")
        if not isinstance(worktree_record, dict) or worktree_record.get("status") != "created":
            errors.append(f"track {track_name!r} has no launcher-created worktree record")
            continue
        try:
            working_dir = track_working_dir(manifest, track_name, info)
        except ValueError:
            errors.append(f"track {track_name!r} is not a launcher-owned worktree")
            continue
        if not worktree_exists(root, working_dir):
            errors.append(f"launcher worktree is missing: {working_dir}")
            continue
        observed_branch = git(["-C", str(working_dir), "branch", "--show-current"], cwd=root, check=False).stdout.strip()
        if observed_branch != branch:
            errors.append(f"launcher worktree branch does not match {branch}: {working_dir}")
            continue
        if args.dry_run:
            err(f"[dry-run] git worktree remove {'--force ' if args.force else ''}{working_dir}")
            planned.append(str(working_dir))
        else:
            result = git(["worktree", "remove", *(["--force"] if args.force else []), str(working_dir)], cwd=root, check=False)
            if result.returncode != 0:
                errors.append(result.stderr.strip() or result.stdout.strip() or f"could not remove {working_dir}")
                continue
            removed.append(str(working_dir))
        if args.delete_branches:
            if args.dry_run:
                err(f"[dry-run] git branch -D {branch}")
            else:
                result = git(["branch", "-D", branch], cwd=root, check=False)
                if result.returncode != 0:
                    errors.append(result.stderr.strip() or result.stdout.strip() or f"could not delete {branch}")
    if not args.dry_run and removed:
        result = git(["worktree", "prune"], cwd=root, check=False)
        if result.returncode != 0:
            errors.append(result.stderr.strip() or result.stdout.strip() or "could not prune worktrees")
    payload = {
        "success": not errors,
        "removed_worktrees": removed,
        "planned_worktrees": planned,
        "errors": errors,
        "dry_run": args.dry_run,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 1 if errors else 0


def add_manifest_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--session-id", help="session id used to resolve the manifest")
    parser.add_argument("--task-id", help="stable task id used to resolve the manifest")
    parser.add_argument("--manifest", help="explicit manifest path")
    parser.add_argument("--working-dir", help="project root for a manifest path when --manifest is omitted")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="launch.py",
        description="Launch the exact user approved implementation and review routes for one task.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("launch", help="start approved implementation routes")
    launch.add_argument("--session-id", required=True)
    launch.add_argument("--task-id", required=True)
    launch.add_argument("--routing-plan", required=True, help="approved routing-plan.json")
    launch.add_argument("--working-dir", help="project root; works without git for one sequential track")
    launch.add_argument(
        "--track",
        dest="track_briefs",
        nargs=2,
        action="append",
        required=True,
        metavar=("NAME", "BRIEF"),
        help="one implementation track and its brief; repeat only for independent tracks",
    )
    launch.add_argument("--isolation", choices=("working-tree", "worktree"), default="working-tree")
    launch.add_argument("--timeout", type=int, default=1800)
    launch.add_argument("--base", help="base commit when worktree isolation is authorized")
    launch.add_argument("--worktrees-dir", help="worktree parent directory")
    launch.add_argument("--allow-dirty", action="store_true")
    launch.add_argument("--force", action="store_true", help="explicitly recreate an existing worktree and branch")
    launch.add_argument("--dry-run", action="store_true", help="validate and preview only; never writes or dispatches")
    launch.set_defaults(handler=cmd_launch)
    poll = commands.add_parser("poll", help="read implementation and review job status")
    add_manifest_arguments(poll)
    poll.add_argument("--wait", action="store_true")
    poll.add_argument("--interval", type=float, default=5.0)
    poll.add_argument("--wait-timeout", type=float, default=300.0)
    poll.set_defaults(handler=cmd_poll)
    review = commands.add_parser("review", help="start the exact approved reviewer for one completed track")
    add_manifest_arguments(review)
    review.add_argument("--track", required=True)
    review.add_argument("--review-brief", required=True)
    review.add_argument("--review-snapshot", required=True, help="prepared source and required-evidence snapshot")
    review.add_argument("--evidence-packet", help="captured evidence packet to validate before spending a review cycle")
    review.add_argument("--cycle", type=int, help="must equal the next persisted review cycle")
    review.add_argument("--timeout", type=int, default=1800)
    review.add_argument("--dry-run", action="store_true")
    review.set_defaults(handler=cmd_review)
    record_review = commands.add_parser("record-review", help="validate and store a completed review response")
    add_manifest_arguments(record_review)
    record_review.add_argument("--track", required=True)
    record_review.add_argument("--cycle", type=int, required=True)
    record_review.set_defaults(handler=cmd_record_review)
    verify_review = commands.add_parser("verify-review", help="check the latest recorded review against current source")
    add_manifest_arguments(verify_review)
    verify_review.add_argument("--track", required=True)
    verify_review.add_argument("--base", required=True, help="current intended review base")
    verify_review.set_defaults(handler=cmd_verify_review)
    record_native = commands.add_parser("record-native", help="record a completed exact native route receipt")
    add_manifest_arguments(record_native)
    record_native.add_argument("--track", required=True)
    record_native.add_argument("--phase", choices=("implementation", "review"), required=True)
    record_native.add_argument("--cycle", type=int, help="required when --phase review")
    record_native.add_argument("--receipt", required=True, help="JSON receipt from the native route")
    record_native.add_argument(
        "--context-recovery-reason",
        help="record why a lost native context is being reconstructed under the same approved route",
    )
    record_native.set_defaults(handler=cmd_record_native)
    resume_native = commands.add_parser(
        "resume-native",
        help="prepare the next exact implementation turn in its persistent native context",
    )
    add_manifest_arguments(resume_native)
    resume_native.add_argument("--track", required=True)
    resume_native.add_argument("--follow-up", required=True, help="derived notes for the next implementation turn")
    resume_native.add_argument("--timeout", type=int, default=1800)
    resume_native.add_argument(
        "--context-recovery-reason",
        help="record why the same approved role must reconstruct a lost native context",
    )
    resume_native.set_defaults(handler=cmd_resume_native)
    evidence = commands.add_parser("evidence-recovery", help="reserve an approved evidence recovery before dispatch")
    add_manifest_arguments(evidence)
    evidence.add_argument("--track", required=True)
    evidence.add_argument("--reason", required=True)
    evidence.set_defaults(handler=cmd_evidence_recovery)
    digests = commands.add_parser("plan-digests", help="calculate routing-plan hashes without approval or dispatch")
    digests.add_argument("--routing-plan", required=True)
    digests.add_argument("--working-dir", help="project root used to resolve relative artifact paths")
    digests.set_defaults(handler=cmd_plan_digests)
    cleanup = commands.add_parser("cleanup", help="remove only launcher created worktrees")
    add_manifest_arguments(cleanup)
    cleanup.add_argument("--delete-branches", action="store_true")
    cleanup.add_argument("--force", action="store_true")
    cleanup.add_argument("--dry-run", action="store_true")
    cleanup.set_defaults(handler=cmd_cleanup)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command in {"poll", "review", "record-native", "record-review", "verify-review", "resume-native", "evidence-recovery", "cleanup"} and not arguments.manifest:
        if not arguments.session_id or not arguments.task_id:
            fail("provide --manifest or both --session-id and --task-id")
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
