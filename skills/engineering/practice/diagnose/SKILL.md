---
name: diagnose
description: "Find and prove the cause of a bug, failing test, or unexpected behavior. Use for unexplained failures, including pipeline verification failures; an understood failure within a TDD loop stays with tdd."
---

# Diagnose

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Find the cause from observed failure evidence and the relevant code. **Pattern-match is not diagnosis**: a familiar symptom gives a hypothesis. An **artifact of proof** connects symptom → mechanism → cause.

A diagnosis is complete when that chain is supported. If the investigation cannot establish it, report the remaining uncertainty and the evidence needed to resolve it. Apply a fix when the request authorizes it.

## Establish the evidence

Read the supplied error, logs, traces, values, failing test results, and the code path they identify. Check that the evidence applies to the affected version and conditions. Reuse sufficient evidence from the current task.

Existing evidence can prove the cause without a new local reproduction. State the connection, for example: “The trace is the **artifact of proof**: the retry leaves the connection open, which exhausts the pool.”

## Resolve open questions

Use only the techniques that can resolve a remaining uncertainty:

1. **Reproduce when needed.** Choose the command, input, and environment that can confirm or reject an open hypothesis. Record the exact command and output.
2. **Bound attempts.** Before repeating a probe, set an attempt or time limit. Reuse the caller's limit when supplied. Stop when the evidence answers the question or the limit is reached. A repeated failure does not reset the limit.
3. **Minimize when useful.** Reduce the input or setup when this separates possible causes or gives a usable regression case.
4. **Choose the cheapest discriminating probe.** When several causes fit, choose a probe whose possible results distinguish them. Do not invent alternatives after the evidence establishes the cause.
5. **Instrument missing evidence.** Add targeted logs, assertions, or breakpoints only when existing evidence is insufficient. Preserve failure state and account for effects on timing or behavior.

If a probe cannot run or does not reproduce the failure, record that result. Continue with other available evidence that can resolve the cause. If uncertainty remains at the investigation limit, report the supported links, open hypotheses, and smallest missing evidence.

## Fix and verify

For an authorized code fix:

1. State how the change addresses the proven mechanism.
2. Use `tdd` to encode that mechanism in a regression test. Observe the expected failure before the fix and a passing result after it. A focused test can establish the mechanism without reproducing the full production incident. Reuse valid failing test evidence already captured.
3. Run the checks affected by the fix and record their results. If required verification cannot run, report the limit and leave the fix unconfirmed.
4. Remove temporary instrumentation and scratch reproductions added during diagnosis. Keep the regression test, useful evidence records, and assertions that protect a real invariant.

An assessment request ends with the diagnosis and evidence. It does not require an implementation or a new regression test.

## Evidence rules

1. Preserve relevant evidence before restarting a process or clearing state.
2. Change one variable per probe so the result can identify its effect.
3. If several code changes remove the symptom, isolate their effects before claiming which change fixes the cause.
4. Label an unsupported causal link as unresolved. A passing test or vanished symptom alone does not establish the cause.

## Pipeline mode (mode:pipeline)

Do not pause for questions. Follow the calling pipeline's escalation rules and the status vocabulary in `shared/references/pr-watch-contracts.md`.

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

Set `reproduced` to `true` only when a reproduction was observed during this run or is supported by captured reproduction evidence supplied to it. Otherwise set it to `false`. In `evidence`, distinguish a reproduction that was unnecessary, unavailable, or attempted without reproducing the failure.

A `false` value can accompany a cause proved by logs or traces. If the cause remains unknown, state that in `root_cause` and record the evidence gap in `residuals`. Use `fixed-and-pushed` only after the fix is verified and an authorized push succeeds.

## Boundaries

1. `tdd` owns the test execution loop. An understood failing test stays in that loop.
2. `fable-mindset` owns the evidence posture; this skill supplies the diagnostic techniques.
3. `safe-incremental-coding` protects untested existing behavior. Use diagnosis when that behavior is unexpected and its cause needs investigation.
