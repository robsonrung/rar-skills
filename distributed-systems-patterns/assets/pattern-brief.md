# Distributed-systems pattern brief

Fill every section. If a fact is inferred, prefix it with `assumed:`.

## Job

- Route: `create` | `maintain` | `review`
- Decision in one sentence:

## Scale

`single-node` | `serving` | `batch`

## Pattern

Catalog name. Compose at most two and name how they join.

## Roles

Container or node → job. Mark the **coscheduled pair** if this is single-node.

## Container API

Parameters, ports, files, signals, and what would be a breaking change. `n/a` only when the pattern has no reusable container surface — say why.

## Failure

The failure that would make this pattern the wrong one (missing **readiness, not liveness**; shard-key miss; election without **need a master**; straggler fan-out; FaaS cold-start on a warm index).

## Evidence

- Files / manifests / probes / shard keys / lock clients:
- `assumed:` constraints:

## Rejected

| Alternative | Cost of taking it |
|---|---|
| | |

At least one row required.

## Next move

One action. Not a program.

## Not this skill

Work that belongs to `macro-architecture`, `event-driven-microservices`, `data-systems-coding-lens`, or `design-patterns`:
