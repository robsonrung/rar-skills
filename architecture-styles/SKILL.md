---
name: architecture-styles
description: Reference and selection guide for the five macro architecture styles — layered, microkernel, event-driven, microservices, space-based — distilled from Mark Richards' "Software Architecture Patterns" (O'Reilly, 2nd ed.). Use when choosing or sanity-checking the overall STYLE of a new system, service, or subsystem ("should this be microservices / event-driven / a monolith", "which architecture style fits", "is layered right here", "score this design's trade-offs", "monolith vs distributed", "technical vs domain partitioning"), or when you need a quick reference on a style's topology, when-to/when-not-to, or characteristic ratings. Distinct from model-lens (layer placement/cohesion review), architect-lens (trade-offs/connascence), design-patterns (GoF code patterns), and ddd-tactical (transaction script vs domain model). This skill picks the MACRO style; those review the code within it.
---

# Architecture Styles — Reference & Selector

Distilled from *Software Architecture Patterns, 2nd ed.* (Mark Richards, O'Reilly 2022).
This skill answers one question: **given a system/service/feature and its driving
requirements, which macro architecture style (or hybrid) fits — and what does the book
warn me about if I pick it?** It also doubles as a quick reference for each style.

This is **style selection**, not code review. For *where code belongs* use `model-lens`;
for *coupling/trade-offs* use `architect-lens`; for *tactical DDD* use `ddd-tactical`.

## How to run a selection

1. **Restate the unit of decision.** A whole system? One backend service? A subsystem
   inside an existing app? Style can differ per subsystem — say which one you're scoping.
2. **Surface the driving characteristics.** Pull the 1–3 that actually matter for *this*
   unit from the requirements/conversation. Don't rate all eight equally — the whole point
   is that styles trade characteristics against each other. Listen for the tells:
   - "event", "trigger", "react to something happening", non-deterministic workflow → event-driven
   - "scale to tens of thousands concurrent", "elastic", "flash load" → space-based / distributed
   - "independent deploy", "team per domain", "drop in new functionality" → microservices
   - "product with plug-ins / per-customer rules / planned extensions" → microkernel
   - "tight budget", "simple CRUD app", "small team", "just ship it" → layered
3. **Check classification first** (cheaper than picking a style):
   - **Monolithic vs distributed** — does the *whole* unit need scale/HA, or only parts?
     Different characteristics across parts ⇒ distributed.
   - **Technical vs domain partitioning** — will most changes be by technical layer
     (swap UI framework, swap DB) or by domain (add a field that cuts every layer)?
     Domain-scoped change + DDD + cross-functional teams ⇒ domain partitioning.
     This is Conway's Law: align partitioning with team structure.
4. **Score against the matrix** below, then read the matching `references/<style>.md` for
   the when-NOT-to red flags. A style is only a fit if its when-not-to list doesn't bite.
5. **Recommend** one style, or an explicit **hybrid** (these are common and expected:
   event-driven microservices, space-based microservices, event-driven microkernel).
   State the top trade-off you're accepting and the biggest risk from the when-not-to list.

## The selection matrix (Appendix A)

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

Read it as: pick the row that's your top driver, scan for ★★★★★, then disqualify with the
when-not-to list. Note microservices buys agility/scale/fault-tolerance with the worst
cost, simplicity, and (surprisingly) only ★★ performance — inter-service calls add network,
security, and data latency.

## One-line picks

- **Layered** — simple/small app, tight budget, technically-organized team, changes isolated to layers. The safe default when unsure.
- **Microkernel** — product with plug-ins, per-customer/per-jurisdiction rules, planned extensions over a stable core.
- **Event-driven** — reactive/async workflows, high scale + fault tolerance + performance, non-deterministic flows. Accepts eventual consistency.
- **Microservices** — many independent single-purpose functions, domain teams, frequent independent deploys. The most expensive and hardest to get right.
- **Space-based** — extreme/variable concurrency (ticketing, auctions, social) where the database is the bottleneck. Removes the DB from the transactional path.

## Style references (read the one you're leaning toward)

- `references/layered.md`
- `references/microkernel.md`
- `references/event-driven.md`
- `references/microservices.md`
- `references/space-based.md`
- `references/traps.md` — the named anti-patterns & fallacies to check against any pick:
  architecture sinkhole, big ball of mud, the 8 fallacies of distributed computing,
  bounded context, event-vs-message ownership, the three microservices "uniques".

## Output shape

Keep it tight. Lead with the recommendation, not a tour of all five styles.

```
Unit scoped: <system / service X / subsystem Y>
Driving characteristics: <the 1–3 that decide it>
Classification: <monolithic|distributed> · <technical|domain> partitioning
Recommendation: <style or hybrid>
Why it wins: <1–2 lines tied to the driving characteristics + matrix>
Trade-off accepted: <the characteristic you're giving up>
Watch out (when-not-to): <the red flag most likely to bite, from references/>
Runner-up: <style> — <when you'd switch to it>
```

If the unit is genuinely simple CRUD with a tight budget, say "layered, don't overthink it"
and stop — resisting over-architecting is itself a correct answer here.
