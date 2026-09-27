# Context, discovery, and evidence

## Revision check before reading

Run `scripts/revision_check.py <repo>` before inspecting any source. It reports HEAD, its upstream as last fetched, commits ahead and behind, uncommitted files and the last fetch time, without fetching or checking anything out.

- When HEAD is behind its upstream, say so and ask which revision the audit should describe. Without an answer, audit HEAD and recheck every P0 to P2 finding on the newer ref before reporting; record the result in the finding's `newer_ref_status`. A finding already fixed there is reported as fixed upstream and cannot stay P0 or P1. Checking only the top findings is not enough: a lower finding that was fixed upstream still misleads the reader.
- To read the newer ref without touching the checkout, export it with `--export-ref <ref> --export-dir <empty dir outside the repo>` (git archive) and point measurements and rechecks at the export.
- Uncommitted files are part of what the user is working on; mark evidence from them as working-tree state and do not recommend changes that collide with them without saying so.
- Record the outcome in `revision_check` in `audit.json`. Do not fetch without permission; a stale upstream is reported as a limitation.

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

For large systems, map the whole known system, then sample critical flows, change hotspots, central components, expensive queries, fragile integrations, and team boundaries. Distinguish change coupling in version history from runtime temporal coupling and connascence; co-change alone does not prove causation. Record known totals, inspected counts, and gaps.

## Measurements and history

Use `scripts/measure.py` for structural numbers instead of ad hoc scripts: `imports` (dependency graph, cycles including in-function imports, fan-in and fan-out, instability, package matrix), `writers` (modules that write each table), `history` (churn, co-change, fix and revert commits), `test-pins` (module paths named in tests), `endpoints`, `callers` and `occurrences`. Every result states its counting conventions; quote them when a number supports a finding, and never compare numbers produced under different conventions without saying so.

History is evidence when git is available. Read it by default: hot spots decide where depth pays off, co-change reveals hidden coupling, and fix commits link a design problem to an incident that already happened. An incident linked through a fix commit raises confidence and priority; record it in the finding's `incident` field. See `module-design.md` for the investigations these measurements feed.

## Delegation and exploration packets

Delegate exploration only when the inventory is larger than the coordinator can read directly; a small repository is cheaper to read than to brief. Split work by dimension or subsystem, never by finding. Each worker receives a packet and returns facts, not judgments.

- **Packet in:** scope and paths, the audited revision, the read-only, no-secrets, no-execution and untrusted-content rules, and the evidence record format below. Do not send the rubric, priorities or Leitwörter; judgment stays with the coordinator.
- **Records out:** JSON lines with `local_id`, `kind`, `location`, `line_start`, `line_end`, `observation`, optional `excerpt`, `command` for measurements and `supports` for inferences. An absence claim states the exact search and scope.
- **Assembly:** `scripts/evidence_tool.py assemble` assigns E-IDs, maps `supports`, removes duplicates and checks files, line ranges and excerpts against the checkout. The coordinator re-reads every record that supports a P0 or P1 finding, a `not_applicable` rating or a system-wide absence claim.
- **Privacy:** a worker that runs through an external provider receives private source code; that is an upload and needs the user's explicit approval (execution boundary 2). Prefer workers native to the host.

## Challenge pass

Before rendering, give every P0 and P1 candidate, and every structural recommendation, to a reviewer that did not produce it. The reviewer's task is to refute: find the guard, constraint, sweep, test or documented decision that makes the claim false or smaller, and check the newer ref when one exists. It returns, per claim, a verdict (confirmed, partly confirmed, refuted), the counterevidence with locations, the newer-ref status and a suggested priority. Record the pass as a verification entry, including how many priorities changed. Use an independent model or person when available; otherwise disclose a second pass by the same reviewer.

## Folding in another review

Another report on the same system is a lead, not evidence. To fold it in: record it as `documentation` evidence; re-verify each claim you adopt at the audited revision and cite your own evidence; reconcile metric differences by convention before calling them disagreements (for example per-statement versus per-name import counts); record agreements, disagreements, adopted findings and anything not re-verified in `external_reviews`; and correct your own report where the other review is right. Use `scripts/compare_audits.py` to line up two `audit.json` files for a follow-up audit.

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
