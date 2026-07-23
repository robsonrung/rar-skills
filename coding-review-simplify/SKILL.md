---
name: coding-review-simplify
description: Final review-and-simplify pass on a just-completed implementation before handoff. Use after an agent finishes coding work, or when the user asks to tighten, audit maintainability, remove unnecessary abstraction, verify architecture fit, or check data risk in a concrete diff.
---

# Coding Review Simplify

Use this skill after code has been changed or when reviewing a concrete diff. The goal is to catch correctness risks and simplify the result before handoff.

## Workflow

1. Read the user request, changed files, diff, and verification already run.
2. Check whether the implementation matches the intended behavior and chosen design shape.
3. Review the smallest relevant surface first, then expand only if the diff crosses boundaries.
4. For a standard or deep review, dispatch the Persona Pass below.
5. Run the Simplification Pass below.
6. Check names, responsibilities, interfaces, and edge cases for one coherent model.
7. If stored state or async behavior changed, review source of truth, invariants, retries, migrations, compatibility, observability, and repair path.
8. If the diff feels tangled or crosses a boundary, run the Connascence Pass below.
9. Turn important concerns into a focused fix, test, static check, contract check, migration check, or explicit follow up.
10. Finish with the shortest honest outcome.

## Review Modes

Choose one mode:

1. Light review for a narrow local change. Focus on behavior, naming, simple control flow, and verification.
2. Standard review for multiple files, shared helpers, APIs, persistence, or meaningful tests. Add boundary, data, and regression checks.
3. Deep review for service boundaries, public contracts, migrations, data ownership, deployment behavior, or long lived decisions. Add tradeoff and decision note checks.

## Persona Pass

For standard and deep reviews (skip in light mode unless the user asks), spawn three reviewer subagents **in parallel** — one message, three calls. Seed each with its persona file plus the diff or resolved file set:

1. `references/personas/code-reuse-reviewer.md` — new code that duplicates existing utilities, reimplements stdlib/runtime primitives, or hand-maintains guarantees a platform layer already provides.
2. `references/personas/code-quality-reviewer.md` — redundant state, parameter sprawl, copy-paste variants, leaky abstractions, stringly-typed code, dead code.
3. `references/personas/efficiency-reviewer.md` — wasted work, missed concurrency, hot-path bloat, no-op update storms, memory leaks.

Every persona is behavior-preserving by contract. Merge their findings through the Findings Bar below: dedupe, keep exact `file:line` references, drop anything below the bar, and reject at merge any finding that would change observable behavior.

## Connascence Pass

Use this only when the diff feels tangled or crosses a boundary. Measure coupling as **connascence** — two pieces of code are connascent when changing one forces a change in the other — and name it along its three axes:

1. Strength: is the connascence static and visible, or dynamic and runtime dependent?
2. Locality: is it inside one cohesive unit, or across modules, services, contracts, or teams?
3. Degree: how many callers, files, records, or systems must change together?
4. Remedy: weaken the strongest distant connascence first, such as replacing magic values with names, positional arguments with named data, hidden order with explicit state, or duplicated algorithms with one owned implementation. The rule of thumb: the more distant the coupling, the weaker its strength should be.
5. Restraint: leave local static connascence alone when extraction would add indirection without safety.

## Findings Bar

Report a finding only when it can cause a bug, regression, maintenance trap, architecture drift, data risk, weak verification, or meaningful reader confusion.

For each finding, include:

1. Where it is.
2. Why it matters.
3. The smallest useful fix.
4. The verification that would prove it.

## Simplification Pass

**Never simplify away a safety check.** Validation at trust boundaries, authorization checks, invariant assertions, escaping and encoding, and accessibility affordances are not removable boilerplate — they stay even when they look redundant from the local diff, and even when a lower layer appears to cover them. Defense in depth is intentional; if a check is truly dead, prove it with a citation, don't assume it.

Before final delivery, ask — every answer must stay **behavior-preserving**, since this is simplification, not a behavior change:

1. Can any new abstraction be deleted or made local?
2. Can dead code, leftover indirection, broad helpers, or noisy comments be removed?
3. Can a name make a helper unnecessary?
4. Can control flow be flatter without changing behavior?
5. Can duplicated code stay duplicated because the concepts may diverge?
6. Can a test express the invariant better than a comment, asserting **observable behavior** rather than implementation detail?
7. Does the final code still fit the repo style?

## Output Contract

For review only, lead with findings ordered by severity and include file and line references.

For completed implementation work, include:

1. `outcome`: safe as is, simplified, needs one focused fix, or needs design escalation.
2. `changes`: simplifications or fixes made.
3. `verification`: tests or checks run.
4. `remaining_risk`: what still needs attention, if anything.

**Net lines removed is not the success metric.** Never report the pass as "-N lines" — that metric rewards deleting safety checks and inlining named concepts. Summarize per dimension with quantities instead: duplications replaced with existing utilities, abstractions deleted or made local, dead code paths removed, inefficiencies fixed, findings deferred. A simplification that adds lines to remove distant coupling is still a win.

## Gotchas

1. Do not perform a full architecture review by default.
2. Do not generate ADRs routinely.
3. Do not expand scope after implementation unless there is a correctness or safety issue.
4. Do not rewrite clear code into clever code.

---
*Persona Pass and its reference personas adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
