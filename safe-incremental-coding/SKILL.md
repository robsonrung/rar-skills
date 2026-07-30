---
name: safe-incremental-coding
description: >-
  Get untested legacy code under a behavior-preserving characterization net so
  it becomes safe to change — then hand execution back to `tdd`. Distilled
  from Dave Farley's "The Software Developers' Guidebook". Use whenever you
  must change code that has no tests, is scary to touch, or is
  tangled/deeply-nested/long ("this is legacy", "add tests before I refactor",
  "make this testable", "characterization tests", "approval tests", "pin the
  current behavior first"). The defining move is building an approval /
  characterization net BEFORE changing anything. Distinct from `tdd`
  (red-green execution on new or already-tested code — the net built here
  hands back to it), `clean-code` (tidying code that already has tests), and
  `test-lens` (judging whether a test is worth keeping). Do NOT use for pure
  diagnosis (use `diagnose`) or for new code with no legacy in sight (go
  straight to `tdd`).
---

# Safe Incremental Coding — the Legacy Net

Take untested code to a state where you can change it safely, distilled from Dave Farley's *The Software Developers' Guidebook*. The single measure of "good" throughout is **ease of change**: quality in code is your ability to change it safely — and for legacy code, that ability starts with a **characterization test** net built *before* any change.

Work **incrementally on the area you actually need to touch**, never as a big-bang rewrite. Stabilise the code you're about to change, change it, move on.

Two principles frame every step:

- **Quality is your ability to change the code.** Every step exists to make the code easier to change.
- **Refactoring is *always* behavior-preserving.** If a change alters what the code does, it isn't refactoring — it's a behavior change needing its own test and its own step. Run the net (step 1) after every transformation to confirm behavior is unchanged.

## Why this is a separate skill from `tdd`

**Do not retrofit fine-grained, TDD-style unit tests to legacy code.** The code isn't shaped for them yet; writing them now bakes in the bad structure. Approval/acceptance tests at a coarser boundary are the right net for now. This rule deliberately opposes `tdd`'s Iron Law (no production code without a failing test first) — which is exactly why the two stay separate skills: `tdd` assumes code shaped for tests; legacy code must first be reshaped under a coarser net.

## The five steps

Ordered — you can't safely simplify code until there's a net under it, and you can't see the structure until the clutter is gone.

### 1. Characterization (approval) tests — build the net

> "Legacy code is code without tests." — Michael Feathers

Capture the code's *current* behavior and pin it, even if weird or buggy — you're documenting reality, not judging it.

- Drive the code with representative inputs and capture its output.
- If output is nondeterministic (timestamps, UUIDs, seeds) or side-effect-only, normalize/scrub the variable parts or introduce a minimal seam to capture it before pinning.
- An approval test records output on first run, then fails on any future run whose output differs — that difference proves a change was *not* behavior-preserving.
- Defend module/service boundaries with extra care and looser coupling (Ports & Adapters, contract tests) — they should change more slowly than the innards.

You can now modify the code and *know* whether you changed its behavior.

### 2. Remove clutter

Delete what isn't earning its keep (it isn't covered by the net and only obscures intent): dead code, unreachable branches, code called from nowhere, commented-out code, superfluous comments. Version control is your history.

### 3. Reduce complexity

Drive down cyclomatic complexity (the number of execution paths):

- **Reduce indentation** — extract the bodies of loops and `if`/`else`/`break`/`continue` blocks into well-named methods, even if called once. Name with your best guess; refine as understanding grows.
- **Eliminate `break`/`continue`** as flow clears.
- **Aim for a single exit/return point** per method.

Use your IDE's automated refactorings — faster and far less risky than hand-editing.

### 4. Compose methods — tell the story

Keep extracting and naming until a function reads as a short narrative, mostly calls to lower-level methods: group related code, separate unrelated code, choose names that make the enclosing function read like sentences, then recurse. The reader of the top-level function should understand *what* happens without wading through *how*.

### 5. Refactor to testability

Restructure so the code is genuinely testable: move unrelated code apart (modularity), move related code together (cohesion), improve separation of concerns, and introduce abstractions at dependency seams so collaborators can be substituted in tests. Now real unit/integration tests are possible, coverage rises naturally, and the code is safe and pleasant to change.

| Step | Move | Done when |
|------|------|-----------|
| 1. Characterization tests | Pin current behavior | A behavior change makes a test fail |
| 2. Remove clutter | Delete dead/commented code | Only live code remains |
| 3. Reduce complexity | Extract blocks, flatten flow | Low indentation, fewer paths |
| 4. Compose methods | Name & arrange sub-methods | Top function reads as a story |
| 5. Refactor to testability | Modularity + cohesion + seams | You can write real tests |

## Net built → hand back to `tdd`

This skill's job ends when the net holds. The actual behavior change — and all new code — runs through `tdd`'s red-green-refactor loop, which the reshaped code can now support. The characterization tests stay as a backstop; add finer-grained tests as the new structure supports them, and retire net tests only when a finer test provably covers the same behavior.

Say the handoff out loud: "the **characterization test** net holds — handing execution to `tdd`."

## Gotchas

1. Do not change behavior while building the net — pinning and changing are separate steps, and bugs get pinned too (fix them later, test-first, as their own move).
2. Do not retrofit fine-grained unit tests before the structure supports them (see above) — the coarse net comes first.
3. Do not big-bang rewrite; stabilise only the area you need to touch.
4. If the code's behavior is *surprising* rather than merely untested, that's diagnosis — route to `diagnose` before pinning a mystery.
5. Do not quote or reconstruct source text from the book this skill distills.

## A note on scope

This skill builds the *legacy safety net* only. For red-green-refactor execution use `tdd`; for naming and local structure on already-tested code use `clean-code`; for whether a test is worth keeping use `test-lens`; for coupling/connascence or layer-placement review use `architecture-lens`.
