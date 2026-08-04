---
label: wayfinder:map
title: Boards as the interface
---

# Boards as the interface

## Destination

A working multi-board workbench: many features in flight at once, each with its own kanban board, each started by typing a prompt — and from that prompt through interview, approval, build, verify and PR, everything happens inside that board. A human leaves the board only to read the diff and merge.

## Notes

**Domain:** this repo's own delivery pipeline (`docs/pipeline.html`), its run-state ledger (`_shared/references/run-state-contract.md`), and the existing [`pipeline-board/`](../pipeline-board/) and [`scripts/pipeline_scheduler.py`](../scripts/pipeline_scheduler.py).

**This map carries execution.** The destination is the built thing, not a spec — overriding Wayfinder's plan-don't-do default. Tickets still resolve a decision first, but they finish by building it.

**Skills to consult each session:** `grilling` and `domain-modeling` for every HITL ticket; `prototype` for anything visual; `design-gate` lens flags where a ticket changes architecture. The pipeline's own `ship` is available for tickets big enough to deserve it.

**Reuse, don't rebuild.** `pipeline_scheduler.py` stays the executor for phases 3–6 — it owns the ledger, worktrees, and merges, and is guarded by 42 tests. The board drives it; it does not replace it.

**Vocabulary** (see [CONCEPTS.md](../CONCEPTS.md)): a **board** is one feature — a worktree, a branch, a resumable agent session, and the run-state tree beneath it. A **station** is a pipeline phase, and a board's column. A **run** is one `ship` execution inside a board.

## Decisions so far

- [Name the destination](tickets/000-destination.md) — the built workbench, not a spec; plan-don't-do is overridden for this map.
- [What a board is, and what isolates one](tickets/000-destination.md#isolation) — one feature = one worktree + branch + session id + run-state tree; a single local server hosts many boards.
- [How a board runs a live conversation](tickets/000-destination.md#live-loop) — a long-lived streaming session per board, not turn-based resume. Chosen for the richer feel; the durability cost it creates is now [Surviving a server restart](tickets/001-restart-durability.md).
- [What an interview looks like](tickets/000-destination.md#interview-ux) — one question per card with clickable option chips, a free-text escape hatch, and a rail of what's been settled. Mirrors the `interview` skill's one-question-at-a-time shape.
- [Where the board's responsibility stops](tickets/000-destination.md#scope-edge) — everything up to the merge. Reading the diff and merging stay with a human, on GitHub.
- [Surviving a server restart](tickets/001-restart-durability.md) — the conversation was never at risk: the CLI persists sessions itself, so a restart loses the live stream only. A reattached board announces the gap rather than resuming silently, and builds run detached so they outlive the server.
- [Board lifecycle and storage layout](tickets/002-board-lifecycle.md) — state centralised at `.ai-workflow/boards/<id>/` so history outlives the worktree; ids are readable slugs (`add-auth-a3f9`); archiving is soft, and deleting refuses a branch holding unmerged commits.

## Not yet specified

- **Surfacing the multi-model council.** `full-review` and `models-consensus` produce rich multi-seat artifacts. How much of that belongs on a board, versus a link to the artifact, is unclear until the streaming protocol exists.
- **Notifications.** A board sitting at `awaiting_human` while you are elsewhere is the whole reason to want a push. Now partly constrained: builds run detached, so a board can reach `awaiting_human` while no server is up at all — any notification path cannot assume the server is the thing that noticed. Still too dim to ticket: the shape depends on where a human wants to be reached.
- **Board templates.** Reusing a prompt or a set of standing preferences across boards. Only worth charting once several boards have been run in anger.
- **Failure ergonomics.** What a board offers when a slice hard-blocks — retry, re-scope, abandon — beyond what the ledger already records.

## Out of scope

- **Diff review and merging in the board** — deliberately left to GitHub; the destination stops at the PR.
- **Deploy, release, and CI dashboards** — downstream of the merge, past the destination.
- **Multi-user or hosted operation** — auth, tenancy, and remote access. This is a local single-user workbench.
- **Replacing the CLI paths** — `pipeline_scheduler.py` and `run-pipeline-acp.py` keep working headlessly; the board is an addition, not a migration.
