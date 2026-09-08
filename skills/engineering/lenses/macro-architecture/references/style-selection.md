# Select an Architecture Style

Paths named below are relative to the loaded skill root.

This answers **which macro style fits**, not code review.

### How to run a selection

1. **Restate the unit of decision.** A whole system? One backend service? A subsystem inside an existing app? Style can differ per subsystem — say which one you're scoping.
2. **Surface the driving characteristics.** Pull the 1–3 that actually matter for _this_ unit; don't rate all eight equally. Tells:
   - "event", "trigger", "react to something happening", non-deterministic workflow → event-driven
   - "scale to tens of thousands concurrent", "elastic", "flash load" → space-based / distributed
   - "independent deploy", "team per domain", "drop in new functionality" → microservices
   - "product with plug-ins / per-customer rules / planned extensions" → microkernel
   - "tight budget", "simple CRUD app", "small team", "just ship it" → layered
3. **Check classification first** (cheaper than picking a style):
   - **Monolithic vs distributed** — does the _whole_ unit need scale/HA, or only parts? Different characteristics across parts ⇒ distributed.
   - **Technical vs domain partitioning** — will most changes be by technical layer (swap UI, swap DB) or by domain (add a field that cuts every layer)? Domain-scoped change + DDD + cross-functional teams ⇒ domain partitioning. (Conway's Law: align partitioning with team structure.)
4. **Score against the matrix** below, then read the matching `references/<style>.md` for the when-NOT-to red flags. A style fits only if its when-not-to list doesn't bite. If recommending a distributed style (event-driven, microservices, space-based), also read `references/traps.md` before finalizing.
5. **Recommend** one style, or an explicit **hybrid** (common and expected: event-driven microservices, space-based microservices, event-driven microkernel). State the top trade-off you're accepting and the biggest risk from the when-not-to list.

**Least Worst Rule.** Do not ask which style is best. Ask which style creates the least harmful trade off for this domain, team, data model, and operating environment. A recommendation that names no harm has not finished the analysis.

### The selection matrix (Appendix A)

Ratings: ★ = poor … ★★★★★ = excellent. Cost: $ = cheap … $$$$$ = expensive.

| Characteristic | Layered | Microkernel | Event-driven | Microservices | Space-based |
| --- | --- | --- | --- | --- | --- |
| **Partitioning** | Technical | Tech _or_ Domain | Technical | Domain | Technical |
| **Overall cost** | $ | $ | $$$ | $$$$$ | $$$$$ |
| **Agility** | ★ | ★★★ | ★★★ | ★★★★★ | ★★ |
| **Simplicity** | ★★★★★ | ★★★★ | ★ | ★ | ★ |
| **Scalability** | ★ | ★ | ★★★★★ | ★★★★★ | ★★★★★ |
| **Fault tolerance** | ★ | ★ | ★★★★★ | ★★★★★ | ★★★ |
| **Performance** | ★★★ | ★★★ | ★★★★★ | ★★ | ★★★★★ |
| **Extensibility** | ★ | ★★★ | ★★★★ | ★★★★★ | ★★★ |
| **Deployment** | monolithic | monolithic | distributed | distributed | distributed |

Read it as: pick the row that's your top driver, scan for ★★★★★, then disqualify with the when-not-to list. Note microservices buys agility/scale/fault-tolerance with the worst cost, simplicity, and (surprisingly) only ★★ performance — inter-service calls add network, security, and data latency.

### One-line picks

- **Layered** — simple/small app, tight budget, technically-organized team, changes isolated to layers. The safe default when unsure.
- **Microkernel** — product with plug-ins, per-customer/per-jurisdiction rules, planned extensions over a stable core.
- **Event-driven** — reactive/async workflows, high scale + fault tolerance + performance, non-deterministic flows. Accepts eventual consistency.
- **Microservices** — many independent single-purpose functions, domain teams, frequent independent deploys. The most expensive and hardest to get right.
- **Space-based** — extreme/variable concurrency (ticketing, auctions, social) where the database is the bottleneck. Removes the DB from the transactional path.

### Style references (read the one you're leaning toward)

`references/layered.md`, `references/microkernel.md`, `references/event-driven.md`, `references/microservices.md`, `references/space-based.md`, and `references/traps.md` — the named anti-patterns & fallacies to check against any pick (architecture sinkhole, big ball of mud, the 8 fallacies of distributed computing, bounded context, event-vs-message ownership, the three microservices "uniques").

`references/other-styles.md` — pipeline, service-based, and orchestration-driven SOA: the three styles outside the matrix, with when-to / when-not-to entries. Read it when the matrix picks nothing convincingly, when the unit is an ordered data transformation, or before recommending microservices for a system that may only need coarse-grained services.

If the unit is genuinely simple CRUD with a tight budget, say "layered, don't overthink it" and stop — resisting over-architecting is itself a correct answer.
