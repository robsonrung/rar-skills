#!/usr/bin/env python3
"""Read an approved task queue and project deterministic scheduling state.

The controller never writes files, changes task status, dispatches a worker, or
marks a task complete. It reads the approved queue configuration, routing plan,
feature ledger, task contracts, task manifests, and immutable review evidence.

Canonical queue schema
======================

Pass a JSON file, or a Markdown file containing one ``json task-queue`` fenced
block, with this shape::

    {
      "schema_version": 1,
      "id": "feature-name",
      "parent_prd": ".ai-workflow/work/feature/prd.md",
      "approval_record": ".ai-workflow/work/feature/combined-approval.json",
      "concurrency": {"max_active": 3, "isolation": "worktree"},
      "tasks": [{
        "id": "T1",
        "manifest": ".ai-workflow/work/feature/tasks/T1-change.md",
        "launch_manifest": ".ai-workflow/impl-review/run/T1/launch-manifest.json",
        "blocked_by": [],
        "write_paths": ["package/module.py"],
        "shared_surfaces": ["interface:public-api"]
      }],
      "merge_plans": []
    }

Queue, task, launch-manifest, and approval-record locators are relative to
``--root`` and must remain inside it. Immutable review snapshot links may be
absolute paths outside the source root and are checked by their recorded
checksum and source identity. The approved routing plan must bind this queue
file, its parent PRD, and every task manifest through ``scope.inputs``. An
accepted merge plan names two or more existing task IDs and every path and
surface that it permits. For example, a plan that permits ``T1`` and ``T2`` to
share ``package/module.py`` is::

    {"id": "shared-api", "tasks": ["T1", "T2"],
     "write_paths": ["package/module.py"],
     "shared_surfaces": ["interface:public-api"]}

``approval-inputs --routing-plan`` produces prospective task digests and the
matching prospective routing scope and route digests without changing task
files. When ``approval_record`` is present, ``schedule`` also requires its
immutable review-evidence envelope to bind both the ``task_queue`` and
``model_plan`` decisions to that preview and the approved routing plan.

``integration_evidence`` belongs to the existing feature ledger. It is a map
from task ID to an immutable review snapshot link::

    {
      "T1": {
        "snapshot": {"path": "/absolute/snapshot.json", "sha256": "..."},
        "base": "base revision",
        "launch_manifest": ".ai-workflow/impl-review/run/T1/launch-manifest.json"
      }
    }

The controller ignores prose status as completion evidence. It releases a
dependent only after ``review_evidence.assess`` reports ``ready`` for this
snapshot, the snapshot binds the task contract, and the current combined source
still matches the snapshot. An optional ``carry_forward`` checksum link can
instead prove dependency release through the original review's approved exact
changes. It preserves the original reviewer binding and is not final acceptance.
An optional ``batch_review`` snapshot link binds a new independent review of a
bounded task set. Several entries can share one approved call while retaining
their original contracts, findings, and validated current acceptance evidence.

Legacy Markdown queues with ``# T<N>:`` headings are accepted for inspection.
They default to one active task and require the same routing and evidence gates
before a task can be released.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


# The read only commands also leave an installed skill collection untouched.
sys.dont_write_bytecode = True


TASK_ID = re.compile(r"T[1-9][0-9]*\Z")
QUEUE_ID = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
TASK_HEADING = re.compile(r"^#\s+(T[1-9][0-9]*)\s*:", re.MULTILINE)
STATUS_LINE = re.compile(r"^\*\*Status:\*\*\s*([^\r\n]+?)[ \t]*(\r?\n|$)", re.MULTILINE)
CANONICAL_STATUS_LINE = re.compile(r"\*\*Status:\*\* (?:ready-for-agent|in-progress|done|blocked)\Z")
PARENT_LINE = re.compile(r"^\*\*Parent:\*\*\s*([^\r\n]+?)\s*$", re.MULTILINE)
APPROVED_STATUS = re.compile(r"^\*\*Status:\*\*\s*approved\s*$", re.MULTILINE | re.IGNORECASE)
GATE_VERDICT = re.compile(r"^\s*(?:[0-9]+\.\s*)?Verdict:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
GATE_DECISION = re.compile(r"^\s*(?:[0-9]+\.\s*)?Decision required:\s*(.+?)\s*$", re.MULTILINE | re.IGNORECASE)
GATE_SECURITY = re.compile(
    r"^\s*(?:[0-9]+\.\s*)?Security:\s*(deep|standard)\s*;\s*trigger:\s*(\S.*?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
FENCED_QUEUE = re.compile(
    r"^```(?:json[ \t]+task-queue|task-queue[ \t]+json)[ \t]*\r?\n(.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
TERMINAL_MANIFEST_STATUSES = {"failed", "ceiling_hit", "cancelled"}
KNOWN_TASK_STATUSES = {"draft", "ready-for-agent", "in-progress", "done", "blocked"}
PROMOTED_TASK_STATUSES = KNOWN_TASK_STATUSES - {"draft"}


class QueueError(ValueError):
    """Report an invalid queue or an evidence gate that cannot be trusted."""


@dataclass(frozen=True)
class Task:
    """One stable task contract and its static scheduling ownership."""

    id: str
    contract_path: Path
    launch_manifest_path: Path | None
    blocked_by: tuple[str, ...]
    write_paths: tuple[str, ...]
    shared_surfaces: tuple[str, ...]
    source_text: str
    status_span: tuple[int, int]
    status: str
    legacy: bool = False


@dataclass(frozen=True)
class MergePlan:
    """An approved exception for named shared write ownership."""

    id: str
    tasks: tuple[str, ...]
    write_paths: tuple[str, ...]
    shared_surfaces: tuple[str, ...]


@dataclass(frozen=True)
class Queue:
    """The immutable queue configuration used for one scheduler projection."""

    id: str
    path: Path
    parent_prd: Path
    configured_max_active: int
    max_active: int
    isolation: str
    tasks: tuple[Task, ...]
    merge_plans: tuple[MergePlan, ...]
    approval_record: Path | None = None
    legacy: bool = False


@dataclass
class TaskState:
    """Read only task state derived from contracts, manifests, and the ledger."""

    task: Task
    kind: str
    reasons: list[str]
    manifest: dict[str, Any] | None = None
    manifest_issues: list[str] | None = None
    integration_reasons: list[str] | None = None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise QueueError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def task_sort_key(task_id: str) -> tuple[int, str]:
    return int(task_id[1:]), task_id


def root_path(value: str | Path | None) -> Path:
    candidate = Path(value or Path.cwd()).expanduser().resolve()
    require(candidate.is_dir(), f"root is missing or not a directory: {candidate}")
    return candidate


def inside_root(root: Path, value: str, field: str, *, must_exist: bool = True) -> Path:
    require(isinstance(value, str) and value.strip(), f"{field} must be a nonempty path")
    raw = Path(value)
    resolved = (raw if raw.is_absolute() else root / raw).resolve()
    require(resolved.is_relative_to(root), f"{field} escapes root: {value}")
    if must_exist:
        require(resolved.is_file(), f"{field} is missing or not a file: {value}")
    return resolved


def referenced_path(root: Path, value: str) -> Path:
    """Resolve a ledger locator relative to the configured source root."""
    candidate = Path(value).expanduser()
    return (candidate if candidate.is_absolute() else root / candidate).resolve()


def local_path(value: str, field: str) -> str:
    """Normalize one declared repository write path without accepting traversal."""
    require(isinstance(value, str) and value.strip(), f"{field} must contain nonempty paths")
    candidate = PurePosixPath(value)
    require(not candidate.is_absolute(), f"{field} must use relative paths")
    require(".." not in candidate.parts and "." not in candidate.parts, f"{field} cannot use traversal")
    normalized = candidate.as_posix()
    require(normalized not in {"", "."}, f"{field} cannot name the repository root")
    return normalized


def unique_strings(value: Any, field: str, normalizer=None) -> tuple[str, ...]:
    require(isinstance(value, list), f"{field} must be a list")
    values = tuple(normalizer(item, field) if normalizer else item for item in value)
    require(all(isinstance(item, str) and item for item in values), f"{field} must contain nonempty strings")
    require(len(set(values)) == len(values), f"{field} has duplicates")
    return values


def surface_type(surface: str) -> str | None:
    prefix, marker, _ = surface.partition(":")
    return prefix if marker else None


def validate_surfaces(value: Any, field: str) -> tuple[str, ...]:
    surfaces = unique_strings(value, field)
    for surface in surfaces:
        kind = surface_type(surface)
        require(kind is not None and re.fullmatch(r"[a-z][a-z0-9-]*", kind) is not None,
                f"{field} entries need a typed surface such as interface:public-api")
        require(surface.partition(":")[2].strip(), f"{field} surface is missing a name: {surface}")
    return surfaces


def requires_migration_surface(paths: Iterable[str]) -> bool:
    return any({"migration", "migrations"} & set(PurePosixPath(path).parts) for path in paths)


def requires_security_surface(paths: Iterable[str]) -> bool:
    markers = {"auth", "authorization", "permission", "permissions", "security"}
    return any(markers & {part.lower() for part in PurePosixPath(path).parts} for path in paths)


def validate_ownership(paths: Any, surfaces: Any, field: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    write_paths = unique_strings(paths, field + ".write_paths", local_path)
    shared_surfaces = validate_surfaces(surfaces, field + ".shared_surfaces")
    kinds = {surface_type(surface) for surface in shared_surfaces}
    require(not requires_migration_surface(write_paths) or "migration" in kinds,
            f"{field} migration paths need a migration: shared surface")
    require(not requires_security_surface(write_paths) or "security" in kinds,
            f"{field} security paths need a security: shared surface")
    return write_paths, shared_surfaces


def status_from_text(text: str, label: str) -> tuple[str, tuple[int, int]]:
    matches = list(STATUS_LINE.finditer(text))
    require(len(matches) == 1, f"{label} needs exactly one **Status:** line")
    match = matches[0]
    status = match.group(1).strip()
    require(status in KNOWN_TASK_STATUSES, f"{label} has unsupported status: {status}")
    return status, match.span()


def task_from_file(
    root: Path,
    item: dict[str, Any],
    *,
    legacy: bool = False,
    source_text: str | None = None,
    status_span: tuple[int, int] | None = None,
) -> Task:
    task_id = item.get("id")
    require(isinstance(task_id, str) and TASK_ID.fullmatch(task_id) is not None,
            "task IDs must use stable T<N> form")
    manifest_value = item.get("manifest", item.get("path"))
    contract_path = inside_root(root, manifest_value, f"task {task_id}.manifest")
    content = source_text if source_text is not None else contract_path.read_bytes().decode("utf-8")
    headings = [heading for heading in TASK_HEADING.finditer(content) if heading.group(1) == task_id]
    require(headings,
            f"task contract heading does not match {task_id}: {contract_path}")
    if status_span is None:
        status, status_span = status_from_text(content, f"task {task_id}")
    else:
        status = content[status_span[0]:status_span[1]]
        status_match = STATUS_LINE.fullmatch(status)
        require(status_match is not None, f"task {task_id} has an invalid status span")
        status = status_match.group(1).strip()
        require(status in KNOWN_TASK_STATUSES, f"task {task_id} has unsupported status: {status}")
    blocked_raw = item.get("blocked_by", item.get("depends_on", []))
    blocked_by = unique_strings(blocked_raw, f"task {task_id}.blocked_by")
    require(all(TASK_ID.fullmatch(blocker) is not None for blocker in blocked_by),
            f"task {task_id}.blocked_by must contain stable task IDs")
    write_paths, shared_surfaces = validate_ownership(
        item.get("write_paths", []), item.get("shared_surfaces", []), f"task {task_id}"
    )
    if not legacy:
        require(write_paths, f"task {task_id} needs owned write_paths")
    launch_value = item.get("launch_manifest")
    if legacy and launch_value is None:
        launch_path = None
    else:
        launch_path = inside_root(root, launch_value, f"task {task_id}.launch_manifest", must_exist=False)
    return Task(
        id=task_id,
        contract_path=contract_path,
        launch_manifest_path=launch_path,
        blocked_by=blocked_by,
        write_paths=write_paths,
        shared_surfaces=shared_surfaces,
        source_text=content,
        status_span=status_span,
        status=status,
        legacy=legacy,
    )


def parse_merge_plans(value: Any, task_ids: set[str]) -> tuple[MergePlan, ...]:
    require(isinstance(value, list), "merge_plans must be a list")
    result = []
    known = set()
    for item in value:
        require(isinstance(item, dict), "each merge plan must be an object")
        plan_id = item.get("id")
        require(isinstance(plan_id, str) and QUEUE_ID.fullmatch(plan_id) is not None,
                "merge plan IDs must use lowercase slugs")
        require(plan_id not in known, f"duplicate merge plan ID: {plan_id}")
        known.add(plan_id)
        tasks = unique_strings(item.get("tasks"), f"merge plan {plan_id}.tasks")
        require(len(tasks) >= 2 and set(tasks) <= task_ids,
                f"merge plan {plan_id} must name at least two known tasks")
        paths, surfaces = validate_ownership(
            item.get("write_paths", []), item.get("shared_surfaces", []), f"merge plan {plan_id}"
        )
        require(paths or surfaces, f"merge plan {plan_id} must name owned paths or shared surfaces")
        result.append(MergePlan(plan_id, tasks, paths, surfaces))
    return tuple(sorted(result, key=lambda plan: plan.id))


def validate_graph(tasks: tuple[Task, ...]) -> None:
    by_id = {task.id: task for task in tasks}
    require(len(by_id) == len(tasks), "task IDs must be unique")
    for task in tasks:
        require(task.id not in task.blocked_by, f"task {task.id} cannot block itself")
        missing = sorted(set(task.blocked_by) - set(by_id), key=task_sort_key)
        require(not missing, f"task {task.id} has missing blockers: {', '.join(missing)}")
    visited: set[str] = set()
    visiting: list[str] = []

    def visit(task_id: str) -> None:
        if task_id in visiting:
            cycle = visiting[visiting.index(task_id):] + [task_id]
            raise QueueError("task dependency cycle: " + " -> ".join(cycle))
        if task_id in visited:
            return
        visiting.append(task_id)
        for blocker in sorted(by_id[task_id].blocked_by, key=task_sort_key):
            visit(blocker)
        visiting.pop()
        visited.add(task_id)

    for task in sorted(tasks, key=lambda value: task_sort_key(value.id)):
        visit(task.id)


def legacy_section(text: str, name: str) -> str:
    match = re.search(rf"^##\s+{re.escape(name)}\s*$\r?\n(.*?)(?=^##\s+|\Z)", text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else ""


def legacy_field_values(text: str, name: str) -> list[str]:
    match = re.search(rf"^\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", text, re.MULTILINE)
    if not match or match.group(1).strip().lower() in {"none", "n/a"}:
        return []
    return [part.strip().strip("`") for part in match.group(1).split(",") if part.strip()]


def parse_legacy_queue(path: Path, root: Path) -> Queue:
    text = path.read_bytes().decode("utf-8")
    parent = PARENT_LINE.search(text)
    require(parent is not None, "legacy queue needs **Parent:** with the approved PRD path")
    parent_prd = inside_root(root, parent.group(1).strip(), "legacy queue parent PRD")
    headings = list(TASK_HEADING.finditer(text))
    require(headings, "legacy queue needs at least one # T<N>: heading")
    tasks = []
    task_dir = path.parent / "tasks"
    for index, heading in enumerate(headings):
        task_id = heading.group(1)
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.start():end]
        status, relative_span = status_from_text(section, f"legacy task {task_id}")
        absolute_span = (heading.start() + relative_span[0], heading.start() + relative_span[1])
        matches = sorted(task_dir.glob(task_id + "-*.md")) if task_dir.is_dir() else []
        require(len(matches) <= 1, f"legacy task {task_id} has ambiguous published contracts")
        contract = matches[0] if matches else path
        item = {
            "id": task_id,
            "manifest": str(contract.relative_to(root)),
            "blocked_by": re.findall(r"\bT[1-9][0-9]*\b", legacy_section(section, "Blocked by")),
            "write_paths": legacy_field_values(section, "Write paths"),
            "shared_surfaces": legacy_field_values(section, "Shared surfaces"),
        }
        if matches:
            published = contract.read_bytes().decode("utf-8")
            item["blocked_by"] = re.findall(r"\bT[1-9][0-9]*\b", legacy_section(published, "Blocked by"))
            item["write_paths"] = legacy_field_values(published, "Write paths")
            item["shared_surfaces"] = legacy_field_values(published, "Shared surfaces")
            task = task_from_file(root, item, legacy=True)
        else:
            task = task_from_file(root, item, legacy=True, source_text=text, status_span=absolute_span)
            require(task.status == status, f"legacy task {task_id} status changed while parsing")
        tasks.append(task)
    validate_graph(tuple(tasks))
    return Queue(
        id=path.stem,
        path=path,
        parent_prd=parent_prd,
        configured_max_active=1,
        max_active=1,
        isolation="working-tree",
        tasks=tuple(sorted(tasks, key=lambda task: task_sort_key(task.id))),
        merge_plans=(),
        legacy=True,
    )


def load_queue(queue_path: str | Path, root: str | Path | None = None) -> Queue:
    """Load one canonical JSON queue or a compatibility Markdown queue."""
    resolved_root = root_path(root)
    path = inside_root(resolved_root, str(queue_path), "queue")
    text = path.read_text(encoding="utf-8")
    value: Any = None
    if path.suffix.lower() == ".json" or text.lstrip().startswith("{"):
        try:
            value = json.loads(text)
        except json.JSONDecodeError as error:
            raise QueueError(f"queue JSON is invalid: {error}") from error
    else:
        fenced = FENCED_QUEUE.search(text)
        if fenced:
            try:
                value = json.loads(fenced.group(1))
            except json.JSONDecodeError as error:
                raise QueueError(f"task queue fence is invalid JSON: {error}") from error
        else:
            return parse_legacy_queue(path, resolved_root)
    require(isinstance(value, dict) and value.get("schema_version") == 1,
            "queue must have schema_version 1")
    queue_id = value.get("id")
    require(isinstance(queue_id, str) and QUEUE_ID.fullmatch(queue_id) is not None,
            "queue id must use a lowercase slug")
    parent_prd = inside_root(resolved_root, value.get("parent_prd"), "queue parent_prd")
    concurrency = value.get("concurrency")
    require(isinstance(concurrency, dict) and type(concurrency.get("max_active")) is int
            and concurrency["max_active"] > 0, "queue concurrency.max_active must be a positive integer")
    isolation = concurrency.get("isolation", "working-tree")
    require(isolation in {"working-tree", "worktree"},
            "queue concurrency.isolation must be working-tree or worktree")
    raw_tasks = value.get("tasks")
    require(isinstance(raw_tasks, list) and raw_tasks, "queue tasks must be a nonempty list")
    tasks = tuple(task_from_file(resolved_root, item) for item in raw_tasks if isinstance(item, dict))
    require(len(tasks) == len(raw_tasks), "each queue task must be an object")
    validate_graph(tasks)
    plans = parse_merge_plans(value.get("merge_plans", []), {task.id for task in tasks})
    approval_value = value.get("approval_record")
    approval_record = None if approval_value is None else inside_root(
        resolved_root, approval_value, "queue approval_record", must_exist=False
    )
    return Queue(
        id=queue_id,
        path=path,
        parent_prd=parent_prd,
        configured_max_active=concurrency["max_active"],
        max_active=concurrency["max_active"] if isolation == "worktree" else 1,
        isolation=isolation,
        tasks=tuple(sorted(tasks, key=lambda task: task_sort_key(task.id))),
        merge_plans=plans,
        approval_record=approval_record,
    )


def prospective_task_text(task: Task, status: str = "ready-for-agent") -> str:
    """Change only this task's status in memory for a combined approval preview."""
    start, end = task.status_span
    original = task.source_text[start:end]
    newline = "\r\n" if original.endswith("\r\n") else "\n" if original.endswith("\n") else ""
    return task.source_text[:start] + f"**Status:** {status}" + newline + task.source_text[end:]


