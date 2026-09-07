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
EFFORT_FLAGS = {
    "codex": "--effort",
    "claude": "--effort",
    "grok": "--effort",
    "pi": "--thinking",
    "cline": "--thinking",
}
RUNNER_CONTROLLED_EFFORTS = {"low", "medium", "high", "xhigh", "max", "ultra"}
RUNNER_EFFORTS = {
    "claude": {"low", "medium", "high", "xhigh", "max"},
    "grok": {"low", "medium", "high"},
    "pi": {"low", "medium", "high", "xhigh"},
    "cline": {"low", "medium", "high", "xhigh"},
}
CODEX_MODEL_EFFORTS = {
    "gpt-6-astra": {"low", "medium", "high", "xhigh", "max", "ultra"},
    "gpt-5.6-sol": {"low", "medium", "high", "xhigh", "max", "ultra"},
    "gpt-5.6-terra": {"low", "medium", "high", "xhigh", "max", "ultra"},
    "gpt-5.6-luna": {"low", "medium", "high", "xhigh", "max"},
    "gpt-5.5": {"low", "medium", "high", "xhigh"},
    "gpt-5.4-mini": {"low", "medium", "high", "xhigh"},
    "gpt-5.3-codex-spark": {"low", "medium", "high", "xhigh"},
}
TERMINAL_JOB_STATUSES = {"completed", "failed", "died", "cancelled"}
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
JOBS_CLI = SKILLS_DIR / "shared" / "scripts" / "runner_jobs.py"


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
    effort_control = route["effort_control"]
    effort = route.get("effort")
    if effort_control == "runner":
        if route["runner"] not in EFFORT_FLAGS:
            raise ValueError(f"route.runner {route['runner']!r} cannot enforce a selected effort")
        if effort not in RUNNER_CONTROLLED_EFFORTS:
            raise ValueError("route.effort must be low, medium, high, xhigh, max, or ultra when effort_control is runner")
        if route["runner"] == "codex":
            supported = CODEX_MODEL_EFFORTS.get(route["model"])
            if supported is None:
                raise ValueError(f"route.model {route['model']!r} has no known codex effort capability")
        else:
            supported = RUNNER_EFFORTS[route["runner"]]
        if effort not in supported:
            raise ValueError(
                f"route.effort {effort!r} is not supported by {route['runner']}/{route['model']}"
            )
    elif effort_control == "runtime":
        if route["runner"] not in {"gemini", "dcode"}:
            raise ValueError("runtime controlled effort is only valid for gemini or dcode")
        if effort is not None:
            raise ValueError("route.effort must be null when effort_control is runtime")
    else:
        raise ValueError("route.effort_control must be runner or runtime")
    unavailable = route.get("unavailable")
    if not isinstance(unavailable, dict) or unavailable.get("action") not in {"block", "use"}:
        raise ValueError("route.unavailable must be {action: block} or an explicit approved fallback")
    if unavailable["action"] == "use":
        fallback = {**route, **unavailable}
        fallback["unavailable"] = {"action": "block"}
        for field in ("seat", "runner", "model", "model_verification", "effort", "mode", "effort_control"):
            if field not in unavailable:
                raise ValueError(f"route.unavailable.{field} is required for an approved fallback")
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


def route_arguments(
    route: dict[str, Any],
    brief: Path,
    working_dir: Path,
    role: str,
    timeout: int,
    metadata: dict[str, Any],
    read_only: bool,
) -> list[str]:
    arguments = [
        "--prompt-file", str(brief),
        "--working-dir", str(working_dir),
        "--model", route["model"],
        "--role", role,
        "--timeout", str(timeout),
        "--disable-fallback",
        "--metadata-json", json.dumps(metadata),
    ]
    if route["runner"] in {"pi", "cline"}:
        arguments.extend(["--seat", route["seat"]])
    if route["effort_control"] == "runner":
        arguments.extend([EFFORT_FLAGS[route["runner"]], route["effort"]])
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
) -> dict[str, Any]:
    if route["mode"] == "native":
        return {
            "mode": "native",
            "status": "orchestrator-managed",
            "selected_route": route,
            "pending": "Dispatch this exact approved native route and record its receipt.",
        }
    try:
        result = fire_runner(
            route["runner"],
            route_arguments(route, brief, working_dir, role, timeout, metadata, read_only),
            working_dir,
            dry_run,
        )
        return {"mode": "runner", "selected_route": route, "effective_route": route, **result}
    except RunnerLaunchError as primary_error:
        fallback = fallback_route(route)
        if fallback is None:
            raise
        try:
            result = fire_runner(
                fallback["runner"],
                route_arguments(fallback, brief, working_dir, role, timeout, metadata, read_only),
                working_dir,
                dry_run,
            )
        except RunnerLaunchError as fallback_error:
            raise RunnerLaunchError(f"primary route failed: {primary_error}; approved fallback failed: {fallback_error}") from fallback_error
        return {
            "mode": "runner",
            "selected_route": route,
            "effective_route": fallback,
            "fallback_reason": str(primary_error),
            **result,
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
) -> tuple[str, dict[str, str]]:
    """Bind derived worker notes to the approved task contract they cannot replace."""
    contract_path = contract["path"]
    contract_text = contract_path.read_text(encoding="utf-8")
    note_text = source.read_text(encoding="utf-8")
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
    }


