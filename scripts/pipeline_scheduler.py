#!/usr/bin/env python3
"""Run ship phases 3-6 over a slice queue — the deterministic half of the pipeline.

This is the scheduler, not the pipeline. It reimplements no phase: every phase is
a prose skill, executed by a headless CLI agent that this script spawns through
the repo's existing `*-runner` wrappers. The split is deliberate:

    this script owns   the ledger, attempt counters and ceilings, gate
                       persistence, side-effect keys, DAG readiness, the
                       concurrency cap, worktree lifecycle, brief writing,
                       envelope parsing, and subprocess lifetime
    the agent owns     all reasoning

That division is what `_shared/references/run-state-contract.md` means by "the
model never decides the retry", and what `handoff-contract.md` means by "hand off
the path, not the payload".

Phases 0-2 are not here. They need a human, so they stay in an interactive
session; this script starts at the design gate, after the approval gate has been
recorded.

Because the runner wrappers already speak `--prompt-file / --working-dir /
--allow-write / --json`, no CLI flags, ACP transport, or API key appear anywhere
below — the agent runs on its own subscription auth.

Usage:
    scripts/pipeline_scheduler.py <target-repo> --approved
    scripts/pipeline_scheduler.py <target-repo> --resume <run-id>
    scripts/pipeline_scheduler.py <target-repo> --slice T3 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

# The only legal values of `status`; a resume protocol branches on this set.
RUNNING = "running"
AWAITING_HUMAN = "awaiting_human"
COMPLETE = "complete"
FAILED = "failed"
CEILING_HIT = "ceiling_hit"
CANCELLED = "cancelled"

APPROVAL_GATE = "phase2_breakdown_approval"

# Seat -> the wrapper that runs it headless. Every wrapper takes the same flags
# (guarded by _shared/tests/test_runner_parity.py), so adding a seat is one line.
RUNNERS = {
    "opus": ("claude-runner/scripts/run_claude.py", ["--model", "opus"]),
    "sonnet": ("claude-runner/scripts/run_claude.py", ["--model", "sonnet"]),
    "codex": ("codex-runner/scripts/run_codex.py", []),
    "gemini": ("gemini-runner/scripts/run_gemini.py", []),
    "grok": ("grok-runner/scripts/run_grok.py", []),
    "kimi": ("kimi-runner/scripts/run_kimi.py", []),
    "glm": ("glm-runner/scripts/run_glm.py", []),
}

# (phase number, step slug, the skill the worker invokes, the runner role)
PHASES: tuple[tuple[int, str, str, str], ...] = (
    (3, "design-gate",
     "`coding-design-plan`, then `design-gate` with this slice's lens flags",
     "planner"),
    (4, "implement",
     "`implement-and-review` for this slice — it lifts the Slice Contract "
     "natively and never pushes",
     "implementer"),
    (5, "verify",
     "ordered and fail-fast: the acceptance contract, then "
     "`coding-review-simplify`, then `full-review`, then `browser-smoke` for "
     "web-facing changes or the harness run check otherwise",
     "codereviewer"),
    (6, "deliver",
     "commit, make unapplied findings durable per "
     "`ship/references/residual-findings.md`, then `open-pr`, then "
     "`session-handoff`",
     "implementer"),
)

MAX_ENVELOPE_RETRY = 1
MAX_EVIDENCE_RECOVERY = 1
DEFAULT_IN_FLIGHT = 3
DEFAULT_STEP_TIMEOUT = 3600


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:4]}"


class CeilingHit(Exception):
    """A bounded loop reached its ceiling. Never caught by the retry itself."""

    def __init__(self, loop: str, ceiling: int) -> None:
        super().__init__(f"{loop} reached its ceiling of {ceiling}")
        self.loop = loop
        self.ceiling = ceiling


# --------------------------------------------------------------------------- #
# T1 — the ledger
# --------------------------------------------------------------------------- #


class RunState:
    """The run-state contract as code.

    Every mutation writes through to disk immediately, because the guarantee the
    contract buys is that a process killed at any instant leaves a ledger a
    restart can act on. Writes are atomic (temp file plus `os.replace`) so a
    crash mid-write cannot leave a truncated file where the ledger should be.
    """

    def __init__(self, path: Path, data: dict[str, Any]) -> None:
        self.path = path
        self.data = data
        self._lock = threading.Lock()

    # -- construction ------------------------------------------------------- #

    @staticmethod
    def state_path(workspace: Path, run_id: str, skill: str = "ship") -> Path:
        return workspace / ".ai-workflow" / skill / run_id / "run-state.json"

    @classmethod
    def create(cls, workspace: Path, run_id: str, skill: str = "ship",
               ceilings: Optional[dict[str, Any]] = None,
               **extra: Any) -> "RunState":
        path = cls.state_path(workspace, run_id, skill)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = utc_now()
        state = cls(path, {
            "run_id": run_id,
            "skill": skill,
            "status": RUNNING,
            "phase": None,
            "started_at": now,
            "updated_at": now,
            "attempts": {},
            "ceilings": dict(ceilings or {}),
            "gates": [],
            "side_effects": [],
            "steps": [],
            **extra,
        })
        state._flush()
        return state

    @classmethod
    def load(cls, workspace: Path, run_id: str, skill: str = "ship") -> "RunState":
        path = cls.state_path(workspace, run_id, skill)
        return cls(path, json.loads(path.read_text(encoding="utf-8")))

    @classmethod
    def load_or_create(cls, workspace: Path, run_id: str, skill: str = "ship",
                       **kwargs: Any) -> "RunState":
        if cls.state_path(workspace, run_id, skill).is_file():
            return cls.load(workspace, run_id, skill)
        return cls.create(workspace, run_id, skill, **kwargs)

    # -- persistence -------------------------------------------------------- #

    def _flush(self) -> None:
        self.data["updated_at"] = utc_now()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    # -- attempts ----------------------------------------------------------- #

    def begin_attempt(self, loop: str, ceiling: int) -> int:
        """Increment before the attempt, never after.

        A crash mid-attempt still counts as an attempt; counting afterwards is
        what makes a crashing step retry forever.
        """
        with self._lock:
            used = int(self.data["attempts"].get(loop, 0))
            if used >= ceiling:
                raise CeilingHit(loop, ceiling)
            self.data["attempts"][loop] = used + 1
            self.data.setdefault("ceilings", {})[loop] = ceiling
            self._flush()
            return used + 1

    def attempts(self, loop: str) -> int:
        return int(self.data["attempts"].get(loop, 0))

    # -- gates -------------------------------------------------------------- #

    def has_gate(self, gate: str) -> bool:
        """A gate absent here was never granted, whatever the transcript says."""
        return any(entry.get("gate") == gate for entry in self.data["gates"])

    def record_gate(self, gate: str, decision: str = "approved") -> None:
        with self._lock:
            if not any(e.get("gate") == gate for e in self.data["gates"]):
                self.data["gates"].append(
                    {"gate": gate, "decision": decision, "decided_at": utc_now()})
            self.data["status"] = RUNNING
            self._flush()

    # -- side effects ------------------------------------------------------- #

    def claim_side_effect(self, key: str) -> bool:
        """Record the key, then act. Returns False when it was already claimed.

        A crash lands between the record and the effect either way; recording
        first means a replay skips the effect rather than duplicating it.
        """
        with self._lock:
            if any(e.get("key") == key for e in self.data["side_effects"]):
                return False
            self.data["side_effects"].append({"key": key, "done_at": utc_now()})
            self._flush()
            return True

    def side_effect_keys(self) -> list[str]:
        return [e.get("key") for e in self.data["side_effects"]]

    # -- steps -------------------------------------------------------------- #

    def record_step(self, step: str, result: str, artifact: Optional[str] = None,
                    brief: Optional[str] = None, report: Optional[str] = None,
                    **extra: Any) -> None:
        entry: dict[str, Any] = {"step": step, "result": result, "at": utc_now()}
        for key, value in (("artifact", artifact), ("brief", brief), ("report", report)):
            if value:
                entry[key] = value
        entry.update(extra)
        with self._lock:
            self.data["steps"].append(entry)  # append; never rewrite history
            self._flush()

    def step_result(self, step: str) -> Optional[str]:
        """The completion signal: a step present here with a non-failed result."""
        for entry in reversed(self.data["steps"]):
            if entry.get("step") == step:
                return entry.get("result")
        return None

    # -- coarse fields ------------------------------------------------------ #

    def set_phase(self, phase: Any) -> None:
        with self._lock:
            self.data["phase"] = phase
            self._flush()

    def set_status(self, status: str, **extra: Any) -> None:
        with self._lock:
            self.data["status"] = status
            self.data.update(extra)
            self._flush()

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def phase(self) -> Any:
        return self.data.get("phase")


# --------------------------------------------------------------------------- #
# T2 — the handoff
# --------------------------------------------------------------------------- #


def write_brief(unit_dir: Path, step: str, *, run_id: str, run_state: Path,
                goal: str, inputs: Iterable[str], constraints: Iterable[str],
                deliverable: str, verification: Iterable[str],
                escalation: str) -> Path:
    """Write the ten-field brief. Inputs are paths — never pasted payloads."""
    unit_dir.mkdir(parents=True, exist_ok=True)
    path = unit_dir / f"{step}.brief.md"
    report_path = unit_dir / f"{step}.report.md"

    def bullets(items: Iterable[str]) -> str:
        listed = [f"- {item}" for item in items]
        return "\n".join(listed) if listed else "- None"

    path.write_text(f"""# Brief — {step}

