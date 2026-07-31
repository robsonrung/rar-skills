# The pipeline scheduler

[`scripts/pipeline_scheduler.py`](../scripts/pipeline_scheduler.py) runs ship phases 3–6 over a slice queue with no orchestration framework underneath — no OpenHands, no SDK, no ACP transport, and no API key. It spawns a headless CLI agent per step through the repo's own `*-runner` wrappers, so the run bills against your CLI subscription.

It is the deterministic half of the pipeline, and it is deliberately small. The split that makes it small:

| | Owns |
|---|---|
| **The scheduler** | the ledger, attempt counters and ceilings, gate persistence, side-effect keys, DAG readiness, the concurrency cap, worktree lifecycle, brief writing, envelope parsing, subprocess lifetime |
| **The agent** | all reasoning |

That is what `run-state-contract.md` means by *the model never decides the retry*, and what `handoff-contract.md` means by *hand off the path, not the payload*. No phase logic lives in the Python — every phase is still a prose skill.

Phases 0–2 are not here. They need a human, so they stay in an interactive session; the scheduler starts at the design gate.

## Quickstart

Plan the feature interactively first — `interview` → `to-spec` → `to-tasks` — until the approval gate produces a `TASKS.md` (or tracker issues). Then:

```bash
scripts/pipeline_scheduler.py /path/to/your-project --approved --dry-run
```

That prints the schedule and touches nothing. When it looks right, drop `--dry-run`:

```bash
scripts/pipeline_scheduler.py /path/to/your-project --approved
```

`--approved` records the phase-2 gate. Without it — and without a gate already in the ledger — the run stops rather than assuming the breakdown was approved.

Watch it move:

```bash
python3 pipeline-board/serve.py /path/to/your-project
```

## Options

| Flag | Effect |
|---|---|
| `--resume <run-id>` | continue a run; finished phases are skipped, counters survive |
| `--slice T3` | limit the run to named slices (repeatable) |
| `--seat opus` | which seat runs the phases (`opus`, `sonnet`, `codex`, `gemini`, `grok`, `kimi`, `glm`) |
| `--max-in-flight 3` | concurrency cap |
| `--timeout 3600` | per-step seconds |
| `--tasks path` | work queue location (default: `<workspace>/TASKS.md`) |

## What it writes

```
.ai-workflow/ship/<run-id>/run-state.json            the feature ledger — DAG, gate, merges
.ai-workflow/ship/<run-id>-<slice>/run-state.json    one ledger per slice
.ai-workflow/ship/<run-id>-<slice>/
  03-design-gate.brief.md / .report.md
  04-implement.brief.md   / .report.md
  05-verify.brief.md      / .report.md
  06-deliver.brief.md     / .report.md
.ai-workflow/worktrees/<run-id>-<slice>/             one worktree per slice
```

Slice ledgers are **siblings** of the feature ledger, not children, because the board globs `.ai-workflow/*/*/run-state.json` — nesting them one level deeper would make every slice invisible.

## The rules it enforces outside the model

- **Attempts are counted before the attempt**, so a crash mid-attempt still costs an attempt. A step that returns prose instead of an envelope is re-prompted exactly once, then recorded `failed` — an unparseable return is a step that did not report, not a step to interpret.
- **The evidence gate is machine-checkable.** A model cannot grade its own diligence, so the stand-in is the report's own `## Evidence` section: it must exist and carry something beyond the heading. A phase-4 report that does not gets exactly one recovery pass — same slice, same scope, reconcile the evidence without reimplementing — and then hard-blocks. Nothing proceeds to verify on unverified behavior.
- **Side effects are claimed before they happen.** A resumed run that finds `merge:T3` skips the merge instead of replaying it.
- **A gate absent from the ledger was never granted**, whatever the transcript appears to say.
- **A blocked slice never dispatches**, and is recorded as an exit rather than silently skipped.
- **A missing seat is reported, never substituted.**

## Isolation and integration

Each slice gets its own worktree branched from the current integration head, so slices in flight cannot collide. When a slice completes, its branch merges back and the head advances — the next slice dispatched builds on already-integrated work. A conflicting merge aborts cleanly and is recorded; it does not leave a half-merged tree.

Slices already in flight keep the base they started from. Serialize slices likely to touch the same files by giving them a `blocked_by` in the breakdown — `to-tasks` already asks for exactly that.

No remote flips the run local-only: the commits still happen, every push and PR attempt is skipped, and no retries are spent hunting for a remote.

## Resume

Kill it whenever. A restart picks up at the recorded phase with counters intact:

```bash
scripts/pipeline_scheduler.py /path/to/your-project --resume 20260731T1926Z-2f26
```

The crash-resume path is exercised by `_shared/tests/test_pipeline_scheduler.py`, which the CI guards run — `run-state-contract.md` calls that check required, not optional.

## Relationship to the OpenHands path

[`docs/openhands.md`](openhands.md) does the same job through OpenHands' SDK over ACP. Both are CLI-only and neither needs an API key. The difference is what you take on:

- **This scheduler** — no framework dependency, real parallel slices, the ledger enforced in Python. You maintain ~600 lines.
- **OpenHands** — a conversation manager, its own persistence, and an ecosystem around it, at the cost of a dependency mid-restructure and sequential sub-agents.

Both remain supported; neither replaces the other.
