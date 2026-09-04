---
name: implement-tasks
description: Build every task in an approved task queue and deliver the result as a PR — step 4 of the workflow (interview-me → to-prd → to-tasks → implement-tasks). Given the slices written by to-tasks (or a plan to decompose through it), execute the dependency DAG by running implement-and-review per task in parallel isolated worktrees, integrate in dependency order, run one feature-wide full-review on the seams, make unapplied review findings durable, and open the PR with acceptance evidence and the decision log. Autonomous after the task approval — contested decisions go to models-consensus, never to the user, except for destructive or irreversible operations. Use when the user says implement the tasks, build the task queue, run the autonomous phase, build and deliver this feature, or wants everything after the approved plan built and shipped. For a single scoped task call implement-and-review directly; models-consensus deliberates only and produces no code.
disable-model-invocation: true
---

# Implement Tasks

The fourth and last step of the workflow. Steps 1–3 (`interview-me`, `to-prd`, `to-tasks`) collect every human decision and write it to disk; this skill turns the approved task queue into an integrated, reviewed, delivered change without asking anything further. You are a **thin conductor** (the main agent, the Opus seat — model ids live only in `shared/references/model-roster.md`): you own scheduling, integration, the feature-wide review, and delivery. Per-task building — the FE/BE split, TDD, cross-model review, self-simplify, and the per-task `full-review` gate — is `implement-and-review`'s job. **Call it; don't reimplement it.**

Pipeline: **task queue → one fresh worker per task running `implement-and-review` (parallel where independent) → integrate in dependency order → feature-wide `full-review` on the seams → residual findings made durable → `open-pr`.**

Two rules from `shared/references/handoff-contract.md` and `shared/references/run-state-contract.md` govern everything below: **hand off the path, not the payload** (what crosses between you and a task build is a file path plus a short envelope, never a pasted report), and progress lives in **the ledger, not the transcript** (a run that crosses a compaction or a restart resumes from the run state, not from memory). Scheduling and integration commands, plus the worker-thread lifecycle (goal, naming, archiving): [references/feature-orchestration.md](references/feature-orchestration.md). Residual-findings durability: [references/residual-findings.md](references/residual-findings.md).

## Hard Rules

