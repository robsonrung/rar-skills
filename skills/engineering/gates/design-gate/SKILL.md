---
name: design-gate
description: Select relevant design lenses for a planned slice and return a proceed-or-revise verdict. Use during task planning or when a design boundary changes; invoke a named lens directly for a single-lens review.
---

# Design Gate

Turn "which design lens applies here?" into a small, evidence-based routing decision, then run only the selected lenses and merge their findings into one verdict. This skill is the routing authority. It does not invent a second review method or call a council.

For the workflow stage boundaries and the practical skills that follow this gate, read `shared/references/workflow-stage-routing.md`.

## Workflow

1. Identify the stage and the surfaces from the plan, Slice Contract, or changed scope. In `to-tasks`, this is the one routing pass for the slice. Before implementation, use the inherited lens flags; re-route only when the slice's design surface changed.
2. Select lenses from the routing table. Multiple rows can match; cap at three. Keep the three most central to the change's risk. No matching row on a local change means no gate.
3. Run each selected lens as a parallel read-only reviewer. Give it the plan or design problem, the files and boundaries in scope, and this gate response: `verdict`, `blocking_findings`, `advisory_findings`, and `required_changes`. This response replaces a lens's standalone edit or implementation route.
4. Merge. Any `revise` with a concrete, load-bearing finding makes the gate verdict `revise`. Cosmetic or speculative findings are advisory.
5. On `revise`, state the required plan changes as a short numbered list. When lenses expose a real unresolved trade-off, set `verdict: revise`, set `decision_required`, and stop. Never call `models-consensus` from this skill. The user may invoke it separately when more opinions are useful.

## Routing table

| Change touches | Lens skill(s) |
| --- | --- |
| Overall shape of a new system, service, or subsystem | `macro-architecture`, `software-design-philosophy` |
| Module/service boundaries, cross-context integration, naming vs business language | `domain-driven-design`, `macro-architecture` |
| Business-logic structure inside one context (aggregates, invariants, events) | `domain-driven-design` |
| Code structure choices, extensibility, sprawling conditionals | `design-patterns` |
| Layer placement, cohesion, dependency direction, scope creep | `architecture-lens` |
| Module/class/API interface design — depth, information hiding, interface complexity | `software-design-philosophy` |
| Stored state, databases, queues, caches, migrations, retries, concurrency, external APIs | `data-systems-coding-lens` |
| Container/process topology of a distributed app — sidecars, ambassadors, adapters, load-balanced replicas, sharding, scatter/gather, FaaS fit, ownership election, work queues, batch workflows | `distributed-systems-patterns` |
| Event streams as a source of truth — adopting or migrating to event-driven microservices, Kafka/Pulsar/Kinesis topics, event schemas, choreography vs orchestration, CDC/outbox data liberation | `distributed-systems-patterns` (event-driven route), `data-systems-coding-lens` |
| The thing being built **is** an agent — an LLM tool-calling loop, a multi-agent pipeline, or a long-running autonomous run needing durable state, mid-run approval, or replay | `agent-architecture-lens` |
| React components, hooks, contexts, rendering performance, state placement | `advanced-react` |
| New or reworked user-facing flow, information hierarchy, or design system | `ui-ux-pro-max` |
| Two or more competing approaches with real trade-offs | `architecture-lens` |

**Fallback row (only when no specific row above fits):** no specific lens fits but the change is architecturally significant → run `architecture-lens` as a **Lens 1 trade-off pass** (name the 2–4 characteristics in tension, the real options, and the cost of each), and apply **all three or no ADR** before recording it with the canonical ADR template at `architecture-lens/references/adr-template.md`. Do not pair this with the rows above — it is the catch-all when a change is significant yet unroutable, not a peer lens.

No row matches and the change is not architecturally significant → the change is local; return `proceed` with the note "no design gate required" and do not invent a review.

## Output contract

Return:

1. `verdict`: `proceed` or `revise`.
2. `lenses_run`: which skills ran and why each was selected.
3. `blocking_findings`: load-bearing findings requiring plan changes (empty when `proceed`).
4. `advisory_findings`: non-blocking observations worth carrying into implementation.
5. `required_changes`: numbered plan amendments (only when `revise`).
6. `decision_required`: the unresolved trade-off and its owner, or `none`.

In a Slice Contract, carry `lenses_run`, `verdict`, `required_changes`, `decision_required`, and the security flag from `security-gate`. Resolve blocking findings before task approval. The implementation engine receives those constraints; it does not replay every lens.

## Gotchas

1. Do not run every lens to be safe — the cap exists to keep the gate cheap and the findings sharp.
2. Do not let lenses edit anything; the gate is read-only.
3. Do not block on style opinions; only findings that change boundaries, data ownership, contracts, or correctness block.
4. Do not re-run the full gate after a `revise` fix — re-run only the lens that raised the blocking finding.
5. Do not use a consensus panel to break a tie. The gate can identify a decision; it cannot manufacture user preference.
