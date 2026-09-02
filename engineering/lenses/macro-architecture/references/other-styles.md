# Other Styles — pipeline, service-based, orchestration-driven SOA

Three styles that sit outside the five-column selection matrix in SKILL.md but are often the right answer. Read this when the matrix picks nothing convincingly, when the unit is a data transformation chain, or when someone proposes microservices for a system that only needs coarse-grained services.

## Pipeline

Ordered filters connected by pipes; each filter does one transformation and knows nothing about its neighbors.

- **When to use:** data flows through ordered transformations — ETL, ingestion, encoding, log/event processing, build pipelines. Cheap, monolithic, easy to reason about.
- **When NOT to use:** steps need heavy shared state, bidirectional coordination, or a step must reach back and change an earlier one. Poor fit for interactive request/response workflows with branching business rules.
- **Coding cue:** keep filters independent and pipes explicit. A filter that reads global state or writes into a later stage's storage has broken the style.

## Service-based

A small number (typically 4–12) of coarse-grained, independently deployed domain services, usually over a shared database, with no per-service data decomposition.

- **When to use:** the domain splits into a few coarse services, moderate distribution is enough, and you want deployability and change isolation without the operational and data cost of microservices. The most common pragmatic middle ground, and the usual first step out of a monolith.
- **When NOT to use:** services genuinely need different quality attributes, independent data ownership, or fine-grained elasticity — that is microservices territory. Also a poor fit when the shared database is already the contention point.
- **Coding cue:** be explicit about service ownership and the migration boundary. Shared database access is the accepted trade-off, so guard schema change with contract tests rather than pretending each service owns its tables.

## Orchestration-driven SOA

Enterprise services coordinated by a central orchestration engine that owns workflow, transformation, and reuse.

- **When to use:** enterprise workflow reuse and central coordination matter more than service autonomy — heavy cross-system process integration, mandated central governance.
- **When NOT to use:** teams need autonomy or independent deploys, or reuse is being chased for its own sake. Reuse coupling and a central engine bottleneck are the classic failures; this style is largely historical for greenfield work.
- **Coding cue:** make orchestration dependencies visible in the code rather than buried in engine configuration, and cover the core flows with tests that run without the engine.