1. **The task queue is the input.** Slices come from `to-tasks` (one file per slice under `.ai-workflow/work/<feature-slug>/tasks/`, each with an acceptance contract, gate flags, `blocked_by`, and HITL/AFK class). A bare plan is decomposed through `to-tasks` first; a genuinely single task skips the DAG and goes straight to `implement-and-review`.
2. **One fresh worker per task, running `implement-and-review`.** Every task gets its own newly created worker context — a native subagent, or on the Codex / ChatGPT desktop app a newly created thread — that runs `implement-and-review` for exactly that task and nothing else. Hand it the task file path, a per-task `--slice` namespace, and the current integration head as `--base`; it lifts the Slice Contract itself. The orchestrator never builds a task inline and never reuses one worker for a second task (see [Worker threads](#worker-threads)).
3. **Every worker starts with a checkable goal.** The first thing a worker receives is a `/goal` whose done-condition can be verified from disk and the shell — envelope written, acceptance commands green, report present with evidence — so the worker keeps working until the goal holds or a ceiling is hit, never until it merely feels finished.
4. **Nothing asks the user after the approval.** The `to-tasks` approval (or this skill's Phase 0 approval) is the last human gate; record it in the run state's `gates`. Afterwards a contested or irreversible decision follows the [escalation ladder](#escalation-ladder-replaces-mid-flight-questions).
5. **Integrate in dependency order.** A task must pass its acceptance contract before its dependents start.
6. **`full-review` gates final code.** It runs per task inside `implement-and-review` and once more feature-wide on the seams. No mutating pass may follow a `full-review` unreviewed; a fix after it re-runs the review (or its `quick_mode`).
7. **Evidence or no delivery.** A task reported `built` without coherent verification evidence gets exactly one recovery re-invocation; still no evidence → the task is hard-blocked, never delivered (see [Evidence gate](#evidence-gate)).
8. **Residual findings become durable before delivery.** Review findings not applied are filed and recorded per `references/residual-findings.md` — never tracked as a PR-body ledger.
9. **Local-only mode.** Run `git remote` once at the start. No remote → make every commit the phases call for, but skip every push, PR create/edit, and CI attempt — zero retries. A missing remote is a terminal state, not an error; in local-only mode do not invoke `open-pr`.
10. **Bounded + escalate.** A task whose `implement-and-review` hits its 3-cycle cap is escalated; it blocks only its dependents.
11. **Never fabricate a seat; degrade** per [Degrade Gracefully](#degrade-gracefully).

## Preflight

1. **Host, git, remote.** Worktrees (and thus parallel tasks) need git; no git → sequential fallback. Run `git remote` once and record `local_only: true|false` in the run state.
2. **Seats.** Shared probe: `python3 .agents/skills/shared/scripts/discover_runners.py probe --native-agent yes --seat codex --seat opus --seat kimi --format json`. Each task's `implement-and-review` needs the default Codex seat and a native or runner-backed Opus seat; Kimi is the first fallback reviewer. Mark missing seats and degrade.
3. **Verification commands.** Detect the project's feature-wide test/build commands; the slices' acceptance commands must exist in the repo.
4. **Concurrency cap.** Default **3 tasks in flight**; lower it when seats or cost are tight.
5. **Base & artifacts.** Record `HEAD` as the feature `<base>`; create the feature integration branch; keep the run state and report under `.ai-workflow/impl-review/<session_id>/`.
6. **Orchestrator thread identity.** This thread is the conductor for the whole run; make that visible in the host UI before any worker exists. Name it `ORCHESTRATOR · implement-tasks · <feature-slug>` and pin it. On the Codex / ChatGPT app use the thread's rename and pin controls; where the host exposes no such control to the agent, put the one-line request ("pin this thread and name it …") in the Phase 0 approval message so it rides the existing human gate instead of adding one. Record the name in the run state (`threads.orchestrator`).
7. **Engine routing.** An explicit "implement with X" directive, or `work_engine_preferences` in the local config (`shared/references/local-config.md`), selects the per-stage engine; sanitize the directive out of anything a task build reads as product content.

## Phase 0 — Intake (gate)

1. **Intake.** Sources, in order of preference: an existing `.ai-workflow/work/<feature-slug>/tasks/` queue; a plan or spec the user gives (decompose it with `to-tasks`); or a `models-consensus` poll-mode report passed as `--from-consensus <path>` — take its _Consensus answer_ as the plan and resolve its _Open caveats_ first. With a consensus report, frame the council blind (the raw request, never your interpretation), thread one session id through both runs, and stop here if the answer is a decision rather than work to build.
2. **Present** the task list (titles, deps, acceptance, gates, HITL/AFK) and the verification commands. **Get approval before any code is written** unless the queue already carries the `to-tasks` approval or `--auto` is set. Never `--auto` a HITL task.

## Phase 1 — Schedule & Build the DAG

Build the dependency graph from `blocked_by`. Then:

- Schedule **HITL** tasks first and attended; run **AFK** tasks unattended.
- Run all currently-unblocked tasks **concurrently, up to the cap**, each in **its own fresh worker** that runs **`implement-and-review`** with the task path, `--slice <T>`, and `--base` = the current integration head. Open the worker, send its `/goal`, then its brief — in that order (see [Worker threads](#worker-threads)). Commands: [references/feature-orchestration.md](references/feature-orchestration.md).
- As each task's build passes **its acceptance contract**, integrate it in dependency order, recompute readiness, and pull the next ready tasks into flight.
- Continue until every task is done, blocked, or escalated. Never silently drop a task.

### Worker threads

One task, one worker, one goal. The worker is a **new** context every time — never the orchestrator itself, never a worker recycled from a finished task, never a fork of the orchestrator's context (`shared/references/handoff-contract.md`: a clean worker seeded by a compact brief beats a fork carrying everything already spent).

**Lifecycle, in order:**

1. **Create** the worker. Native `Agent` tool → one subagent per task. Codex / ChatGPT desktop app → a **newly created thread** per task, named `<T> · <feature-slug> · implement-and-review`. No host worker tool → fall back per [Degrade Gracefully](#degrade-gracefully) and say so; never imply a thread exists that nobody opened.
2. **Send the `/goal` first.** The goal is a done-condition, not a task description, and every clause must be checkable without reading the transcript:
   - the `implement-and-review` envelope for `<T>` exists at its report path with `status: complete` (or a recorded `failed` / `ceiling_hit`);
   - the task's acceptance commands (named verbatim) exit green on the task's branch;
   - the report's `Evidence` section is non-empty and lists the tests inspected, added, and run.
   The goal closes with the standing instruction: keep working until every clause holds or a ceiling is hit, then return the envelope and stop. Template in [references/feature-orchestration.md](references/feature-orchestration.md#worker-thread-lifecycle). A worker whose goal cannot be phrased as checks is a task that `to-tasks` left under-specified — route it back, do not launch it.
3. **Send the brief** (handoff-contract shape: paths only) as the second message. The goal says when the worker is done; the brief says what to do.
4. **Wait on the envelope**, not the transcript. Poll the report path or the launcher's `poll --wait`; read the envelope only.
5. **Close** the worker as soon as its envelope is recorded in the run state. On the Codex / ChatGPT app, **archive the thread in the UI** (`codex archive "<thread name>"` when the UI is not reachable from the agent); a native subagent simply ends. Write `side_effects` key `archive:<T>` before archiving so a resumed run does not look for a thread that is already gone. An `escalated` or `failed` worker is archived too — its report is the durable artifact, the thread is not.

**The orchestrator stays pinned and named.** Only the conductor thread carries the `ORCHESTRATOR` name and the pin; worker threads are transient and never pinned. If a resumed run finds the orchestrator thread unnamed, restore the name before scheduling anything.

**Registry.** Every worker gets a `threads.workers[<T>]` entry in the run state: host (`claude-code` / `codex-app` / `cmux`), thread or agent id, thread name, the goal text, `opened_at`, and `closed_at` once archived. This is what lets a resumed run tell an open worker from a finished one.

### Evidence gate

Every task envelope must carry its verification evidence: which existing tests were inspected, which were added or run, and what they proved (`implement-and-review` writes this in its report's _Evidence_ section). A task that reports a behavior change without it is re-invoked **exactly once** in recovery mode — same task, same scope, reconcile the evidence from the already-implemented work without reimplementing. "Exactly once" is `attempts.evidence_recovery` against a ceiling of 1, incremented in the run state _before_ the re-invocation — the model never decides the retry. A second return without evidence hard-blocks the task.

### Run state

Follow `shared/references/run-state-contract.md`; only the keys specific to this skill are stated here:

- **`ceilings.max_in_flight`** — the concurrency cap. Count what is actually in flight.
- **`gates.task_approval`** — the last human gate. A resumed run that cannot find it stops and asks; one that finds it treats it as decided and never re-asks.
- **`side_effects`** keys are written _before_ the effect and skipped when already present: `merge:<task-id>`, `archive:<task-id>`, `commit:<task-id>`, `pr:<branch>`, `ticket:<finding-id>`, `record:<sha>`. This is what stops a resumed run from merging twice or filing every residual ticket twice.
- **`threads`** — `threads.orchestrator` (the pinned conductor thread's name and id) and `threads.workers[<T>]` per task as described in [Worker threads](#worker-threads). Closing a worker writes `side_effects` key `archive:<T>` first, then archives.
- **The integration head is the resume anchor.** `steps` are keyed by stable T-ID; a task in `steps` is done. On resume, re-read the integration head, recompute readiness from the ledger, and schedule only what is left.
- **Three exits per task:** `complete`, `failed` (hard-block or exhausted ladder), or `ceiling_hit`. A blocked task is a recorded exit, not a silent skip.

## Phase 2 — Feature-wide Review

After all tasks integrate, run **`full-review`** across the whole feature (diff vs `<base>`), focused on **cross-task seams** and what the per-task reviews could not see; `security_focus=true` if any task was `security: deep`. Apply findings through the owning task's implementer or a scoped fix, re-run the review on what changed, and re-verify the full suite **green**. Every finding _not_ applied goes to the residual list for Phase 3.

## Phase 3 — Deliver

1. **Commit** the integrated feature branch (key `commit:<task-id>` per task, or one feature commit when the tasks were squashed by design).
2. **Residual findings.** Follow [references/residual-findings.md](references/residual-findings.md): file tickets through the detected sink (probed once per run), always commit the `docs/residual-review-findings/<branch-or-head-sha>.md` record, back-fill the PR URL best-effort.
3. **Open the PR** with `open-pr` (skipped in local-only mode). PR composition is `open-pr`'s job; this skill adds the sections the workflow requires: **acceptance evidence** (commands run, output), **design-gate and review verdicts** per task, the **decision log** with every assumption the escalation ladder recorded, and **remaining risks**. Report outcomes faithfully — a failed or skipped check is stated, never smoothed over.
4. **Continuity.** When the run solved a non-obvious problem, invoke `capture-learning` in headless mode; when the run outgrew the session, store a `session-handoff` note. The human merges; `resolve-pr-feedback` closes the loop when review comments arrive.

## Escalation ladder (replaces mid-flight questions)

When a task build or the seam review hits a contested or irreversible decision:

1. Run `models-consensus` in poll mode with `--auto` (budget preset for routine escalations). It deliberates only; it never starts implementation.
2. Still unresolved: take the most reversible default, record assumption and rationale in the decision log carried into the PR body, proceed.
3. Hard-stop and wait for the human **only** for destructive or irreversible operations: data deletion, force-push, external publication, irreversible migration against real data. Record `status: awaiting_human` in the run state.

## Report

Deliver inline and write `.ai-workflow/impl-review/<session_id>/report.md`:

1. **Feature** and final status (`delivered` / `local-only` / `partial` / `escalated`).
2. **Tasks** — task, deps, status, acceptance result, review cycles, evidence, which ran in parallel.
3. **Workers** — per task: host, thread name or agent id, the goal, whether the thread was archived; and the orchestrator thread's name.
4. **Integration** — order merged, conflicts resolved.
5. **Feature-wide full-review** — verdict, findings by severity, what was fixed.
6. **Residuals** — filed tickets, the committed record path, `no_sink` items.
7. **Delivery** — PR URL or the local commits; the decision log.
8. **Escalations and blocked tasks** — with the open findings or the missing evidence.

## Degrade Gracefully

- **Not a git repo:** run tasks sequentially in the working tree via `implement-and-review`'s no-git fallback; no parallelism, no PR. Still one fresh worker and one `/goal` per task.
- **No worker tool (no `Agent`, no thread creation, no runner):** run each task inline, one at a time, but still write the brief, the goal text, and the report per task, and state in the final report that no worker was spawned. Never present an inline build as a worker thread.
- **Few seats / tight cost:** lower the cap toward 1.
- **Single task:** skip the DAG — call `implement-and-review` and deliver its result.
- **A task escalates or blocks:** keep building independents; list it in the report.
- **`open-pr` unavailable or no remote:** local-only exit — commits, the residual record, and the handoff note are the deliverable.

## Gotchas

- **Don't reimplement `implement-and-review`.** This skill is DAG + integration + seam review + delivery only.
- **Don't build a task in the orchestrator thread**, even a "tiny" one. The conductor's context is the scarce resource; a task built inline is a task with no goal, no envelope, and no archive.
- **Don't reuse a worker.** A second task in a finished worker inherits the first task's context and breaks the one-task-one-thread registry. Open a new one.
- **A goal that is not checkable is not a goal.** "Implement T3 well" cannot end a `/goal`; "envelope at <path> says complete and `npm test` is green on `impl/T3-backend-<id>`" can.
- **Archive, don't delete.** Worker threads are archived when their envelope is recorded; deletion is destructive and needs the human.
- Each task builds on the **current integration head**, not the stale base; serialize tasks likely to touch the same files with a `blocked_by`.
- Per-task `full-review` already ran inside each build; the feature-wide pass targets the **seams** so you don't pay to re-review every task in full.
- Do not read a task's report body to stay informed — the envelope is the interface. Open a report only to route a failure, assemble the final report, or reconcile two tasks that disagree.
- Do not paste a report's content into the next task's brief. Cite the path.
- Do not retry pushes or PR actions in local-only mode — one `git remote` check decides the whole run.
- Do not let a routing directive leak into task briefs or review inputs.
