---
name: design-gate
description: Select relevant design lenses for a planned slice and return a proceed-or-revise verdict. Use during task planning or when a design boundary changes; invoke a named lens directly for a single-lens review.
---

# Design Gate

Pick the design lenses a planned slice actually needs, apply them, and merge their findings into one `proceed` or `revise` verdict.

## Workflow

1. Identify the surfaces that the plan, slice contract, or changed scope touches. Reuse decisions already settled for the feature while their scope, assumptions, and sources still match. Re-route only when evidence changes the design surface.
2. Select lenses from the table for each unresolved decision or changed risk. Start with up to three, one per central risk, each with a bounded scope. Add another only for another material risk. When no row matches a local change, return `proceed` with "no design gate required".
3. Apply each lens read-only in the current role. Dispatch a specialist seat only when a risk needs expertise or independence the current role lacks. Give it the design problem, the files and boundaries in scope, and the gate result shape.
4. Merge. A concrete, load-bearing finding from any lens makes the verdict `revise`; load-bearing means it changes boundaries, data ownership, contracts, or correctness. Style and speculative findings are advisory.
5. On `revise`, list the required plan changes. After they land, recheck only the lens that raised the blocker. When the lenses expose a real trade-off that only the user's preference can settle, set `decision_required` and stop.

## Routing table

| Lens | When the change touches |
| --- | --- |
| `architecture-lens` | Unresolved system style; splitting or merging services; service and data ownership; two or more competing approaches with a real trade-off |
| `domain-driven-design` | Business vocabulary, bounded contexts, or relationships between them; business logic inside one context (aggregates, invariants, events) |
| `software-design-philosophy` | Module, class, or API interface design: depth, information hiding, placement, cohesion, dependency direction, scope pressure; a proposed design pattern, extension point, or sprawling conditional |
| `data-systems-coding-lens` | Stored state, databases, queues, caches, migrations, retries, concurrency, external APIs |
| `distributed-systems-patterns` | Container or process topology: sidecars, ambassadors, adapters, load-balanced replicas, sharding, scatter/gather, FaaS fit, ownership election, work queues, batch workflows |
| `distributed-systems-patterns` (event-driven route) with `data-systems-coding-lens` | Event streams as a source of truth: adopting event-driven microservices, Kafka, Pulsar, or Kinesis topics, event schemas, choreography versus orchestration, CDC or outbox data liberation |
| `agent-architecture-lens` | The thing being built is an agent: an LLM tool-calling loop, a multi-agent pipeline, or a long-running autonomous run needing durable state, mid-run approval, or replay |
| `advanced-react` | React state placement, rendering, effects, or asynchronous behavior |
| `frontend-design` | A new or reworked user-facing flow, information hierarchy, visual direction, or design system |

When a decision carries a real trade-off but no row fits, run only the `architecture-lens` trade-off pass: name the two to four characteristics in tension, the real options, and the cost of each, then pick the least harmful. Record an ADR with `architecture-lens/references/adr-template.md` only when **all three or no ADR** holds.

## Output

Return `proceed` or `revise`, the lenses run with their evidence, each finding with a stable ID, its lens, evidence, and status (`open`, `resolved` with the evidence, or `dismissed` with the reason), the required changes, any decision only the user can make, and the review focus for implementation. `proceed` needs no open blocking finding, change, or decision. Keep finding IDs stable across merges and rechecks. Security classification belongs to `security-gate`.

## Seats

Before dispatching other models, show the plan (seats, models, briefs) and get a clear yes. Defaults come from `shared/model-routing.json`. Inside T3 Code, use `delegate_task` with the configured provider and model, and continue with `t3_thread_send`. In Claude Code or Codex, use a native subagent when the host has the model, and continue by messaging it. Otherwise use `cli-runner`, `pi-runner`, or `muse-runner`. Send follow-ups, such as a blocker recheck, to the same seat so it keeps its context. Tell lens seats to leave files unchanged.
