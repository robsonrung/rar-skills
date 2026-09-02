# Batch computational patterns

Read when the family is batch — work queues, linked queues, or coordinated reduce/join.

## Contents

1. [Work queue](#work-queue)
2. [Event-driven batch](#event-driven-batch)
3. [Coordinated batch](#coordinated-batch)
4. [Compose, do not hide the graph](#compose-do-not-hide-the-graph)

## Work queue

One input item → one reliable output. The reusable piece is the _queue infrastructure_; the user supplies two **container API**s.

| Role | Interface | Why this shape |
| --- | --- | --- |
| Source | HTTP on localhost: list items, fetch item body. Does **not** mark completion | Repeated calls, no cluster security surface; completion is the manager's job |
| Worker | One-shot. Env `WORK_ITEM_FILE` (or equivalent) points at a mounted file with `item.data` | One call, no extra HTTP server in a shell-script worker; the file can be a ConfigMap |

The manager's loop: load items from the source → diff against jobs already created → spawn a Job per new item → record success when the Job completes. Prefer the orchestrator's Job primitive so retries and node death are its problem, not yours.

Dynamic scale workers with queue depth. Multi-worker: several specialist containers in one worker group (detect, then blur) so each image stays reusable.

State it as: _"work queue — source lists, worker consumes a file, Jobs own reliability."_

## Event-driven batch

When one transformation is not enough, link queues. The completion of one stage is the event that feeds the next. Without a named graph this becomes an undebuggable function stew — same failure as FaaS-without-a-blueprint.

Name every hop as one of these primitives:

| Primitive | Job | Typical use |
| --- | --- | --- |
| Copier | Duplicate one stream onto N identical streams | Transcode the same video into 4K / 1080p / mobile / GIF |
| Filter | Drop items that fail a predicate | Keep only users who opted into email |
| Splitter | Send each item to one (or more) of N queues by a predicate | Shipping notices → email queue and/or SMS queue |
| Sharder | Partition evenly by a shard function | Staged worker rollouts (a bad image hits 1/4 of users); spread across regions |
| Merger | Many sources → one queue | All git repos feed one build farm |

A splitter can be a copier plus filters; prefer the splitter when that is the actual job. A sharder that loses a shard must spill to healthy shards, not stall.

Filters and mergers are adapters around existing sources — reuse the work-queue **container API**, do not fork the source image.

State it as: _"event-driven batch — the graph is copier → filter → …; every hop is a named primitive."_

## Coordinated batch

Use when parallelism has to _rendezvous_, not just hand off.

### Join (barrier)

Hold items until every parallel branch has finished. Example: do not delete originals until every blur shard has succeeded, so a catastrophic failure can rerun the pipeline.

A join is _not_ a reduce. It waits; it does not fold values.

### Reduce

Optimistically merge partial outputs into a smaller set of the same shape, repeat until one remains. Unlike join, reduce can start before the map/shard phase is finished.

Same code at every level: count (sum frequencies), sum (add measures), histogram (re-weight by population, then merge bins). Because input and output have the same shape, you can add reduce layers without rewriting workers.

State it as: _"join — wait for all; reduce — fold now, repeat until one."_

## Compose, do not hide the graph

Real pipelines are serving-family patterns plus these primitives. Burns' image pipeline: shard → multi-worker (detect + blur) → join → copier (delete originals \| recognize) → shard → multi-worker (type + color) → reduce.

On `create`, draw the graph with named primitives before picking images. On `review`, an implicit chain of queues with no named primitive per hop is incomplete. On `maintain`, change one hop; do not collapse two primitives into a custom worker to "simplify."
