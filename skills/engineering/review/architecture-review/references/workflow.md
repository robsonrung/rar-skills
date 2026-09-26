# Context, discovery, and evidence

## Questions that change decisions

Inspect authorized sources first. Ask at most eight questions, omitting answered topics. Accept approximate ranges and record their origin. Explain which decision needs each answer.

1. **Product and horizon:** What does the system do, who uses it, which journeys cannot fail, what stage is it in, and how long must it remain useful?
2. **Workload:** What are peak active users and request rates? Are there persistent connections, batch workloads, or expensive jobs? Are these observed or estimated?
3. **Size:** What are data volume, distribution, growth, and retention? How many domains, integrations, deployment units, and maintainers exist?
4. **Growth and sufficiency:** Is current capacity sufficient? What concrete problems exist? Which product, workload, geography, or team changes are plausible within the agreed horizon? Is growth a commitment, forecast, or exploration?
5. **Quality and risk:** What latency, availability, recovery, consistency, isolation, and data-loss limits apply? Which security, accessibility, and compliance constraints have actually been identified?
6. **Testability:** Which failures are unacceptable, what does a regression cost, and what automation effort is justified? Where is manual verification acceptable? Which journeys need automated verification before release?
7. **People and economics:** Who operates and changes the system? What budget, release frequency, skills, support obligations, and hiring constraints matter?
8. **Agents and access:** Must an agent understand and review, or also implement, reproduce, and verify? Which commands, environments, sources, costs, and output destinations are authorized?

Do not invent answers. Without interaction, record unknowns, assumptions, and conditional decisions. Do not impose 99.99% availability, 100% coverage, or tenfold growth as defaults. Use **fit for purpose** in the sufficiency checkpoint.

## Quality Attribute Scenarios

Use the six-part structure: **source of stimulus, stimulus, environment, artifact, response, response measure**. Add horizon, priority, requirement owner/origin, observed state, and evidence. This scenario-based approach draws on B01 and W01; it is not a formal ATAM engagement.

Examples illustrate form, not universal targets. At agreed peak load, a statement query meets the agreed latency percentile and error rate against representative data. During integration failure, a committed operation preserves invariants and supports recovery without duplicate effects. A domain rule changes without forcing unrelated Bounded Contexts to change. A clean local environment reproduces a critical journey with synthetic data and a deterministic oracle.

## Inventory and sampling

Start with README, applicable instructions, manifests, lockfiles, workspaces, entry points, composition roots, schemas, migrations, public contracts, CI, and deployment files. Follow references to implementations and callers. Before claiming absence, check equivalent mechanisms across the relevant scope and record that scope.

File count is not quality. Automatic inventory is a conservative candidate list. Ignored directories, submodules, generated code, and dependencies may be excluded. Investigate relevant exceptions separately only when authorized.

For large systems, map the whole known system, then sample critical flows, change hotspots, central components, expensive queries, fragile integrations, and team boundaries. Use history only when available and permitted. Distinguish change coupling in version history from runtime temporal coupling and connascence; co-change alone does not prove causation. Record known totals, inspected counts, and gaps.

## Traceable evidence

Assign stable IDs such as E001. Record kind, location, revision, verified line range where applicable, observation, date, environment, and supporting evidence. Prefer relative paths and short sanitized excerpts over complete files.

Execution evidence needs the actual command or collection procedure, working directory, relevant versions, nonsecret configuration, seed, fixtures, workload, repetitions, duration, outcome, and artifact location. Separate setup failures from product failures. A proposed command was not executed.

**High confidence** requires relevant direct evidence and considered counterevidence. **Medium confidence** allows a supported inference or incomplete dependency inspection. **Low confidence** means provisional clues or unverified documentation. **Unknown** means insufficient information to judge. These labels are not calculated probabilities.

A serious hypothesis may justify an experiment, not an immediate migration. Separate architecture quality, implementation quality, and evidence quality. Use **evidence before opinion** in checkpoint decisions.

## Trace the flow

Record actor, entry point, authentication, authorization, contract, domain rule, transaction, data operation, external effect, response, and failure path. Include timeout, retry, deduplication, compensation, and correlation where relevant.

Use separate views for source dependencies and runtime communication. A source import is not a network call, and an in-process call is not necessarily a module boundary. Use **The Dependency Rule** only for the direction of source dependencies toward policy. Link observed nodes and edges to evidence. Label proposed structures explicitly.

## Second pass

Does the issue lie on an executed path? Is there a database, middleware, or infrastructure control? Does it occur with valid inputs? Would the proposed layer hide complexity or just add indirection? Does the cost of inaction exceed the cost of change? What evidence would reverse the recommendation?

Resolve conflicting diagnoses and deduplicate common root causes. At the final checkpoint, state the **smallest reversible move**, its **deterministic oracle**, and remaining uncertainty.
