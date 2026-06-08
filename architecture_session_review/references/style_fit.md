# Style Fit

Use this reference when the task asks for architecture choice, service boundaries, refactoring direction, or migration planning.

## First Choice

Decide these before naming a style:

1. Does one set of quality attributes fit the whole system, or do different parts need different attributes?
2. Does the domain naturally split into independent behavior areas?
3. Where should data live, and who owns writes?
4. Should communication be sync, async, or mixed?
5. What do team skill, delivery process, operations, and cost make realistic?

Default to sync communication when it is sufficient. Use async communication when reliability, scale, latency isolation, workflow decoupling, or buffering justify the complexity.

## Style Signals

Layered architecture:

1. Best when the system is simple, cost constrained, technically partitioned, and needs familiar organization.
2. Watch for sinkholes, weak deployability, and weak testability if layer boundaries become ceremony.
3. Coding cue: add layer access checks when layers matter.

Pipeline architecture:

1. Best when data flows through ordered transformations.
2. Watch for poor fit when steps need heavy shared state or bidirectional coordination.
3. Coding cue: keep filters independent and pipes clear.

Microkernel architecture:

1. Best when custom behavior or product variation can live in plugins around a stable core.
2. Watch for plugin contract drift and accidental coupling between plugins.
3. Coding cue: protect core contracts and plugin registry behavior.

Service based architecture:

1. Best when domain services can be coarse grained and moderate distribution is enough.
2. Watch for database coupling, service granularity mistakes, and weak elasticity.
3. Coding cue: clarify service ownership and migration boundaries.

Event driven architecture:

1. Best when async behavior, loose coupling, burst handling, or event reaction is central.
2. Watch for data loss, error handling, workflow visibility, ordering, and contract sprawl.
3. Coding cue: test idempotency, retries, dead letter behavior, and event schema compatibility.

Space based architecture:

1. Best when extreme concurrent load and high elasticity dominate.
2. Watch for data collision, cache consistency, testability, and operational complexity.
3. Coding cue: verify cache, write behind, data reader, and data writer behavior carefully.

Orchestration driven service oriented architecture:

1. Best when enterprise workflow reuse and central coordination are stronger concerns than service autonomy.
2. Watch for tight reuse coupling and central engine bottlenecks.
3. Coding cue: make orchestration dependencies visible and test core flows.

Microservices:

1. Best when domain boundaries are strong and independent deployment, testability, team autonomy, and different quality attributes per service matter.
2. Watch for performance, data consistency, transaction complexity, operational overhead, and too much orchestration.
3. Coding cue: protect bounded context, data isolation, contract versioning, and operational signals.

## Least Worst Rule

Do not ask which style is best. Ask which style creates the least harmful trade off for this domain, team, data model, and operating environment.
