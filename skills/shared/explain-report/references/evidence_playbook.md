# Evidence playbook

## Contents

1. Establish the snapshot
2. Build the explanation chain
3. Qualify evidence
4. Make repository precedents concrete
5. Explain semantic changes
6. Describe verification honestly
7. Adapt depth to risk
8. Integrate with the agent workflow

## 1. Establish the snapshot

Use the user's requested repository and scope. Read local instructions before investigation. Record exact base and head when explaining a change. Choose explicit comparison semantics: two committed trees, branch since common ancestor, or baseline against current working tree. Never silently mix them.

Record local changes separately from committed changes. A Git SHA alone does not identify unstaged or untracked content. The collector can fingerprint those inputs. Its record is evidence of what was inspected, not a live freshness monitor, a complete backup, or a cryptographic attestation that the explanation is correct.

Recheck the snapshot at delivery. If source changes, inspect the affected evidence and regenerate before claiming the report describes the latest work.

## 2. Build the explanation chain

Use stable identifiers, such as R001, D001, A001, C001, and E001. Preserve existing project identifiers when available.

Each requirement should connect to the affected area and a check. Each significant decision should connect to the problem, considered alternatives, repository evidence, and affected areas. Each area should explain behavior before and after. Each asserted successful check should connect to observed evidence.

The reader should be able to answer these questions from any significant code area:

1. What problem makes this change necessary?
2. Which decision introduced it?
3. Why is this responsibility in this layer?
4. What similar code already exists, and how does this case differ?
5. What becomes possible and what could regress?
6. Which evidence supports the claims and what is still unknown?

Do not force trivial formatting or generated changes into fictitious architectural decisions. Account for them briefly with a real reason.

## 3. Qualify evidence

`shared/references/grounded-evidence.md` owns citation, verbatim excerpts, publishing safety, and naming what was not verified. One exception: code a plan labels **proposed** (pseudocode or an example diff) may appear although no file holds it yet. Every observed excerpt stays verbatim with its `path:line`.

Use four explicit states.

1. Observed, directly inspected source, executed output, screenshot, trace, or author statement. State what was observed and where.
2. Inferred, an interpretation supported by observations. Explain the inference and its uncertainty.
3. Proposed, a plan, future check, anticipated path, or unimplemented behavior.
4. Unknown, evidence unavailable, blocked, missing, or not inspected.

An observed plan establishes what was proposed, not that the behavior exists. An observed test definition establishes a check is present, not that it passed. An observed exit code supports the command result, not unrelated requirements. A static source observation can support architectural structure but not measured performance.

Evidence should name a path and symbol or artifact location, inspected revision, useful excerpt, and limits. Prefer immutable source URLs when a permitted remote is available. Otherwise include enough local context that the report remains useful offline. Avoid external fetches at report viewing time.

Never use confidence percentages or reassuring color as a substitute for evidence. Do not label the whole change verified simply because the renderer accepted its JSON.

## 4. Make precedents concrete

Weak explanation: follows existing conventions.

Useful explanation: BillingService.completeInvoice writes its event through the transaction object in src/billing.ts. Reusing that mechanism lets purchase state and notification intent commit together. Billing has one event type; purchases need a tenant scoped event identity. The existing worker provides retries, but it does not establish real provider deduplication.

Inspect the precedent, its callers or interface, and tests when the claim depends on runtime behavior. One similar file establishes an analogy. Multiple independent examples can support a broader convention. Preserve differences rather than hiding them to make the rationale persuasive.

Existing patterns can be flawed. Explain why reuse is suitable under the current constraints, and document any deliberate departure. Distinguish observed author intent from your reconstruction.

## 5. Explain semantic changes

Group by behavior, contract, responsibility, or dependency order. A useful group might be event identity, transactional persistence, then delivery retries. Alphabetical file lists rarely provide this narrative.

For each group explain the previous behavior, new behavior, affected users or callers, decision rationale, failure behavior, and compatibility implications. Include exact paths and relevant symbols. Put selected actual diffs underneath. Do not make the reader infer purpose from changed lines.

Account for deletions, renames, migrations, generated files, lockfiles, binaries, and configuration. If a path is out of scope, include its reason. Show remaining unexplained paths prominently.

For UI work, show actual before and after screenshots when available, then explain state, interactions, accessibility, and responsive behavior. Label mockups as proposals. For data work, explain ownership, invariants, migration ordering, and rollback limitations. For distributed flows, distinguish request success, durable intent, delivery, retry, deduplication, and eventual completion.

## 6. Describe verification honestly

For each check record criterion, method, status, command or procedure, environment, executed revision, timestamp if known, exit code if applicable, observed result, evidence, and limits. Preserve unavailable values as unknown, never fabricate timestamps or command output.

Use these statuses: planned, passed, failed, blocked, not_run. Include failed and critical unrun checks in the overview. A test that passed before the current implementation needs a different revision label and may require rerunning before it supports the current claim.

Keep these meanings distinct:

1. Behavioral tests provide evidence about the exercised scenarios.
2. Static analysis and builds establish selected structural or type properties.
3. Manual inspection and screenshots establish the specific observations made.
4. Independent review produces findings within its inspected scope.
5. Formal methods establish a stated property under explicit assumptions, or explore a bounded model. Record the artifact, property, assumptions, solver or prover, and actual result.

Do not claim production persistence, real provider semantics, concurrency safety, performance, or deployment readiness from an in memory fixture. Select checks for the concrete risks present. Reuse relevant results; do not repeatedly run broad suites simply to populate a report.

## 7. Adapt depth to risk

For a small local change, use a compact overview, one decision if needed, affected areas, and acceptance evidence. For a feature crossing layers, add before and after relationships, alternatives, actual precedents, compatibility, and failure behavior. For migrations or distributed state, include invariants, ordering, retries, rollout, observability, and recovery.

Choose meaningful visual forms. Use a relationship diagram for topology, a sequence for event order, a state view for transitions, and exact comparisons for tradeoffs. Avoid decorative charts, arbitrary risk scores, and generated architectural pictures. Prefer a small complete figure over a large unreadable graph.

## 8. Integrate with the agent workflow

Use explain-plan after initial repository discovery and before the user evaluates design choices. Use explain-work when implementation and targeted verification have produced concrete evidence. Reuse an existing plan, specification, or ADR rather than replacing its workflow.

Treat report notes as feedback. Export only reader entered comments, with report ID, revision, and snapshot context. Never infer acceptance from a page view, default choice, or opened section.
