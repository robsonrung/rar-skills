---
name: diagnose
description: "Find and prove the cause of a bug, failing test, or unexpected behavior. Use for unexplained failures, including pipeline verification failures; an understood failure within a TDD loop stays with tdd."
---

# Diagnose — From Symptom to Proven Cause

An evidence-driven method for root-causing a failure. The posture comes from `fable-mindset`'s Diagnosis moment: **pattern-match is not diagnosis**. Use the techniques below to resolve uncertainty; do not perform a step whose question the evidence already answers. Say the leitwörter as you work; they are the checkpoints.

## The procedure

1. **Reproduce first.** A bug you cannot reproduce is a report, not a diagnosis. Capture the exact failing command and its exact output before anything else — that pair is the ground truth every later step is measured against. If you cannot reproduce it, say so and stop guessing (see the pipeline return below).
2. **Minimize when needed.** Shrink the input, scope, or setup when doing so separates possible causes or produces a usable regression case. Keep an existing reproduction when it already establishes the mechanism.
3. **Read the actual error and the actual code path.** The real message, the real stack, the real code it names — before hypothesizing. The tell that you skipped this: your explanation describes similar bugs ("this is usually…") instead of facts from this one.
4. **Resolve competing hypotheses.** When more than one cause fits, choose the **cheapest discriminating probe** that separates them. Do not invent alternatives after the existing evidence establishes one cause.
5. **Instrument only for missing evidence.** Use existing logs, values, code paths, or a failing test as the **artifact of proof** when sufficient. Add targeted logging, assertions, or breakpoints only to resolve the remaining uncertainty. Prefer probes that preserve failure state; instrumentation can itself affect timing or behavior.
6. **Fix the cause, not the symptom.** Before editing, state why this fix addresses the mechanism the artifact proved — _"the fix clears the leaked connection in the retry path, which is the mechanism behind the pool exhaustion"_ — not merely why it makes the symptom stop.
7. **Regression-test.** Encode the failure as a test that fails before the fix and passes after — both runs observed, not assumed. Hand the write-the-test loop to `tdd`; the reproduction from step 1 is its red.
8. **Clean up.** Remove any temporary instrumentation added during diagnosis. Keep only what earns permanent residence (an assertion stating a real invariant); scratch repros and debug logging go.

## Rules

- **Pattern-match is not diagnosis.** The click of recognition earns a hypothesis in step 4 — never the fix.
- **Never "fix" by restarting or clearing state before extracting the evidence.** The restart that makes the symptom vanish also burns the state that would have told you why — and the bug returns next week with the evidence gone.
- **One variable at a time.** Change one thing per probe, or the result attributes to nothing.
- **Two fixes, one disappearance — back one out.** If two changes are in place when the bug stops, you don't know which one worked; you have a coincidence, not a diagnosis.
- A closed diagnosis narrates symptom → mechanism → cause with the artifact of proof at the mechanism link. Anything less is a lead — label it as one.

## Pipeline mode (mode:pipeline)

Non-interactive: never pause to ask; decisions follow the calling pipeline's escalation ladder. Return a structured result whose field names align with the delegate-return vocabulary in `shared/references/pr-watch-contracts.md` (status states verbatim from there — never invent new ones):

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

If it cannot reproduce, it returns `"reproduced": false` with what it tried (commands, environments, inputs) rather than a guessed cause — a not-reproduced return is a valid result; a fabricated diagnosis is not.

## Boundaries

- `tdd` owns the red-green loop; a test failure mid-loop that you understand at a glance is just the red — fix it there, don't ceremonially invoke this.
- `fable-mindset` owns the posture (evidence over recognition, no state change without evidence); this skill owns the procedure. Cite it, don't restate it.
- `safe-incremental-coding` handles code that is merely untested; come here when behavior is _surprising_, not just unpinned.

## Gotchas

1. Do not skip reproduction because the cause "is obvious" — obvious is a hypothesis.
2. Do not fix during minimization; shrinking is measurement, not repair.
3. Do not leave step-5 instrumentation in the shipped diff.
4. Do not report "should be fixed" — the regression test passing after the fix is the sentence that ends a diagnosis.
