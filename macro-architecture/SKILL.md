---
name: macro-architecture
description: Macro / system-level architecture — choose the overall STYLE of a system or subsystem and reason through the hard decomposition trade-offs of building it. Use when picking or sanity-checking a macro style ("should this be microservices / event-driven / a monolith", "which architecture style fits", "layered vs distributed", "technical vs domain partitioning", "score this design's trade-offs"), AND when the decision is about coupling, modularity, monolith decomposition, service granularity, bounded contexts, data ownership, distributed transactions, sagas, workflow orchestration vs choreography, contracts, ADRs, or architecture fitness functions. Distilled from Mark Richards' "Software Architecture Patterns" and "Software Architecture: The Hard Parts" (Ford & Richards). Distinct from architecture-lens (code-level trade-offs/connascence/layer placement), domain-driven-design (bounded-context boundaries, ubiquitous language & integration patterns), and design-patterns (GoF code patterns). Avoid for routine bug fixes unless architecture choices are involved.
---

# Macro Architecture

Two complementary system-level tools that work at the same altitude — **what shape should this system take?**

- **Style selection** — given a system/service/feature and its driving requirements, which macro architecture style (or hybrid) fits, and what does the book warn about if you pick it? (from *Software Architecture Patterns, 2nd ed.*, Mark Richards.)
- **Hard-parts decomposition** — once you're decomposing, merging, or re-shaping a system, which way do the trade-offs actually push, anchored in the current code and runtime? (from *Software Architecture: The Hard Parts*, Ford & Richards.)

Use **Style selection** when choosing an overall shape for something new (or sanity-checking an existing one). Use **Hard-parts decomposition** when the decision is whether to pull a system apart or put it back together. They compose: pick a style, then stress-test the decomposition.

**Distinct from** `architecture-lens` (code-level trade-offs/connascence and layer placement/cohesion in the code under your hands), `domain-driven-design` (bounded-context boundaries, ubiquitous language, cross-context integration patterns), and `design-patterns` (GoF code patterns). This skill picks the MACRO shape; those review the code and contexts within it.

---

## Part A — Style selection

This answers **which macro style fits**, not code review.

### How to run a selection

1. **Restate the unit of decision.** A whole system? One backend service? A subsystem inside an existing app? Style can differ per subsystem — say which one you're scoping.
2. **Surface the driving characteristics.** Pull the 1–3 that actually matter for *this* unit; don't rate all eight equally. Tells:
   - "event", "trigger", "react to something happening", non-deterministic workflow → event-driven
   - "scale to tens of thousands concurrent", "elastic", "flash load" → space-based / distributed
   - "independent deploy", "team per domain", "drop in new functionality" → microservices
   - "product with plug-ins / per-customer rules / planned extensions" → microkernel
   - "tight budget", "simple CRUD app", "small team", "just ship it" → layered
