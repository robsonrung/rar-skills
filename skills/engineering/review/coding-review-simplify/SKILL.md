---
name: coding-review-simplify
description: Simplify a completed code change through behavior-preserving reuse, quality, efficiency, and connascence passes. Use after a scoped task or when the user asks to simplify a concrete diff; use full-review for a feature or deep review.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Edit
  - Agent
---

# Coding Review Simplify

Tighten a completed diff while its context is fresh. Every change this pass makes is **behavior-preserving**: the **observable behavior** (outputs, errors, side effects, ordering) stays exactly as it was. Success is a simpler change, not fewer lines.

## Workflow

1. Read the diff, the changed files, the task's acceptance contract, and the verification already captured. Expand past the changed surface only across a real boundary.
2. Check the change against its intended observable behavior. Report a concern only when it can cause a bug, regression, data risk, weak verification, or maintenance trap.
3. Run the reuse, quality, and efficiency passes. Run them inline, or as parallel read-only seats with one pass each, whichever suits the diff's size. When the diff changes stored state or asynchronous behavior, also apply `data-systems-coding-lens`.
4. Run the **Connascence Pass** when the diff crosses a boundary or feels tangled.
5. Turn each accepted finding into a fix, a test, or an explicit follow-up. As the implementer, apply fixes and re-run the verification they touch. As an independent reviewer, report and leave files unchanged. A design concern that spans a boundary is escalated, not refactored here.

## Guards for every pass

- Safety checks stay: validation at trust boundaries, authorization, escaping and encoding, accessibility affordances, invariant assertions. Defense in depth is intentional even when a lower layer seems to cover it.
- Delete only with evidence. Check every caller and entry point, including dynamic imports, re-exports, barrel files, and framework-loaded exports. Prefer the project's dead-code linter or a structural search such as `ast-grep` over text grep. Unknown reachability blocks the deletion.
- When a platform guarantee makes code redundant, remove only what the guarantee owns. If a downstream projection makes a field filter redundant, keep the value transformations and apply them before projection. Swap a serializer or coercion only with tests proving identical output for every value type. Branches that become reachable once the filter goes are not dead code.
- Keep a helper that names a concept, an abstraction whose purpose you have not confirmed obsolete (check `git blame`), and duplication whose concepts may diverge. Drop any change that reads longer or harder than the original.
- **Precision over volume**: a wrong finding costs more than a missed one.

## Reuse pass

- A new function or inline logic that an existing utility already covers. Search utility directories, shared modules, and neighbouring files.
- A hand-rolled standard-library or runtime primitive, such as a dedup loop or deep clone. Swap it only when the built-in is behavior-equivalent for the inputs in play. Native UI controls, `Intl` formatting, sort stability, and serialization edge cases differ from hand-rolled versions.
- Code that hand-maintains a guarantee the platform, framework, or downstream layer provides, such as a GraphQL layer that already projects to the selection set. Name the layer and what the code collapses to.

## Quality pass

Use the `clean-code` vocabulary.

- Redundant state: duplicated or derivable values, effects or observers that could be direct calls, needless memoization.
- Parameter sprawl: a new parameter where generalizing the existing ones fits.
- Near-duplicate blocks: first try deriving them from an existing source of truth. Consolidate only when elimination is not behavior-preserving.
- Leaky abstractions, and types that hide an awkward contract.
- Raw strings where constants, unions, or branded types already exist.
- Wrapper elements with no layout value, in component-tree UI frameworks only.
- Conditionals nested three deep: flatten with guard clauses, early returns, or a lookup table.
- Comments that narrate what the code does or what the change did. Keep the **earned comment** that carries a non-obvious why.
- Dead code, unused imports and exports, compatibility code with no callers, a helper that makes no decision, unrelated diff churn.

## Efficiency pass

- Redundant work: repeated reads, duplicate calls, N+1 queries.
- Independent operations run sequentially.
- New blocking work on startup or on per-request or per-render hot paths.
- Unconditional state updates in loops, intervals, or handlers. Add a change guard, and check that wrappers honour the "no change" return.
- Existence pre-checks before an operation (TOCTOU). Operate and handle the error, unless the check is a trust-boundary control; then flag the race instead.
- Unbounded structures, missing cleanup, listener leaks.
- Reading a whole file or collection to use one part.

## Connascence Pass

Name what is **connascent**: two elements that must change together to stay correct. Rank each instance by strength (static is weaker than dynamic), locality, and degree, then pick the smallest remedy that weakens it toward connascence of name or brings it closer. Model the finding: "The status code `3` is connascent by meaning across the API handler and the worker, a distant and strong form; a shared enum weakens it to name." Leave local connascence alone when extraction adds indirection without safety.

## Seats

Before dispatching other models, show the plan (seats, models, briefs) and get a clear yes. Defaults come from `shared/model-routing.json`. Inside T3 Code, use `delegate_task` with the configured provider and model, and continue with `t3_thread_send`. In Claude Code or Codex, use a native subagent when the host has the model, and continue by messaging it. Otherwise use the matching `*-runner` skill. Send follow-ups to the same seat so it keeps its context. Give each pass seat the diff, the guards, and its pass, and tell it to leave files unchanged.

## Output

Review only: findings by severity, each with location, consequence, smallest fix, and verification.

Implementation:

1. Outcome: safe as is, simplified, needs a focused fix, or needs design escalation.
2. Changes made.
3. Verification captured.
4. Remaining risk.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
