# DDD Strategic — Context Boundaries, Language & Integration Catalog

Detailed reference for the `domain-driven-design` skill (strategic part — Part A). Source: *Learning Domain-Driven Design*,
Vlad Khononov (O'Reilly, 2021), Chapters 1–4, 11, 14–15.

## Subdomains vs. bounded contexts (Ch. 1, 3)

- **Subdomain** — a *problem* area of the business. Three types:
  - **Core** — competitive advantage; complex and volatile; build in-house, model richly.
  - **Supporting** — necessary but not differentiating; simple; CRUD-ish; can outsource.
  - **Generic** — solved elsewhere; buy/integrate (auth, PDF, payments, ERP connectors).
- **Bounded context** — a *solution* boundary where exactly one model and one ubiquitous
  language are internally consistent.
- They can align 1:1 or a context can span several subdomains. The book's guidance: let
  the context's size be a **function of its model**, not a target size.

## Bounded-context boundary heuristics (Ch. 3, 10)

- A bounded context is the **consistency boundary of a ubiquitous language**. Where the
  same term changes meaning, you've found a boundary.
- **Start wide, split later** for volatile/uncertain areas. Logical (in-process) boundaries
  are cheap to refactor; physical (service/db) boundaries are expensive. For a core
  subdomain, you can protect against wrong guesses by drawing the context wide enough to
  include the subdomains it interacts with most.
- A change that **must touch multiple contexts together** = boundaries are wrong. Such
  changes need cross-team coordination and tend to ossify into tech debt.
- **Ownership:** one team per context (a team can own several; a context shouldn't be split
  across teams).

## Integration-pattern catalog (Ch. 4)

Relationships between two contexts, by who controls the model and how much they cooperate:

### Cooperation (teams succeed/fail together)
- **Partnership** — ad hoc, bidirectional coordination; integration evolves as needed.
- **Shared Kernel** — a shared subset of the model owned by multiple contexts/teams. Any
  change ripples to all sharers → high coordination cost. Keep it small and stable. In this
  repo: `backend/common` + `gslogic`. Watch for context-specific logic creeping into it
  that should live in one service instead.

### Customer–Supplier (one upstream, one downstream)
- **Conformist** — downstream conforms to upstream's model with no translation. Cheap, but
  upstream's model leaks in. Acceptable only when upstream's model is good enough and you
  can't influence it — fine for non-core consumers, risky for core subdomains.
- **Anticorruption Layer (ACL)** — downstream translates upstream's model into its own at
  the boundary, preventing corruption of its model. **Use for external/legacy/third-party
  integrations** — e.g. every ERP connector in `erp-sync-workflow`. The ACL is where the
  foreign vocabulary is mapped to ours and never deeper.
- **Open-Host Service (OHS)** — upstream protects *downstream* by exposing a stable,
  versioned **published language** (a public API/event contract) decoupled from its
  internal model. Use when a context has many consumers. The OpenAPI contract that
  generates the frontend RTK Query layer is an OHS-style boundary; consumers should bind
  to the published contract, not internals.

### Separate Ways
- No integration — duplicate the functionality instead. Rational when integration cost >
  duplication cost, when models differ too much, or for a generic subdomain that's cheap to
  re-implement locally.

## Context Map (Ch. 4)

A context map is the high-level view of all contexts and their integration relationships.
It reveals communication patterns, ownership, and organizational issues (e.g., a context
every team must conform to is an organizational bottleneck). Useful as the mental model
when judging whether a new edge between two services is healthy.

## Asynchronous integration (Ch. 9, 15)

Across contexts on a message bus (EventBridge here):
- **Outbox** — atomically commit state + outgoing events, relay publishes reliably. Prevents
  lost or premature events. (See Part B Lens B5 for the algorithm.)
- **Saga** — listens to events from one context, issues commands to another, compensates on
  failure. For reactive cross-context flows.
- **Process Manager** — owns the explicit state of a multi-step, possibly branching process.
  It is itself an aggregate with a lifecycle.
- **Event-driven coupling traps (Ch. 15):** beware a *distributed big ball of mud* —
  temporal coupling (B must run right after A), functional coupling (B duplicates A's
  rules), implementation coupling (B depends on A's internal event shape). Prefer events
  that carry meaning over events that leak internals; consume an OHS/published event, not a
  raw internal one.

## Ubiquitous language rules (Ch. 2)

- The language is **of the business**, captured from domain experts, used consistently in
  conversation, models, **and code** (class/method/table/field names, tests, docs).
- It is **per bounded context** — consistent *within*, allowed to differ *across*. The same
  word meaning two things in two contexts is the point of having two contexts.
- It's a **continuous effort** — the language evolves as understanding deepens; keep code
  names in sync rather than letting a glossary rot.
- Smells (jargon for business terms, one concept under many names, CRUD names hiding a
  real business process, primitive types where a named concept belongs): the actionable
  checklist lives in `SKILL.md` Lens 2.

## Subdomain drift (Ch. 11)

Subdomain types change over time; the **inability of the current design to support new
needs** (extension pain) is the signal:
- Supporting → core: move in-house, invest in a richer model.
- Core → supporting/generic: simplify; stop paying for sophistication you no longer need.
- Generic → core (rare): a bought solution became your differentiator; build it.

Strategic drift should pull tactical patterns with it (see Part B Lens B6).
