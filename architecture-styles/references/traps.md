# Named traps, fallacies & cross-cutting concepts

Check any candidate style against these before committing.

## Anti-patterns
- **Big ball of mud** — what you get coding with no architecture: ill-defined, tightly
  coupled, brittle, no clear direction. The thing every style exists to prevent.
- **Architecture sinkhole** (layered) — requests fall through layers doing pure
  pass-through (no logic). Tolerable at ~20% of requests; a problem if it's the majority.
  See `layered.md`.

## The 8 fallacies of distributed computing
Things we *assume* true about networks but are false — they make any **distributed** style
(event-driven, microservices, space-based) hard. Surface these whenever recommending
distributed:
1. The network is reliable — it isn't; networks fail.
2. Latency is zero — it isn't (30–300 ms+ for remote calls).
3. Bandwidth is infinite — it isn't.
4. The network is secure — it isn't.
5. Topology doesn't change — it does.
6. There is one administrator — there isn't.
7. Transport cost is zero — it isn't.
8. The network is homogeneous — it isn't.

Plus the rest of the distributed tax: distributed transactions, eventual consistency,
workflow management, error handling, data synchronization, contract management — all add
cost over a monolith.

## Three latencies that bite distributed styles
- **Network latency** — packets to the target service (30–300 ms+).
- **Security latency** — authn/authz at the endpoint (ms–300 ms+).
- **Data latency** — extra DB call when a service must fetch data it doesn't own (the
  microservices performance killer; a monolith does this with one join).

## Cross-cutting concepts
- **Classification (two axes)** — *monolithic vs distributed* (deployment units) and
  *technical vs domain partitioning* (organized by layer vs by domain area). Decide these
  before picking a style.
- **Bounded context** (Evans/DDD) — a domain owns its code *and* data; others ask via
  contract. The foundation of microservices; see `microservices.md`.
- **Conway's Law** — system partitioning tends to mirror team structure. Technically
  partitioned teams → layered/space-based; cross-functional domain teams → microservices.
- **Event vs message** — event = "I did X" (sender owns channel+contract, pub-sub);
  message = "do X" (receiver owns channel+contract, point-to-point). See `event-driven.md`.
- **Style < pattern < design pattern** — architecture *styles* (this skill) are the macro
  structure; architecture *patterns* (e.g. CQRS) are building blocks within a style;
  *design patterns* (e.g. Builder — see the `design-patterns` skill) shape the source code.
  Hybrids are normal: event-driven microservices, space-based microservices, event-driven
  microkernel.
```
