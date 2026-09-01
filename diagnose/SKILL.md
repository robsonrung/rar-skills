---
name: diagnose
description: >-
  Procedural debugging from reproduction to regression test — reproduce,
  minimize, read the actual error, differential hypotheses, instrument, fix
  the cause, encode the regression. Use when a bug, failing test, or
  unexpected behavior needs root-causing; when the user says diagnose this,
  debug this, find the root cause, or why does this fail; or when a pipeline
  loops a verify failure back to implementation (mode:pipeline for the
  non-interactive structured return). Distinct from `tdd` (owns the
  implementation loop — a test failure understood at a glance mid-loop needs
  no diagnosis), `fable-mindset` (the epistemic posture of its Diagnosis
  moment — this skill is the procedure), and `full-review` (finds issues in
  diffs, not in live failures).
---

# Diagnose — From Symptom to Proven Cause

The step-by-step procedure for root-causing a failure. The posture comes from
`fable-mindset`'s Diagnosis moment — **pattern-match is not diagnosis**:
recognition proposes, evidence disposes — and every step below exists to turn
a recognition into evidence or kill it. Say the leitwörter as you work; they
are the checkpoints.

## The procedure

1. **Reproduce first.** A bug you cannot reproduce is a report, not a
   diagnosis. Capture the exact failing command and its exact output before
   anything else — that pair is the ground truth every later step is measured
   against. If you cannot reproduce it, say so and stop guessing (see the
   pipeline return below).
2. **Minimize.** Shrink the input, the scope, and the setup until the failure
   is tight: smallest input that fails, fewest components involved, shortest
   path from command to symptom. Every layer removed is a hypothesis you no
   longer have to hold.
3. **Read the actual error and the actual code path.** The real message, the
   real stack, the real code it names — before hypothesizing. The tell that
   you skipped this: your explanation describes similar bugs ("this is
   usually…") instead of facts from this one.
4. **Differential hypotheses.** List the 2–3 candidate causes that fit the
   evidence. For each, say what evidence would discriminate it from the
   others, then run the **cheapest discriminating probe** first: *"a log line
   at the cache read splits stale-key from race — cheaper than bisecting, so
   it goes first."* A probe that cannot tell two hypotheses apart is not worth
   running.
5. **Instrument.** Add targeted logging, assertions, or breakpoints until the
   surviving hypothesis produces an **artifact of proof** — a printed value, a
   log line, a failing test you wrote. Instrumentation is not a state change:
   it creates evidence and destroys none, which is exactly what fix-shaped
   moves (restart, clear, reinstall) do not.
6. **Fix the cause, not the symptom.** Before editing, state why this fix
   addresses the mechanism the artifact proved — *"the fix clears the leaked
   connection in the retry path, which is the mechanism behind the pool
   exhaustion"* — not merely why it makes the symptom stop.
7. **Regression-test.** Encode the failure as a test that fails before the fix
   and passes after — both runs observed, not assumed. Hand the write-the-test
   loop to `tdd`; the reproduction from step 1 is its red.
8. **Clean up.** Remove the instrumentation from step 5. Keep only what earns
   permanent residence (an assertion stating a real invariant); scratch repros
   and debug logging go.

## Rules

- **Pattern-match is not diagnosis.** The click of recognition earns a
  hypothesis in step 4 — never the fix.
- **Never "fix" by restarting or clearing state before extracting the
  evidence.** The restart that makes the symptom vanish also burns the state
  that would have told you why — and the bug returns next week with the
  evidence gone.
- **One variable at a time.** Change one thing per probe, or the result
  attributes to nothing.
- **Two fixes, one disappearance — back one out.** If two changes are in place
  when the bug stops, you don't know which one worked; you have a coincidence,
  not a diagnosis.
- A closed diagnosis narrates symptom → mechanism → cause with the artifact of
  proof at the mechanism link. Anything less is a lead — label it as one.

## Pipeline mode (mode:pipeline)

Non-interactive: never pause to ask; decisions follow the calling pipeline's
escalation ladder. Return a structured result whose field names align with the
delegate-return vocabulary in `shared/references/pr-watch-contracts.md`
(status states verbatim from there — never invent new ones):

```json
{
  "status": "fixed-and-pushed | diagnosed-no-fix | flaky-infra | needs-human",
  "reproduced": true,
  "root_cause": "<causal chain: symptom → mechanism → cause>",
  "evidence": "<the artifact of proof>",
  "fix": "<commits or diff, null when no fix>",
  "regression_test": "<test name/path, or null>",
  "residuals": [ { "title": "...", "decision_context": "..." } ]
}
```

If it cannot reproduce, it returns `"reproduced": false` with what it tried
(commands, environments, inputs) rather than a guessed cause — a not-reproduced
return is a valid result; a fabricated diagnosis is not.

## Boundaries

- `tdd` owns the red-green loop; a test failure mid-loop that you understand at
  a glance is just the red — fix it there, don't ceremonially invoke this.
- `fable-mindset` owns the posture (evidence over recognition, no state change
  without evidence); this skill owns the procedure. Cite it, don't restate it.
- `safe-incremental-coding` handles code that is merely untested; come here
  when behavior is *surprising*, not just unpinned.

## Gotchas

1. Do not skip reproduction because the cause "is obvious" — obvious is a
   hypothesis.
2. Do not fix during minimization; shrinking is measurement, not repair.
3. Do not leave step-5 instrumentation in the shipped diff.
4. Do not report "should be fixed" — the regression test passing after the fix
   is the sentence that ends a diagnosis.
