---
name: tdd
description: "Implement behavior through the red-green-refactor loop. Apply it when test-first execution is requested or selected by the coding workflow; apply safe-incremental-coding first for untested legacy code."
---

# TDD — Test-First Execution

## The Iron Law

**No behavior repair without a failing behavioral case first.** A captured failure that proves the same defect on the same code counts. A new test that passes on arrival characterizes existing behavior; it proves nothing about a missing one until you have seen it fail against a relevant counterexample.

## The loop

One loop per increment of behavior, each small enough to throw away without grief.

1. **Frame the smallest reversible move.** One caller-visible increment, smaller than feels natural. If you can't state its outcome in a sentence, split it. Say it while choosing: "the **smallest reversible move** here is…".
2. **Red.** Write the test from the caller's side, predict the failure out loud, run it. A different failure has already taught you something.
3. **Green.** The least code that passes; naive is fine. Design waits.
4. **Refactor under green.** Fix a concrete design problem, naming its smell (`clean-code`), and rerun the affected tests before the next behavior change. Assert invariants that must hold: an assertion is **executable documentation**, and its failure is a bug, never a condition to swallow.
5. **Integrate** each coherent, passing increment. When the design needs to turn, steer green-to-green in small refactoring steps.

## Control the variables

- **One change at a time.** A refactor, a behavior change, and a config tweak are three steps.
- An intermittent test is a **failure**, never a pass to re-run.
- No programming by coincidence: know why it passes.
- **Never game the check.** Deleting, skipping, weakening, narrowing, or mocking away a test to reach green is forbidden. Fix a proven test bug; a change to the accepted product contract is a decision, not a refactor.

## The test-writing bar

`test-lens` judges an existing test's value; these are the standards you write to.

- Rank styles **output-based** > state-based > communication-based. Push toward output-based with a **functional core** of pure decisions inside a thin **mutable shell** of I/O.
- Assert **observable behavior**; never assert calls to a stub.
- **AAA**, one of each, named as a domain statement: `delivery_with_a_past_date_is_invalid`, not `testIsValid_case3`.
- A test that is hard to write is a design smell; fix the design.
- Refactoring litmus: swap in a completely different implementation, and the test should still hold.

## Design and risk cues

- **Farley's five levers** (modularity, cohesion, separation of concerns, abstraction, low coupling): repair a regression in any of them within the changed scope.
- **"What happens if…?"**: pick the failure cases this behavior exposes (invalid input, dependency failure, concurrency, security, money loss).

## Handoffs

Untested legacy code gets a **characterization test** net from `safe-incremental-coding` first. An unexplained failure mid-loop goes to `diagnose`; an understood red stays in the loop.

## Gotchas

- **Monster steps**: hours of code before the first test run.
- **Test-after**: a test fitted to existing code can miss the intended behavior. Check it against the acceptance contract and a counterexample, and keep valid work rather than deleting it to redo the history.
- **Coverage-chasing**: coverage is a side effect of the loop, never the target.
- **Gold-plating in green**: design belongs in the refactor step.
- **"No time to test"**: speed comes from low rework, and small steps are what buy it.

Do not quote or reconstruct source text from the books this skill distills.
