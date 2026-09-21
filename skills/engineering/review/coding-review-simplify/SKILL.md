---
name: coding-review-simplify
description: Review a completed code change for behavior-preserving simplification, local correctness, and maintainability. Use after implementing a scoped task or when the user asks to simplify a concrete diff. Do not use as a full feature review or to choose the delivery reviewer plan.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Agent
---

# Coding Review Simplify

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Tighten a completed diff while the implementation context is fresh. The result is a smaller coherent shape, or a focused concern with proof. The next consumer is the approved review plan.

This is a behavior-preserving pass. It does not automatically call `full-review`. The approved routing plan decides whether a later focused, seam, or deep review is needed.

## Workflow

1. Read the task acceptance contract, changed files, diff, and verification already captured. Start with the changed surface and expand only across a real boundary.
2. Check the change against its intended observable behavior. Report a concern only when it can cause a bug, regression, maintenance trap, data risk, weak verification, or material reader confusion.
3. Simplify only when the result remains behavior-preserving. Keep validation at trust boundaries, authorization checks, invariant assertions, encoding, and accessibility safeguards unless evidence proves they are dead.
4. Select a focused review when the diff adds a helper, changes ownership, or affects a hot or asynchronous path. Read the matching persona from `references/personas/` only for that concern. Use `data-systems-coding-lens` when stored state or asynchronous behavior changes.
5. Run the **Connascence Pass** only when the diff crosses a boundary or feels tangled. Identify what is **connascent**, then state its strength, locality, degree, and smallest safe remedy. Leave local static coupling alone when extraction adds indirection without safety.
6. Escalate a boundary-wide design concern to the relevant lens. Do not start a broader refactor from this pass.
7. Turn each accepted concern into a focused fix, test, check, or explicit follow-up. Re-run only the verification affected by a made change.

## Simplification cues

Use the `clean-code` vocabulary. Look for a helper with no decision, a type that hides an awkward contract, needless memoization or effects, compatibility code with no callers, and unrelated diff churn. A name can be better than a wrapper. Duplication can stay when the concepts may diverge.

## Output

For review-only work, list findings by severity with location, consequence, smallest useful fix, and verification.

For implementation work, return:

1. Outcome: safe as is, simplified, needs a focused fix, or needs design escalation.
2. Changes made.
3. Verification captured.
4. Remaining risk.

Use `references/team-checklists.md` only immediately before handoff or deployment. Do not measure success by lines removed; the measure is a simpler change that preserves observable behavior.
