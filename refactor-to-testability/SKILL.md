---
name: refactor-to-testability
description: >-
  Tame untested or hard-to-change legacy code by following Dave Farley's five
  ordered steps to testability (from "The Software Developers' Guidebook"). Use
  whenever you must change code that has no tests, is scary to touch, or is
  tangled/deeply-nested/long; whenever the user says "this is legacy", "there
  are no tests", "I'm afraid to change this", "characterise this", "add tests
  before I refactor", "untangle this function", or "make this testable"; and as
  the safety-net step BEFORE applying test-first work to existing code. The
  defining move is building a behaviour-preserving net first (approval /
  characterisation tests) rather than retrofitting unit tests. Distinct from
  `tdd`/`small-steps` (new code, test-first) and `clean-code` (tidy code that's
  already tested). Do NOT use to design new functionality from scratch.
---

# Refactor to Testability

A procedure for getting legacy code — code that is hard to change because it has
no tests — into a state where you can change it safely. Distilled from Dave
Farley's *The Software Developers' Guidebook*.

Two principles frame everything below:

- **Quality is your ability to change the code.** Legacy code is a problem
  precisely because it's hard to change; the goal of every step is to make it
  easier to change.
- **Refactoring is *always* behaviour-preserving.** If a change alters what the
  code does, it isn't refactoring — it's a behaviour change, and it needs its
  own test and its own step.

Work **incrementally on the area you actually need to touch**, not the whole
codebase, and never as a big-bang rewrite. Stabilise the code you're about to
change, change it, move on.

## The five steps (in order)

The order matters: you can't safely simplify code until you have a net under it,
and you can't see the structure until the clutter is gone.

### 1. Approval (characterisation) tests — build the net

> "Legacy code is code without tests." — Michael Feathers

Before changing anything, capture the code's *current* behaviour and pin it,
even if that behaviour is weird or buggy — you're documenting reality, not
judging it.

- Drive the code with representative inputs and capture its output.
- An approval test records that output on first run, then fails on any future
  run whose output differs. That difference is your alarm: it proves a change
  was *not* behaviour-preserving.
- **Do not retrofit fine-grained, TDD-style unit tests to legacy code.** The
  code isn't shaped for them yet, and writing them now bakes in the bad
  structure. Approval/acceptance tests at a coarser boundary are the right net
  for now.
- Defend module/service boundaries with extra care and looser coupling (e.g.
  Ports & Adapters, contract tests) — they should change more slowly than the
  innards.

You now have a safety net: you can modify the code and *know* whether you
changed its behaviour.

### 2. Remove clutter

With the net in place, delete what isn't earning its keep. Clutter isn't covered
by your approval tests and only obscures intent.

- Delete dead code, unreachable branches, and code called from nowhere.
- Delete commented-out code and superfluous comments — version control is your
  history, so there's no reason to keep "just in case" corpses.
- Run the approval tests after removals to confirm behaviour is unchanged.

This alone sharpens the structure and reveals where the real work is.

### 3. Reduce complexity

Cyclomatic complexity (the number of execution paths) is what makes code hard to
follow and change. Drive it down:

- **Reduce indentation.** Extract the bodies of `for`/`while` loops and
  `if`/`else`/`break`/`continue` blocks into well-named methods — even if a block
  is only called once. Name each with your best guess of its purpose; you'll
  refine as understanding grows.
- **Eliminate `break`/`continue`** as the flow becomes clearer.
- **Aim for a single exit/return point** per method.

These flatten control flow and make the next step possible. Use your IDE's
automated refactorings — they're faster and far less risky than hand-editing.

### 4. Compose methods — tell the story

Keep extracting and naming until a function reads as a short narrative of what it
does, mostly calls to lower-level methods:

- Group related code; separate unrelated code.
- Choose descriptive names that make the enclosing function read like sentences.
- Extract each block into a named method, then recurse into those methods and
  compose them too.

The aim: someone reading the top-level function understands *what* happens
without wading through *how*.

### 5. Refactor to testability

Now restructure so the code is genuinely testable, simplifying and clarifying
dependencies. This is the same move as designing for testability in new code:

- **Move unrelated code apart** (increase modularity).
- **Move related code together** (improve cohesion).
- Improve **separation of concerns** and introduce **abstractions** at
  dependency seams so collaborators can be substituted in tests.

The payoff: you can now write unit and integration tests, coverage rises
naturally, and — most importantly — the code is safe and pleasant to change.

## After the net is in place

Once the code is testable, hand off to the normal test-first rhythm: switch to
the `small-steps` / `tdd` loop for the actual behaviour change you came here to
make. The approval tests stay as a backstop; add finer-grained tests as the new
structure supports them.

## Quick reference

| Step | Move | Done when |
|------|------|-----------|
| 1. Approval tests | Pin current behaviour | A behaviour change makes a test fail |
| 2. Remove clutter | Delete dead/commented code | Only live code remains |
| 3. Reduce complexity | Extract blocks, flatten flow | Low indentation, fewer paths |
| 4. Compose methods | Name & arrange sub-methods | Top function reads as a story |
| 5. Refactor to testability | Modularity + cohesion + seams | You can write real tests |

Keep every step behaviour-preserving, confirmed by the net from step 1.
