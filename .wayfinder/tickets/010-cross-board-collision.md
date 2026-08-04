---
id: "010"
title: When two boards touch the same files
type: grilling
status: open
parent: map
blocked_by: []
---

# When two boards touch the same files

## Question

Graduated from the fog once [Board lifecycle and storage layout](002-board-lifecycle.md) settled that a board is a branch plus a worktree.

Boards are isolated *while they run* — separate worktrees mean no board can corrupt another's working tree. They are not isolated *when they land*: two boards that edited the same files produce two branches that conflict, and the conflict only surfaces at merge time, in GitHub, after both have already been built and reviewed.

The pipeline solves this one level down and refuses to solve it here. `to-tasks` asks whether each slice is parallel-safe, the scheduler enforces `blocked_by` between slices, and `implement-feature`'s rule is explicit: *never parallelize tasks that write the same files; when in doubt, serialize.* Nothing applies that reasoning **between** boards, because boards are started independently by a human typing a prompt.

To settle: whether the workbench detects the overlap at all, and when. Candidate moments — at board creation, by comparing the new prompt against in-flight boards; continuously, by watching which files each board's branch actually touches; or never, treating merge conflicts as a normal cost of parallel work.

Then: what it does with what it finds. A warning at start, a badge on both boards once the overlap is real, an offer to serialize by making one board wait, or nothing beyond surfacing it.

Worth weighing honestly: parallel features colliding is the *expected* case in a small repo, so a detector that cries wolf on every board is worse than none. The destination stops at the PR, so resolving conflicts is out of scope — this ticket decides only what the workbench **knows** and **says**, never what it merges.