def has_exact_status_line(task: Task, status: str) -> bool:
    """Require the status spelling used by combined draft and promotion binding."""
    original = task.source_text[task.status_span[0]:task.status_span[1]]
    newline = "\r\n" if original.endswith("\r\n") else "\n" if original.endswith("\n") else ""
    return original == f"**Status:** {status}" + newline


def readiness_gates(task: Task) -> list[str]:
    """Read only gates that must be settled before a ready task can start."""
    from gate_contract import readiness_errors

    reasons = readiness_errors(task.source_text)
    if task.legacy:
        return reasons
    gates = legacy_section(task.source_text, "Gates")
    if not gates:
        return ["task contract has no Gates section"]
    verdicts = [match.group(1).strip().lower() for match in GATE_VERDICT.finditer(gates)]
    decisions = [match.group(1).strip().lower() for match in GATE_DECISION.finditer(gates)]
    security = list(GATE_SECURITY.finditer(gates))
    if len(verdicts) != 1:
        reasons.append("task Gates needs exactly one Verdict: proceed gate")
    elif verdicts[0] == "revise":
        reasons.append("task gate verdict is revise")
    elif verdicts[0] != "proceed":
        reasons.append("task gate verdict must be proceed")
    if len(decisions) != 1:
        reasons.append("task Gates needs exactly one Decision required: none gate")
    elif decisions[0] != "none":
        reasons.append("task gate has an unresolved decision")
    if len(security) != 1:
        reasons.append("task Gates needs Security: deep or standard; trigger: <value>")
    return reasons


