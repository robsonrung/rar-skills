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

Mode selection

1. Use the mode supplied by the user or inherited from the caller. Otherwise use the skill's safe scoped default when it fits the invocation authority.
2. Ask only when the choice changes scope, cost, permitted effects, or a material unresolved decision. Name the relevant choices and consequences in one question. Continue independent authorized work while waiting.
3. Silence is not approval. Preserve explicit council approval and any mode that requires additional authority. A documented invocation such as `--auto` supplies its stated mandate.

Contract integrity

1. Preserve tests and acceptance checks. Never delete, skip, weaken, narrow, or mock-away them to make a contract pass.
2. Distinguish the accepted product contract from a test implementation error. Within repair authority, correct a selector, fixture, type expectation, or response expectation when authoritative requirements and source establish the result. Preserve the failed evidence and record the reason. Do not remove an assertion or weaken the accepted behavior. If the requirement itself changes or remains ambiguous, obtain the missing decision.
3. Green obtained by gaming the check is a failure with extra steps: it converts a visible red into an invisible defect.
