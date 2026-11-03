---
name: diagnose
description: "Find and prove the cause of a bug, failing test, or unexpected behavior. Use for unexplained failures, including pipeline verification failures; an understood failure within a TDD loop stays with tdd."
---

# Diagnose

**Pattern-match is not diagnosis.** A familiar symptom gives you a hypothesis. The diagnosis is an **artifact of proof** that links symptom → mechanism → cause. When the chain will not close, report the links you could support, the open hypotheses, and the smallest missing evidence.

**Act or assess**: an assessment ends with the diagnosis and its evidence. Only a requested fix goes on to *Fix and verify*.

## Start from the evidence

Read the error, logs, traces, values, and failing results, then the code path they point to. Confirm they come from the affected version and conditions. Existing evidence can prove the cause without a fresh reproduction: "The trace is the **artifact of proof**: the retry leaves the connection open, which exhausts the pool."

## Close the open questions

Use the moves that resolve the uncertainty you still have:

1. **Reproduce** with the command, input, and environment that confirm or reject the open hypothesis. Record the exact command and output.
2. **Bound attempts.** Set an attempt or time limit before repeating a probe, or reuse the caller's. A repeated failure does not reset it.
3. **Minimize** the input or setup when that separates candidate causes or yields a regression case.
4. **Cheapest discriminating probe.** When several causes fit, pick the probe whose outcomes tell them apart.
5. **Instrument** only where evidence is missing. Preserve the failure state, and account for any effect the probe has on timing.

A probe that cannot run or does not reproduce is a result: record it and keep going with other evidence.

## Evidence rules

- Preserve evidence before restarting a process or clearing state.
- Change one variable per probe.
- When several changes remove the symptom, isolate their effects before naming the fix.
- A passing test or a vanished symptom does not prove the cause. Label an unsupported link unresolved.

## Fix and verify

1. State how the change addresses the proven mechanism.
2. Encode the mechanism in a regression test through `tdd`: watch it fail before the fix and pass after. A focused test can prove the mechanism without replaying the whole incident.
3. Run the affected checks. If required verification cannot run, the fix stays unconfirmed.
4. Remove temporary instrumentation and scratch reproductions. Keep the regression test and the assertions that guard a real invariant.

## Pipeline mode (mode:pipeline)

Ask no questions. Follow the caller's escalation rules and return this shape, keeping the status vocabulary identical to [references/pr-watch-contracts.md](references/pr-watch-contracts.md):

```json
{
  "status": "fixed-and-pushed | diagnosed-no-fix | flaky-infra | needs-human",
  "reproduced": true,
  "root_cause": "<causal chain: symptom → mechanism → cause>",
  "evidence": "<the artifact of proof>",
  "fix": "<commits or diff, null when no fix>",
  "regression_test": "<test name/path, or null>",
  "residuals": [{ "title": "...", "decision_context": "..." }]
}
```

`reproduced` is `true` only for a reproduction observed in this run or backed by captured evidence; `evidence` says whether reproduction was unnecessary, unavailable, or failed. A cause proved by logs can stand with `reproduced: false`. An unknown cause is stated in `root_cause`, and its gap goes in `residuals`. `fixed-and-pushed` requires a verified fix and a successful push.
