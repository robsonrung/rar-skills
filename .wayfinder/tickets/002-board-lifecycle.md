---
id: "002"
title: Board lifecycle and storage layout
type: grilling
status: closed
parent: map
blocked_by: []
---

# Board lifecycle and storage layout

## Question

A board owns a worktree, a branch, a session id, and a run-state tree. Where does all of that live on disk, and what is a board's full lifecycle?

To settle: the board id scheme (human-readable slug versus timestamp, and what happens to duplicate titles); whether board state lives under `.ai-workflow/boards/<id>/` beside the existing run state or somewhere outside the repo; what archiving a board does to its worktree and branch; whether deleting a board deletes its branch, and what protects unmerged work from that.

The run-state contract's rule applies here too: a fixed path shared across boards turns two concurrent boards into one corrupted board.

## Resolution

### State is centralised in the main repo

```
<repo>/.ai-workflow/
  boards/<id>/board.json        record: title, prompt, session_id, station, status
  boards/<id>/ship/<run-id>/    run ledgers for this board's runs
  worktrees/<id>/               the board's checkout — code only
```

The subtlety this settles: the scheduler writes its ledger relative to **the workspace it is given**. Had a board's workspace been its own worktree, that board's entire history would live inside the checkout — scattered across N trees, and destroyed whenever a worktree was removed. Centralising keeps one tree for the server to scan, and lets history outlive the worktree it was produced in.

It also matches what the scheduler already does: state central, worktrees separate. `/.ai-workflow` is gitignored at the root, so none of this is ever committed.

Rejected: per-worktree state (self-contained, but the server would scan N trees and a removed worktree would take its board's history with it) and a home-directory store (survives a re-clone, but divorces board state from the project and abandons the established gitignored convention).

### Ids are readable slugs

`<slug-from-prompt>-<4 hex>` — `add-auth-a3f9` — with the branch `board/add-auth-a3f9`. The scheduler's timestamp ids (`20260731T1926Z-2f26`) are right for machine-generated runs and wrong for a list a human reads. The suffix keeps duplicate titles from colliding.

Decided without asking: it follows from the board list being a human surface, and nothing downstream turns on the exact format.

### Archiving is soft; deleting refuses unmerged work

- **Archive** — the board leaves the list and its worktree is removed. The branch and the full ledger stay. This is the ordinary end of a board's life and reclaims the disk that matters.
- **Delete** — explicit, and **refuses** when the branch holds commits merged nowhere, naming the count and requiring a second, deliberate confirmation to proceed.

The asymmetry is the point: worktrees are cheap to recreate from a branch, so removing one costs nothing; commits are not, so destroying them takes a deliberate act. This is the same instinct the pipeline applies to irreversible operations elsewhere — a hard stop for a human rather than a default.

Rejected: a single delete that removes everything (clean, but an abandoned board that turns out to have mattered is unrecoverable) and never deleting at all (full history, unbounded growth of branches and state).

### Consequence for the map

Unblocks [Driving the scheduler from a board](006-driving-the-scheduler.md) and [The board list](008-board-list.md). One fog patch graduates: **cross-board collision** is now sharp enough to ticket — see [When two boards touch the same files](010-cross-board-collision.md).
