---
id: "000"
title: Chart the destination and the first frontier
type: grilling
status: closed
parent: map
blocked_by: []
---

# Chart the destination and the first frontier

## Question

What is this effort finding its way to, and which decisions define the space around it?

## Resolution

Five decisions settled in the charting session.

### Destination

**The working thing, built** — not a spec to hand off, and not an architecture decision in isolation. A multi-board workbench, running.

This overrides Wayfinder's plan-don't-do default, recorded in the map's Notes so later sessions carry execution rather than stopping at a decision.

A consequence worth naming: because interviews happen in the board, a board spans the **whole** pipeline, phase 0 through 6 — not just the autonomous half `pipeline_scheduler.py` covers today.

### Isolation

**One feature = one worktree + branch.** A board owns:

```
board = {
  id, title, prompt,
  worktree:  a git worktree of its own,
  branch:    board/<id>,
  session:   a resumable agent session id,
  runs:      its own run-state tree
}
```

A single local server hosts many boards. This lifts the isolation the scheduler already builds per *slice* up one level to the *feature*, so parallel features genuinely cannot collide on the working tree.

Rejected: a server per board (costs a process and port each, and gives no cross-board view), and boards as a mere filter over run-ids (cheapest, but parallel features would write the same files, making "parallel" false).

### Live loop

**A long-lived streaming session per board.** The server keeps a CLI process open per board and streams to the browser, giving live tokens and visible tool calls.

Chosen over turn-based `--resume` deliberately, for the richer feel. The cost is real and was flagged at the time: a long-lived session is not restart-safe, and an interview in flight dies with the server — the opposite of the "ledger, not the transcript" rule the scheduler follows everywhere else. That cost is not accepted silently; it is the question in [Surviving a server restart](001-restart-durability.md).

### Interview UX

**One question per card, with option chips.** A single question fills the view, offering clickable recommended answers plus a free-text escape hatch, over a rail showing what has already been settled.

This mirrors the `interview` skill rather than fighting it: that skill asks one question at a time with a recommended answer, and the pipeline's skills already document a "numbered options" fallback that maps directly onto selectable UI.

Rejected: a chat transcript (the live question competes with scrollback), and a multi-question wizard (the interview is one-at-a-time precisely because later questions depend on earlier answers).

### Scope edge

**Everything up to the merge.** Prompt, interview, approval gate, build, verify, and PR all happen in the board. Reading the diff and merging stay with a human on GitHub — the one genuinely irreversible act, left in the tool built for it, matching where the pipeline's own escalation ladder already stops.

### Decided without asking

`pipeline_scheduler.py` remains the executor for phases 3–6. It owns the ledger, worktrees, and merges and carries 42 guarding tests; rebuilding that behind a web UI would be duplication. The board drives it.