def require_approved_prd(queue: Queue) -> None:
    text = queue.parent_prd.read_text(encoding="utf-8")
    require(APPROVED_STATUS.search(text) is not None,
            "queue parent PRD is not approved")


def skills_root() -> Path:
    try:
        from skill_paths import find_skills_root

        return find_skills_root(Path(__file__))
    except ImportError as error:
        raise QueueError("cannot load the shared skill path resolver") from error


@lru_cache(maxsize=1)
def launcher_module():
    """Load the launcher's canonical digest and approved route validator."""
    root = skills_root()
    shared_scripts = str(root / "shared" / "scripts")
    if shared_scripts not in sys.path:
        sys.path.insert(0, shared_scripts)
    try:
        from skill_paths import skill_dir

        path = skill_dir("implement-and-review", root=root, start=Path(__file__)) / "scripts" / "launch.py"
    except ImportError as error:
        raise QueueError("cannot resolve the implement-and-review launcher") from error
    require(path.is_file(), "implement-and-review launcher is missing")
    spec = importlib.util.spec_from_file_location("task_queue_launcher", path)
    require(spec is not None and spec.loader is not None, "cannot load the task launcher")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_text_sha256(text: str) -> str:
    """Match the public launcher status normalization without loading the engine."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    canonical = "".join(
        line for line in normalized.splitlines(keepends=True)
        if not CANONICAL_STATUS_LINE.fullmatch(line.removesuffix("\n"))
    )
    return sha256_bytes(canonical.encode("utf-8"))


def approval_inputs(
    queue_path: str | Path,
    root: str | Path | None = None,
    routing_plan_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return current and prospective task digests without writing status changes."""
    resolved_root = root_path(root)
    queue = load_queue(queue_path, resolved_root)
    for task in queue.tasks:
        reasons = readiness_gates(task)
        require(not reasons, f"task {task.id} cannot enter approval preview: {'; '.join(reasons)}")
    result = {
        "schema_version": 1,
        "queue": {
            "id": queue.id,
            "path": str(queue.path),
            "file_sha256": file_sha256(queue.path),
            "legacy": queue.legacy,
        },
        "tasks": [
            {
                "id": task.id,
                "path": str(task.contract_path),
                "status": task.status,
                "current_file_sha256": file_sha256(task.contract_path),
                "current_content_sha256": canonical_text_sha256(task.source_text),
                "prospective_ready_content_sha256": canonical_text_sha256(prospective_task_text(task)),
            }
            for task in queue.tasks
        ],
    }
    if routing_plan_path is not None:
        embedded = [task.id for task in queue.tasks if task.legacy and task.contract_path == queue.path]
        require(not embedded,
                "legacy embedded tasks must derive canonical task files before approval or dispatch: "
                + ", ".join(sorted(embedded, key=task_sort_key)))
        for task in queue.tasks:
            require(task.status == "draft" and has_exact_status_line(task, "draft"),
                    f"task {task.id} must use exact **Status:** draft before combined approval preview")
        routing_path = inside_root(resolved_root, str(routing_plan_path), "draft routing plan")
        result["prospective_routing"] = prospective_routing(queue, routing_path, resolved_root)
    return result


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise QueueError(f"{label} is invalid JSON: {error}") from error
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def prospective_routing(queue: Queue, routing_path: Path, root: Path) -> dict[str, Any]:
    """Produce launch compatible approval digests while task files remain draft."""
    launcher = launcher_module()
    plan = load_json(routing_path, "draft routing plan")
    require(plan.get("schema_version") == 1, "draft routing plan must have schema_version 1")
    scope = plan.get("scope")
    require(isinstance(scope, dict) and isinstance(scope.get("inputs"), list) and scope["inputs"],
            "draft routing plan must contain scope.inputs")
    prospective_by_path: dict[Path, str] = {}
    for task in queue.tasks:
        require(task.contract_path not in prospective_by_path,
                "draft routing preview cannot bind multiple embedded tasks through one file")
        prospective_by_path[task.contract_path] = canonical_text_sha256(prospective_task_text(task))
    scope_inputs = []
    seen = set()
    for item in scope["inputs"]:
        require(isinstance(item, dict) and isinstance(item.get("path"), str)
                and isinstance(item.get("content_sha256"), str),
                "draft scope inputs need path and content_sha256")
        path_value = item["path"]
        require(path_value not in seen, f"draft scope has duplicate input path: {path_value}")
        seen.add(path_value)
        source = referenced_path(root, path_value)
        require(source.is_file(), f"draft scope input is missing: {path_value}")
        current = launcher.content_digest(source)
        require(current == item["content_sha256"], f"draft scope input changed: {path_value}")
        replacement = prospective_by_path.get(source)
        scope_inputs.append({**item, "content_sha256": replacement or item["content_sha256"]})
    resolved_scope = {
        referenced_path(root, item["path"])
        for item in scope_inputs
    }
    required = {queue.path, queue.parent_prd, *(task.contract_path for task in queue.tasks)}
    missing = sorted(str(path) for path in required - resolved_scope)
    require(not missing, "draft routing scope is missing queue inputs: " + ", ".join(missing))
    routes = plan.get("routes")
    require(isinstance(routes, list), "draft routing plan must contain routes")
    route_ids = set()
    for route in routes:
        validated = launcher.validate_route(route)
        require(validated["id"] not in route_ids, f"draft routing plan has duplicate route ID: {validated['id']}")
        route_ids.add(validated["id"])
        require(validated["input_path"] in seen,
                f"draft route input_path is not in scope.inputs: {validated['input_path']}")
    normalized_inputs = launcher.normalized_scope_inputs(scope_inputs)
    return {
        "routing_plan": str(routing_path),
        "scope_inputs": normalized_inputs,
        "scope_digest": launcher.canonical_digest(normalized_inputs),
        "routes_digest": launcher.canonical_digest(launcher.normalized_routes(routes)),
    }


