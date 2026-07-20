---
name: pr-shepherd
description: Drive a pull request to done — loop review-swarm on new pushes, review-triage on unresolved threads, and approval-gate once the PR is quiet, until the PR reaches a terminal state (merged, closed, or parked with a human). Use when the user asks to shepherd, babysit, watch, monitor, or autofix a PR, keep kicking it until green, or get it mergeable. Do not use for a one-shot review (review-swarm, full-review), a one-shot comment cleanup (review-triage), or a one-shot approval check (approval-gate).
---

# PR Shepherd

A loop with an exit. The shepherd runs the PR-lifecycle skills in the right order, over and over, and is only ever finished in a **terminal state**:

- `merged` — the PR landed.
- `closed` — the PR was abandoned.
- `parked` — a human must act, has been told exactly what is needed, and the shepherd stands down until the PR changes again.

Every iteration ends by naming its state out loud: *"HEAD moved since the swarm baseline — not a terminal state, going around again"*, or *"approval-gate said ESCALATE (deny-list: migrations), reasons posted — parked."*

## Iteration

Each wake-up, refresh state first:

```bash
gh pr view <n> --json state,mergeable,headRefOid,reviewDecision,statusCheckRollup
```

Then take the **first** matching row:

| Observation | Action | State after |
|---|---|---|
| PR merged or closed | Final report | terminal: `merged` / `closed` |
| Merge conflicts | Tell the author what conflicts; never rebase or force-push on their behalf without an explicit standing instruction | `parked` |
| HEAD ≠ swarm baseline (`swarm-sha` marker) and the delta touches more than docs | Run `review-swarm` | loop |
| Unresolved review threads exist | Run `review-triage` (as sub-step: pass PR metadata + baseline, read its JSON) | loop |
| Triage left `unresolved_actionable_remaining: true` | Fix what broke (tests, push failure), or report why not | loop |
| Quiet: threads only deferred-to-humans or none, checks settled | Run `approval-gate` | see verdict table |
| Nothing changed since last iteration | Do nothing this round | wait for next wake-up |

Approval-gate verdict handling:

| Verdict | Shepherd action |
|---|---|
| `APPROVE` | Report it (post only per approval-gate's own posting rules). **The shepherd never merges.** Terminal once the humans/queue take over: `parked` with "ready" |
| `WAIT` | Nothing; re-check next iteration |
| `REFUSE` | The reasons are the work queue: fix in-diff showstoppers or red CI, push, loop |
| `ESCALATE` | Post/report the reasons | `parked` |

`parked` is not a stop: the shepherd stays subscribed, and any new push or thread activity re-enters the loop. It is terminal for the *shepherd's initiative* — no further action until the PR changes or a human answers.

## Scheduling

Never busy-wait and never poll with in-band sleeps. Use the host's mechanisms:

- Event-driven when available: PR-activity subscriptions (comments, reviews, CI events wake the session).
- Interval fallback: the host's loop/cron facility (e.g. a `/loop`-style recurring invocation, a scheduled self check-in roughly hourly) — events do not cover everything; CI success and new pushes may arrive silently.
- Standalone one-shot: run the iteration once, report the state, tell the user what would resume it.

## Carried state

Between iterations the shepherd needs only three facts, all recoverable from the PR itself after a cold start (cold-start test: a fresh session must be able to resume from the PR alone):

1. Swarm baseline — the `swarm-sha` marker in the review-swarm summary comment.
2. Deferred thread ids — re-derivable from `review-triage`'s human-participation gate; never act on these.
3. Last gate verdict — the `<!-- approval-gate-status -->` sticky comment.

## Composition

| Concern | Delegate to |
|---|---|
| Finding problems in new code | `review-swarm` (which itself escalates CRITICAL regions to `full-review`) |
| Processing feedback threads | `review-triage` |
| The stamp decision | `approval-gate` |
| A deep one-shot audit mid-flight (user asks) | `full-review` |

The shepherd itself reviews nothing, fixes nothing directly, and approves nothing — it sequences the skills that do, and it reports honestly which state the loop is in.

## Gotchas

1. Respect a stop request immediately: unsubscribe, cancel schedules, report the last state.
2. Never merge, even on `APPROVE` — merging is a human or merge-queue decision.
3. Never reply to human reviewers — the human-participation gate is the triage skill's law and the shepherd's too; the author speaks for the PR.
4. Doc-only pushes do not re-trigger the swarm; do not burn seats on typo commits.
5. One narration line per iteration (`[shepherd] <observation> → <action> → <state>`); the thread of these lines is the audit trail.
6. If a sub-skill is missing, run the ones present and name the gap in the report — a shepherd with no swarm still triages and gates.
