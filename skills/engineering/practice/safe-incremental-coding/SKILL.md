---
name: safe-incremental-coding
description: "Build characterization tests before a risky change to untested legacy code. Use to preserve existing behavior while making the affected code testable, then hand behavior changes to tdd."
---

# Safe Incremental Coding

Protect the existing behavior needed for a requested change, using the legacy change method from Dave Farley's _The Software Developers' Guidebook_. The aim is **ease of change**: the affected code can be changed safely.

Build a **characterization test** net before refactoring. Keep the work within the area needed for the requested change.

## Build the net

1. Identify the affected behavior and an observable boundary that can exercise it.
2. Capture current outputs or side effects with representative inputs, including relevant boundary and failure cases. Pin existing behavior even when it contains a known defect; an intentional behavior change is a separate step.
3. Control or normalize timestamps, identifiers, seeds, and other variable values without hiding behavior that matters to the change.
4. Prefer tests at an acceptance or integration boundary when unit tests would depend on the current internal structure.
5. If no existing boundary exposes the behavior, limit the initial production edit to the minimum observation seam. Keep its business logic unchanged and capture the baseline before further production changes.
6. Check that the test passes against the baseline and would detect a relevant change in behavior.

A passing baseline protects only the cases it exercises. Add coverage for a missing case when the requested change depends on it.

## Remove a testability obstacle

Once the net exists, identify what still prevents the requested change from being tested. Use only a structural technique that removes that obstacle.

| Obstacle | Possible change |
| --- | --- |
| Proven dead code or comments obscure the affected path | Remove that material within the requested scope. Test coverage alone does not prove code is unused. |
| A block combines several decisions that the change must isolate | Extract a cohesive operation with a name that explains its purpose. |
| Control flow hides the behavior that needs testing | Simplify the affected conditions or flow while preserving behavior. |
| A dependency prevents control of input or observation of output | Add a narrow seam or separate the relevant decision from its side effect. |
| Unrelated responsibilities prevent a focused test | Separate those responsibilities within the affected boundary. |

Choose structure that fits the surrounding code and the required test. Use supported refactoring tools when they reduce risk.

Keep each structural change **behavior-preserving**. Run the affected characterization checks after each coherent structural change before starting the next one. Investigate a failure before continuing. Broaden checks when a change or failure exposes a wider risk.

## Completion and handoff

Stop this preparation when:

1. The relevant existing behavior has a passing characterization test.
2. The requested change can be exercised through a usable test boundary.
3. Any required structural changes preserve the captured behavior.

If these conditions already hold after the net is built, proceed directly to the requested work.

For example: “The **characterization test** protects the current output, and the dependency seam lets `tdd` test the requested change.”

Use `tdd` for the intentional behavior change. Keep the characterization tests as protection while finer tests become useful. Retire one only when replacement tests demonstrably cover the same behavior.

Report the protected behavior, any testability changes, checks run, and remaining evidence gaps.

## Boundaries

1. Keep intentional behavior changes separate from characterization and refactoring.
2. Use `diagnose` when unexpected behavior needs an explanation before it can be safely pinned.
3. Use `clean-code` for local cleanup of code already protected by tests, `test-lens` for test value, and `architecture-lens` for module boundary decisions.
4. Do not quote or reconstruct source text from the book.
