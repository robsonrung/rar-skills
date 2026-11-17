---
name: test-lens
description: "Judge test value and choose what to test or mock. Apply it to brittle tests, test reviews, and unit or integration test design; apply tdd for the test-first execution loop."
---

# Test Lens: Valuable Unit Testing

Khorikov's framework (_Unit Testing: Principles, Practices, and Patterns_) for one question: **is this test worth its maintenance cost, and does it test the right thing the right way?** A suite exists for sustainable growth: adding features and refactoring without fear. Test code is a liability, so a few valuable tests beat many mediocre ones. Set a high bar and delete what falls below it.

## The four pillars

Score each test 0–1 on the **four pillars**. Its value is their product, so a zero on any pillar makes the test worthless.

1. **Regression protection**: how much code it exercises, weighted by complexity and domain significance.
2. **Resistance to refactoring**: how few false positives it raises when behavior is intact. This one is non-negotiable.
3. **Fast feedback**: how quickly it runs.
4. **Maintainability**: how easy it is to read and to run.

The first three trade against each other. Resistance must stay high, so the real trade is protection ⇄ speed. Each failure mode zeroes one pillar:

| Test | Zeroes | Why it is low-value |
| --- | --- | --- |
| End-to-end only | Fast feedback | Resilient and broad, but too slow to be the whole suite |
| Trivial (a plain getter) | Protection | Nothing to catch |
| **Brittle** (asserts private structure or incidental SQL and call order) | Resistance | Fails when behavior stays the same after a refactor |

Judge whether the asserted interaction is part of the contract. For example: "This has low **resistance to refactoring** because it asserts private call order that can change without changing behavior." Apply the protocol exception in Lens 3.

## Lens 1: observable behavior

The rule that matters most. False positives come from asserting _how_ the code works instead of _what_ it produces. Assert the end result a domain expert would recognize: rendered HTML rather than which sub-renderers ran, and returned rows rather than SQL text. Implementation coupling shows up as:

- asserting private calls, order, or counts that are not part of an observable protocol or required side effect;
- asserting incidental SQL text, internal collaborator structure, or private state;
- recomputing the expected value with the production formula (**leaking domain knowledge**); hardcode independently derived literals;
- a test you edit whenever a private method is renamed.

## Lens 2: style

| Style | Verifies | Quality |
| --- | --- | --- |
| **Output-based** | return value of a pure function | Best: resists refactoring by construction |
| State-based | state after the act | Acceptable when mutation is the outcome |
| Communication-based | an observable protocol or required side effect | Use the boundary and limits in Lens 3 |

Move toward output-based by splitting decisions from actions: a **functional core** that takes values and returns a decision, wrapped in a **mutable shell** that reads, delegates, and applies. Test the core with plain values. Cover the shell lightly with integration tests.

## Lens 3: doubles

- A **stub** supplies data that the code under test reads. Avoid assertions on incidental reads. Assert an interaction only when it is an observable protocol or a required side effect. Classify the method by that role, not by the name of the double.
- A **mock** stands in for an _outgoing_ side effect. Assert it only when that side effect is itself the observable outcome.
- One double can play both roles on different methods.
- A **managed dependency** is reachable only through your app, such as your database. Prefer its observable result. A focused double can check a required transaction protocol, such as use of the transaction writer before commit. This proves only the asserted protocol. Use the real dependency for claims about isolation, rollback, or concurrent writes.
- An **unmanaged dependency** is visible outside the system (SMTP, a message bus, a third-party API). Its interactions are a contract, so mock it.
- Mock **only at the system edge** (the outermost interface before I/O) and **only types you own**: wrap a third-party SDK in your own adapter and mock the adapter. A focused transaction-protocol test can use the managed-dependency exception above; it does not prove database behavior.

## Lens 4: what to test

Classify the code by complexity or domain significance × number of collaborators:

|  | Few collaborators | Many collaborators |
| --- | --- | --- |
| **High complexity** | **Domain model / algorithms**: unit-test hard | **Overcomplicated**: split it |
| **Low complexity** | **Trivial**: skip | **Controllers**: a few integration tests |

Drain the overcomplicated quadrant with **Humble Object**. Move the logic into a pure domain or algorithm object and test it output-based. The humble wrapper that remains only orchestrates dependencies. Coverage is a side effect, not a goal, and no test is better than a bad one.

Integration tests cover a controller with at least one real out-of-process dependency. Take the longest path, the one that touches the most dependencies, plus one shortest happy path. Test logging only when another system consumes it, as with an audit log, which is effectively an unmanaged dependency.

## Anti-patterns

| Anti-pattern | Fix |
| --- | --- |
| Testing private methods | Complex private logic is a missing abstraction: extract a class and test it publicly |
| Exposing private state to assert on it | Assert observable behavior instead |
| Code pollution (test-only flags in production) | Inject the varying behavior |
| Mocking a concrete class while keeping half of it | SRP violation: split logic from I/O and mock the I/O side |
| Time as ambient context (`Date.now()`) | Inject a clock and pass a fixed time in tests |
| Asserting incidental interactions with stubs | Remove the assertion; retain observable protocol checks under Lens 3 |
| Coverage as the target | Set a value bar per test, even if coverage drops |

## Mechanics

- **AAA**, one of each. More than one act means an integration test. Keep `if` out of tests, and keep the act to one line.
- Name each test as a domain statement a non-programmer can read: `delivery_with_a_past_date_is_invalid`.
- Parameterize similar cases, but keep distinct behaviors in separate tests.
- Share fixtures through factory functions, not shared mutable `beforeEach` state.

## State, fixtures, and evidence

- For stateful or asynchronous code, derive a small case table from the real state machine. Cover meaningful event orders and retained invariants, not each handler once. Carry a prior defect case forward when the same causal path exists.
- A passing fixture proves only the boundary it exercises. Exercise production adapters with representative stored values, including absent, legacy, and malformed ones when the schema allows them. Use real transactions for lock and rollback claims. Give a fixture no stronger schema than production has. Use inputs whose correct and wrong results differ. Assert associated identities together. Keep distinct doubles when the wrong writer must fail the test; this proves writer selection, not database isolation.
- Report model, DOM, partial-browser, and full-application evidence separately. A DOM test or screenshot cannot establish deployed authorization, and test counts cannot establish completeness.

## Tests that cannot fail, or cannot run

- An assertion that a failed setup skips (inside a branch, or a loop that can be empty) proves nothing; assert the setup produced its record first.
- A fixture the code does not recognize (an unknown route, a removed flag) takes the early return, and the test passes over nothing. Break the behavior on purpose; the test must fail. Make setup pass earlier guards, then assert the intended failure or result. A generic rejection does not identify the guard that rejected the request.
- A test asserts only behavior its own change implements, and waits for a state, never a fixed time.
- The test file passes the workspace's type check, lint, and build, not only the runner. After a fix changes behavior, search for assertions on the old behavior; a new export of a mocked module goes into every hand-written mock of it.
- No machine-specific values: ports, container names, and paths come from configuration. A local suite refuses a non-local target, scopes its cleanup to its own tenant, and restores shared state from disk, not memory.

## Reporting

For a test under review, score the four pillars and name the weakest. Then apply the lenses that fit. Each finding reads `file:line` → the rule → the fix. Recommend a rewrite or deletion when any pillar is near zero, and say plainly when a test is already good.
