---
name: small-steps
description: >-
  Work in a tight small-steps / fast-feedback rhythm during a coding session,
  distilled from Dave Farley's "Software Developers' Guidebook". Use whenever
  starting a feature, bug fix, or any non-trivial code change; whenever a change
  is growing large, branchy, or scary; whenever you're about to write new code
  and want it test-first and easy to change; or when the user says "let's build
  X", "add Y", "work in small steps", "keep this small", "TDD this", or asks how
  to approach a piece of work. Also use to sanity-check, before committing, that
  a change is small, behaviour-focused, and still easy to change. This is the
  session-cadence skill — it orchestrates HOW you make progress; lean on `tdd`
  for red-green-refactor mechanics and `clean-code` for naming/structure tidy-ups.
  Do NOT use for pure diagnosis (use `diagnose`) or macro architecture-style
  choices (use `architecture-styles`).
---

# Small Steps

A working rhythm for making progress in software, distilled from Dave Farley's
*The Software Developers' Guidebook*. The whole point: **software development is
learning, and you learn fastest by taking small steps, getting fast feedback,
and controlling the variables so you can tell what each step actually did.**

This skill is about *cadence and discipline*, not a specific technique. It tells
you how to size a step, how to keep feedback fast, and how to judge — after each
step — whether the code is still good. The single measure of "good" throughout
is **ease of change**: quality in code is your ability to change it safely.

## The core loop

Run this loop for each increment of behaviour. Keep each pass small enough that
you could throw it away without grief.

1. **Frame the smallest next step.** Identify one user-visible (or
   caller-visible) increment of behaviour — smaller than feels natural. The step
   you want is usually simpler than you think, not more complex. If you can't
   state the outcome in a sentence, the step is too big; split it.

2. **Write the test first, predict the failure, see it fail.** Express *what*
   the code should do from the perspective of its user (who may be another
   programmer). Say the expected failure out loud before running — if the test
   fails differently than predicted, you've already learned something. A test
   that's hard to write is a design smell: the code is too coupled or doing too
   much. Fix the design, not the test. (Defer to the `tdd` skill for the
   red-green-refactor mechanics.)

3. **Get back to green the simplest way.** You're in an unsafe state with a
   failing test. Write the least code that passes — naive is fine here. This is
   a tactical step, not a design step. Don't polish yet.

4. **Refactor under green.** *Now* improve the design, tests still passing,
   running them after each tiny change. This is where design happens. Leave the
   code slightly better than you found it, every single pass.

5. **Integrate often.** Commit small changes frequently — think every 10–15
   minutes, not per-feature — straight to trunk where you can. Small commits
   hide fewer problems, are easier to revert, and keep the route to production
   open. Run the fast tests locally first so you're the first to see your own
   mistakes.

The rhythm is the value: each small step is a small experiment, and you reflect
after each one. This applies to writing code, testing, refactoring, and design
alike.

## Control the variables

You can only learn from a step if you can attribute its effect. So reduce what's
changing at once:

- **One change at a time.** Don't bundle a refactor with a behaviour change with
  a config tweak. Separate them so a failure points at one cause.
- **Isolate test data.** Each test starts from a known, empty state and creates
  what it needs; share no writable data between tests; generate unique IDs.
  Shared state is the usual root of intermittent tests.
- **No reliance on timing.** Wait for an observable condition, not a sleep.
- **Version-control everything** that affects the outcome: code, tests, config,
  infra. If the environment can drift, your feedback is lying to you.
- Treat an intermittent test as a **failure**, never a pass to be re-run.

## Behaviour, not implementation

Keep tests (and your thinking) on *what* the system does, not *how*:

- Start the description with **"should"** — "should reject passwords shorter
  than 8 characters". Frame it as Given / When / Then if it helps.
- A good test survives a reimplementation. Litmus test: *if I swapped the
  implementation for a completely different one, would this test still be valid?*
  It should be.
- Avoid UI/mechanism language ("click Buy") in favour of intent ("place order").
  The UI is not the user's perspective.
- Push I/O and edges (UI, storage, network, third parties) behind a thin
  abstraction — `storeAccount(account)`, not a raw SQL string in your logic.
  Minimise edge code; maximise the easily-testable core.

## Judge each step by ease of change

Before you move on (and especially before committing), do a quick pass on the
five properties Farley returns to again and again for managing complexity. These
are levers, not a gate — if a step made one noticeably worse, that's a signal to
refactor now while it's cheap:

- **Modularity** — move unrelated code further apart.
- **Cohesion** — move related code closer together; each unit does one thing.
- **Separation of concerns** — distinct responsibilities stay distinct.
- **Abstraction** — hide detail behind intention-revealing interfaces.
- **Low coupling** — a change here shouldn't force a change there.

If the code is now harder to change than before, the step regressed quality even
if the test passes. Functions that read like a few short sentences (~5–10 lines),
named so they form sentences, are the usual outward sign you got this right.

## Before you call it done: "What happens if…?"

Happy-path-only is magical thinking. Spend a moment on the negative space, even
if you consciously decide to defer some of it:

- Unexpected/invalid inputs? Missing file, full disk?
- A dependency throws, times out, or returns garbage?
- Concurrency, queues full, load too high *or* too low?
- A security or money-loss path?

Thinking them through is the deliverable here — not necessarily handling them all
today, but never ignoring them.

## When the design needs to turn

Your understanding *will* change; revisiting design is good, not failure. Don't
attempt a big-bang redesign. Steer code and tests toward the new model in small,
safe refactoring steps, keeping tests green as long as you can. Changing your
mind has a cost — that's the bill for the speed small steps bought you earlier.

## Anti-patterns this skill exists to stop

- **Monster steps** — a half-day of code before the first test run.
- **Test-after** — writing the test to fit code you already wrote (you lose the
  design feedback entirely).
- **Chasing coverage** as a goal — coverage is a side effect of good TDD, not a
  target.
- **Gold-plating in the green phase** — designing while unsafe.
- **"No time to test / refactor"** — there's no speed-vs-quality trade-off; the
  way to go faster is to keep quality high so rework stays low.
- **Code ownership** — it's the team's code; be glad to delete it, glad to have
  it critiqued.

## A note on scope

This skill sets the *tempo*. For the red-green-refactor specifics use `tdd`; for
naming and local structure use `clean-code`; for coupling/connascence review use
`architect-lens`; for legacy code with no tests to stand on, switch to
`refactor-to-testability` first to build a safety net, then come back to this
loop.