def routes_for_queue(queue: Queue, routing_plan: Path, root: Path) -> dict[str, dict[str, Any]]:
    """Validate the exact approved route plan and its bound queue inputs."""
    launcher = launcher_module()
    raw_plan = load_json(routing_plan, "routing plan")
    routes = raw_plan.get("routes")
    require(isinstance(routes, list), "routing plan must contain routes")
    result = {}
    for task in queue.tasks:
        task_routes = [route for route in routes if isinstance(route, dict) and route.get("task_id") == task.id]
        require(task_routes, f"routing plan has no routes for task {task.id}")
        tracks = {route.get("track") for route in task_routes if isinstance(route.get("track"), str)}
        require(tracks, f"routing plan has no track for task {task.id}")
        try:
            routed = launcher.load_routing_plan(str(routing_plan), task.id, tracks, True, root)
        except (ValueError, OSError, KeyError, TypeError) as error:
            raise QueueError(f"routing plan for {task.id} is invalid: {error}") from error
        input_paths = {
            Path(route["input_path"] if Path(route["input_path"]).is_absolute() else root / route["input_path"]).resolve()
            for roles in routed["routes"].values() for route in roles.values()
        }
        require(input_paths == {task.contract_path},
                f"routing plan routes for {task.id} must bind its task contract")
        result[task.id] = routed
    scope_paths = {
        Path(item["path"] if Path(item["path"]).is_absolute() else root / item["path"]).resolve()
        for item in raw_plan.get("scope", {}).get("inputs", []) if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    required = {queue.path, queue.parent_prd, *(task.contract_path for task in queue.tasks)}
    missing = sorted((str(path) for path in required - scope_paths))
    require(not missing, "routing plan scope.inputs is missing queue inputs: " + ", ".join(missing))
    return result


def validate_combined_preview_tasks(
    queue: Queue,
    preview_value: dict[str, Any],
    scope_inputs: list[Any],
    root: Path,
) -> None:
    """Bind promoted task files to the draft rows approved in a combined preview."""
    preview_queue = preview_value.get("queue")
    require(isinstance(preview_queue, dict) and preview_queue.get("id") == queue.id,
            "combined approval preview has another queue identity")
    require(isinstance(preview_queue.get("path"), str)
            and referenced_path(root, preview_queue["path"]) == queue.path,
            "combined approval preview has another queue path")
    rows = preview_value.get("tasks")
    require(isinstance(rows, list) and len(rows) == len(queue.tasks),
            "combined approval preview task rows differ from the queue")
    required_fields = {
        "id", "path", "status", "current_file_sha256", "current_content_sha256",
        "prospective_ready_content_sha256",
    }
    by_id = {}
    for row in rows:
        require(isinstance(row, dict) and set(row) == required_fields and isinstance(row.get("id"), str)
                and row["id"] not in by_id,
                "combined approval preview has invalid task rows")
        by_id[row["id"]] = row
    require(set(by_id) == {task.id for task in queue.tasks},
            "combined approval preview task IDs differ from the queue")
    inputs_by_path = {}
    for item in scope_inputs:
        require(isinstance(item, dict) and isinstance(item.get("path"), str)
                and isinstance(item.get("content_sha256"), str),
                "approved scope inputs are invalid")
        path = referenced_path(root, item["path"])
        require(path not in inputs_by_path, "approved scope has duplicate input paths")
        inputs_by_path[path] = item
    for task in queue.tasks:
        row = by_id[task.id]
        require(isinstance(row["path"], str) and referenced_path(root, row["path"]) == task.contract_path,
                f"combined approval preview task {task.id} has another contract path")
        require(row["status"] == "draft", f"combined approval preview task {task.id} was not a draft")
        require(task.status in PROMOTED_TASK_STATUSES,
                f"task {task.id} was not promoted from draft before combined approval")
        require(has_exact_status_line(task, task.status),
                f"task {task.id} promoted status line is not exact")
        draft_text = prospective_task_text(task, "draft")
        prospective_text = prospective_task_text(task, "ready-for-agent")
        require(row["current_file_sha256"] == sha256_bytes(draft_text.encode("utf-8")),
                f"task {task.id} changed beyond status promotion after combined approval")
        require(row["current_content_sha256"] == canonical_text_sha256(draft_text),
                f"combined approval preview task {task.id} has another draft content digest")
        prospective_digest = canonical_text_sha256(prospective_text)
        require(row["prospective_ready_content_sha256"] == prospective_digest,
                f"combined approval preview task {task.id} has another ready content digest")
        scope_row = inputs_by_path.get(task.contract_path)
        require(scope_row is not None and scope_row["content_sha256"] == prospective_digest,
                f"approved scope does not bind prospective ready task {task.id}")


def validate_approval_record(
    queue: Queue,
    routing_path: Path,
    routing: dict[str, dict[str, Any]],
    root: Path,
) -> None:
    """Verify one combined task and model decision when the queue declares it."""
    if queue.approval_record is None:
        return
    require(queue.approval_record.is_file(), "combined approval record is missing")
    try:
        import review_evidence

        payload = review_evidence.load_record(queue.approval_record)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise QueueError(f"combined approval record is invalid: {error}") from error
    require(isinstance(payload, dict), "combined approval payload must be an object")
    required = {
        "schema_version", "decisions", "response_reference", "decided_at", "queue_file_sha256",
        "preview", "scope_digest", "routes_digest",
    }
    require(set(payload) == required and payload.get("schema_version") == 1,
            "combined approval payload has invalid fields")
    decisions = payload["decisions"]
    require(isinstance(decisions, list) and len(decisions) == len(set(decisions))
            and set(decisions) == {"task_queue", "model_plan"},
            "combined approval must cover task_queue and model_plan")
    require(all(isinstance(payload[field], str) and payload[field].strip()
                for field in ("response_reference", "decided_at", "queue_file_sha256", "scope_digest", "routes_digest")),
            "combined approval needs response and digest values")
    require(payload["queue_file_sha256"] == file_sha256(queue.path),
            "queue file changed after combined approval")
    preview = payload["preview"]
    require(isinstance(preview, dict) and set(preview) == {"path", "sha256"}
            and isinstance(preview.get("path"), str) and isinstance(preview.get("sha256"), str),
            "combined approval preview needs path and checksum")
    preview_path = referenced_path(root, preview["path"])
    require(preview_path.is_file() and file_sha256(preview_path) == preview["sha256"],
            "combined approval preview is missing or changed")
    preview_value = load_json(preview_path, "combined approval preview")
    prospective = preview_value.get("prospective_routing")
    require(isinstance(prospective, dict), "combined approval preview has no prospective routing")
    require(prospective.get("scope_digest") == payload["scope_digest"]
            and prospective.get("routes_digest") == payload["routes_digest"],
            "combined approval preview digests differ from its record")
    require(preview_value.get("queue", {}).get("file_sha256") == payload["queue_file_sha256"],
            "combined approval preview has another queue identity")
    raw_plan = load_json(routing_path, "routing plan")
    launcher = launcher_module()
    actual_inputs = raw_plan.get("scope", {}).get("inputs") if isinstance(raw_plan.get("scope"), dict) else None
    require(isinstance(actual_inputs, list), "routing plan has no scope inputs")
    normalized_inputs = launcher.normalized_scope_inputs(actual_inputs)
    require(prospective.get("scope_inputs") == normalized_inputs,
            "approved scope inputs differ from combined approval preview")
    validate_combined_preview_tasks(queue, preview_value, normalized_inputs, root)
    approval = next(iter(routing.values()))["approval"]
    require(payload["scope_digest"] == approval["scope_digest"]
            and payload["routes_digest"] == approval["routes_digest"],
            "combined approval digests differ from routing approval")
    require(payload["response_reference"] == approval["reference"]
            and payload["decided_at"] == approval["decided_at"],
            "routing approval does not cite the combined response")


def load_ledger(ledger_path: str | Path, routing_plan: Path, root: Path) -> dict[str, Any]:
    path = inside_root(root, str(ledger_path), "ledger")
    state = load_json(path, "ledger")
    ledger = state.get("call_ledger")
    require(isinstance(ledger, dict), "ledger has no call_ledger")
    reference = ledger.get("plan")
    require(isinstance(reference, dict), "ledger has no routing plan reference")
    recorded_path = reference.get("path")
    recorded_sha = reference.get("sha256")
    require(isinstance(recorded_path, str) and isinstance(recorded_sha, str),
            "ledger routing plan reference is invalid")
    recorded = referenced_path(root, recorded_path)
    require(recorded == routing_plan.resolve(), "ledger belongs to another routing plan")
    require(file_sha256(routing_plan) == recorded_sha, "routing plan changed after ledger initialization")
    calls = ledger.get("calls")
    require(isinstance(calls, dict), "ledger calls must be an object")
    limits = ledger.get("limits")
    attempts = state.get("attempts")
    require(isinstance(limits, dict) and limits,
            "ledger has no approved call limits")
    require(all(isinstance(key, str) and key and type(value) is int and value > 0
                for key, value in limits.items()),
            "ledger call limits must be positive integer ceilings")
    require(isinstance(attempts, dict)
            and all(isinstance(key, str) and key and type(value) is int and value >= 0
                    for key, value in attempts.items()),
            "ledger attempts must be nonnegative integer counters")
    require("total_role_calls" in limits,
            "ledger call limits need a total_role_calls ceiling")
    require(set(attempts) <= set(limits),
            "ledger attempts contain a counter without an approved ceiling")
    integration = state.get("integration_evidence", {})
    require(isinstance(integration, dict), "ledger integration_evidence must be an object")
    return state


def initial_implementer_routes(routing: dict[str, Any]) -> tuple[str, ...]:
    """Return the exact initial implementation reservations needed for one task."""
    tracks = routing.get("routes")
    require(isinstance(tracks, dict) and tracks, "task routing has no implementation tracks")
    route_ids = []
    for track in sorted(tracks):
        routes = tracks[track]
        route = routes.get("implementer") if isinstance(routes, dict) else None
        require(isinstance(route, dict) and isinstance(route.get("id"), str) and route["id"],
                f"task routing track {track} has no implementer route")
        route_ids.append(route["id"])
    return tuple(route_ids)


def reservation_reasons(
    routing: dict[str, Any],
    limits: dict[str, int],
    attempts: dict[str, int],
    selected_reservations: dict[str, int],
) -> list[str]:
    """Check only initial implementer reservations against the existing ledger ceilings."""
    routes = initial_implementer_routes(routing)
    needed = {"total_role_calls": len(routes)}
    for route_id in routes:
        needed[route_id] = needed.get(route_id, 0) + 1
    reasons = []
    for key, count in sorted(needed.items()):
        require(key in limits, f"ledger has no approved call ceiling for {key}")
        used = attempts.get(key, 0) + selected_reservations.get(key, 0)
        if used + count > limits[key]:
            reasons.append(f"approved call ceiling {key} has {limits[key] - used} initial slots remaining")
    return reasons


def reserve_initial_routes(routing: dict[str, Any], selected_reservations: dict[str, int]) -> None:
    """Account for projected initial reservations without changing the ledger."""
    routes = initial_implementer_routes(routing)
    selected_reservations["total_role_calls"] = selected_reservations.get("total_role_calls", 0) + len(routes)
    for route_id in routes:
        selected_reservations[route_id] = selected_reservations.get(route_id, 0) + 1


def calls_by_task(state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    calls = state["call_ledger"]["calls"]
    for call in calls.values():
        if not isinstance(call, dict):
            continue
        intent = call.get("intent")
        route = intent.get("route") if isinstance(intent, dict) else None
        task_id = route.get("task_id") if isinstance(route, dict) else None
        owners = {task_id} if isinstance(task_id, str) else set()
        reference = intent.get("review_snapshot") if isinstance(intent, dict) else None
        if isinstance(reference, dict) and isinstance(reference.get("path"), str):
            try:
                import review_evidence
                path = Path(reference["path"])
                require(path.is_absolute() and file_sha256(path) == reference.get("sha256"),
                        "review snapshot checksum differs while resolving call ownership")
                snapshot = review_evidence.load_record(path)
                batch = snapshot["requirements"]["value"].get("batch", {})
                owners.update(batch.get("tasks", {}))
            except (ValueError, OSError, KeyError, TypeError) as error:
                if call.get("status") == "pending":
                    raise QueueError(f"pending review ownership cannot be resolved: {error}") from error
        for owner in owners:
            result.setdefault(owner, []).append(call)
    return result


def validate_ledger_calls(
    state: dict[str, Any],
    routing_path: Path,
    root: Path,
) -> None:
    """Reject malformed or unapproved call rows before they can be ignored."""
    launcher = launcher_module()
    plan = load_json(routing_path, "routing plan")
    routes = plan.get("routes")
    require(isinstance(routes, list), "routing plan has no routes")
    approved = set()
    for route in routes:
        validated = launcher.validate_route(route)
        for variant in launcher.route_variants(validated):
            approved.add(launcher.canonical_digest(variant))
    for call_id, call in state["call_ledger"]["calls"].items():
        require(isinstance(call, dict), f"ledger call {call_id} is not an object")
        intent = call.get("intent")
        route = intent.get("route") if isinstance(intent, dict) else None
        require(isinstance(route, dict) and isinstance(route.get("task_id"), str),
                f"ledger call {call_id} has no task route")
        require(call.get("status") in {"pending", "completed", "failed"},
                f"ledger call {call_id} has an unknown status")
        try:
            digest = launcher.canonical_digest(route)
        except (TypeError, ValueError) as error:
            raise QueueError(f"ledger call {call_id} route is invalid: {error}") from error
        require(digest in approved, f"ledger call {call_id} route is not approved")


def validate_ledger_accounting(state: dict[str, Any]) -> None:
    """Require stored attempt counters to cover all persisted call reservations."""
    ledger = state["call_ledger"]
    limits = ledger["limits"]
    attempts = state["attempts"]
    calls = ledger["calls"]
    route_counts: dict[str, int] = {}
    for call in calls.values():
        route_id = call["intent"]["route"]["id"]
        require(route_id in limits, f"ledger has no approved call ceiling for recorded route {route_id}")
        route_counts[route_id] = route_counts.get(route_id, 0) + 1
    require(attempts.get("total_role_calls", 0) >= len(calls),
            "ledger total_role_calls attempts are lower than recorded calls")
    for route_id, count in route_counts.items():
        require(attempts.get(route_id, 0) >= count,
                f"ledger attempts for {route_id} are lower than recorded calls")


def load_launch_manifest(
    task: Task,
    routing: dict[str, Any],
    routing_path: Path,
    root: Path,
    isolation: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Read an existing manifest while retaining ownership for malformed partial state."""
    if task.launch_manifest_path is None or not task.launch_manifest_path.exists():
        return None, []
    try:
        manifest = load_json(task.launch_manifest_path, f"launch manifest for {task.id}")
    except (QueueError, OSError, UnicodeError) as error:
        return None, [f"launch manifest is incomplete or invalid: {error}"]
    issues = []
    if manifest.get("skill") != "implement-and-review":
        issues.append("launch manifest has another owner")
    if manifest.get("task_id") != task.id:
        issues.append("launch manifest belongs to another task")
    working_root = manifest.get("working_root")
    if not isinstance(working_root, str) or referenced_path(root, working_root) != root:
        issues.append("launch manifest has another working root")
    if manifest.get("isolation") != isolation:
        issues.append(f"launch manifest isolation does not match approved {isolation} isolation")
    bound = manifest.get("routing_plan")
    if not isinstance(bound, dict) or not isinstance(bound.get("path"), str):
        issues.append("launch manifest has no routing plan binding")
    else:
        if referenced_path(root, bound["path"]) != routing_path.resolve():
            issues.append("launch manifest has another routing plan")
        if bound.get("approval") != routing["approval"]:
            issues.append("launch manifest has a changed approval binding")
    tracks = manifest.get("tracks")
    if not isinstance(tracks, dict):
        issues.append("launch manifest tracks are incomplete")
    else:
        for track, routes in routing["routes"].items():
            record = tracks.get(track)
            if not isinstance(record, dict):
                issues.append(f"launch manifest is missing approved track {track}")
                continue
            if record.get("implementer_route") != routes["implementer"]:
                issues.append(f"launch manifest implementer route differs for {track}")
            if record.get("reviewer_route") != routes["reviewer"]:
                issues.append(f"launch manifest reviewer route differs for {track}")
    return manifest, issues


def matching_link(value: Any, expected_path: Path, expected_sha256: str, root: Path) -> bool:
    """Compare evidence links after resolving their locator from the source root."""
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        return False
    if not isinstance(value.get("path"), str) or value.get("sha256") != expected_sha256:
        return False
    try:
        return referenced_path(root, value["path"]) == expected_path.resolve()
    except (OSError, TypeError, ValueError):
        return False


def route_binds_contract(route: Any, task: Task, root: Path) -> bool:
    """A review route can support this evidence only when it names this contract."""
    if not isinstance(route, dict) or route.get("role") != "reviewer":
        return False
    input_path = route.get("input_path")
    if not isinstance(input_path, str):
        return False
    try:
        return referenced_path(root, input_path) == task.contract_path
    except (OSError, TypeError, ValueError):
        return False


def approved_reviewer_route_digests(task: Task, routing_path: Path, root: Path) -> set[str]:
    """Return every approved reviewer route and explicit fallback for this contract."""
    launcher = launcher_module()
    plan = load_json(routing_path, "routing plan")
    routes = plan.get("routes")
    require(isinstance(routes, list), "routing plan has no routes")
    digests = set()
    for route in routes:
        validated = launcher.validate_route(route)
        for candidate in launcher.route_variants(validated):
            if candidate.get("task_id") != task.id and route_binds_contract(candidate, task, root):
                digests.add(launcher.canonical_digest(candidate))
    return digests


def ledger_reviewer_binding(
    task: Task,
    state: dict[str, Any],
    routing_path: Path,
    snapshot_path: Path,
    snapshot_sha256: str,
    review_path: Path,
    review_sha256: str,
    root: Path,
) -> bool:
    """Find a completed approved reviewer call bound to the reviewed snapshot."""
    approved_routes = approved_reviewer_route_digests(task, routing_path, root)
    calls = state.get("call_ledger", {}).get("calls", {})
    if not isinstance(calls, dict):
        return False
    for call in calls.values():
        if not isinstance(call, dict) or call.get("status") != "completed" or call.get("review_status") != "ready":
            continue
        intent = call.get("intent")
        route = intent.get("route") if isinstance(intent, dict) else None
        if not route_binds_contract(route, task, root):
            continue
        if route.get("task_id") == task.id:
            continue
        if launcher_module().canonical_digest(route) not in approved_routes:
            continue
        if not matching_link(intent.get("review_snapshot"), snapshot_path, snapshot_sha256, root):
            continue
        if matching_link(call.get("review"), review_path, review_sha256, root):
            return True
    return False


def manifest_reviewer_binding(
    task: Task,
    manifest: dict[str, Any] | None,
    routing: dict[str, Any],
    snapshot_path: Path,
    snapshot_sha256: str,
    review_path: Path,
    review_sha256: str,
    root: Path,
) -> bool:
    """Accept the launcher's recorded review link for established manifests."""
    if not isinstance(manifest, dict):
        return False
    reviews = manifest.get("reviews")
    routes = routing.get("routes") if isinstance(routing, dict) else None
    if not isinstance(reviews, list) or not isinstance(routes, dict):
        return False
    for record in reviews:
        if not isinstance(record, dict) or not isinstance(record.get("track"), str):
            continue
        approved = routes.get(record["track"])
        reviewer = approved.get("reviewer") if isinstance(approved, dict) else None
        if record.get("reviewer_route") != reviewer or not route_binds_contract(reviewer, task, root):
            continue
        if not matching_link(record.get("source_snapshot"), snapshot_path, snapshot_sha256, root):
            continue
        if matching_link(record.get("review_evidence"), review_path, review_sha256, root):
            return True
    return False



def batch_dispatch_reasons(task, assessment, queue_tasks, state, routing_path, root):
    import review_evidence

    batch_path = Path(assessment["snapshot"]["path"])
    batch_snapshot = review_evidence.snapshot_record(batch_path)
    contracts = {member.id: member.contract_path for member in queue_tasks}
    for task_id, row in batch_snapshot["requirements"]["value"]["batch"]["tasks"].items():
        endorsed = review_evidence.load_record(row["snapshot"]["path"])
        if task_id not in contracts or Path(endorsed["contract"]["path"]) != contracts[task_id]:
            return ["batch task set differs from canonical queue contracts"]
    for call in state["call_ledger"]["calls"].values():
        prior_link = call.get("review")
        if call.get("status") != "completed" or not isinstance(prior_link, dict):
            continue
        prior_path = referenced_path(root, prior_link.get("path", ""))
        if prior_path == batch_path.parent / "review.json":
            continue
        require(file_sha256(prior_path) == prior_link.get("sha256"), "prior review ledger binding changed")
        prior_record = review_evidence.load_record(prior_path)
        require(review_evidence.file_hash(prior_record["snapshot_path"]) == prior_record["snapshot_sha256"],
                "prior batch snapshot binding changed")
        prior_snapshot = review_evidence.load_record(prior_record["snapshot_path"])
        prior_batch = prior_snapshot["requirements"]["value"].get("batch")
        if prior_batch and set(assessment["task_ids"]).intersection(prior_batch["tasks"]):
            if not any(matching_link(link, prior_path, prior_link["sha256"], root)
                       for link in batch_snapshot["previous_reviews"]):
                return ["batch review omits a prior batch review and its findings"]
    batch_task = replace(task, contract_path=Path(batch_snapshot["contract"]["path"]))
    batch_review = batch_path.parent / "review.json"
    eligible_state = {**state, "call_ledger": {**state["call_ledger"], "calls": {
        key: call for key, call in state["call_ledger"]["calls"].items()
        if call.get("intent", {}).get("route", {}).get("task_id") not in assessment["task_ids"]
    }}}
    if not ledger_reviewer_binding(batch_task, eligible_state, routing_path, batch_path,
                                   assessment["snapshot"]["sha256"], batch_review,
                                   file_sha256(batch_review), root):
        return ["batch review has no approved independent reviewer dispatch binding"]
    return []

def integration_assessment(
    task: Task,
    state: dict[str, Any],
    manifest: dict[str, Any] | None,
    manifest_issues: list[str],
    routing: dict[str, Any],
    routing_path: Path,
    root: Path,
    queue_tasks: tuple[Task, ...],
    batch_cache: dict,
) -> list[str]:
    """Return failed closed reasons. An empty list proves current integration readiness."""
    entries = state.get("integration_evidence", {})
    entry = entries.get(task.id)
    if entry is None:
        return ["no integration evidence is recorded"]
    if not isinstance(entry, dict):
        return ["integration evidence entry is not an object"]
    if manifest is None or task.launch_manifest_path is None:
        return ["integration evidence has no task launch manifest"]
    if manifest_issues:
        return ["launch manifest is incomplete or differs from the approved route"]
    launch_path = entry.get("launch_manifest")
    if not isinstance(launch_path, str) or referenced_path(root, launch_path) != task.launch_manifest_path:
        return ["integration evidence is bound to another launch manifest"]
    reference = entry.get("snapshot")
    base = entry.get("base")
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        return ["integration evidence needs a snapshot path and checksum"]
    if not isinstance(base, str) or not base:
        return ["integration evidence needs its review base"]
    snapshot_path = referenced_path(root, reference["path"]) if isinstance(reference.get("path"), str) else None
    if snapshot_path is None or not snapshot_path.is_file():
        return ["integration snapshot is missing"]
    if not isinstance(reference.get("sha256"), str) or file_sha256(snapshot_path) != reference["sha256"]:
        return ["integration snapshot checksum changed"]
    try:
        import review_evidence

        checkpoint = entry.get("carry_forward")
        batch = entry.get("batch_review")
        if checkpoint is not None and batch is not None:
            return ["integration evidence cannot combine carry forward and batch review"]
        snapshot = (review_evidence.snapshot_record(snapshot_path) if checkpoint is not None or batch is not None
                    else review_evidence.current_snapshot(snapshot_path, base))
        if Path(snapshot["source"]["root"]).resolve() != root:
            return ["integration snapshot belongs to another source root"]
        if Path(snapshot["contract"]["path"]).resolve() != task.contract_path:
            return ["integration snapshot is bound to another task contract"]
        if snapshot["contract"]["sha256"] != review_evidence.contract_hash(task.contract_path):
            return ["task contract changed after integration review"]
        assessment = (review_evidence.assess_batch(batch, task.id, snapshot_path, base) if batch is not None else
                      review_evidence.assess_carry_forward(checkpoint, snapshot_path, base) if checkpoint is not None
                      else review_evidence.assess(snapshot_path, base))
        if assessment.get("status") != "ready":
            return ["integration review is not ready"]
        review_path = snapshot_path.parent / "review.json"
        review_sha256 = file_sha256(review_path)
        if not (
            ledger_reviewer_binding(
                task, state, routing_path, snapshot_path, reference["sha256"], review_path, review_sha256, root
            )
            or manifest_reviewer_binding(
                task, manifest, routing, snapshot_path, reference["sha256"], review_path, review_sha256, root
            )
        ):
            return ["integration review has no approved reviewer dispatch binding"]
        if batch is not None:
            key = (batch["path"], batch["sha256"], base)
            if key not in batch_cache:
                batch_cache[key] = batch_dispatch_reasons(task, assessment, queue_tasks, state, routing_path, root)
            if batch_cache[key]:
                return batch_cache[key]
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        return [f"integration evidence is invalid or stale: {error}"]
    return []


def manifest_has_terminal_failure(manifest: dict[str, Any] | None) -> str | None:
    if manifest is None:
        return None
    status = manifest.get("status")
    if status in TERMINAL_MANIFEST_STATUSES:
        return f"launch manifest status is {status}"
    if manifest.get("dry_run") is True or manifest.get("approval_preview") is True:
        return "launch manifest is only a dry run preview"
    return None


def classify_tasks(
    queue: Queue,
    state: dict[str, Any],
    routing: dict[str, dict[str, Any]],
    routing_path: Path,
    root: Path,
) -> dict[str, TaskState]:
    per_task_calls = calls_by_task(state)
    result = {}
    batch_cache = {}
    for task in queue.tasks:
        manifest, manifest_issues = load_launch_manifest(
            task, routing[task.id], routing_path, root, queue.isolation
        )
        calls = per_task_calls.get(task.id, [])
        failed_calls = [call for call in calls if call.get("status") == "failed"]
        pending_calls = [call for call in calls if call.get("status") == "pending"]
        unknown_calls = [
            call for call in calls if call.get("status") not in {"pending", "completed", "failed"}
        ]
        failure = manifest_has_terminal_failure(manifest)
        integration_reasons = integration_assessment(
            task, state, manifest, manifest_issues, routing[task.id], routing_path, root, queue.tasks, batch_cache
        )
        call_reasons = []
        if pending_calls:
            call_reasons.append("ledger has a pending route call")
        if unknown_calls:
            call_reasons.append("ledger has a route call with an unknown status")
        if failed_calls and integration_reasons:
            call_reasons.append("ledger has a failed route call whose source effects need integration evidence")
        if call_reasons:
            result[task.id] = TaskState(
                task, "active", call_reasons, manifest, manifest_issues, integration_reasons
            )
            continue
        if manifest_issues:
            result[task.id] = TaskState(task, "active", manifest_issues, manifest, manifest_issues, integration_reasons)
            continue
        if failure and "dry run" in failure:
            result[task.id] = TaskState(task, "active", [failure], manifest, manifest_issues, integration_reasons)
            continue
        if not integration_reasons:
            result[task.id] = TaskState(task, "integrated", [], manifest, manifest_issues, [])
            continue
        if manifest is not None:
            reasons = ["task has a launch manifest"]
            if failure:
                reasons.append(failure + "; source effects retain ownership until integration passes")
            result[task.id] = TaskState(task, "active", reasons, manifest, manifest_issues, integration_reasons)
            continue
        if calls:
            result[task.id] = TaskState(
                task, "active", ["ledger shows a started task without a launch manifest"], None, [], integration_reasons
            )
            continue
        if task.status == "ready-for-agent":
            result[task.id] = TaskState(task, "fresh", [], None, [], integration_reasons)
        elif task.status == "draft":
            result[task.id] = TaskState(task, "blocked", ["task contract status is draft"], None, [], integration_reasons)
        elif task.status == "blocked":
            result[task.id] = TaskState(task, "blocked", ["task contract status is blocked"], None, [], integration_reasons)
        else:
            result[task.id] = TaskState(
                task, "blocked", [f"task contract status is {task.status} without integration evidence"], None, [], integration_reasons
            )
    return result


def path_conflicts(left: str, right: str) -> bool:
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


def ownership_conflicts(left: Task, right: Task) -> tuple[tuple[str, ...], tuple[str, ...]]:
    def intersection(left_path: str, right_path: str) -> str:
        left_parts = PurePosixPath(left_path).parts
        right_parts = PurePosixPath(right_path).parts
        return left_path if len(left_parts) >= len(right_parts) else right_path

    paths = sorted({
        intersection(left_path, right_path)
        for left_path in left.write_paths
        for right_path in right.write_paths
        if path_conflicts(left_path, right_path)
    })
    surfaces = sorted(set(left.shared_surfaces) & set(right.shared_surfaces))
    return tuple(paths), tuple(surfaces)


def plan_covers_conflict(plan: MergePlan, paths: tuple[str, ...], surfaces: tuple[str, ...]) -> bool:
    def path_covered(path: str) -> bool:
        path_parts = PurePosixPath(path).parts
        return any(PurePosixPath(scope).parts == path_parts[:len(PurePosixPath(scope).parts)]
                   for scope in plan.write_paths)

    def surface_covered(surface: str) -> bool:
        return surface in plan.shared_surfaces

    return all(path_covered(path) for path in paths) and all(surface_covered(surface) for surface in surfaces)


def accepted_merge_plan(queue: Queue, left: Task, right: Task, paths: tuple[str, ...], surfaces: tuple[str, ...]) -> MergePlan | None:
    if not paths and not surfaces:
        return None
    for plan in queue.merge_plans:
        if {left.id, right.id} <= set(plan.tasks) and plan_covers_conflict(plan, paths, surfaces):
            return plan
    return None


def conflict_reason(left: Task, right: Task, paths: tuple[str, ...], surfaces: tuple[str, ...]) -> str:
    items = [*paths, *surfaces]
    return f"write ownership conflicts with {right.id}: {', '.join(items)}"


def required_integration(queue: Queue, states: dict[str, TaskState]) -> list[dict[str, Any]]:
    required = []
    for task_id in sorted(states, key=task_sort_key):
        state = states[task_id]
        if state.kind == "active" and state.integration_reasons:
            required.append({
                "task_id": task_id,
                "launch_manifest": str(state.task.launch_manifest_path) if state.task.launch_manifest_path else None,
                "reasons": state.integration_reasons,
            })
    for plan in queue.merge_plans:
        members = [states[task_id] for task_id in plan.tasks]
        if any(member.kind == "active" for member in members):
            required.append({
                "merge_plan": plan.id,
                "tasks": list(sorted(plan.tasks, key=task_sort_key)),
                "reasons": ["accepted shared ownership needs combined integration evidence for each affected task"],
            })
    return required


def _schedule(
    queue_path: str | Path,
    routing_plan_path: str | Path,
    ledger_path: str | Path,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Project deterministic ready tasks, blockers, and integration work."""
    resolved_root = root_path(root)
    queue = load_queue(queue_path, resolved_root)
    require_approved_prd(queue)
    routing_path = inside_root(resolved_root, str(routing_plan_path), "routing plan")
    routing = routes_for_queue(queue, routing_path, resolved_root)
    validate_approval_record(queue, routing_path, routing, resolved_root)
    state = load_ledger(ledger_path, routing_path, resolved_root)
    validate_ledger_calls(state, routing_path, resolved_root)
    validate_ledger_accounting(state)
    limits = state["call_ledger"]["limits"]
    attempts = state["attempts"]
    states = classify_tasks(queue, state, routing, routing_path, resolved_root)
    active = [item for item in states.values() if item.kind == "active"]
    active.sort(key=lambda item: task_sort_key(item.task.id))
    active_tasks = [item.task for item in active]
    ready = []
    blocked: list[dict[str, Any]] = []
    selected: list[Task] = []
    selected_reservations: dict[str, int] = {}
    for task in queue.tasks:
        task_state = states[task.id]
        if task_state.kind in {"integrated", "active"}:
            continue
        reasons = list(task_state.reasons)
        if task_state.kind == "fresh":
            if task.legacy and task.contract_path == queue.path:
                reasons.append("derive canonical task files before approval or dispatch")
            reasons.extend(readiness_gates(task))
            for blocker in task.blocked_by:
                blocker_state = states[blocker]
                if blocker_state.kind != "integrated":
                    reasons.append(f"blocker {blocker} lacks current integration evidence")
            conflicts = []
            for owner in [*active_tasks, *selected]:
                paths, surfaces = ownership_conflicts(task, owner)
                if not paths and not surfaces:
                    continue
                plan = accepted_merge_plan(queue, task, owner, paths, surfaces)
                if plan is None:
                    conflicts.append(conflict_reason(task, owner, paths, surfaces))
            reasons.extend(conflicts)
            if not reasons and len(active_tasks) + len(selected) >= queue.max_active:
                owners = [owner.id for owner in [*active_tasks, *selected]]
                reasons.append(f"approved concurrency cap {queue.max_active} is occupied by {', '.join(owners)}")
            if not reasons:
                reasons.extend(reservation_reasons(routing[task.id], limits, attempts, selected_reservations))
            if not reasons:
                selected.append(task)
                reserve_initial_routes(routing[task.id], selected_reservations)
                ready.append({
                    "id": task.id,
                    "manifest": str(task.contract_path),
                    "launch_manifest": str(task.launch_manifest_path) if task.launch_manifest_path else None,
                })
                continue
        blocked.append({"id": task.id, "reasons": sorted(set(reasons))})
    return {
        "schema_version": 1,
        "queue": {
            "id": queue.id,
            "path": str(queue.path),
            "configured_max_active": queue.configured_max_active,
            "max_active": queue.max_active,
            "isolation": queue.isolation,
            "legacy": queue.legacy,
        },
        "ready": ready,
        "active": [
            {"id": item.task.id, "reasons": item.reasons}
            for item in active
        ],
        "integrated": [
            task_id for task_id in sorted(states, key=task_sort_key) if states[task_id].kind == "integrated"
        ],
        "blocked": blocked,
        "required_integration": required_integration(queue, states),
    }



def schedule(queue_path, routing_plan_path, ledger_path, root=None):
    import review_evidence

    try:
        with review_evidence.validation_context():
            return _schedule(queue_path, routing_plan_path, ledger_path, root)
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise QueueError(str(error)) from error

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("approval-inputs", help="show current and prospective ready task input digests")
    preview.add_argument("--queue", required=True, help="canonical queue JSON or a Markdown queue index")
    preview.add_argument("--root", default=".", help="project root that owns every queue path")
    preview.add_argument("--routing-plan", help="draft routing plan for a prospective combined approval")
    schedule_parser = commands.add_parser("schedule", help="project ready tasks without writing queue state")
    schedule_parser.add_argument("--queue", required=True, help="canonical queue JSON or a Markdown queue index")
    schedule_parser.add_argument("--routing-plan", required=True, help="approved routing-plan.json")
    schedule_parser.add_argument("--ledger", required=True, help="existing feature run-state.json")
    schedule_parser.add_argument("--root", default=".", help="project root that owns every queue path")
    args = parser.parse_args(argv)
    try:
        if args.command == "approval-inputs":
            result = approval_inputs(args.queue, args.root, args.routing_plan)
        else:
            result = schedule(args.queue, args.routing_plan, args.ledger, args.root)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (QueueError, OSError, UnicodeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
