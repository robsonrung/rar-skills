---
name: tdd
description: 'Execute coding work test-first through the red-green-refactor loop — the pipeline''s execution-with-TDD skill. Use when implementing a feature, bug fix, or behavior change with tests; when the user says "tdd", "test-first", "red-green-refactor", "write the test first", or "implement this with tests"; and as the execution phase of a pipeline once a plan or task exists. Entry rule: untested legacy code goes to `safe-incremental-coding` first (characterization net), then returns here. Distinct from `test-lens` (judging whether an existing test is worth keeping), `clean-code` (tidying already-tested code), and `diagnose` (root-causing a bug). Do NOT use for backfilling tests onto code already written — test-after is exactly what this skill forbids.'
---

# TDD — Test-First Execution

## The Iron Law

**No production code without a failing test first.** This is enforcement, not advice:

- Code written before its test gets **deleted and redone test-first**. Not "test added after" — deleted, then rebuilt from the test.
- A test that passes on first run is wrong. You never saw it fail, so you don't know it _can_ fail. See the red before you make the green.

## Step 0 — whose code is this?

Touching untested legacy code? **STOP.** Run `safe-incremental-coding` to build the characterization net first, then return here. That skill deliberately opposes the Iron Law (no fine-grained TDD tests on legacy structure — they bake in the bad shape), which is exactly why it is a separate skill. New code, or code with tests you can stand on, proceeds directly.

## The loop

Run one loop per increment of behavior. Keep each pass small enough that you could throw it away without grief.

1. **Frame the smallest reversible move.** One caller-visible increment of behavior — the cheapest reversible learning step, smaller than feels natural. If you can't state the outcome in a sentence, the step is too big; split it. Say it while choosing: "the **smallest reversible move** here is…".
2. **Write the test first, predict the failure, see it fail.** Express _what_ the code should do from its caller's perspective. Say the expected failure out loud before running — a different failure already taught you something.
3. **Get to green the simplest way.** The least code that passes; naive is fine. This is a tactical step, not a design step — don't polish yet.
4. **Refactor under green.** _Now_ improve the design, tests passing, re-run after each tiny change. This is where design happens — diagnose smells by name with the `clean-code` vocabulary. Assert the invariants the code relies on where they must hold: an assertion is **executable documentation** that cannot drift, and its failure is a bug — crash at the assumption, never catch and continue.
5. **Integrate often.** Commit small changes every 10–15 minutes, not per-feature. Run the fast tests locally first so you're the first to see your own mistakes.

## Control the variables

You can only learn from a step if you can attribute its effect:

- **One change at a time.** Never bundle a refactor with a behavior change with a config tweak.
- An intermittent test is a **failure**, never a pass to be re-run.
- Avoid programming by coincidence. If the code passes, know why.
- **Never game the check.** Deleting, skipping, weakening, narrowing, or mocking-away a test to reach green is forbidden; if the test or contract is wrong, stop and report it (`shared/references/engineering-rules.md`, Contract integrity).

## The test-writing bar

Write-time rules. `test-lens` is the judge when an existing test's value is in question; these are the standards you write to so it never has to convict you.

- Style ranking: **output-based** (assert a pure function's return) > state-based > communication-based (mocks). Push code toward output-based with a **functional core** (pure decisions) wrapped in a **mutable shell** (thin I/O glue).
- Assert **observable behavior**, never implementation details. Never assert calls to a stub.
- **AAA** — Arrange / Act / Assert, one of each — named as a domain statement of behavior: `delivery_with_a_past_date_is_invalid`, not `testIsValid_case3`.
- A test that's hard to write is a design smell — fix the design, not the test.
- Refactoring litmus: _if the implementation were swapped for a completely different one, would this test still be valid?_ It should be.

## Pre-commit scan

Two quick passes before each integrate:

1. **Farley's five levers** — did this step make any of them noticeably worse? **Modularity, cohesion, separation of concerns, abstraction, low coupling.** If yes, refactor now while it's cheap; a passing test does not excuse code that got harder to change.
2. **"What happens if…?"** — the negative space: unexpected or invalid input, a dependency throws / times out / returns garbage, concurrency, a security or money-loss path. Thinking them through is the deliverable, even when handling one is consciously deferred.

## Per-step output contract

After each loop iteration (or coherent batch), report:

1. `changed`: what was edited.
2. `behavior`: what the code now does that it didn't before, or that behavior was preserved.
3. `risk_guarded`: the main design or data risk this step's test now guards.
4. `verification`: tests or checks run, or why they could not run.

## Routing

- Stored state, queues, retries, migrations, external APIs → run `data-systems-coding-lens` before the step.
- Smell vocabulary and naming during the refactor step → `clean-code`.
- Judging whether an existing test is worth keeping → `test-lens`.
- A bug surfaces mid-loop → `diagnose`; don't patch from a hunch.

## Gotchas

1. **Monster steps** — a half-day of code before the first test run.
2. **Test-after** — writing the test to fit code you already wrote; you lose the design feedback, and the Iron Law says delete and redo.
3. **Coverage-chasing** — coverage is a side effect of the loop, never the target.
4. **Gold-plating in green** — designing while unsafe; design belongs in the refactor step.
5. **"No time to test"** — there is no speed-vs-quality trade-off; the way to go faster is to keep rework low.
6. Do not expand scope to clean unrelated code.
7. Do not add layers, services, or helpers because they sound tidy.
8. Do not weaken harmless local coupling when the cure adds more indirection than clarity.
9. When the design needs to turn, steer green-to-green in small refactoring steps — changing your mind has a cost; that bill is the speed small steps bought you earlier.
10. Do not quote or reconstruct source text from the books this skill distills.
