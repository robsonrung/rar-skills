# Document personas

Each persona is one seat's lens on a plan, PRD, or requirements document. Pick the personas the document's content calls for; the adversarial and whole-document personas join only a `deep` review.

Every persona returns findings for `doc-findings-schema.json`: a section, quoted evidence, why it matters, and a fix. A finding changes the planned work, its cost, its risk, or its verification; wording preference and a different organization are not findings. Settled decisions are **already decided**: challenge one only when the document or local evidence shows it cannot work. An unanswered hypothetical goes to residual risks or deferred questions.

## Coherence

For linked requirements, tasks, decisions, or sections. Terms, identifiers, scope statements, and dependencies agree; every cross-reference resolves; every stated count matches its list. Ambiguity counts only when two reasonable readings lead to different work.

## Feasibility

For technical decisions, integrations, migrations, or operational changes. Compare claims with the local architecture, named dependencies, and constraints. Check implementation order, failure handling, migration safety, and verification. For an uncertain point, state the evidence that would resolve it.

## Scope guardian

For added tasks, abstractions, dependencies, or phases. Every task serves a stated outcome; no abstraction waits for a future use; dependencies and order permit the promised increment; deferred work stays deferred.

## Product

For goals, outcomes, success measures, or priorities. Every planned outcome serves a stated goal, every goal has a measurable path to success, and no priority or scope conflict changes the expected value.

## Design

For user-facing flows, screens, components, or interactions. Trace the main goal from entry to success. Check the loading, empty, error, interruption, and recovery states the change creates, plus accessibility, feedback, and consistency with recorded design decisions. Flag what would block use, mislead a user, or contradict a decision.

## Security

For trust boundaries, identity, sensitive data, external services, or privileged actions. Name the actor, data, entry point, and boundary; check access control, validation, data handling, credentials, and recovery. Trace a realistic exploit or failure path, and flag only gaps the document must close before safe implementation.

## Adversarial

For an unsettled premise, a costly decision, or an assumption that could sink the work. Name a concrete condition under which an important decision fails, and the smallest experiment that would reduce the uncertainty.

## Whole document

An independent broad pass that complements the focused personas. Read the document as one delivery contract and return the few findings a focused persona would miss: contradictions across sections, missing handoffs, impossible verification, a gap between outcome and work.
