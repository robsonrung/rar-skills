# Microservices Architecture

**Class:** Distributed · Domain partitioning. The most popular and the **hardest to get
right** / most expensive style.

## Topology
Ecosystem of single-purpose, separately deployed services behind an **API gateway**. The
gateway hides service location and does cross-cutting infra (security, metrics, request-ID)
— **no business logic, no orchestration/mediation** (unlike an ESB). Each service owns its
own data.

## What is a microservice?
Single-purpose unit that "does one thing really well" — defined by *what it does*, not its
size (a 312-class email service is still one microservice if it only sends emails). Expect
hundreds to thousands; deploy as containers or serverless functions.

## Bounded context (the load-bearing idea — Eric Evans, DDD)
A service owns its source code **and its data**; other services must ask via a contract,
never touch its tables. Without this, 250 services hitting one shared schema means a column
drop forces coordinating 120 deploys — infeasible. The contract is usually a different
representation than the physical tables, so DB changes don't ripple out.
Real systems sometimes share data across 2–6 services (FK constraints, triggers, views,
materialized views) — then the bounded context expands to include those shared tables.

## Three things unique to microservices
1. **Distributed data** — the only style that *requires* breaking data into per-service
   stores.
2. **Operational automation** — too many services to manage by hand ⇒ containers +
   Kubernetes + DevOps are mandatory, not "nice to have".
3. **Organizational change** — requires cross-functional domain teams (Conway's Law);
   teams own testing and release of their own services.

## When to consider
- App splits into dozens–hundreds of independent single-purpose functions.
- Need high **agility** (independent, low-risk hot deploys), **scalability**, **fault
  tolerance** (both at the function level; MTTR in ms).
- Lots of planned **extensibility** — "drop-in" a new service + API endpoint.

## When NOT to consider
- Functionality must be tied together with complex **workflows / heavy inter-service
  orchestration** — that fights the style.
- **Tightly coupled data** that can't be split (FKs, triggers, stored procs) — use
  service-based architecture instead.
- Tight **cost/time** budget — most complex and expensive style; licensing scales with
  service count.
- Need high **performance / responsiveness** — surprisingly only ★★: remote calls add
  **network + security + data latency** (each service must query data it doesn't own).

The hard parts (granularity, sync vs async, orchestration vs choreography, data sharing,
distributed transactions, contracts) are covered in *Software Architecture: The Hard Parts*.

## Characteristics
Partitioning Domain · Cost $$$$$ · Agility ★★★★★ · Simplicity ★ · Scalability ★★★★★ ·
Fault tolerance ★★★★★ · Performance ★★ · Extensibility ★★★★★
