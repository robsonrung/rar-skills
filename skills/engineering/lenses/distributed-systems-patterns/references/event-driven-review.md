# Event-Driven Decision and Review

Paths named below are relative to the loaded skill root.

Sub-route from the ask and the repo, then stay on it:

| Sub-route | Signal |
| --- | --- |
| `new-system` | Greenfield, "should we use events/Kafka", first service on a broker |
| `existing-edm` | Broker clients, topics, schemas, stream processors already in the repo |
| `migrate` | Monolith/SOA with locked data, batch syncs, shared DBs, "liberate this" |

Verdicts: `adopt` | `hybrid` | `hold` | `review-fix` | `migrate-slice`.

**Adopt gate** — run on `new-system` and `migrate` before any design; read `references/edm-adopt-or-not.md` before naming the verdict. **`hold`** if any of these is true: the org will not treat streams as the **single source of truth** (the monolith DB stays authoritative and streams are a dump); the microservice tax (broker, schema registry, deploy/reset tooling, ownership) will not be paid centrally in the planning horizon; no second team or product needs the same domain data in near real time; the work is request-shaped (auth, fetch-a-profile, third-party HTTP) with no shareable narrative. `adopt` or `hybrid` only when shared domain data is locked in an implementation _and_ the tax will be paid; **`hybrid` is the default** when adopting — request-response stays for UIs, auth, and third parties. On `hold`, write the brief and stop. Do not design topics.

- **`new-system`** — after a non-hold gate, read `references/edm-event-contracts.md`, then `references/edm-implementation-styles.md`. Design the **data communication layer** first (streams, schemas, writers), then pick one implementation style per bounded context.
- **`existing-edm`** — read `references/edm-review-and-migrate.md` and walk the smell catalog against repo evidence. For every contract finding, load `references/edm-event-contracts.md` before prescribing a fix. Verdict is `review-fix` unless the system already satisfies the catalog.
- **`migrate`** — after a non-hold gate, read `references/edm-review-and-migrate.md`. Pick **one** liberation slice: the most-shared, most-locked domain data. Name the liberation pattern and why it is **event-first** enough. Do not plan a rewrite.

## Decision brief

Use `assets/edm-decision-brief.md` from this skill directory.

Decision brief (event-driven), required fields:

1. `job` — sub-route + one-sentence decision
2. `verdict`
3. `data_communication_layer` — what is (or would be) the stream-backed source of truth; or why there isn't one
4. `single_writer` — producer per public stream, or the violation
5. `evidence` — files, topics, schemas, or `assumed: …`
6. `rejected` — at least one alternative and the cost of taking it
7. `next_move` — one action (liberate _this_ entity, add _this_ schema, stop _this_ second writer)
8. `not_this_skill` — adjacent work that belongs to `macro-architecture`, `domain-driven-design`, or `data-systems-coding-lens`

## Event architecture constraints

8. A message queue that deletes after consume is not a **data communication layer**. Call that messaging, not event-driven microservices.
9. Do not split services to look "micro." Align on a business bounded context. Technical layers as services are a defect.
10. Do not share a materialized store across services; each consumer projects its own copy. Do not mix incompatible event types in one stream to "save topics." Do not dual-produce two versions of a service onto the same output stream.
11. Do not treat connector-based CDC as the finished architecture, and do not recommend a distributed transaction when a compensation workflow will do. Hybrid is expected; an all-event architecture is almost never the answer.