def write_bound_brief(rendered: str, destination: Path, dry_run: bool) -> Path:
    if not dry_run:
        destination.write_text(rendered, encoding="utf-8")
    return destination


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
    return {
        "schema_version": 1,
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
            prepared[track] = {"rendered": rendered, "binding": binding, "source": source}
    except (OSError, UnicodeError) as error:
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
        save_manifest(manifest, manifest_path_value)
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
        except (RunnerLaunchError, OSError, UnicodeError) as error:
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
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def jobs_query(subcommand: str, job_id: str, working_dir: str) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(JOBS_CLI), subcommand, job_id, "--working-dir", working_dir, "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"status": "unknown", "raw": (result.stdout or result.stderr or "").strip()[:300]}


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
    return None


def job_snapshot(entry: dict[str, Any], working_dir: str) -> tuple[dict[str, Any], bool]:
    if entry.get("mode") == "native":
        receipt = entry.get("completion_receipt")
        if not isinstance(receipt, dict):
            return {"mode": "native", "status": "orchestrator-managed", "route": entry.get("selected_route")}, False
        route = entry.get("selected_route")
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
    status = jobs_query("status", job_id, working_dir).get("status", "unknown")
    snapshot: dict[str, Any] = {"mode": "runner", "job_id": job_id, "status": status}
    if status in TERMINAL_JOB_STATUSES:
        result = jobs_query("result", job_id, working_dir)
        snapshot["success"] = status == "completed" and result.get("success") is True
        snapshot["runner_session_id"] = result.get("session_id")
        snapshot["model_receipt"] = result.get("model_receipt")
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


def poll_once(manifest: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"session_id": manifest.get("session_id"), "task_id": manifest.get("task_id"), "tracks": {}, "reviews": {}}
    terminal = True
    for track, info in manifest.get("tracks", {}).items():
        snapshot, done = job_snapshot(info.get("implementation", {}), info.get("working_dir", "."))
        result["tracks"][track] = snapshot
        terminal = terminal and done
    for review in manifest.get("reviews", []):
        key = f"{review.get('track', 'unknown')}:{review.get('cycle', '0')}"
        snapshot, done = job_snapshot(review.get("launch", {}), review.get("working_dir", "."))
        result["reviews"][key] = snapshot
        terminal = terminal and done
    result["all_terminal"] = terminal
    return result


def cmd_poll(args: argparse.Namespace) -> int:
    manifest, _ = load_manifest(args)
    deadline = time.time() + args.wait_timeout
    while True:
        snapshot = poll_once(manifest)
        if not args.wait or snapshot["all_terminal"] or time.time() >= deadline:
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))
            failures = [entry for group in (snapshot["tracks"], snapshot["reviews"]) for entry in group.values() if entry.get("success") is False]
            return 1 if failures else 0
        err(f"[poll] waiting {args.interval}s")
        time.sleep(args.interval)


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


