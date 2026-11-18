---
name: pr-readiness
description: Check existing review evidence and complete missing work before opening a pull request. Use for a final development check with scoped fixes; use full-review for a review report only.
disable-model-invocation: true
---

# PR Readiness

Decide whether a finished implementation is ready for pull request review. Reuse valid evidence and do only the work that closes a gap. The **acceptance contract** is a scoped, verified local change with no confirmed P0, P1, or P2 finding open. A reviewer's approval alone does not meet it.

Running this skill authorizes local simplification, scoped fixes, and verification. Keep the result local: no commit, push, published comment, pull request, merge, or deploy. Preserve unrelated changes.

## 1. Check existing evidence

Confirm the intended base branch from the task or repository configuration, asking only if it stays ambiguous (for one pull request in a stack, the base is the branch below it), and pass that same base and the requirements to every stage. Review committed and uncommitted changes against it. No changes means `no-changes`; an unreadable diff is a blocker.

Start from the work folder or reports the caller names (`shared/references/work-state.md`). A report path or completion label is not proof; captured evidence and a recorded review are:

- **Feature run:** the final `full-review` that accepted the feature must cover the current source. A passing final review already covers deferred tasks; their missing separate reviews are not gaps.
- **Validation run:** `validate-feature`'s captured evidence supplies facts, not reviewer judgment.
- **Any run:** the combined review must name the intended base and the revision it reviewed, and `shared/scripts/capture_check.py stale` must report the required checks current. When the repository has written rules scoped to the changed paths, a recorded review must list the rule sources it read. That list, on the current source, is the record that the rules were checked.
- **Rules packs:** a rules pack is any installed skill whose description says it holds this repository's review rules. Treat every such pack as a rule source and pass its rule files to the `repo_rules` seat. The description is the pointer; no config key is needed.

Reuse evidence only while the source (including post-review edits), base, contract, check definitions, dependencies, and environment still match; a commit ID change alone does not invalidate it. Never repair stale evidence by editing it or copying labels.

If the records show complete combined coverage, passing required checks and affected interface flows, no open or disputed finding, no deferred P0 to P2, and a reason for each deferred P3, return `ready` without further work. Otherwise name the specific gaps and continue.

## 2. Close only the gaps

| Gap | Action |
| --- | --- |
| Changes after review | Review the changed paths and their callers; keep valid coverage for the rest. |
| Missing integration review | `full-review` on the combined change: the whole feature contract in feature mode, interactions and task-review gaps in task mode. |
| No usable review evidence | An independent `full-review` in `gate` mode on the task diff, reusing valid check results. |
| The recorded reviews list no rule sources, or the rules or the changed paths changed since | A `repo_rules` seat from `full-review` on the changed paths, with each rules pack's rule files as sources. Run it before section 3, so its findings join the one correction batch. When no pack is installed, record "no rules skill found"; a repository with no written rules for the changed paths has no gap, so record that none were found. |
| Missing or invalid check results | `verify-changes` for the affected and required fresh checks. |
| Missing browser evidence | `browser-smoke` for the affected flows, against the running local app's explicit URL and port. |
| Confirmed or disputed findings | Section 3. |
| A concrete simplification need | `simplify-changes` on that scope, **behavior-preserving**. |

A missing simplification report is not a gap after a complete task review. Recheck through the existing approved reviewer context when one remains. A new reviewer runs on a route resolved with `python3 shared/scripts/model_routing.py resolve review --provider <host>`, shown to the user with "Approve this plan, or specify changes.", and routed by host as `implement-and-review` describes; its model differs from the implementer's. Give the reviewer the base, the diff, and the captured evidence, and accept its verdict only with a severity, location, and evidence for each finding.

## 3. Correct and recheck

Judge each finding against the current code. Send confirmed defects to the original implementer and route; use `diagnose` first when the cause is unknown. A disputed finding stays open until evidence settles it.

Fix every confirmed P0, P1, and P2 within scope. Fix a P3 when the change is small and useful, and record a reason for each deferred one. A fix outside the task scope needs the user.

Batch the fixes, then have the same reviewer recheck the fixes, affected paths, and interactions in one pass. Rerun affected checks and changed browser flows. Allow at most three correction cycles, including any count carried from an earlier run; restarting the skill does not reset it. At the limit, stop and report.

## 4. Return the result

Report one status:

1. `ready`: no confirmed P0 to P2 remains, each deferred P3 has a reason, coverage is complete, and required checks and affected flows passed.
2. `needs-work`: defects remain or the cycle limit was reached.
3. `blocked`: a required decision, route, dependency, or verification is unavailable.
4. `no-changes`: there is no diff to review.

Include the base and scope, reused evidence, gaps found, work done, remaining findings, checks run now versus reused or skipped, browser evidence, cycle count, and report path. Apply the acceptance contract apart from the reviewer's verdict: "The review returned approve, but one confirmed P2 remains. Status: needs-work." `ready` describes the inspected local state, not a promise about later reviews.
