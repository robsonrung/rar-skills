---
name: tdd
description: "Implement behavior through the red-green-refactor loop. Use when test-first execution is requested or selected by the coding workflow; use safe-incremental-coding first for untested legacy code."
---

# TDD — Test-First Execution

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

## The Iron Law

**Establish a failing behavioral case before a requested behavior repair.** Reuse a captured failure when it proves the same defect on the same code.

- Preserve existing valid work. Do not delete and recreate code solely to change the order of its history.
- A passing new test can characterize existing behavior. It does not demonstrate a missing behavior or prove that the test is wrong. Use a relevant failure or controlled counterexample to establish what it detects.

## Step 0 — whose code is this?

For a risky change to untested legacy code, use `safe-incremental-coding` for the missing characterization. Reuse existing behavioral and failure evidence that covers the changed surface. Proceed directly when that protection already exists.

## The loop

Run one loop per increment of behavior. Keep each pass small enough that you could throw it away without grief.

1. **Frame the smallest reversible move.** One caller-visible increment of behavior — the cheapest reversible learning step, smaller than feels natural. If you can't state the outcome in a sentence, the step is too big; split it. Say it while choosing: "the **smallest reversible move** here is…".
2. **Write the test first, predict the failure, see it fail.** Express _what_ the code should do from its caller's perspective. Say the expected failure out loud before running — a different failure already taught you something.
3. **Get to green the simplest way.** The least code that passes; naive is fine. This is a tactical step, not a design step — don't polish yet.
4. **Refactor under green.** Improve a concrete design problem, then run the affected tests before the next behavior change. Use `clean-code` to name a smell when one exists. Assert internal invariants where they must hold: an assertion is **executable documentation**, and its failure is a bug rather than a condition to catch and ignore.
5. **Integrate coherent increments.** Keep each increment small and passing. Commit only when the user or caller has authorized it; use completed behavior and passing checks to choose the boundary, not a timer.

## Control the variables

You can only learn from a step if you can attribute its effect:

- **One change at a time.** Never bundle a refactor with a behavior change with a config tweak.
- An intermittent test is a **failure**, never a pass to be re-run.
- Avoid programming by coincidence. If the code passes, know why.
- **Never game the check.** Deleting, skipping, weakening, narrowing, or mocking-away a test to reach green is forbidden; correct a proven test implementation error within repair authority. A change to the accepted product contract needs a decision (`shared/references/engineering-rules.md`, Contract integrity).

## The test-writing bar

Write-time rules. `test-lens` is the judge when an existing test's value is in question; these are the standards you write to so it never has to convict you.

- Style ranking: **output-based** (assert a pure function's return) > state-based > communication-based (mocks). Push code toward output-based with a **functional core** (pure decisions) wrapped in a **mutable shell** (thin I/O glue).
- Assert **observable behavior**, never implementation details. Never assert calls to a stub.
- **AAA** — Arrange / Act / Assert, one of each — named as a domain statement of behavior: `delivery_with_a_past_date_is_invalid`, not `testIsValid_case3`.
- A test that's hard to write is a design smell — fix the design, not the test.
- Refactoring litmus: _if the implementation were swapped for a completely different one, would this test still be valid?_ It should be.

## Design and risk cues

Use these cues while choosing tests and refactoring; they do not require another review pass before each integration.

1. **Farley's five levers**: **modularity, cohesion, separation of concerns, abstraction, low coupling**. Address a regression in these properties within the changed scope.
2. **"What happens if…?"**: select the failure cases exposed by this behavior, such as invalid input, dependency failure, concurrency, security, or money loss. Reuse cases and decisions already present in the acceptance contract.

## Per-step output contract

After each loop iteration (or coherent batch), report:

1. `changed`: what was edited.
2. `behavior`: what the code now does that it didn't before, or that behavior was preserved.
3. `risk_guarded`: the main design or data risk this step's test now guards.
4. `verification`: tests or checks run, or why they could not run.

## Routing

- Stored state, queues, retries, migrations, external APIs → reuse the approved data-systems-coding-lens findings. Run the lens only for an uncovered data risk or a changed design surface, not before every loop iteration.
- Smell vocabulary and naming during the refactor step → `clean-code`.
- Judging whether an existing test is worth keeping → `test-lens`.
- An unexplained failure surfaces mid-loop → `diagnose`. An understood red or regression stays in the current loop; use the existing evidence instead of starting a second investigation.

## Gotchas

1. **Monster steps** — a half-day of code before the first test run.
2. **Test-after** — a test fitted to existing code can miss the intended behavior. Check it against the acceptance contract and a relevant counterexample; preserve valid work.
3. **Coverage-chasing** — coverage is a side effect of the loop, never the target.
4. **Gold-plating in green** — designing while unsafe; design belongs in the refactor step.
5. **"No time to test"** — there is no speed-vs-quality trade-off; the way to go faster is to keep rework low.
6. Do not expand scope to clean unrelated code.
7. Do not add layers, services, or helpers because they sound tidy.
8. Do not weaken harmless local coupling when the cure adds more indirection than clarity.
9. When the design needs to turn, steer green-to-green in small refactoring steps — changing your mind has a cost; that bill is the speed small steps bought you earlier.
10. Do not quote or reconstruct source text from the books this skill distills.
