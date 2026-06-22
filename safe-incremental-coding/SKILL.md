---
name: safe-incremental-coding
description: >-
  Make code changes safely in tight small steps with fast feedback — and, when
  the code is untested/legacy, build a behavior-preserving test net first.
  Distilled from Dave Farley's "The Software Developers' Guidebook". Use whenever
  starting a feature, bug fix, or any non-trivial change; whenever a change is
  growing large, branchy, or scary; whenever you're about to write new code and
  want it test-first and easy to change; whenever you must change code that has
  no tests, is scary to touch, or is tangled/deeply-nested/long ("this is
  legacy", "add tests before I refactor", "make this testable"); and to
  sanity-check, before committing, that a change is small, behavior-focused, and
  still easy to change. The defining move for legacy code is building an approval
  / characterization net BEFORE changing it. Distinct from `tdd` (red-green
  mechanics for new code, when installed), `clean-code` (tidy code that's already
  tested), and `test-lens` (judging whether a test is worth keeping). Do NOT use
  for pure diagnosis (use `diagnose`) or macro architecture-style choices (use
  `macro-architecture`).
---

# Safe Incremental Coding

A working rhythm for making progress in software, distilled from Dave Farley's *The Software Developers' Guidebook*. The whole point: **software development is learning, and you learn fastest by taking small steps, getting fast feedback, and controlling the variables so you can tell what each step actually did.** The single measure of "good" throughout is **ease of change**: quality in code is your ability to change it safely.

**Choose your entry point:**

- **Code has tests you can stand on (or is new code)** → go straight to **The core loop**.
- **Code is untested / legacy / scary / tangled** → do **Phase 0** first to build a net, then come back to the core loop for the actual behavior change.

Work **incrementally on the area you actually need to touch**, never as a big-bang rewrite. Stabilise the code you're about to change, change it, move on.

---

## Phase 0 — Get legacy code under a net (only when there are no tests to stand on)

Five ordered steps to take untested code to a state where you can change it safely. The order matters: you can't safely simplify code until there's a net under it, and you can't see the structure until the clutter is gone. Two principles frame all five:

- **Quality is your ability to change the code.** Every step exists to make the code easier to change.
- **Refactoring is *always* behavior-preserving.** If a change alters what the code does, it isn't refactoring — it's a behavior change needing its own test and its own step. Run the net (step 1) after every transformation to confirm behavior is unchanged.

### 1. Approval (characterization) tests — build the net

> "Legacy code is code without tests." — Michael Feathers

Capture the code's *current* behavior and pin it, even if weird or buggy — you're documenting reality, not judging it.
- Drive the code with representative inputs and capture its output.
- If output is nondeterministic (timestamps, UUIDs, seeds) or side-effect-only, normalize/scrub the variable parts or introduce a minimal seam to capture it before pinning.
- An approval test records output on first run, then fails on any future run whose output differs — that difference proves a change was *not* behavior-preserving.
- **Do not retrofit fine-grained, TDD-style unit tests to legacy code.** It isn't shaped for them yet; writing them now bakes in the bad structure. Approval/acceptance tests at a coarser boundary are the right net for now.
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

Restructure so the code is genuinely testable: move unrelated code apart (modularity), move related code together (cohesion), improve separation of concerns, and introduce abstractions at dependency seams so collaborators can be substituted in tests. Now you can write real unit/integration tests, coverage rises naturally, and the code is safe and pleasant to change.

| Step | Move | Done when |
|------|------|-----------|
| 1. Approval tests | Pin current behavior | A behavior change makes a test fail |
| 2. Remove clutter | Delete dead/commented code | Only live code remains |
| 3. Reduce complexity | Extract blocks, flatten flow | Low indentation, fewer paths |
| 4. Compose methods | Name & arrange sub-methods | Top function reads as a story |
| 5. Refactor to testability | Modularity + cohesion + seams | You can write real tests |

The approval tests stay as a backstop once you switch to the core loop; add finer-grained tests as the new structure supports them.

---

## The core loop

Run this loop for each increment of behavior. Keep each pass small enough that you could throw it away without grief.

1. **Frame the smallest reversible move.** One caller-visible increment of behavior — the cheapest reversible learning step, smaller than feels natural. If you can't state the outcome in a sentence, the step is too big; split it.
2. **Write the test first, predict the failure, see it fail.** Express *what* the code should do from its user's perspective. Say the expected failure out loud before running — a different failure already taught you something. A test that's hard to write is a design smell (too coupled / doing too much) — fix the design, not the test.
3. **Get back to green the simplest way.** Write the least code that passes; naive is fine. This is a tactical step, not a design step — don't polish yet.
4. **Refactor under green.** *Now* improve the design, tests passing, running them after each tiny change. This is where design happens. Leave the code slightly better than you found it, every pass.
5. **Integrate often.** Commit small changes frequently — every 10–15 minutes, not per-feature — straight to trunk where you can. Run the fast tests locally first so you're the first to see your own mistakes.

The rhythm is the value: each small step is a small experiment you reflect on.

## Control the variables

You can only learn from a step if you can attribute its effect:
- **One change at a time.** Don't bundle a refactor with a behavior change with a config tweak.
- **Isolate test data.** Each test starts from a known, empty state and creates what it needs; share no writable data; generate unique IDs.
- **No reliance on timing.** Wait for an observable condition, not a sleep.
- **Version-control everything** that affects the outcome: code, tests, config, infra.
- Treat an intermittent test as a **failure**, never a pass to be re-run.

## Observable behavior, not implementation

- Start the description with **"should"** — "should reject passwords shorter than 8 characters". Given / When / Then if it helps.
- Litmus test: *if I swapped the implementation for a completely different one, would this test still be valid?* It should be.
- Avoid UI/mechanism language ("click Buy") in favor of intent ("place order").
- Push I/O and edges (UI, storage, network, third parties) behind a thin abstraction — `storeAccount(account)`, not raw SQL in your logic. Minimize edge code; maximize the easily-testable core.

## Judge each step by ease of change

Before committing, scan the five levers Farley returns to for managing complexity — levers, not a gate; if a step made one noticeably worse, refactor now while it's cheap:

- **Modularity** — move unrelated code further apart.
- **Cohesion** — move related code closer together; each unit does one thing.
- **Separation of concerns** — distinct responsibilities stay distinct.
- **Abstraction** — hide detail behind intention-revealing interfaces.
- **Low coupling** — a change here shouldn't force a change there.

If the code is now harder to change than before, the step regressed quality even if the test passes. Functions that read like a few short sentences (~5–10 lines), named so they form sentences, are the usual sign you got it right.

## Before you call it done: "What happens if…?"

Happy-path-only is magical thinking. Spend a moment on the negative space, even if you consciously defer some of it: unexpected/invalid inputs, missing file / full disk; a dependency throws, times out, or returns garbage; concurrency, queues full, load too high *or* too low; a security or money-loss path. Thinking them through is the deliverable — not necessarily handling them all today, but never ignoring them.

## When the design needs to turn

Your understanding *will* change; revisiting design is good, not failure. Don't attempt a big-bang redesign. Steer code and tests toward the new model in small, safe refactoring steps, keeping tests green as long as you can. Changing your mind has a cost — the bill for the speed small steps bought you earlier.

## Anti-patterns this skill exists to stop

- **Monster steps** — a half-day of code before the first test run.
- **Test-after** — writing the test to fit code you already wrote (you lose the design feedback).
- **Chasing coverage** as a goal — coverage is a side effect of good TDD, not a target.
- **Gold-plating in the green phase** — designing while unsafe.
- **"No time to test / refactor"** — there's no speed-vs-quality trade-off; the way to go faster is to keep quality high so rework stays low.
- **Code ownership** — it's the team's code; be glad to delete it, glad to have it critiqued.

## A note on scope

This skill sets the *tempo* and the *legacy safety net*. For red-green-refactor specifics use `tdd` (when installed); for naming and local structure on already-tested code use `clean-code`; for whether a test is worth keeping use `test-lens`; for coupling/connascence or layer-placement review use `architecture-lens`.
