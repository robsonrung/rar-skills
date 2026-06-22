---
name: design-gate
description: Route a planned change to the right architecture and design lens skills by the surfaces it touches, run them as parallel read-only reviewers, and return a single proceed-or-revise verdict. Use before implementing a non-trivial task, when a pipeline phase requires a design gate, or when the user asks which design review applies, says run the design gate, check this plan against the architecture lenses, or wants an automatic pre-implementation design check. Do not use to perform a single named review — invoke that lens skill directly.
---

# Design Gate

Turn "which of the design lenses applies here?" from a judgment call into a lookup, then run only the selected lenses and merge their findings into one verdict. This skill reviews nothing itself.

## Workflow

1. Identify the surfaces the change touches from the plan, slice contract, or diff scope. If lens flags were already set at planning time (the `to-tasks` Slice Contract), use them and skip step 2 — the cap below still applies; keep the 3 most central flags.
2. Select lenses from the routing table. Multiple rows can match; cap at 3 lenses — pick the rows most central to the change's risk.
3. Run each selected lens as a parallel read-only subagent. Give each: the plan or design problem, the files/boundaries in scope, and the instruction to return findings plus a `proceed` or `revise` recommendation with reasons.
4. Merge: any `revise` with a concrete, load-bearing finding makes the gate verdict `revise`; cosmetic or speculative findings are listed but do not block.
5. On `revise`, restate the required plan changes as a short numbered list. On disagreement between lenses about a real trade-off, escalate per the ladder in `ship` (multi-model consensus, then logged assumption) instead of asking the user.

## Routing table

| Change touches | Lens skill(s) |
|---|---|
| Overall shape of a new system, service, or subsystem | `macro-architecture`, `design-integrity` |
| Module/service boundaries, cross-context integration, naming vs business language | `domain-driven-design`, `macro-architecture` |
| Business-logic structure inside one context (aggregates, invariants, events) | `domain-driven-design` |
| Code structure choices, extensibility, sprawling conditionals | `design-patterns` |
| Layer placement, cohesion, dependency direction, scope creep | `architecture-lens` |
| Module/class/API interface design — depth, information hiding, interface complexity | `software-design-philosophy` |
| Stored state, databases, queues, caches, migrations, retries, concurrency, external APIs | `data-systems-coding-lens` |
| React components, hooks, contexts, rendering performance | `react-performance` |
| Two or more competing approaches with real trade-offs | `architecture-lens` |

**Fallback row (only when no specific row above fits):** no specific lens fits but the change is architecturally significant → `architecture_session_review` for a session-level review / ADR. Do not pair it with the rows above — it is the catch-all when a change is significant yet unroutable, not a peer lens.

No row matches and the change is not architecturally significant → the change is local; return `proceed` with the note "no design gate required" and do not invent a review.

## Output contract

Return:

1. `verdict`: `proceed` or `revise`.
2. `lenses_run`: which skills ran and why each was selected.
3. `blocking_findings`: load-bearing findings requiring plan changes (empty when `proceed`).
4. `advisory_findings`: non-blocking observations worth carrying into implementation.
5. `required_changes`: numbered plan amendments (only when `revise`).

## Gotchas

1. Do not run every lens to be safe — the cap exists to keep the gate cheap and the findings sharp.
2. Do not let lenses edit anything; the gate is read-only.
3. Do not block on style opinions; only findings that change boundaries, data ownership, contracts, or correctness block.
4. Do not re-run the full gate after a `revise` fix — re-run only the lens that raised the blocking finding.
