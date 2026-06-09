---
name: test-lens
description: Judge and write valuable unit/integration tests using Khorikov's framework — score tests on the four pillars (regression protection, resistance to refactoring, fast feedback, maintainability), test observable behavior not implementation details, pick the right testing style, and apply the mock-vs-stub / managed-vs-unmanaged rules. Use when writing tests, reviewing tests, deciding WHAT to test or WHETHER a test is worth keeping, when a test is brittle/flaky on refactor, or when deciding what to mock. Triggers on "is this a good test", "why does this test break when I refactor", "should I mock this", "what should I test here", "review my tests", "is this test worth it". Distinct from tdd (red-green loop mechanics), clean-code (prod readability), and code-review (bugs).
---

# Test Lens — Valuable Unit Testing

Judge or write tests through the framework in *Unit Testing: Principles, Practices, and
Patterns* (Vladimir Khorikov). This is **not** the red-green loop (use `tdd` for cadence)
and **not** a bug hunt (use `code-review`). It answers one question: **is this test worth
its maintenance cost, and does it test the right thing the right way?**

The goal of a test suite is **sustainable project growth** — letting you add features and
refactor without fear. A small number of highly valuable tests beats a large number of
mediocre ones. **Test code is a liability too.** Set a high bar; delete tests that don't clear it.

Examples below are TypeScript + Jest. Apply the lens, then report findings concretely:
cite `file:line`, name the rule, propose the fix. If a test is already good, say so plainly.

## The core rubric: the four pillars

Every test is scored 0–1 on four attributes; **value = the four multiplied**. A zero on any
pillar makes the test worthless — even if it's perfect on the other three.

1. **Protection against regressions** — how much code (yours + libraries) the test exercises,
   weighted by complexity and domain significance. Trivial code → low protection.
2. **Resistance to refactoring** — how few **false positives** (failures when behavior is
   intact) it produces. Driven entirely by coupling to implementation details. **Non-negotiable.**
3. **Fast feedback** — how quickly it runs.
4. **Maintainability** — how hard it is to read and to run (setup, out-of-process deps).

**Key tension:** the first three are mutually exclusive — you can't maximize all three.
Since resistance-to-refactoring must stay high, you trade **protection ⇄ fast feedback**.
The three classic failure modes, each maxing two pillars and zeroing a third:

| Test type | Sacrifices | Why it's low-value |
|-----------|-----------|--------------------|
| End-to-end only | Fast feedback | Great coverage + resilient, but too slow to be the whole suite |
| Trivial (`expect(user.name).toBe('John')` on a plain getter) | Protection | Nothing to catch |
| **Brittle** (asserts SQL string / call order / private structure) | Resistance to refactoring | Breaks on every refactor → ignored → real bugs slip through |

> Brittle tests are the dangerous ones. They train the team to ignore failures, then a real
> regression rides along with the noise into production.

## Lens 1 — Observable behavior, not implementation details

The **single most important rule.** False positives come from coupling a test to *how* the
code works instead of *what* it produces. Verify the **end result meaningful to a domain
expert / end user** — disregard the steps taken to get there.

Red flags (all couple to implementation):
- Asserting which internal methods were called, in what order, or how many times (on a stub).
- Asserting a generated SQL string, the list/types of internal collaborators, or private state.
- A test that mirrors the production algorithm step-for-step ("leaking domain knowledge").
- A test you must edit every time you rename a private method or reshuffle internals.

> A good test tells a story about the problem domain. If it fails, the story and the code
> disagree — and that's the only failure worth your attention.

## Lens 2 — Pick the right style (ranked)

| Style | Verifies | Quality | Prefer when |
|-------|----------|---------|-------------|
| **Output-based** | return value of a pure function | **Best** — naturally resists refactoring | always, if the code allows |
| State-based | object/system state after the act | OK — can tie to leaking state | mutation is the actual outcome |
| Communication-based | calls to collaborators (mocks) | Most brittle | only at the system edge, for unmanaged deps |

