# Architecture characteristics checklist (the "-ilities")

When making a decision, you rarely optimize all of these — you pick the 2–4 that matter *here* and accept worse scores on the rest. The job is to name the tension, not to maximize everything (that's impossible; characteristics conflict).

Use this list to ask: *"Which of these does this decision actually trade on?"*

## Operational (runtime behavior)
- **Performance** — latency / response time under expected load.
- **Scalability** — holds up as load grows.
- **Elasticity** — handles sudden bursts (spikes), not just steady growth.
- **Availability** — uptime; tolerance of partial failure.
- **Reliability / fault tolerance** — keeps working when a part fails.
- **Recoverability** — how fast it comes back after an incident.

## Structural (code & change)
- **Maintainability** — ease of routine changes.
- **Testability** — ease of writing & running meaningful tests.
- **Deployability** — how easily/safely it ships (size, frequency, risk of a release).
- **Modularity** — clean separation into cohesive, loosely-coupled parts.
- **Configurability / extensibility** — adding behavior without surgery.
- **Evolvability** — tolerance of large structural change over time.

## Cross-cutting (don't fit neatly)
- **Security** — authn/authz, data protection, attack surface.
- **Usability / accessibility** — for the people who use it.
- **Observability** — can you see what it's doing in production?
- **Privacy / compliance** — regulatory and data-handling constraints.

## How to apply

1. From the change at hand, pick the **2–4 characteristics in genuine tension** (e.g. "this is performance vs. maintainability"). Naming more than ~4 usually means the decision isn't really framed yet.
2. State which you're prioritizing and which you're consciously sacrificing.
3. That prioritization *is* the justification for the option you pick. Write it down if the decision is significant (→ ADR).

Watch the common traps:
- Treating every characteristic as required ("we need it all") — that yields no architecture, just wishful thinking.
- Optimizing a characteristic nobody asked for (gold-plating scalability for a tool with 5 users).
- Ignoring an *implicit* one the domain demands (e.g. auditability in finance, even if no ticket says so).
