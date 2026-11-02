---
name: safe-incremental-coding
description: "Build characterization tests before a risky change to untested legacy code. Apply it to preserve existing behavior while making the affected code testable, then hand behavior changes to tdd."
---

# Safe Incremental Coding

Farley's legacy-change method, aimed at **ease of change**: protect the behavior a requested change touches, then make that code testable. Stay inside the area the change needs.

## Build the net

A **characterization test** net pins current behavior before any refactoring.

1. Find the affected behavior and an observable boundary that exercises it. Prefer an acceptance or integration boundary when unit tests would bind to the current internals.
2. Capture current outputs and side effects for representative inputs, including boundary and failure cases. Pin a known defect too; changing it is a separate, intentional step.
3. Normalize timestamps, identifiers, and seeds without hiding behavior the change depends on.
4. When no boundary exposes the behavior, the first production edit is the minimum observation seam, with business logic untouched. Capture the baseline before any other production change.
5. Confirm the net passes on the baseline and would catch a relevant change.

The net protects only the cases it exercises. Add any case the requested change depends on.

## Remove a testability obstacle

Use only the structural move that removes what still blocks testing the change:

| Obstacle | Move |
| --- | --- |
| Proven dead code or comments obscure the path | Remove them. Coverage alone does not prove code unused. |
| One block makes several decisions the change must isolate | Extract a cohesive, well-named operation. |
| Control flow hides the behavior under test | Simplify the affected conditions or flow. |
| A dependency blocks controlling input or observing output | Add a narrow seam, or split the decision from its side effect. |
| Unrelated responsibilities block a focused test | Separate them within the affected boundary. |

Each move is **behavior-preserving**. Run the net after each coherent move, and stop to investigate any failure before the next.

## Done

Preparation is done when:

1. The relevant existing behavior has a passing characterization test.
2. The requested change can be exercised through a usable test boundary.
3. Every structural change preserved the captured behavior.

Say it like this: "The **characterization test** protects the current output, and the dependency seam lets `tdd` test the requested change."

Hand the intentional behavior change to `tdd`. Keep the net until finer tests demonstrably cover the same behavior. Report the protected behavior, the testability changes, the checks run, and the remaining evidence gaps. Behavior that surprises you and needs explaining before you can pin it goes to `diagnose`.

Do not quote or reconstruct source text from the book.
