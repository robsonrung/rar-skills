---
name: pre-pr-review
description: Check existing review evidence and complete missing work before opening a pull request. Use for a final development check with scoped fixes; use review-gate for a review report only.
disable-model-invocation: true
---

# Pre-PR Review

Check whether a completed implementation is ready for pull request review. Reuse valid task and integration evidence. Run only the work needed to close gaps. The **acceptance contract** is a scoped, verified local change with no confirmed P0, P1, or P2 finding left open. Approval from a reviewer alone does not meet this contract.

## Scope and authority

An explicit request to run this workflow authorizes local simplification, scoped fixes, and verification. Preserve unrelated changes. Keep the result local: do not commit, push, publish comments, open a pull request, merge, or deploy.

Read the task requirements and active project rules. Confirm the intended pull request base branch from the task or repository configuration. Ask only if the target remains ambiguous. Review committed and uncommitted task changes against that base, and pass the same base and requirements to every stage. Do not let a child skill replace the intended base with the repository default.

If no task changes exist, report `no-changes` and stop before review. An unreadable diff is a blocker, not an empty result.

## 1. Check existing evidence

Read the available task reports, integration report, residual findings, and referenced review and verification evidence. Inspect the existing run state and approved model plan when present. A report path or completion label alone is not proof of coverage.

Read `shared/references/review-evidence.md`. Run the shared verifier on the current
combined review record with the intended PR base; use the launcher's `verify-review`
for a task record. Require exit code 0 and `ready` before reusing that record for
readiness. Missing or stale structured evidence is a gap. Legacy Markdown reports
can guide a focused review but cannot establish deterministic readiness.

Compare that evidence with the current task diff, intended base, requirements, relevant dependencies, and environment. Include uncommitted edits and changes made after review. A different commit alone does not invalidate evidence when the relevant content and assumptions still match. Missing or unverifiable evidence leaves a gap.

Record which evidence is valid and which work is missing: task review, integration review, required checks, browser flows, or finding resolution. Task reviews do not prove that the combined change was reviewed. For multiple tasks, confirm coverage of shared contracts, migration order, and interactions between tasks.

This workflow permits reuse of matching evidence unless the caller requires fresh runs. When the acceptance contract is already met, return `ready` with the evidence references. Do not simplify code, start reviewers, probe model routes, or repeat checks in that case.

Refresh runtime and external context before reuse. If those facts cannot be
confirmed, run fresh checks. Never convert a stale result to ready by editing
its hashes or copying an approval label.

## 2. Close only the gaps

Resolve only the selected skills by name through the host catalog or collection layout, then read their `SKILL.md` files. Source skills are grouped under `skills/`; installed skills can be flat siblings. A missing skill blocks only the work that needs it.

| Gap | Action |
| --- | --- |
| Changes made after review | Review the changed paths and affected callers. Preserve valid coverage for the rest of the diff. |
| Missing integration review | Use `full-review` on the combined change, limited to interactions and gaps not covered by task reviews. |
| Missing or invalid check results | Use `verify-changes` for the affected checks and any required fresh checks. |
| Missing browser evidence | Use `browser-smoke` for the affected interface flows. |
| Confirmed defects or disputed findings | Apply the correction and recheck rules below. |
| A concrete simplification need | Use `coding-review-simplify` on that scope. Keep the change **behavior-preserving**. |
| No usable review evidence | Run the full sequence described below. Reuse any valid check results. |

Use the existing approved reviewer context for a focused recheck, or `full-review` with a focused scope when no suitable context remains. Select specialists only for exposed risks. The absence of a separate simplification report is not a gap after a complete task review. Do not run simplification just because this skill was invoked.

Before dispatch, follow the collection's shared model routing and host execution references. Reuse approved implementation and review routes for the same scope. Present new or changed routes for approval before starting workers. Keep the reviewer context separate from the implementer. Do not silently replace an unavailable route.

Keep review reports and evidence in a temporary directory outside the project. Pass the task requirements as the specification when no pull request exists. Preserve valid coverage from prior reports; the combined evidence must cover every file with a meaningful task change.

After closing gaps, prepare the current source snapshot, capture required checks,
and obtain the shared structured review response. Record the actual response and
run the shared verifier before reporting readiness. Preserve older records and
let the reviewer assess which prior findings and coverage remain valid.

For browser checks, pass the running local application's URL and port explicitly. Reuse matching browser evidence when available. A missing server or skipped required flow remains a verification gap. The absence of a published preview does not complete browser verification.

### Full sequence when review evidence is unavailable

Run `coding-review-simplify`, then an independent `review-gate`. Keep required validation, authorization, and error handling during simplification. Configure `verify: true` for missing or invalid check results and let the gate call `verify-changes`. Use `verify: false` only when all required checks already have valid evidence and no fresh run is required. Pass those evidence references into the final report. Complete missing browser checks separately when needed.

Do not repeat commands already covered by an aggregate check. After simplification or a fix, invalidate only the evidence affected by that change.

## 3. Correct and recheck

Evaluate findings against the current code. Return confirmed defects to the original implementer and its approved route. Use `diagnose` before a fix when the cause is unknown. Keep disputed findings open until evidence supports fixing or rejecting them.

Correct all confirmed P0, P1, and P2 findings within the task scope. Correct P3 findings when the change is small and useful; record the reason for each deferred P3. A correction outside the task scope requires a user decision.

After each correction, have the independent reviewer check the fix and affected paths. Run `verify-changes` for affected checks and any required fresh checks. Repeat browser checks when their flows changed. Preserve review coverage for unchanged files and expand it when a fix affects another boundary.

Allow at most three correction and recheck cycles in this workflow. For work continued from an earlier run, also honor that run's remaining correction allowance. Starting this skill or resuming a context does not reset an exhausted limit. Record the counts, findings, changed paths, and evidence in the temporary report before each cycle. At the limit, stop and report the remaining work.

## 4. Return the result

Report one status:

1. `ready`: no confirmed P0, P1, or P2 remains; each deferred P3 has a reason; review coverage is complete; all required checks and affected interface flows passed; no disputed finding or verification gap remains.
2. `needs-work`: defects remain or the correction limit was reached.
3. `blocked`: a required decision, route, dependency, or verification is unavailable.
4. `no-changes`: there is no task diff to review.

Include the base and reviewed scope, reused evidence, gaps found, work performed, remaining findings, captured check results, browser evidence, cycle count, and report path. Distinguish checks run now from reused evidence and skipped checks. If existing evidence covers all required reviews and checks, state that readiness was confirmed from that evidence.

Apply the acceptance contract separately from the review verdict. For example: "The review returned approve, but one confirmed P2 remains. Status: needs-work."

A `ready` result describes the inspected local state. It does not guarantee that a later review or pipeline will find no defects.
