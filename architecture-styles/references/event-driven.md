# Event-Driven Architecture

**Class:** Distributed · Technical partitioning. Asynchronous, highly decoupled.

## Topology
Components:
- **Event processor** (today: a *service*) — the deployment unit; ranges from a single
  function (validate an order) to a large process (settle a trade). Triggers and/or
  responds to events.
- **Initiating event** — comes from outside, kicks off a workflow (place order, file claim).
  Noun-verb (`Place Order`). Usually point-to-point (queue) to one service.
- **Processing / derived event** — a service advertising a state change it made. Verb-noun
  (`Order Placed`). Usually publish-subscribe (topic) — one initiating event fans out to
  many processing events, fully decoupled and non-deterministic.
- **Event channel** — the messaging artifact (queue or topic).

**Architectural extensibility:** services advertise *what they did* even if nothing
listens yet — future services hook in with zero changes to existing ones.

## Event vs message (subtle but important)
- **Event** = "I did X" (state change). Sender owns the channel *and* the contract;
  broadcast, sender doesn't know who responds. Pub-sub.
- **Message** = "do X" / "give me X" (command/request to one known service). Receiver owns
  the channel and contract. Point-to-point.

## When to consider
- Business is **reacting** to things happening (listen for "event", "trigger", "react"),
  not just responding to user requests.
- Need high **performance, scalability, fault tolerance** (its superpowers).
- Complex, **non-deterministic** workflows that defy modeling as decision trees (CEP).

## When NOT to consider
- Mostly **request-based** processing (CRUD, fetch-a-profile) needing synchronous results.
- Need high **data consistency** — everything is eventually consistent; no timing guarantee.
- Need control over workflow **ordering/timing** ("A&B before C, D before E") — use
  orchestrated service-based / orchestrated microservices instead.
- **Error handling** is hard: no central orchestrator; a service must self-repair while
  other async actions already happened (customer charged + notified, then inventory fails).

## Characteristics
Partitioning Technical · Cost $$$ · Agility ★★★ · Simplicity ★ · Scalability ★★★★★ ·
Fault tolerance ★★★★★ · Performance ★★★★★ · Extensibility ★★★★
