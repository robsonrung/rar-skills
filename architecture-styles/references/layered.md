# Layered (n-tier) Architecture

**Class:** Monolithic · Technical partitioning. The de-facto default; aligns with teams
organized by technical role (UI / backend / DBA).

## Topology
Horizontal layers, each with one responsibility: **presentation → business → persistence →
database**. Smaller apps collapse to three (business+persistence merged); larger ones add
layers (e.g. a shared services layer).

- **Closed layer** (default): a request *must* pass through it to reach the next — this is
  *layers of isolation*: a change in one layer doesn't ripple to others. Swapping
  Angular→React touches only presentation; swapping RDBMS→NoSQL touches only persistence.
- **Open layer**: requests may bypass it. Use for a shared-services layer placed *below*
  business so business can skip it to reach persistence.

## When to consider
- Tight budget / time constraints — simplest, cheapest, best-understood style.
- Small or simple apps and websites.
- Most changes isolate to a single technical layer (re-skin UI, swap DB, change rules only).
- Team is technically partitioned (Conway's Law alignment).
- Good **starting point** when you don't yet know the right style.

## When NOT to consider
- High operational needs: scalability, elasticity, fault tolerance, performance — it's
  monolithic; a fatal error takes the whole app down, and you must scale 100% of it to
  scale any part.
- Most changes are **domain-scoped**, not layer-scoped: adding one field
  ("expiration date on My Movie List") cuts *every* layer and may need 3–4 teams to
  coordinate. Domain-partitioned (cross-functional) teams fit this style poorly.

## Watch out: architecture sinkhole anti-pattern
Requests that fall straight through every layer doing nothing (pure pass-through). Apply
the **80/20 rule**: ~20% pass-through is fine; if the *majority* of requests are
pass-through, the layering is buying isolation you aren't using — consider opening layers
or a different style.

## Characteristics
Partitioning Technical · Cost $ · Agility ★ · Simplicity ★★★★★ · Scalability ★ ·
Fault tolerance ★ · Performance ★★★ · Extensibility ★
