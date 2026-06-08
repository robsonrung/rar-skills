# Space-Based Architecture

**Class:** Distributed · Technical partitioning. Specialized; built to defeat the
**database bottleneck** under extreme/variable concurrency. Name comes from *tuple space*
(parallel processors with shared memory).

## The problem it solves
Normal flow web → app → DB: scaling web servers just pushes the bottleneck to app servers,
then to the DB — the hardest, most expensive tier to scale. Space-based **removes the
database from the transactional path**.

## Topology
- **Processing unit** — holds business logic + an **in-memory data grid** (transactional
  data lives in memory, replicated across all active units). Started/stopped dynamically
  with load ⇒ near-infinite, elastic scalability. No DB in the hot path.
- **Virtualized middleware** — manages it all:
  - **Messaging grid** — routes incoming requests to an available processing unit (web server).
  - **Data grid** — *the most crucial part*; replicates data across units so every unit
    holds identical in-memory data (Hazelcast, Apache Ignite, Oracle Coherence).
  - **Processing grid** — optional; orchestrates requests spanning multiple unit types.
  - **Deployment manager** — starts/stops units on load (Kubernetes).
- **Data pumps / data writers / data readers** — async path to a backing DB: writers
  persist updates from queues; readers reverse-pump on a cold start (crash/deploy).

Deployment can be all-cloud, all-on-prem, or split (cloud processing + on-prem data via
data pumps to on-prem writers).

## When to consider
- Very high **concurrent scalability / elasticity** — tens of thousands+ concurrent
  (ticketing flash sale, online auctions, high-volume social feeds).
- Need top **performance / responsiveness** — in-memory, update/retrieve in nanoseconds.

## When NOT to consider
- Large **transactional data volumes** — it all lives in memory; you can't fit a 45 TB DB.
- Tight **budget/time** — complex; realistic high-load testing is expensive and slow, so
  agility is low.
- Need high **data consistency** — eventually consistent; in-memory updates take time to
  reach the DB.

## Characteristics
Partitioning Technical · Cost $$$$$ · Agility ★★ · Simplicity ★ · Scalability ★★★★★ ·
Fault tolerance ★★★ · Performance ★★★★★ · Extensibility ★★★
