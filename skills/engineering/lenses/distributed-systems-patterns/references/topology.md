# Topology

Default to the **smallest coherent shape**: reusable container before new service; singleton before election; replica before shard; work queue before coordinated batch.

## Decision order

Walk top to bottom and stop at the first yes.

1. Two processes must share a machine and a namespace → single-node: sidecar (augment), ambassador (broker outbound), adapter (normalize inbound).
2. One-shot or offline transformation of a set → batch.
3. Otherwise serving:
   1. Every replica can answer every request, with no per-user durable state → replicated.
   2. One request needs every leaf, merged at a root → scatter/gather.
   3. State or the cache working set no longer fits one machine → sharded.
   4. A short stateless transform scaled apart from the service → FaaS.
   5. Exactly one process must own a task → **need a master**? No: singleton. Yes: election.

## Single-node

Run the **coscheduled pair** test first: scheduled as one atomic group, sharing localhost, volumes, or PID namespace as needed, failing and restarting together. A proxy on another host is a service, not an ambassador.

- **Sidecar**: add TLS, config sync, or git-pull deploy to an app you won't change. Not when the helper must place or scale independently, or carries core business logic.
- **Ambassador**: the app talks to localhost; the helper owns sharding, a service broker, or traffic splitting. Not when you own the server and can route there more cheaply. Shard routing as a service simplifies clients and complicates the storage deploy; a client-side ambassador does the reverse.
- **Adapter**: make metrics, logs, or health of a vendor image match the platform contract. Not when you own the app and changing it is cheaper. A patched vendor image costs more than a shared adapter.

Don't bake HTTPS, metrics, log shipping, or config sync into every app image; that is a reusable container with a **container API**. A change is breaking if an old invocation stops working or silently changes load: an update interval moving from seconds to milliseconds still parses and still breaks. Name the parameters on create; flag unnamed or renamed ones on review. A helper only one app can use has too specific an API.

## Serving

- **Replicated**: the default for stateless serving. Two replicas minimum for any serious SLA; one instance cannot hold three nines through daily deploys. Probe **readiness, not liveness**: apps that load plugins, warm caches, or open databases are alive before they are ready. A replicated service with only a liveness probe, or none, is a blocking finding.
- **Sharded**: shard when state no longer fits, or when a replicated cache would store the same hot set N times. Don't shard stateless load; replicate it. Hash only the parts that make two requests return the same body: too general serves the wrong body, too specific wrecks the hit rate (`path`, or `country(ip) + path` when locale matters). Resize only with a consistent hash; `hash % N` remaps nearly every key. Ask what happens to users when a shard dies: losing a 50% hit-rate cache in front of a 1,000 RPS backend doubles its load. Rate the service below cache-up capacity or replicate each shard. Hot shards are expected; the remedy is sharded and replicated.
- **Scatter/gather**: latency is the slowest leaf. A leaf whose 99th percentile is 2 s gives a 2 s median at 100 leaves. Name the merge function and a leaf-count cap; unbounded fan-out without a straggler story is `revise`.
- **FaaS**: for short stateless transforms (an HTTP decorator, an event handler, a short pipeline). Not for long-running work, a large warm working set, or a core that stays busy (pay-per-request loses to a reserved container). A function graph that can loop needs budget and recursion alerts before launch. An adapter scales with the app; a FaaS decorator scales independently.
- **Election**: an orchestrated singleton restarts in seconds and relocates in minutes; deploy time is its real tax. Elect only when the SLA is four nines or more and two active replicas would corrupt ownership. Never home-roll consensus: compare-and-swap plus TTL in etcd, ZooKeeper, or Consul. A lock without a TTL is a permanent outage when its holder dies.

## Batch

- **Work queue**: one item to one reliable output. The source lists items over localhost and never marks completion; the worker is one-shot and reads its item from a mounted file. Let the orchestrator's Job primitive own retries and node death. Scale workers on queue depth.
- **Event-driven batch**: linked queues, every hop a named primitive: copier (one stream to N identical), filter (drop by predicate), splitter (route by predicate), sharder (partition evenly; a lost shard spills to healthy ones), merger (many to one). An implicit chain of queues with unnamed hops is incomplete. On maintain, change one hop; don't collapse two primitives into a custom worker.
- **Join** waits for every branch and does not fold values. **Reduce** folds same-shaped partial outputs and can start before the map phase finishes.

## Composes

Compose at most two in the brief; for more, the graph goes in roles and the headline is the outermost pattern. Legal: ambassador plus sharded service; adapter plus anything; replicated shards; scatter/gather plus leaf sharding; FaaS decorator before a replicated service. Rename these: a "sidecar" on another node is a service; a "shard" of a keyless stateless API is a replica; an "election" around a job queue is a singleton or work queue; a "FaaS pipeline" of long jobs is event-driven batch.
