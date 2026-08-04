---
id: "009"
title: Delivery, surfaced
type: grilling
status: open
parent: map
blocked_by: ["006"]
---

# Delivery, surfaced

## Question

Phase 6 commits, files residual findings, opens a PR, and writes a handoff note. The destination stops at the merge, so the board's last job is to hand a human everything needed to review — and nothing more.

To settle: what a finished board shows (PR link, acceptance evidence, decision log, residual findings, blocked slices); how a board that finished with failures reads differently from a clean one; what a local-only run shows in place of a PR; and whether a board stays live after its PR opens, so `resolve-pr-feedback` has somewhere to run when review comments arrive.

Blocked by Driving the scheduler from a board, since what phase 6 can surface depends on how its output reaches the board at all.
