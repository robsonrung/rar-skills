---
name: architecture-lens
description: "Decide system shape and architecture trade-offs: style, service decomposition, data ownership, and competing approaches. Use for monolith-versus-services, splitting or merging services, or an unresolved choice with real costs; use software-design-philosophy for module-level structure."
---

# Architecture Lens

Judge the shape of a system: which style fits, where service and data boundaries go, and what each choice costs. Module placement, cohesion, dependency direction, and scope belong to `software-design-philosophy`; container and event-stream topology to `distributed-systems-patterns`; bounded contexts to `domain-driven-design`; connascence inside a diff to the **Connascence Pass** in `coding-review-simplify`.

Anchor every claim in the current code and runtime: modules, schemas, migrations, deployment descriptors, contracts, queues, jobs. Prefer that evidence over remembered architecture. A local change does not need a map of the whole repository, and a routine code change is not a system redesign.

## Trade-off pass

Use for any unresolved architecture choice. Settled decisions stay inputs unless new evidence invalidates them.

1. Name the 2–4 characteristics actually in tension here. Most decisions trade two against each other. More than four means the decision is not framed yet. Watch for an implicit characteristic the domain demands that no ticket names, such as auditability in finance.
2. List the real options. "Keep current" can be one. Don't manufacture alternatives: when a settled contract or repository constraint already determines the move, say so and stop.
3. For each option, state what it gains and what it gives up. Record an actual cost; never invent a drawback to fill a field.
4. Decide against the characteristics from step 1 and say why in one sentence. The reasoning is the deliverable.

Apply the **Least Worst Rule**: do not ask which option is best; ask which one does the least harm for this domain, team, data model, and operating environment. A recommendation that names no harm has not finished the analysis.

If the decision creates a rule future code could silently break ("billing never reads the orders schema"), propose the smallest automated check that fails when it drifts, and add none for rules nobody is at risk of breaking.

## Style

Decide the two axes before naming a style: monolithic or distributed (does the whole unit need independent scale and availability, or only part of it?), and technical or domain partitioning (do most changes cut one layer or one business area?). Partitioning tends to follow team structure.

Distributed styles pay a standing tax: network, security, and data latency on every hop; eventual consistency; distributed error handling; contract management. Recommend one only when a named characteristic needs it and the team will pay that tax. Coarse-grained services often deliver the benefit for a fraction of the cost of microservices. For event-driven adoption, use the event-driven route of `distributed-systems-patterns`.

If the unit is simple CRUD with a tight budget and a small team, say "layered, don't overthink it" and stop. Resisting over-architecture is a correct answer.

## Decomposition

Use when the question is pulling a system apart, putting it back together, or re-owning data. Run the **integrator-versus-disintegrator test**: list the forces on each side from evidence, and split only when the most important disintegrator beats every integrator with acceptable consequences.

- **Disintegrators:** weak cohesion or a service that is hard to name; volatility isolated to one part; different scaling, throughput, or fault-isolation needs; different security or data-access requirements; many services contending for one schema or connection pool.
- **Integrators:** a required ACID transaction; workflow chatter that dominates the request; shared domain code that changes often or cannot be versioned safely; data relationships that force repeated cross-service reads or writes.

A boundary is real only if the unit deploys independently. If it still shares a database, a release train, a mutable model, or synchronous coordination for most work, it is not yet a boundary.

Data ownership: one writer per piece of data, others ask through a contract. When two services write the same data, resolve it by splitting the table by concern, delegating writes through one owner, or consolidating the services. For workflow coordination, orchestration makes state and error handling visible at the cost of a central dependency; choreography scales and decouples but hides workflow state and grows stamp coupling.

The four decomposition gotchas:

1. Don't split because smaller sounds cleaner. First prove the disintegrator beats the integrator.
2. Don't merge just because a workflow is noisy. First check whether orchestration, async messaging, or a contract change addresses the actual coupling.
3. Don't treat database ownership as an implementation detail. It controls change safety, consistency, and bounded-context integrity.
4. Don't rely on generic architecture advice. The repo's own domain cases decide the trade-off.

## Authority and output

This lens reports findings and decisions. A user's request for scoped changes authorizes those edits; a structural refactor stays behavior-preserving. Under `design-gate` or another read-only caller, return the caller's canonical gate result only. A load-bearing issue can require revision; a cosmetic preference cannot.

For a decision, return the chosen shape, the evidence, the trade-off accepted, and the next concrete move. A small decision fits in two lines. A clean review returns `clean`; never invent a finding or a counterpoint.

Use **all three or no ADR**: hard to reverse, surprising without context, and a real trade-off. **Record on settle** with [references/adr-template.md](references/adr-template.md) when all three hold; otherwise keep the reason in the task or review note. In an interview, add the decision, rationale, constraints, and sources to the existing decision record.
