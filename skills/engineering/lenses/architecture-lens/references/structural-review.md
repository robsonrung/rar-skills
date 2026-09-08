Use the lenses that match the affected boundaries. A full structural review covers Lenses 3–6 without a required order. Load [review-rubric.md](review-rubric.md) for their detailed checks and public-seam rules.

# Lens 3 — Layer placement & boundary leaks

Each piece of code belongs to one layer. Map the affected code and its layer relationships (generic model; infer the repo's equivalent before reviewing):

- **Business layer** — domain rules: invariants, pricing, compliance, lifecycle. Lives in domain/entities, callable from any application caller.
- **Application layer** — software that automates business logic: routes & services, workers, the frontend state/API layer.
- **Technology layer** — infra-neutral plumbing: cloud, DB connection, auth. Business-agnostic.

Flag leaks:

- **Business logic in the wrong layer** — pricing/compliance/lifecycle rules inside a route handler, a UI component, a glue function, or a migration. It belongs in domain code.
- **Technology bleeding up** — raw SQL, cloud SDK calls, queue payloads, storage keys showing up in business/domain code. The domain shouldn't know what it runs on.
- **Layer skip** — frontend reaching past the application API into infra; a route reaching past services into raw infra.

Rule of thumb: _application services apply technology to solve business problems_ — business rules stay technology-neutral, tech stays business-neutral.

## Lens 4 — Element cohesion ("one element = one idea")

An element (module, service, function, component, entity) should have **one focus**:

- A function/service doing two unrelated jobs → split it.
- A `util`/`helpers`/`misc` grab-bag accreting unrelated responsibilities → name the real responsibilities and separate them.
- A component mixing data-fetching, business rules, and presentation → extract.
- An entity carrying fields/logic for an unrelated concern → it's modeling two things.

Ask: _if I had to write a one-line "viewpoint" for this element — who reads it, what's its one concern — could I?_ If the sentence needs an "and", suspect low cohesion. Low cohesion + high coupling is the signal to split or regroup.

## Lens 5 — Dependency direction

In a focused model each element only connects to elements it's _allowed_ to, and dependencies flow a defined way:

- **Direction across layers** — dependencies point **down**: application → business → (nothing); technology supports above. Business code importing a route handler, or domain importing application code, is backwards.
- **Allowed relationships** — does this new import/call connect things that _should_ know about each other? A worker reaching into frontend code, a service importing a sibling's internals instead of its public interface, etc.
- **Depend on the exposed interface, not the implementation.** Importing internals = depending on structure, not behavior.

## Lens 6 — Scope discipline (the smallest coherent shape)

Hold the change to its **smallest coherent shape**:

- **Premature abstraction / gold-plating** — generic frameworks, config knobs, or extension points with one caller and no second use case in sight. Deliver the MVP slice.
- **Scope creep** — a focused bugfix/feature that's quietly become a refactor of everything it touched. Flag the part that exceeds the stated goal.
- **Over-modeling** — layers, indirection, or "future-proofing" the task didn't ask for. Tangible artifacts now over complete theory later.

State it as: "X is in scope; Y, Z look like scope creep / speculative — split or drop?"