def next_review_cycle(manifest: dict[str, Any], track_name: str, requested_cycle: int | None, dry_run: bool, path: Path) -> int:
    attempts = manifest.setdefault("attempts", {}).setdefault("review_cycles", {})
    previous = attempts.get(track_name, 0)
    if not isinstance(previous, int) or previous < 0:
        fail(f"manifest has an invalid review cycle count for {track_name}")
    if previous >= MAX_REVIEW_CYCLES:
        manifest["status"] = "ceiling_hit"
        manifest["phase"] = f"{track_name}_review"
        if not dry_run:
            save_manifest(manifest, path)
        fail(f"review/fix cycle ceiling reached for {track_name}: {MAX_REVIEW_CYCLES}")
    cycle = previous + 1
    if requested_cycle is not None and requested_cycle != cycle:
        fail(f"next review cycle for {track_name} is {cycle}, not {requested_cycle}")
    if not dry_run:
        attempts[track_name] = cycle
        save_manifest(manifest, path)
    return cycle


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
    route = routing["routes"][args.track]["reviewer"]
    try:
        saved_route = track.get("reviewer_route")
        validate_route(saved_route)
    except ValueError as error:
        fail(f"invalid reviewer route in manifest: {error}")
    if canonical_digest(saved_route) != canonical_digest(route):
        fail("manifest reviewer route no longer matches the approved routing plan")
    if manifest.get("routing_plan", {}).get("approval") != routing["approval"]:
        fail("manifest approval record no longer matches the approved routing plan")
    try:
        working_dir = track_working_dir(manifest, args.track, track)
    except ValueError as error:
        fail(str(error))
    implementation_ready(track, working_dir)
    brief_candidate = Path(args.review_brief).expanduser()
    brief = (brief_candidate if brief_candidate.is_absolute() else root / brief_candidate).resolve()
    if not brief.is_file():
        fail("review brief is missing or not a file")
    try:
        rendered, binding = render_bound_brief(
            routing["scope_inputs"][route["input_path"]], brief, REVIEW_BOUNDARY, "Derived review notes"
        )
    except (OSError, UnicodeError) as error:
        fail(f"could not prepare a bound review brief: {error}")
    cycle = next_review_cycle(manifest, args.track, args.cycle, args.dry_run, path)
    bound_brief = Path(manifest["artifact_dir"]) / f"{args.track}-review-{cycle}-brief.md"
    metadata = {
        "session": manifest.get("session_id"),
        "task_id": manifest.get("task_id"),
        "track": args.track,
        "cycle": cycle,
        "phase": "review",
        "routing_plan": manifest.get("routing_plan", {}).get("path"),
    }
    record = {
        "track": args.track,
        "cycle": cycle,
        "status": "starting",
        "working_dir": str(working_dir),
        "brief": str(bound_brief),
        "brief_binding": binding,
        "reviewer_route": route,
        "launch": {"status": "pending", "selected_route": route},
    }
    if not args.dry_run:
        manifest.setdefault("reviews", []).append(record)
        save_manifest(manifest, path)
    try:
        written = write_bound_brief(rendered, bound_brief, args.dry_run)
        record["brief"] = str(written)
        record["launch"] = {"status": "starting", "selected_route": route}
        if not args.dry_run:
            save_manifest(manifest, path)
        launch = dispatch_route(route, written, working_dir, "codereviewer", args.timeout, metadata, True, args.dry_run)
    except (RunnerLaunchError, OSError, UnicodeError) as error:
        record["status"] = "failed"
        record["launch"] = {"status": "failed", "selected_route": route, "error": str(error)}
        manifest["status"] = "failed"
        manifest["phase"] = f"{args.track}_review"
        if not args.dry_run:
            save_manifest(manifest, path)
        fail(str(error))
    record["status"] = "running"
    record["launch"] = {"status": "running", **launch}
    if not args.dry_run:
        save_manifest(manifest, path)
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


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
    selected_route = entry.get("selected_route")
    try:
        validate_route(selected_route)
    except ValueError as error:
        fail(f"native route record is invalid: {error}")
    if canonical_digest(selected_route) != canonical_digest(approved_route):
        fail("native route record no longer matches the approved routing plan")
    receipt_candidate = Path(args.receipt).expanduser()
    receipt_path = (receipt_candidate if receipt_candidate.is_absolute() else root / receipt_candidate).resolve()
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"native receipt is not readable JSON: {error}")
    if not isinstance(receipt, dict):
        fail("native receipt must be a JSON object")
    if receipt.get("success") is True:
        mismatch = receipt_error(selected_route, receipt)
        if mismatch:
            fail(f"native receipt does not match the approved route: {mismatch}")
    entry["completion_receipt"] = receipt
    entry["status"] = "completed" if receipt.get("success") is True else "failed"
    save_manifest(manifest, path)
    print(json.dumps({"track": args.track, "phase": args.phase, "status": entry["status"], "model_receipt": receipt.get("model_receipt")}, indent=2, ensure_ascii=False))
    return 0 if receipt.get("success") is True else 1


def cmd_evidence_recovery(args: argparse.Namespace) -> int:
    manifest, path = load_manifest(args)
    track = manifest.get("tracks", {}).get(args.track)
    if not isinstance(track, dict):
        fail(f"track not found in manifest: {args.track}")
    attempts = manifest.setdefault("attempts", {}).setdefault("evidence_recoveries", {})
    previous = attempts.get(args.track, 0)
    if not isinstance(previous, int) or previous < 0:
        fail(f"manifest has an invalid evidence recovery count for {args.track}")
    if previous >= MAX_EVIDENCE_RECOVERIES:
        manifest["status"] = "ceiling_hit"
        manifest["phase"] = f"{args.track}_evidence_recovery"
        save_manifest(manifest, path)
        fail(f"evidence recovery ceiling reached for {args.track}: {MAX_EVIDENCE_RECOVERIES}")
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
    review.add_argument("--cycle", type=int, help="must equal the next persisted review cycle")
    review.add_argument("--timeout", type=int, default=1800)
    review.add_argument("--dry-run", action="store_true")
    review.set_defaults(handler=cmd_review)
    record_native = commands.add_parser("record-native", help="record a completed exact native route receipt")
    add_manifest_arguments(record_native)
    record_native.add_argument("--track", required=True)
    record_native.add_argument("--phase", choices=("implementation", "review"), required=True)
    record_native.add_argument("--cycle", type=int, help="required when --phase review")
    record_native.add_argument("--receipt", required=True, help="JSON receipt from the native route")
    record_native.set_defaults(handler=cmd_record_native)
    evidence = commands.add_parser("evidence-recovery", help="reserve the one allowed evidence recovery before dispatch")
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
    if arguments.command in {"poll", "review", "record-native", "evidence-recovery", "cleanup"} and not arguments.manifest:
        if not arguments.session_id or not arguments.task_id:
            fail("provide --manifest or both --session-id and --task-id")
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
