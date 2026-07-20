---
name: review-triage
description: Triage every unresolved review thread on a PR — re-run review-swarm when the head moved, apply clear localized fixes and resolve them silently, close nits with a logged reason, and defer anything with human participation or genuine design judgment. Use when the user asks to triage, process, address, or clean up review comments or bot findings on a PR, to handle reviewer feedback, or as pr-shepherd's triage step. Do not use to produce new review findings — that is review-swarm or full-review.
---

# Review Triage

Turn a wall of unresolved review threads into three piles — fixed, closed-with-reason, and handed-to-a-human — without ever speaking for the author.

Two rules do all the work, so name them as you triage:

- The **human-participation gate**: any thread a human has written in is deferred untouched — no fix, no resolve, no reply. Replies to humans come from the PR author, never from automation. *"@reviewer commented here — human-participation gate, deferring."*
- The **autonomy ladder** for ambiguous bot threads, three rungs: **just-do-it** (concrete, localized, obviously correct → fix it), **recommend-and-defer** (fix is clear but touches design/scope → write the recommendation into the report, leave the thread open), **stop-and-ask** (genuine judgment call → defer with a stated question). *"This one is recommend-and-defer: the fix is clear but it widens the API."*

When a thread cannot be confidently classified, treat it as human — the human-participation gate wins ties.

## Workflow

### 1. Resolve the PR and baseline

`gh pr view <n> --json number,url,state,baseRefName,headRefOid`. If the PR is merged or closed, report that and stop. Read the swarm baseline from the `<!-- swarm-sha: ... -->` marker in the `review-swarm` summary comment (null when absent). When running as a `pr-shepherd` sub-step, take PR metadata and baseline from the shepherd instead of re-fetching.

### 2. Re-run review-swarm when warranted

Run the sibling `review-swarm` skill when the baseline is null, or when `HEAD` differs from the baseline **and** the diff since it touches anything beyond documentation (`.md`, `.txt`, whitespace). Doc-only movement never re-triggers the swarm. If `review-swarm` is not installed, note it and triage the threads that already exist.

### 3. Fetch and normalize threads

Run the exact fetch pipeline from `references/github-thread-ops.md`:

```bash
gh api graphql --paginate -F owner=... -F name=... -F pr=... -f query='<query from the reference>' \
  | python3 .agents/skills/review-triage/scripts/triage_threads.py --head-sha <HEAD>
```

The script normalizes the payload: per-comment authors classified bot/human, `has_human` flag per thread, bodies trimmed to 1500 characters, and `stale` marked on bot-only threads whose anchor GitHub reports outdated. Skip stale threads entirely — they describe code that no longer exists. Outdated threads with humans in them are still deferred, not skipped.

### 4. Bucket and act

| Bucket | Criteria | Action |
|---|---|---|
| deferred (human) | `has_human` true | Nothing — human-participation gate |
| actionable | Bot-only; HIGH/CRITICAL or convergent; concrete single-file (or tightly related) fix; no new design or dependencies; obviously correct | Fix → commit `fix: address review feedback — <description>` → push → resolve silently |
| nit | Bot-only; style-only, speculative, duplicate, or already addressed | Resolve silently; one-line reason goes in the report, not the thread |
| ambiguous | Bot-only; architectural judgment, broad scope, or design decision | Run the autonomy ladder: just-do-it → treat as actionable; recommend-and-defer / stop-and-ask → leave open, record rung and reasoning |

Batch all actionable fixes into as few commits as they naturally group into; push once, then resolve each fixed thread. Never post a reply in any thread, in any bucket.

### 5. Report

Standalone, print:

```text
[triage] done — sha=<short> swarm=<ran|skip> fixed=<n> resolved=<n> deferred=<n> (human=<n> ladder=<n>) stale=<n>
<per-thread line: path:line  bucket  author  one-line reason>
```

As a `pr-shepherd` sub-step, return JSON instead:

```json
{"head_sha_in": "...", "new_head_sha": "...", "swarm_ran": false,
 "fixed": 0, "resolved": 0, "deferred_threads": ["<thread-id>"],
 "unresolved_actionable_remaining": false, "narration": ["[triage] ..."]}
```

`unresolved_actionable_remaining` is true only when an actionable fix failed (tests broke, push rejected) and the thread stayed open — that is the shepherd's signal to hold the approval gate.

## Gotchas

1. Deferring is a success outcome, not a failure — the report saying "5 threads with humans, untouched" is the skill working.
2. Resolve silently means silently: no "done ✅" replies, no reactions. The commit and the report are the record.
3. A fix that grows beyond the thread's file neighborhood has left just-do-it territory — re-classify up the autonomy ladder instead of pushing a surprise refactor.
4. Verify an actionable fix before pushing (run the nearest tests); a broken fix converts to `unresolved_actionable_remaining: true`, it does not get force-pushed variants.
5. Trim thread bodies to 1500 characters before reasoning over them — walls of bot text drown the classification.
6. Do not resolve a deferred thread to tidy up; open threads with humans are the author's queue.
