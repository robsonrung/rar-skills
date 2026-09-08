# Assess System Decomposition

Paths named below are relative to the loaded skill root. This method produces a decision note. Implement its move only when implementation is authorized; design-gate calls remain read-only.

Use this when a session contains an architecture decision (pull apart / put together / re-own data), not just an implementation task.

**Mental model:** architecture choices are contextual trade-offs; no pattern is best outside the current constraints. Anchor each recommendation in **connascence** (strength × locality × degree — see `architecture-lens`), data ownership, deployability, runtime behavior, and validation.

### Workflow

1. **Name the decision in one sentence** — current system shape, the change considered, and the force involved (service boundaries, data ownership, transaction consistency, workflow coordination, shared code, contract shape, scaling pressure, failure isolation).
2. **Reproduce the current shape from code and runtime evidence** — relevant modules, schemas, migrations, tests, dependency manifests, deployment descriptors, contracts, queues, jobs, logs, dashboards. Prefer current repo evidence over remembered architecture.
3. **Map connascence before proposing a change.** Static (imports, package deps, shared libs, schema access, deployment coupling, config, infra) and dynamic (request flow, messaging, consistency requirements, workflow state, coordination ownership, retries, timeouts, compensation). Strong, distant, high-degree connascence is the decomposition target.
4. **Decide: pulling apart or putting back together?** Pull apart when evidence favors maintainability, testability, deployability, scalability, fault/security isolation, change isolation, or database-type fit. Put back together when it favors single-unit transactions, tightly related data, heavy workflow chatter, frequently co-changing shared domain code, low latency, or simpler ownership.
5. **Read the focused reference only when needed** — `references/catalog.md` for the decision catalog (decomposition, service granularity, data decomposition, reuse, data ownership, eventual consistency, workflows, sagas, contracts, data mesh). Use **all three or no ADR** before loading `references/adrtemplate.md`: hard to reverse, surprising without context, and a real tradeoff. A cross-team change alone does not require an ADR.
6. **Compare options against local context** — a short prose matrix; keep options mutually exclusive and collectively complete. Avoid generic pros/cons that ignore the repo, domain workflow, data model, operational constraints, or team boundaries.
7. **Prefer bottom-line clarity** — state the practical choice as an outcome (e.g. faster response over immediate consistency; independent deployability over shared-transaction simplicity; a shared library over a shared service because the function is domain-local and latency-sensitive).
8. **Name the smallest coherent shape** and how to verify its architecture property. For an authorized implementation, make the scoped move and add a test or fitness function when the property needs a guard. A structural refactor is behavior-preserving. A review or design-gate call returns the recommendation without editing code.
9. **Report the decision and evidence** — the tradeoff, next move, and any risk needing a follow-up decision. For an implementation, also report changed code and captured verification.

### Fitness-function prompts

1. What must stay isolated after this change?
2. What dependency, import, schema access, service call, queue, or shared library would violate that isolation?
3. Can a test, static check, migration check, contract test, monitor, or alert fail when the architecture drifts?
4. Is the check architecture-focused rather than domain-focused?

### Output contract (for a decision)

A concise decision note: **1. Decision · 2. Context Evidence · 3. Options Considered · 4. Trade-offs · 5. Implementation Move · 6. Validation · 7. Consequences.**

When writing an ADR, use the repo convention if one exists; otherwise `docs/adr/YYYYMMDD_slug.md`. The helper `scripts/newadr.py` can draft one, e.g. `python <skill_dir>/scripts/newadr.py --title "Split billing schema" --out-dir docs/adr --dry-run` (path relative to this skill; `--help` for flags).

### Gotchas

1. Don't split services because smaller sounds cleaner — first prove the disintegrator beats the integrator.
2. Don't merge services just because a workflow is noisy — first check whether orchestration, async messaging, or contract changes address the actual coupling.
3. Don't treat database ownership as an implementation detail — ownership controls change safety, consistency, and bounded-context integrity.
4. Don't rely on generic architecture advice — the relevant domain cases decide the trade-off.
