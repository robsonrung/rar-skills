---
name: full-review
description: Run an evidence-backed, proportionate review of a pull request, branch, diff, task seam, or requirements document. Use for feature integration seams, public contracts, security-sensitive changes, migrations, or an explicitly requested deep review. Do not make this the automatic final pass for every small task.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# Full Review

Review the risks that a focused implementation pass cannot see. The result is a precise, evidence-backed verdict. The next consumer is the author or delivery workflow. A review is complete when its scope, evidence, findings, verification limits, and verdict are explicit.

## Review plan

The review plan is a **scope contract**. Do not claim coverage outside it. It states `scope`, `risk`, `seats`, `effort`, and `verification`. In a delivery workflow, derive it from the user-approved routing-plan JSON. That JSON is the exact executable source for seat, runner, model, effort, mode, and unavailable action.

| Scope | Use when | Minimum review shape |
| --- | --- | --- |
| `focused` | One bounded change with local risk | One review seat and relevant deterministic checks. |
| `seam` | Integrated tasks, shared contracts, or cross-boundary behavior | Approved route or routes that cover logic and state plus root-cause precision. Add a second route only when the plan names it. |
| `deep` | Explicit deep request, security-sensitive boundary, migration, public contract, or high residual risk | The seam shape plus selected security, data, compatibility, or structural specialists. |

Do not launch a blanket panel. Seat names, model choice, runner, and effort come only from the approved plan and the model roster. When a direct review request has no plan, infer the narrowest scope from the diff and state it before reviewing. Do not dispatch an external route until its plan is approved. A direct request for a deep review authorizes the deep scope, not an unplanned route dispatch.

## Workflow

1. Establish the target: pull request, commit range, local diff, task file set, or document. An empty diff is an outcome, not a failure.
2. Read the active project conventions already in context and the local contracts that affect the changed paths. Collect the diff, changed files, relevant surrounding code, and existing review comments. Existing comments are candidates, not facts.
3. Run `scripts/review_scope.py` from this skill's directory when reviewing code. Use its risk signals to confirm or narrow the plan; do not widen a focused review merely because a helper is available.
4. Read `references/review-dispatch.md` before allocating review seats. Load only the reference that matches a planned concern: `references/bug_finders.md`, `references/panel_roles.md`, `references/conditional_specialists.md`, or `references/structural_quality_review.md`. For a requirements document, use only the relevant persona from `references/doc-personas/`.
5. Give every selected seat the same scoped context, conventions, and output contract. Preserve **seat fidelity**: an unavailable seat is recorded as unavailable, never replaced silently. Run independent seats concurrently when the host supports it.
6. Verify runtime, security, correctness, compatibility, reliability, and performance findings when execution is possible. Evidence-check structural findings against the changed code. Mark an unverified claim as unverified or lower confidence; do not turn it into a blocker by assertion.
7. For code, read `references/filtering_pipeline.md` and `references/review_output_schema.json`. For a document, use `references/doc-findings-schema.json`. Deduplicate, retain only evidence-backed findings with a location, then apply the active threshold and cap. **Precision over volume**: do not report cosmetic preference, broad refactor wishes, or pre-existing issues outside scope.
8. Return the verdict. The default is report-only. Apply fixes only with explicit `apply_fixes: true` authority, then re-review the changed paths before delivery.

## Security and documents

When `security_focus=true`, check the implementation against the recorded security decisions and include only the security and data specialists that the plan names. Do not drop a security finding to meet a comment cap.

For a plan or requirements document, review feasibility, scope, coherence, and decision gaps instead of a code diff. Keep the same scope contract and evidence bar.

## Output

For code, return a human report and JSON that matches `references/review_output_schema.json`. For a requirements document, use `references/doc-findings-schema.json` instead. Use `references/review_report_template.md` for the report.

Every code finding includes severity, confidence, category, location, evidence, smallest useful fix, and verification. A document finding uses its section and quoted evidence. End a code report with:

```text
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```

State the selected scope, planned and unavailable seats, verification performed, and any coverage limit. `REQUEST_CHANGES` requires a remaining critical or high finding; `COMMENT` requires a meaningful medium finding; otherwise use `APPROVE`.