Push code toward **output-based** by separating decisions from actions: a **functional core**
(pure business logic, easy to output-test) wrapped in a **mutable shell** (thin, does I/O).
This is hexagonal architecture taken to its extreme. See `references/decision-trees.md`.

## Lens 3 — Mocks: stub vs mock, managed vs unmanaged

The rules agents most often get wrong. Full flowchart in `references/decision-trees.md`.

- **Stub** = emulates an *incoming* interaction (input data the SUT reads). **Never assert
  calls to a stub** — that's overspecification and the #1 source of fragile tests.
- **Mock** = emulates an *outcoming* interaction (a side effect the SUT causes). Asserting it
  is fine *only* when that side effect is itself the observable outcome.
- **Managed dependency** (you fully control it; only your app touches it — e.g. your DB):
  interactions are **implementation details** → use the **real thing** in integration tests.
- **Unmanaged dependency** (externally observable — SMTP, message bus, third-party API):
  interactions are **observable behavior / a contract** → **mock it**.
- Mock **only at the system edge**, and **only types you own** — wrap third-party SDKs in
  your own adapter and mock the adapter, not the library.

## Lens 4 — What to test at all (the code quadrant)

Classify the code under test on two axes — **complexity/domain significance** × **number of
collaborators**:

| | Few collaborators | Many collaborators |
|---|---|---|
| **High complexity/significance** | **Domain model / algorithms** → unit-test hard (best ROI) | **Overcomplicated** → refactor: split into the two below |
| **Low** | **Trivial** → don't test | **Controllers** → a few integration tests |

> The more important or complex the code, the **fewer collaborators** it should have.

The overcomplicated quadrant (e.g. a fat controller doing real logic *and* I/O) is the trap.
Split it with the **Humble Object** pattern: extract the logic into a pure
algorithm/domain class (unit-test it output-based), leaving a thin humble wrapper that just
glues to dependencies (cover lightly via integration tests). **100% coverage is not the
goal** — it's possible to have high coverage and worthless tests (and vice versa);
significant value per test is. Better no test than a bad test.

## Anti-pattern checklist (flag these)

- Testing **private methods** → a private method doing complex work is a missing abstraction; extract a class.
- **Exposing private state** just to assert on it → test observable behavior instead.
- **Leaking domain knowledge** → test hardcodes the algorithm's expected intermediate math.
- **Code pollution** → test-only switches/flags in production code.
- **Mocking concrete classes** to keep half their behavior → SRP violation; split the class.
- **Time as ambient context** (`Date.now()` reached directly) → inject time as an explicit dependency.
- Asserting interactions **with stubs**, or chasing a **coverage number** as the target.

## Mechanics (when writing tests)

- **AAA** — Arrange / Act / Assert, one of each; if you need multiple act sections it's
  probably an integration test. No `if` statements in a test (split it). Keep the act to one
  line for a unit of behavior.
- **Name** the test as a domain statement of behavior — `delivery_with_a_past_date_is_invalid`,
  not `IsValid_PastDate_ReturnsFalse`. No method names in the title; a non-programmer should read it.
- **Parameterize** similar cases (`it.each`) — but keep distinct behaviors as separate tests.
- Reuse fixtures via **factory functions**, not shared mutable state in `beforeEach` (high
  coupling between tests is an anti-pattern).

## Workflow

1. **Whose test is this?** New code → guide style choice (Lens 2/4) before writing. Existing
   test under review → score it.
2. **Score the four pillars.** Name the weakest. If any is ≈0, recommend rewrite or deletion.
3. **Apply the lenses** that fit: observable-behavior (always), mock rules (if it has doubles),
   quadrant (if deciding what/whether to test).
4. **Run the anti-pattern checklist.**
5. **Report** concretely per finding: `file:line` → which rule → the fix. Skip lenses that
   don't apply rather than padding.

For the detailed decision trees (style transition, mock flowchart, Humble Object refactor,
integration-test rules — path selection, logging, pyramid — and the full anti-pattern
catalog with before/after code), read `references/decision-trees.md`.
