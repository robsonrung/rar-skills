# Full Review Report

## Review plan

State the scope, risk, seats, effort, planned routes, completed routes, unavailable routes, and coverage limit. State the active confidence threshold and nonblocking cap when either differs from the default.

## Summary

State what changed and the most important result in a few sentences.

## Findings

List `CRITICAL` and `HIGH` findings first. For every finding, include the path and line range, impact, evidence, smallest useful fix, and verification result. Mark a concern that could not be verified as unverified.

## Verification

List commands, test results, manual checks, and relevant limits.

## Verdict

Use `APPROVE`, `COMMENT`, or `REQUEST_CHANGES`. A remaining critical or high finding requires `REQUEST_CHANGES`. A meaningful medium finding requires `COMMENT`. Otherwise use `APPROVE`.

## Questions

Ask only questions that block a confident conclusion.

End every code report with:

```text
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```