| Field | Value |
|---|---|
| `run_id` | `{run_id}` |
| `run_state` | `{run_state}` |
| `step` | `{step}` |

## Goal

{goal}

## Inputs

Read these; do not wait to be handed their contents.

{bullets(inputs)}

## Constraints and non-goals

{bullets(constraints)}

## Deliverable

{deliverable}

Write your report to `{report_path}` using the seven fixed sections from
`_shared/references/handoff-contract.md`, in order, present even when empty:
Verdict, What ran, Evidence, Decisions & assumptions, Findings not applied,
Inputs for the next step, Artifacts.

## Required verification

The output of these commands must appear verbatim under `## Evidence`. Claims
about output are not output.

{bullets(verification)}

## Escalation

{escalation}

## Output contract

Your final message must be this JSON object and nothing else — no prose before
it, no commentary after it:

```json
{{"step": "{step}",
 "status": "complete | failed | ceiling_hit | awaiting_human",
 "verdict": "the step's own vocabulary, e.g. pass | fail | proceed | revise",
 "report": "{report_path}",
 "artifacts": [],
 "next_inputs": [],
 "blockers": []}}
```
""", encoding="utf-8")
    return path


def parse_envelope(text: str) -> Optional[dict[str, Any]]:
    """Recover the envelope from an agent's final message.

    Agents wrap the object in prose or fences however they like, so scan for
    balanced top-level JSON objects and take the last one that looks like an
    envelope. A return this cannot parse is a step that did not report — not a
    step to interpret.
    """
    if not text:
        return None
    candidates: list[dict[str, Any]] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    try:
                        parsed = json.loads(text[start:index + 1])
                    except json.JSONDecodeError:
                        parsed = None
                    if isinstance(parsed, dict) and "status" in parsed:
                        candidates.append(parsed)
    return candidates[-1] if candidates else None


def has_evidence(report_path: Path) -> bool:
    """The evidence gate, made machine-checkable.

    A model cannot be trusted to grade its own diligence, so the deterministic
    stand-in is the report's own `## Evidence` section: it must exist and carry
    something beyond its heading.
    """
    try:
        body = report_path.read_text(encoding="utf-8")
    except OSError:
        return False
    match = re.search(r"^##\s+Evidence\s*$(.*?)(?=^##\s|\Z)",
                      body, re.MULTILINE | re.DOTALL)
    return bool(match and match.group(1).strip())


# --------------------------------------------------------------------------- #
# T3 — dispatch
# --------------------------------------------------------------------------- #


def runner_argv(seat: str, brief: Path, cwd: Path, role: str, timeout: int,
                out_file: Path) -> list[str]:
    script, seat_args = RUNNERS[seat]
    return [
        sys.executable, str(REPO_ROOT / script),
        "--prompt-file", str(brief),
        "--working-dir", str(cwd),
        "--allow-write",
        "--role", role,
        "--timeout", str(timeout),
        "--json",
        "--output-file", str(out_file),
        *seat_args,
    ]


def dispatch(seat: str, brief: Path, cwd: Path, role: str, timeout: int,
             out_file: Path) -> tuple[bool, str]:
    """Run one step on one seat. Returns (ok, the agent's final message)."""
    if seat not in RUNNERS:
        return False, f"seat_unavailable: no runner registered for {seat!r}"
    argv = runner_argv(seat, brief, cwd, role, timeout, out_file)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True,
            timeout=timeout + 60, cwd=str(cwd), stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, f"timeout: {seat} exceeded {timeout}s on {brief.name}"
    except OSError as exc:
        return False, f"seat_unavailable: {seat} could not be launched ({exc})"

    payload: dict[str, Any] = {}
    try:
        payload = json.loads(out_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    message = (payload.get("agent_message") or payload.get("stdout")
               or completed.stdout or completed.stderr or "")
    ok = bool(payload.get("success")) if payload else completed.returncode == 0
    return ok, message


# --------------------------------------------------------------------------- #
# T5 — the slice queue
# --------------------------------------------------------------------------- #


TASK_HEADING = re.compile(r"^#{2,3}\s+(T\d+)[.:]?\s*(.*)$", re.MULTILINE)
STATUS_LINE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?Status(?:\*\*)?\s*:\s*"
                         r"([A-Za-z-]+)", re.MULTILINE | re.IGNORECASE)
BLOCKED_HEADING = re.compile(r"^#{2,4}\s*Blocked by\s*$(.*?)(?=^#{2,4}\s|\Z)",
                             re.MULTILINE | re.DOTALL | re.IGNORECASE)
BLOCKED_INLINE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?Blocked by(?:\*\*)?\s*:\s*(.+)$",
                            re.MULTILINE | re.IGNORECASE)
