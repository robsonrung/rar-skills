# Engineering rules

Spec driven development

1. Treat the accepted specification as the source of truth.
2. Every task, test, and implementation decision must trace back to a spec item, accepted assumption, or explicit user instruction.
3. When the spec and codebase disagree, record the conflict and choose the safer path until the user decides.

Domain driven design

1. Use ubiquitous language from the domain.
2. Keep domain rules out of interface and infrastructure layers.
3. Make invariants explicit.
4. Define bounded contexts before sharing models across areas.
5. Avoid anemic domain objects when behavior belongs in the domain.

Clean architecture

1. Dependencies point inward.
2. Application use cases orchestrate domain behavior and ports.
3. Adapters translate external systems, databases, frameworks, and user interface concerns.
4. Infrastructure choices must not leak into the domain.
5. Prefer small seams over broad shared utilities.

Test driven development

1. Write or update the failing test first for behavior changes.
2. Prove the failure is meaningful.
3. Implement the smallest change to pass.
4. Refactor only with tests green.
5. Record commands and evidence.

Contract integrity

1. Never delete, skip, weaken, narrow, or mock-away tests — and never loosen acceptance checks — to make a contract pass.
2. If the contract itself is wrong, stop and report it; a corrected contract is a user decision, not an implementation move.
3. Green obtained by gaming the check is a failure with extra steps: it converts a visible red into an invisible defect.
