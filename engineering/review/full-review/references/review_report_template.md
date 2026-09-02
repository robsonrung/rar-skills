# Full Review Report

## Summary

What changed, why, and what to validate. Keep it short.

## Walkthrough

File-by-file intent, focus on the most important flows.

## Risks

What could go wrong in production or in future maintenance. Include worst-case paths and any structural regressions that would make safe follow-up work harder.

## Verdict

`APPROVE`, `COMMENT`, or `REQUEST_CHANGES` — include reasoning tied to severity.

## Top Issues

List CRITICAL and HIGH first, then MEDIUM quick wins. Include path and line ranges. Mark verified bugs with ✓. For structural maintainability findings, state the simpler framing and smallest safe refactor path.

## Test Plan

Commands to run, plus any manual steps.

## Panel Activity

Two short subsections, present only when triangulation was active:

- **Triangulation panel** — seats engaged, lens per seat, posture (`light | quality | degraded`), and any seats marked `unavailable` with reason.
- **Adversarial-verify activity** — count of findings entered, count refuted, count survived, count inconclusive. List the refuted titles in one line each.
- **Synthesis activity** — the synthesizer's short log: which multi-model corroboration bumps fired, which severity upgrades fired, which findings were dropped by the confidence filter vs. by the risk-based cap.

Omit this entire section when `triangulation: off`.

## Questions

Targeted questions for unclear intent or missing context.

---

## Summary Line

Always end the report with:

```
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```

If no bugs were verified, explicitly say the diff looks clean — do not manufacture findings. Optionally mention refuted candidates briefly so the user knows what was checked and dismissed.