ACCEPTANCE_HEADING = re.compile(
    r"^#{2,4}\s*Acceptance(?:\s+contract)?\s*$(.*?)(?=^#{2,4}\s|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE)
TID = re.compile(r"\bT\d+\b")
COMMAND_LINE = re.compile(r"`([^`]+)`")


class Slice:
    def __init__(self, slice_id: str, title: str, body: str) -> None:
        self.id = slice_id
        self.title = title.strip() or slice_id
        self.body = body
        self.status = self._status()
        self.blocked_by = self._blocked_by()
        self.acceptance = self._acceptance()

    def _status(self) -> str:
        match = STATUS_LINE.search(self.body)
        return match.group(1).lower() if match else "todo"

    def _blocked_by(self) -> list[str]:
        chunk = ""
        heading = BLOCKED_HEADING.search(self.body)
        if heading:
            chunk = heading.group(1)
        else:
            inline = BLOCKED_INLINE.search(self.body)
            if inline:
                chunk = inline.group(1)
        if re.search(r"\bnone\b", chunk, re.IGNORECASE):
            return []
        return [tid for tid in TID.findall(chunk) if tid != self.id]

    def _acceptance(self) -> list[str]:
        match = ACCEPTANCE_HEADING.search(self.body)
        if not match:
            return []
        return [c.strip() for c in COMMAND_LINE.findall(match.group(1)) if c.strip()]

    def __repr__(self) -> str:
        return f"<Slice {self.id} status={self.status} blocked_by={self.blocked_by}>"


def parse_tasks(text: str) -> list[Slice]:
    """Parse a to-tasks work queue.

    Task boundaries are only `## T<N>` headings, so a `## Blocked by` subsection
    inside a task stays part of that task rather than starting a new one.
    """
    matches = list(TASK_HEADING.finditer(text))
    slices = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        slices.append(Slice(match.group(1), match.group(2), text[match.end():end]))
    return slices


def ready_slices(slices: list[Slice], done: set[str]) -> list[Slice]:
    """Unblocked, not-yet-done slices. A slice with incomplete blockers never
    dispatches — implement-feature's rule, enforced here rather than trusted."""
    return [s for s in slices
            if s.id not in done
            and s.status not in ("done", "blocked")
            and all(dep in done for dep in s.blocked_by)]


# --------------------------------------------------------------------------- #
# git helpers
# --------------------------------------------------------------------------- #


def git(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(workspace), check=check,
                          capture_output=True, text=True)


def has_remote(workspace: Path) -> bool:
    try:
        return bool(git(workspace, "remote").stdout.strip())
    except (subprocess.CalledProcessError, OSError):
        return False


def is_git_repo(workspace: Path) -> bool:
    try:
        return git(workspace, "rev-parse", "--git-dir").returncode == 0
    except (subprocess.CalledProcessError, OSError):
        return False


def add_worktree(workspace: Path, path: Path, branch: str, base: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = git(workspace, "rev-parse", "--verify", branch, check=False)
    if existing.returncode == 0:
        git(workspace, "worktree", "add", str(path), branch)
    else:
        git(workspace, "worktree", "add", str(path), "-b", branch, base)


# --------------------------------------------------------------------------- #
# T4 — the phase sequencer
# --------------------------------------------------------------------------- #


class SliceRunner:
    """Phases 3-6 for one slice, in one worktree, against one ledger."""

    def __init__(self, scheduler: "Scheduler", slice_: Slice, cwd: Path,
                 state: RunState) -> None:
        self.scheduler = scheduler
        self.slice = slice_
        self.cwd = cwd
        self.state = state
        self.unit_dir = state.path.parent

    def run(self) -> str:
        for number, step_slug, skill, role in PHASES:
            step = f"{number:02d}-{step_slug}"
            if self.state.step_result(step) in ("ok", "skipped"):
                continue  # the report is the completion signal
            self.state.set_phase(number)
            try:
                result = self._run_step(step, number, skill, role)
            except CeilingHit as exc:
                self.state.record_step(step, "ceiling_hit", **{"ceiling": exc.loop})
                self.state.set_status(CEILING_HIT, blocked_reason=str(exc))
                return CEILING_HIT
            if result != "ok":
                self.state.set_status(
                    FAILED, blocked_reason=f"{step} returned {result}")
                return FAILED
        self.state.set_status(COMPLETE)
        return COMPLETE

    # -- one step ----------------------------------------------------------- #

    def _run_step(self, step: str, number: int, skill: str, role: str) -> str:
        brief = self._write_brief(step, number, skill)
        report = self.unit_dir / f"{step}.report.md"
        envelope = self._dispatch_with_envelope_retry(step, brief, role)

        if envelope is None:
            self.state.record_step(step, "failed", brief=str(brief),
                                   note="no parseable envelope")
            return "failed"

        if number == 4 and not has_evidence(report):
            envelope = self._recover_evidence(step, brief, role, report, envelope)
            if envelope is None:
                self.state.record_step(step, "failed", brief=str(brief),
                                       report=str(report),
                                       note="no verification evidence")
                return "failed"

        status = str(envelope.get("status", "")).lower()
        result = "ok" if status == COMPLETE else (status or "failed")
        self.state.record_step(
            step, result, brief=str(brief),
            report=str(envelope.get("report") or report),
            verdict=envelope.get("verdict"),
            blockers=envelope.get("blockers") or [])
        return result

    def _dispatch_with_envelope_retry(self, step: str, brief: Path,
                                      role: str) -> Optional[dict[str, Any]]:
        """A worker returning prose is re-prompted once, then recorded failed."""
        loop = f"{step}:envelope_retry"
        for attempt in range(MAX_ENVELOPE_RETRY + 1):
            if attempt:
                try:
                    self.state.begin_attempt(loop, MAX_ENVELOPE_RETRY)
                except CeilingHit:
                    return None
            out_file = self.unit_dir / f"{step}.seat-{attempt}.json"
            ok, message = dispatch(
                self.scheduler.seat, brief, self.cwd, role,
                self.scheduler.timeout, out_file)
            envelope = parse_envelope(message)
            if envelope is not None:
                return envelope
            if not ok and "seat_unavailable" in message:
                return None  # never silently substitute a seat
        return None

    def _recover_evidence(self, step: str, brief: Path, role: str, report: Path,
                          envelope: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Re-invoke once to reconcile evidence — never to reimplement.

        The counter is incremented here, outside the model, so a run that
        crashes during recovery does not award itself a fresh attempt.
        """
        try:
            self.state.begin_attempt(f"{step}:evidence_recovery",
                                     MAX_EVIDENCE_RECOVERY)
        except CeilingHit:
            return None
        recovery = brief.with_name(f"{step}.recovery.brief.md")
        recovery.write_text(
            brief.read_text(encoding="utf-8")
            + "\n\n## Recovery pass\n\nThe work is already implemented. Do not "
              "reimplement it and do not change its scope. Reconcile the "
              "verification evidence from what is already on disk: state which "
              "existing tests you inspected, which tests you added or ran, and "
              "what their output proves. Then rewrite the report's `## Evidence` "
              "section with that command output verbatim.\n",
            encoding="utf-8")
        out_file = self.unit_dir / f"{step}.recovery.json"
        _, message = dispatch(self.scheduler.seat, recovery, self.cwd, role,
                              self.scheduler.timeout, out_file)
        recovered = parse_envelope(message)
        if recovered is None or not has_evidence(report):
            return None
        return recovered

    # -- the brief ---------------------------------------------------------- #

    def _write_brief(self, step: str, number: int, skill: str) -> Path:
        prior = [f"`{p.name}` — the {p.stem.split('.')[0]} report"
                 for p in sorted(self.unit_dir.glob("*.report.md"))]
        constraints = [
            f"Stay inside this slice: {self.slice.id}. Do not start, finish, or "
            "refactor another slice's work.",
            "The phase-2 breakdown is already approved. Do not re-open it and do "
            "not ask the user anything.",
        ]
        if number != 6:
            constraints.append("Do not commit, push, or open a pull request — "
                               "phase 6 owns delivery.")
        elif self.scheduler.local_only:
            constraints.append("Local-only run: this repo has no git remote. "
                               "Make the commits, but skip every push and PR "
                               "attempt. A missing remote is a terminal state, "
                               "not an error to retry.")
        return write_brief(
            self.unit_dir, step,
            run_id=self.state.data["run_id"],
            run_state=self.state.path,
            goal=f"Run pipeline phase {number} for slice {self.slice.id} "
                 f"({self.slice.title}) by invoking {skill}.",
            inputs=[f"`{self.scheduler.tasks_path}` § {self.slice.id} — the "
                    f"Slice Contract: acceptance commands, gate flags, "
                    f"rollback note, and expected review focus",
                    *prior],
            constraints=constraints,
            deliverable=f"Invoke {skill}.",
            verification=self.slice.acceptance
            or ["The acceptance commands named in this slice's Slice Contract."],
            escalation="Run `models-consensus` in poll mode with `--auto`. Never "
                       "ask the user. Only a destructive or irreversible "
                       "operation is a hard stop — return `awaiting_human` for "
                       "that and nothing else.",
        )


# --------------------------------------------------------------------------- #
# the scheduler
# --------------------------------------------------------------------------- #


class Scheduler:
    def __init__(self, workspace: Path, run_id: str, slices: list[Slice],
                 *, seat: str, max_in_flight: int, timeout: int,
                 tasks_path: Path, dry_run: bool = False) -> None:
        self.workspace = workspace
        self.run_id = run_id
        self.slices = slices
        self.seat = seat
        self.max_in_flight = max_in_flight
        self.timeout = timeout
        self.tasks_path = tasks_path
        self.dry_run = dry_run
        self.local_only = not has_remote(workspace)
        self.git_ok = is_git_repo(workspace)
        self.integration_head = "HEAD"
        self._merge_lock = threading.Lock()
        self.state = RunState.load_or_create(
            workspace, run_id, "ship",
            ceilings={"max_in_flight": max_in_flight},
            queue=[s.id for s in slices],
            local_only=self.local_only)

    # -- worktrees ---------------------------------------------------------- #

    def _slice_cwd(self, slice_: Slice) -> Path:
        if not self.git_ok:
            return self.workspace  # degrade: sequential, in the working tree
        path = self.workspace / ".ai-workflow" / "worktrees" / \
            f"{self.run_id}-{slice_.id}"
        add_worktree(self.workspace, path,
                     f"pipeline/{self.run_id}/{slice_.id}", self.integration_head)
        return path

    def _integrate(self, slice_: Slice) -> None:
        """Merge a finished slice, then advance the head the next slice builds on."""
        if not self.git_ok:
            return
        key = f"merge:{slice_.id}"
        with self._merge_lock:
            if not self.state.claim_side_effect(key):
                return
            branch = f"pipeline/{self.run_id}/{slice_.id}"
            merged = git(self.workspace, "merge", "--no-ff", branch, "-m",
                         f"Integrate {slice_.id}: {slice_.title}", check=False)
            if merged.returncode != 0:
                git(self.workspace, "merge", "--abort", check=False)
                self.state.record_step(f"integrate:{slice_.id}", "conflict",
                                       note=merged.stderr.strip()[:400])
                return
            self.integration_head = git(
                self.workspace, "rev-parse", "HEAD").stdout.strip()
            self.state.record_step(f"integrate:{slice_.id}", "ok",
                                   artifact=self.integration_head)

    # -- the loop ----------------------------------------------------------- #

    def run(self) -> dict[str, str]:
        if not self.state.has_gate(APPROVAL_GATE):
            self.state.set_status(AWAITING_HUMAN)
            raise SystemExit(
                "The phase-2 approval gate is not recorded in this run state.\n"
                "It is the last human gate, so this run stops rather than "
                "assuming it.\nRe-run with --approved once the breakdown is "
                "approved.")

        done = {s.id for s in self.slices if s.status == "done"}
        for slice_ in self.slices:  # a resumed run never rebuilds a finished slice
            if self._finished_earlier(slice_):
                done.add(slice_.id)

        outcomes: dict[str, str] = {sid: COMPLETE for sid in done}
        if self.git_ok:
            self.integration_head = git(
                self.workspace, "rev-parse", "HEAD").stdout.strip()

        while True:
            ready = [s for s in ready_slices(self.slices, done)
                     if s.id not in outcomes]
            if not ready:
                break
            batch = ready[:self.max_in_flight]
            with ThreadPoolExecutor(max_workers=self.max_in_flight) as pool:
                results = list(pool.map(self._run_slice, batch))
            progressed = False
            for slice_, outcome in zip(batch, results):
                outcomes[slice_.id] = outcome
                if outcome == "dry-run":
                    # Satisfy dependents so the whole schedule prints; a dry run
                    # that stopped at the first blocker would show nothing.
                    done.add(slice_.id)
                    progressed = True
                elif outcome == COMPLETE:
                    done.add(slice_.id)
                    self._integrate(slice_)
                    progressed = True
            if not progressed:
                break  # every slice in flight failed; dependents stay blocked

        for slice_ in self.slices:
            outcomes.setdefault(slice_.id, "blocked")
        if not self.dry_run:
            self.state.set_status(
                COMPLETE if all(v == COMPLETE for v in outcomes.values())
                else FAILED,
                outcomes=outcomes)
        return outcomes

    def _finished_earlier(self, slice_: Slice) -> bool:
        """Read-only: asking whether a slice is done must not create its ledger."""
        path = RunState.state_path(self.workspace, f"{self.run_id}-{slice_.id}")
        if not path.is_file():
            return False
        try:
            return json.loads(path.read_text(encoding="utf-8"))["status"] == COMPLETE
        except (OSError, json.JSONDecodeError, KeyError):
            return False

    def _slice_state(self, slice_: Slice) -> RunState:
        # A sibling of the feature state, not a child, so the board's
        # .ai-workflow/*/*/run-state.json glob still finds it.
        return RunState.load_or_create(
            self.workspace, f"{self.run_id}-{slice_.id}", "ship",
            ceilings={"max_evidence_recovery": MAX_EVIDENCE_RECOVERY},
            slice_id=slice_.id, title=slice_.title)

    def _run_slice(self, slice_: Slice) -> str:
        if self.dry_run:
            # Touch no ledger: a dry run that created slice state would leave
            # phantom `running` cards on the board with nothing behind them.
            return "dry-run"
        state = self._slice_state(slice_)
        state.record_gate(APPROVAL_GATE)  # inherited from the feature gate
        if state.status == COMPLETE:
            return COMPLETE
        cwd = self._slice_cwd(slice_)
        state.set_status(RUNNING, worktree=str(cwd))
        return SliceRunner(self, slice_, cwd, state).run()


# --------------------------------------------------------------------------- #
# T6 — the command line
# --------------------------------------------------------------------------- #


def find_tasks(workspace: Path, explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).resolve()
    for name in ("TASKS.md", "tasks.md", ".codex_workflow/tasks/tasks.md"):
        candidate = workspace / name
        if candidate.is_file():
            return candidate
    raise SystemExit(
        f"No work queue found under {workspace}. Run the `to-tasks` phase first, "
        f"or pass --tasks <path>.")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workspace", help="target repo the agents work in")
    parser.add_argument("--tasks", help="work queue (default: <workspace>/TASKS.md)")
    parser.add_argument("--run-id", help="run id to create or resume")
    parser.add_argument("--resume", metavar="RUN_ID",
                        help="resume a run; alias for --run-id")
    parser.add_argument("--slice", action="append", dest="slices", metavar="T_ID",
                        help="limit the run to these slices (repeatable)")
    parser.add_argument("--seat", default="opus", choices=sorted(RUNNERS),
                        help="which seat runs the phases (default: opus)")
    parser.add_argument("--max-in-flight", type=int, default=DEFAULT_IN_FLIGHT,
                        help=f"concurrency cap (default: {DEFAULT_IN_FLIGHT})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_STEP_TIMEOUT,
                        help=f"per-step seconds (default: {DEFAULT_STEP_TIMEOUT})")
    parser.add_argument("--approved", action="store_true",
                        help="record the phase-2 approval gate for a new run")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the schedule without dispatching any agent")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"error: {workspace} is not a directory", file=sys.stderr)
        return 2

    tasks_path = find_tasks(workspace, args.tasks)
    slices = parse_tasks(tasks_path.read_text(encoding="utf-8"))
    if args.slices:
        wanted = set(args.slices)
        slices = [s for s in slices if s.id in wanted]
    if not slices:
        print(f"error: no slices parsed from {tasks_path}", file=sys.stderr)
        return 2

    run_id = args.resume or args.run_id or new_run_id()
    scheduler = Scheduler(workspace, run_id, slices, seat=args.seat,
                          max_in_flight=args.max_in_flight, timeout=args.timeout,
                          tasks_path=tasks_path, dry_run=args.dry_run)
    if args.approved:
        scheduler.state.record_gate(APPROVAL_GATE)

    print(f"run {run_id}  |  {len(slices)} slice(s)  |  seat {args.seat}  |  "
          f"cap {args.max_in_flight}"
          f"{'  |  local-only' if scheduler.local_only else ''}")
    for slice_ in slices:
        deps = ", ".join(slice_.blocked_by) or "none"
        print(f"  {slice_.id:<5} {slice_.title[:52]:<52} blocked_by: {deps}")

    outcomes = scheduler.run()
    print("\nresult:")
    for slice_id, outcome in outcomes.items():
        print(f"  {slice_id:<5} {outcome}")
    print(f"\nledger: {scheduler.state.path}")
    print(f"board:  python3 pipeline-board/serve.py {workspace}")
    return 0 if all(v in (COMPLETE, "dry-run") for v in outcomes.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
