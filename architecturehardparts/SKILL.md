---
name: architecturehardparts
description: Apply Software Architecture The Hard Parts style tradeoff analysis during coding sessions. Use when the user asks about coupling, modularity, monolith decomposition, microservices, bounded contexts, service granularity, data ownership, distributed transactions, sagas, workflow orchestration, choreography, contracts, ADRs, or architecture fitness functions. Avoid for routine bug fixes unless architecture choices are involved.
---

# Architecture Hard Parts

Use this when a coding session contains an architecture decision, not just an implementation task.

## Mental Model

Architecture choices are contextual tradeoffs. No pattern is best outside the current constraints. Anchor each recommendation in coupling, data ownership, deployability, runtime behavior, and validation.

## Workflow

1. Name the decision in one sentence.

   Include the current system shape, the change being considered, and the architectural force involved. Example forces include service boundaries, data ownership, transaction consistency, workflow coordination, shared code, contract shape, scaling pressure, and failure isolation.

2. Reproduce the current shape from code and runtime evidence.

   Read the relevant modules, schemas, migrations, tests, dependency manifests, deployment descriptors, service contracts, queues, jobs, logs, and dashboards. Prefer current repo evidence over remembered architecture.

3. Map coupling before proposing a change.

   Check static coupling through imports, package dependencies, shared libraries, schema access, deployment coupling, configuration, and infrastructure dependencies. Check dynamic coupling through request flow, messaging, consistency requirements, workflow state, coordination ownership, retries, timeout behavior, and compensation paths.

4. Decide whether the work is pulling apart or putting back together.

   Pull apart when the evidence favors maintainability, testability, deployability, scalability, fault isolation, security isolation, change isolation, or database type fit. Put back together when the evidence favors single unit transactions, tightly related data, heavy workflow chatter, frequent shared domain code changes, low latency, or simpler ownership.

5. Read the focused reference only when needed.

   Read `references/catalog.md` for the decision catalog when the task involves decomposition, service granularity, data decomposition, reuse, data ownership, eventual consistency, workflows, sagas, contracts, or data mesh.

   Read `references/adrtemplate.md` when the user wants a durable written decision, when the choice affects multiple teams, or when the code change creates an architectural precedent.

6. Compare options with the local context.

   Use a short matrix in prose. Keep options mutually exclusive and collectively complete for the decision at hand. Avoid generic pros and cons that ignore the repo, domain workflow, data model, operational constraints, or team boundaries.

7. Prefer bottom line clarity.

   Give the user or stakeholder the practical choice in terms of outcome. Examples: choose faster response over immediate consistency, choose independent deployability over shared transaction simplicity, choose a shared library over a shared service because the function is domain local and latency sensitive.

8. Implement the smallest architecture preserving change.

   Keep edits scoped to the decision. Preserve existing module boundaries unless the decision is to change them. Add tests or fitness functions that guard the architecture property, not only the domain behavior.

9. Close with verification.

   Report the code changed, the tradeoff accepted, the fitness function or test added, and any risk that still needs a follow up decision.

## Fitness Function Prompts

Use these prompts to turn an architecture choice into validation:

1. What must stay isolated after this change?
2. What dependency, import, schema access, service call, queue, or shared library would violate that isolation?
3. Can a test, static check, migration check, contract test, monitor, or alert fail when the architecture drifts?
4. Is the check architecture focused rather than domain focused?

## Output Contract

For architecture decisions, produce a concise decision note with these sections:

1. Decision
2. Context Evidence
3. Options Considered
4. Tradeoffs
5. Implementation Move
6. Validation
7. Consequences

When writing an ADR, use the repository convention if one exists. If none exists, use `docs/adr/YYYYMMDD_slug.md`. The helper script `scripts/newadr.py` can draft a markdown file.

## Gotchas

1. Do not split services because smaller sounds cleaner. First prove the disintegrator beats the integrator.
2. Do not merge services just because a workflow is noisy. First check whether orchestration, asynchronous messaging, or contract changes address the actual coupling.
3. Do not treat database ownership as an implementation detail. Ownership controls change safety, consistency, and bounded context integrity.
4. Do not rely on generic architecture advice. The relevant domain cases decide the tradeoff.
