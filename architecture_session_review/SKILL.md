---
name: architecture_session_review
description: Use when a coding task may affect software architecture, module boundaries, service boundaries, data ownership, dependencies, deployment behavior, quality attributes, architecture decisions, technical risk, or long lived implementation direction. Use for architecture reviews, refactors, migrations, feature design, pull request review, ADR drafting, and code work where trade offs matter.
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

## Trade Off Frame

For important choices, compare options using this compact frame:

1. Option.
2. Benefits.
3. Costs.
4. Quality attributes helped.
5. Quality attributes harmed.
6. Business reason.
7. Failure mode.
8. Verification.

Never present an option as universally correct. Favor the option with the least harmful trade off for the current domain, team, and constraints.

## Boundary Review

Use this pass before large edits and during review:

1. Cohesion: does each module or component have one clear responsibility at the current granularity?
2. Coupling: what now depends on what, and did the change add a harder to change dependency?
3. Connascence: will a change in one place force another change elsewhere because of names, types, values, order, timing, identity, or shared algorithm?
4. Locality: are strong dependencies kept close and weaker dependencies used across boundaries?
5. Data flow: does the owning component or service remain clear?
6. Runtime flow: does sync or async communication match the needed reliability, latency, and consistency?
7. Fitness function: what automated check can guard this boundary in future changes?

## Decision Record Trigger

Create or draft an ADR when the decision changes long lived direction, affects more than one team, changes risk posture, introduces a platform or vendor, changes data ownership, changes public contracts, or resolves a repeated debate.

Use this structure:

1. Title.
2. Status.
3. Context.
4. Decision.
5. Consequences.
6. Compliance.
7. Notes.

Put more weight on why than how. Include rejected options when the decision is likely to be revisited.

## Risk Pass

For standard and deep passes, name risks with impact and likelihood:

1. Low: small impact or unlikely.
2. Medium: meaningful impact or plausible.
3. High: severe impact and plausible, or unknown technology.

For each high risk item, provide a mitigation, verification step, and owner if the user has given team context. If the task is code only, make the owner the current change set.

## Verification Menu

Choose checks that match the quality attributes:

1. Modularity: dependency cycle checks, forbidden import checks, architecture tests, public API tests.
2. Maintainability: complexity budgets, cohesive file and module boundaries, duplication checks, clear naming.
3. Performance: benchmarks, query plans, p95 checks, load focused smoke tests.
4. Scalability and elasticity: queue depth checks, concurrency tests, capacity assumptions, back pressure tests.
5. Availability and resilience: retry behavior, timeout checks, fallback tests, chaos or failure mode tests when appropriate.
6. Security and privacy: auth path tests, least privilege checks, dependency scans, sensitive data checks.
7. Data integrity: migration tests, contract tests, idempotency tests, transaction and consistency tests.
8. Deployability: build checks, migration dry runs, rollback notes, release checklist.
9. Observability: logs, metrics, traces, alert coverage, local log review.

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
