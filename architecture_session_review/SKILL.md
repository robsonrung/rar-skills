---
name: architecture_session_review
description: Session-level architecture review for a change that is architecturally significant but has no single specific lens — it ties the lenses together into one pass plus an ADR. Use for whole-session architecture reviews, refactors, migrations, feature design, pull request review, and ADR drafting. Distinct from design-gate, which ROUTES a change to the right specific lenses; if you need to pick lenses, use design-gate. Distinct from architecture-lens (code-level connascence/trade-offs and layer placement/cohesion), which this skill points to rather than re-implementing.
---

# Architecture Session Review

Use this skill to make architecture thinking useful during coding work. The goal is not to summarize architecture theory. The goal is to turn architectural concerns into better implementation choices, concrete verification, and clear decision notes.

## Core Workflow

1. Inspect the live code, repo guidance, current behavior, and any user supplied issue or design context before judging the architecture.
2. Classify the scope of the change as local code, module, component, service, data boundary, deployment unit, or enterprise integration.
3. Identify the top quality attributes that matter for this task. Prefer three or fewer unless the user asks for a broad review.
4. Map the relevant boundaries: components, dependencies, public contracts, data ownership, runtime communication, and deployment constraints.
5. Choose the smallest useful architecture pass:
   1. Light pass for one file, one function, or a narrow refactor.
   2. Standard pass for cross module changes, shared abstractions, public APIs, data access, or important tests.
   3. Deep pass for service boundaries, storage ownership, architecture style choices, migration plans, operational behavior, or decisions that should be recorded.
6. Implement the change in the style of the repo, keeping edits scoped.
7. Convert each important concern into a verification step. Prefer executable checks over opinions.
8. Finish with changed files, checks run, decision summary, and remaining risk.

## Architectural Significance Filter

Treat a choice as architecturally significant when it affects at least one of these:

1. System structure or component boundaries.
2. Quality attributes such as maintainability, scalability, performance, availability, security, resilience, deployability, observability, testability, usability, or portability.
3. Dependencies between modules, services, teams, or vendors.
4. Public interfaces, contracts, protocols, schemas, migrations, or versioning.
5. Data ownership, read and write paths, transactions, consistency, or integration flow.
6. Construction technique, framework, platform, tool, build system, or process choice that will be hard to reverse.

If none apply, keep the work at normal code review depth.

## Lenses to run, not re-implement

This skill is the session-level frame; it does not re-derive the per-lens analyses. Delegate them:

- **Trade-offs and coupling** → run `architecture-lens`: name the **connascence** type (strength × locality × degree) for any coupling the change adds, and use its decision lens to compare options (every option states what it gains and gives up — no option is free).
- **Layer placement and cohesion** → run `architecture-lens`: does each module keep one clear responsibility, and does the dependency direction stay clean?
- **Runtime / data flow** → confirm the owning component or service stays clear and that sync vs async matches the needed reliability, latency, and consistency.
- **Fitness function** → for each boundary worth protecting, name the automated check that guards it in future changes.

Carry the findings from these lenses into the risk pass and the decision note below.

## Decision Record Trigger

Create or draft an ADR when the decision changes long lived direction, affects more than one team, changes risk posture, introduces a platform or vendor, changes data ownership, changes public contracts, or resolves a repeated debate.

Use the ADR template in `references/adr_risk.md`.

## Risk Pass

For standard and deep passes, name risks with impact and likelihood:

1. Low: small impact or unlikely.
2. Medium: meaningful impact or plausible.
3. High: severe impact and plausible, or unknown technology.

For each high risk item, provide a mitigation, verification step, and owner if the user has given team context. If the task is code only, make the owner the current change set. For the full per-risk record fields, use `references/adr_risk.md`.

## Verification Menu

Choose checks matching your top quality attributes — pick checks for the two or three attributes the change most affects, not every attribute. The full per-attribute catalog of concrete checks is in `references/verification_menu.md`; read it when you need the specific checks for an attribute.

## Output Contract

For implementation work, keep the final response concise:

1. What changed.
2. Why the change is architecturally safe or what trade off it accepts.
3. Verification run.
4. Remaining risk.

For review work, lead with findings by severity and include file and line references.

## References

Read only what is needed:

1. `references/architecture_lens.md` for quality attributes, modularity, component thinking, and fitness functions.
2. `references/style_fit.md` for architecture style selection.
3. `references/adr_risk.md` for ADRs, risk analysis, and diagrams.
4. `references/team_checklists.md` for team boundaries, review checklists, and release checks.
5. `references/verification_menu.md` for the per-attribute catalog of concrete verification checks.