3. **Check classification first** (cheaper than picking a style):
   - **Monolithic vs distributed** — does the *whole* unit need scale/HA, or only parts? Different characteristics across parts ⇒ distributed.
   - **Technical vs domain partitioning** — will most changes be by technical layer (swap UI, swap DB) or by domain (add a field that cuts every layer)? Domain-scoped change + DDD + cross-functional teams ⇒ domain partitioning. (Conway's Law: align partitioning with team structure.)
4. **Score against the matrix** below, then read the matching `references/<style>.md` for the when-NOT-to red flags. A style fits only if its when-not-to list doesn't bite. If recommending a distributed style (event-driven, microservices, space-based), also read `references/traps.md` before finalizing.
5. **Recommend** one style, or an explicit **hybrid** (common and expected: event-driven microservices, space-based microservices, event-driven microkernel). State the top trade-off you're accepting and the biggest risk from the when-not-to list.

### The selection matrix (Appendix A)

Ratings: ★ = poor … ★★★★★ = excellent. Cost: $ = cheap … $$$$$ = expensive.

| Characteristic | Layered | Microkernel | Event-driven | Microservices | Space-based |
|---|---|---|---|---|---|
| **Partitioning** | Technical | Tech *or* Domain | Technical | Domain | Technical |
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

If the unit is genuinely simple CRUD with a tight budget, say "layered, don't overthink it" and stop — resisting over-architecting is itself a correct answer.

---

## Part B — Hard-parts decomposition

Use this when a session contains an architecture decision (pull apart / put together / re-own data), not just an implementation task.

**Mental model:** architecture choices are contextual trade-offs; no pattern is best outside the current constraints. Anchor each recommendation in **connascence** (strength × locality × degree — see `architecture-lens`), data ownership, deployability, runtime behavior, and validation.

### Workflow

1. **Name the decision in one sentence** — current system shape, the change considered, and the force involved (service boundaries, data ownership, transaction consistency, workflow coordination, shared code, contract shape, scaling pressure, failure isolation).
2. **Reproduce the current shape from code and runtime evidence** — relevant modules, schemas, migrations, tests, dependency manifests, deployment descriptors, contracts, queues, jobs, logs, dashboards. Prefer current repo evidence over remembered architecture.
3. **Map connascence before proposing a change.** Static (imports, package deps, shared libs, schema access, deployment coupling, config, infra) and dynamic (request flow, messaging, consistency requirements, workflow state, coordination ownership, retries, timeouts, compensation). Strong, distant, high-degree connascence is the decomposition target.
4. **Decide: pulling apart or putting back together?** Pull apart when evidence favors maintainability, testability, deployability, scalability, fault/security isolation, change isolation, or database-type fit. Put back together when it favors single-unit transactions, tightly related data, heavy workflow chatter, frequently co-changing shared domain code, low latency, or simpler ownership.
5. **Read the focused reference only when needed** — `references/catalog.md` for the decision catalog (decomposition, service granularity, data decomposition, reuse, data ownership, eventual consistency, workflows, sagas, contracts, data mesh); `references/adrtemplate.md` when the user wants a durable written decision, the choice affects multiple teams, or the change sets an architectural precedent.
6. **Compare options against local context** — a short prose matrix; keep options mutually exclusive and collectively complete. Avoid generic pros/cons that ignore the repo, domain workflow, data model, operational constraints, or team boundaries.
7. **Prefer bottom-line clarity** — state the practical choice as an outcome (e.g. faster response over immediate consistency; independent deployability over shared-transaction simplicity; a shared library over a shared service because the function is domain-local and latency-sensitive).
8. **Implement the smallest coherent shape** — a behavior-preserving move when the decision is structural. Keep edits scoped; preserve existing boundaries unless the decision is to change them. Add tests or fitness functions that guard the architecture property, not only domain behavior.
9. **Close with verification** — report the code changed, the trade-off accepted, the fitness function/test added, and any risk needing a follow-up decision.

### Fitness-function prompts

1. What must stay isolated after this change?
2. What dependency, import, schema access, service call, queue, or shared library would violate that isolation?
3. Can a test, static check, migration check, contract test, monitor, or alert fail when the architecture drifts?
4. Is the check architecture-focused rather than domain-focused?

### Output contract (for a decision)

A concise decision note: **1. Decision · 2. Context Evidence · 3. Options Considered · 4. Trade-offs · 5. Implementation Move · 6. Validation · 7. Consequences.**

When writing an ADR, use the repo convention if one exists; otherwise `docs/adr/YYYYMMDD_slug.md`. The helper `scripts/newadr.py` can draft one, e.g. `python <skill_dir>/scripts/newadr.py --title "Split billing schema" --out-dir docs/adr --dry-run` (path relative to this skill; `--help` for flags).

### Gotchas

1. Don't split services because smaller sounds cleaner — first prove the disintegrator beats the integrator.
2. Don't merge services just because a workflow is noisy — first check whether orchestration, async messaging, or contract changes address the actual coupling.
3. Don't treat database ownership as an implementation detail — ownership controls change safety, consistency, and bounded-context integrity.
4. Don't rely on generic architecture advice — the relevant domain cases decide the trade-off.
