# Serving patterns

Read when the family is long-running serving — replicas, shards, scatter/gather, FaaS, or ownership.

## Contents

1. [Replicated load-balanced](#replicated-load-balanced)
2. [Readiness, not liveness](#readiness-not-liveness)
3. [Sharded](#sharded)
4. [Scatter/gather](#scattergather)
5. [FaaS](#faas)
6. [Ownership election](#ownership-election)

## Replicated load-balanced

Every replica is homogeneous and can serve every request. A load balancer sits in front. Default for **stateless** serving.

Need at least two replicas for any serious SLA. A single instance cannot stay at three nines if you deploy daily: 1.4 minutes of allowed downtime per day disappears in one slow rollout. Horizontal scale is "add replicas."

Session stickiness is a variant, not the default. Caching, rate-limit, and TLS-termination layers are themselves more replicated load-balanced services in front of the app — compose, do not fold them into the app image.

State it as: *"replicated — every replica can answer; scale is replica count."*

## Readiness, not liveness

Two different probes, two different actions:

| Probe | Question | Action on fail |
|---|---|---|
| Liveness | Is the process sick? | Restart it |
| Readiness | May I send it user traffic? | Leave it running; take it out of the balancer |

Apps that load plugins, warm caches, or open databases are *alive* before they are *ready*. A missing readiness probe during rollout sends traffic to starting pods and looks like an outage.

On `review`, a replicated Service / Ingress / ALB with only a liveness probe (or none) is a blocking finding.

State it as: *"**readiness, not liveness** — this replica is up; it is not in rotation yet."*

## Sharded

Each shard can serve only a subset of requests. A root examines the request and sends it to the owning shard. Default when **state no longer fits one machine**, or when a replicated cache would store the same working set on every replica (Burns' 10×10 GB cache holding 5% vs 50% of a 200 GB set).

### Shard key

Hash only the parts that make two requests return the *same* body.

- Too general (path only, while language depends on client IP) → wrong cached body.
- Too specific (path + raw IP + timestamp) → no hits.
- Often right: `path` (+ query); or `country(ip) + path` when locale matters.

Deterministic and uniform. Re-shard only with a **consistent hash** — `hash % N` remaps almost every key when N changes; a consistent hash remaps about `keys / shards`.

### Cache criticality

Ask: if this shard dies, what happens to users?

Hit rate sets both capacity and latency. A 50% hit-rate cache in front of a 1,000 RPS layer is the difference between 2,000 RPS and a 500 storm when the cache vanishes. Rate the service below "cache-up" capacity, or replicate each shard.

**Hot shards** (one viral key) are expected. The remedy is a sharded *and* replicated service: each shard is itself a replica set you can scale independently.

State it as: *"sharded — the key is X; a miss on shard Y costs Z; consistent hash on resize."*

## Scatter/gather

Replication for *time*. The root farms one request to many leaves in parallel and merges the partial answers. Use when one request is an embarrassingly parallel computation, or when the data is sharded and every shard must contribute.

Two shapes:

| Shape | Leaf contents | Root merge |
|---|---|---|
| Root distribution | Homogeneous leaves; work is split | Combine partial results (intersect, reduce) |
| Leaf sharding | Each leaf holds a data slice | Union / concatenate the slice answers |

### Leaf count

Gains are asymptotic: request overhead grows with leaf count and eventually dominates. Worse, the user waits for the *slowest* leaf. A leaf with 99th-percentile 2 s latency becomes a 95th-percentile 2 s system at 5 leaves, and an almost-guaranteed 2 s system at 100 leaves. That is the straggler problem.

On `create`, name the merge function and the leaf-count cap. On `review`, unbounded fan-out without a straggler story is `revise`.

State it as: *"scatter/gather — merge is X; leaf cap is N because of stragglers."*

## FaaS

Functions are the most granular building block: no artifact beyond source, auto-scale, auto-restart. They also force total decoupling — no local memory, all state in a store, communication only over the network.

**Use** for small stateless transforms: HTTP decorator (default missing fields, then call the real API), event handlers (2FA SMS on a login event), short event pipelines (signup → email → CRM).

**Do not use** when any of these is true:

- the work is long-running / background (transcode, compact logs) — FaaS runtimes are time-bounded
- the handler needs a large warm working set (search index) — cold start blows the SLA, and if traffic is high enough to stay warm you are overpaying
- a core is already busy serving requests — pay-per-request loses to a reserved VM/container; prefer an open-source FaaS on your orchestrator so the developer UX stays and the cost model changes
- the function graph can loop (`A→B→C→A`) — there is no static call graph; this needs **observable failure** (budget + recursion alerts) before launch

Decorator vs adapter: an adapter **coscheduled pair** scales with the app. A FaaS decorator scales independently — right when the transform is much cheaper than the service.

State it as: *"FaaS — this is a decorator/event/pipeline; it is not a long job and has no warm index."*

## Ownership election

**Need a master** is the first question, not the last.

A singleton in an orchestrator already:

- restarts on process crash (seconds → roughly four nines if it crashes daily)
- restarts on a hung liveness probe
- relocates on node death (minutes; two nines if *every* node dies daily — you have bigger problems)

Deploy time is the real singleton tax. Daily 2-minute image pulls → two nines. Pre-pull shrinks that, at the cost of the complexity election was supposed to avoid. Many background jobs should stay singletons.

Elect only when the SLA is four+ nines *and* two replicas cannot both be active. Do not implement Paxos/Raft. Use a store that already did (etcd, ZooKeeper, Consul): compare-and-swap + TTL is enough for locks, leases, and ownership. A lock without TTL is a permanent outage when the holder dies.

On `review`, an election library with no proof of **need a master** is `revise`. On `create`, prefer the singleton and name the SLA that would change your mind.

State it as: *"**need a master**? no — singleton; yes — lease in etcd with TTL, not a home-rolled consensus."*
