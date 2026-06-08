# Architecture Lens

Use this reference when coding work touches structure, boundaries, or long lived quality.

## Architecture Elements

Assess architecture through four practical elements:

1. Structure: the chosen topology, components, services, deployment units, and runtime flow.
2. Quality attributes: the success criteria beyond feature behavior.
3. Decisions: rules that guide implementation choices.
4. Design principles: softer guidance that helps developers choose within constraints.

## Quality Attribute Discovery

Start from the domain and the task. Avoid broad lists unless doing a broad review.

1. Operational attributes: availability, continuity, performance, recoverability, reliability, robustness, scalability, elasticity.
2. Structural attributes: configurability, extensibility, installability, reuse, localization, maintainability, portability, supportability, upgradeability.
3. Cross cutting attributes: accessibility, archivability, authentication, authorization, legal and regulatory fit, privacy, security, supportability, usability.

Good architecture work usually selects a small set and makes trade offs explicit.

## Modularity Review

Use these questions:

1. Cohesion: would splitting this module increase coupling and reduce readability?
2. Coupling: did the change add incoming or outgoing dependencies that make the module harder to reuse or change?
3. Abstraction balance: is the code too concrete to evolve or too abstract to understand?
4. Connascence: what knowledge must two places share for the system to stay correct?
5. Locality: are strong forms of shared knowledge kept inside the same component?
6. Degree: how many files, modules, services, or teams are affected if this changes?

Favor weaker coupling across wider boundaries. Strong coupling can be acceptable inside a cohesive component.

## Component Thinking

When a task touches component structure, use this loop:

1. Identify candidate components from domain behavior, not only data entities.
2. Assign requirements or stories to components.
3. Check roles and responsibilities.
4. Apply the most important quality attributes.
5. Restructure components when feedback shows wrong granularity.
6. Revisit public contracts and data ownership.

Watch for entity shaped components that only mirror tables. That often means the design is driven by storage rather than behavior.

## Fitness Functions

A fitness function is an objective integrity check for architecture.

Useful coding session forms:

1. Dependency cycle test.
2. Layer access rule.
3. Forbidden import rule.
4. Public contract test.
5. API schema compatibility test.
6. Query performance check.
7. Migration dry run.
8. Security configuration check.
9. Service health or smoke test.
10. Observability check for logs, metrics, or traces.

If a concern matters repeatedly, encode it so future work cannot quietly break it.
