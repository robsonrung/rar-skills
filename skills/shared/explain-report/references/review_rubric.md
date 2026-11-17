# Delivery rubric

Use this as an internal review, not a score to display.

## Reader understanding

1. The first view explains the concrete problem, affected behavior, recommended or actual outcome, main reason, and material risks.
2. The reader can understand every major architectural decision without opening code.
3. Deeper details explain responsibility and mechanism rather than repeating overview wording.
4. Significant alternatives, accepted costs, and conditions for revisiting decisions are explicit.
5. The report includes enough context to make sense outside the conversation.

## Repository grounding

1. The inspected repository, revisions, scope, and working tree state are explicit.
2. Claimed precedents were actually inspected and include paths, symbols, similarities, and differences.
3. All changed paths are explained or explicitly excluded, including deletions and renames.
4. Observations, proposals, inferences, and missing evidence are distinguishable.
5. Source facts are separate from reconstructed author intent.

## Plan and implementation continuity

1. The completed report identifies the original plan or explicitly says it is unavailable.
2. Existing requirement and decision IDs remain stable.
3. Added, revised, deferred, and dropped choices have explanations and consequences.
4. The original plan was preserved rather than edited to erase differences.
5. Implementation completeness is distinct from release readiness.

## Evidence integrity

1. Passed checks point to observed output or a recorded manual procedure.
2. Commands, environment, revision, results, and limits are explicit when known.
3. Missing, failed, blocked, and stale checks are visible before opening deep details.
4. Ordinary tests are not described as formal proof.
5. Report structure validation is not described as implementation validation.
6. The snapshot remains current at the time of delivery, or the stale scope is disclosed.

## Navigation and presentation

`shared/references/html-page-conventions.md` owns anchors, narrow screens, escaping, self-containment, and disclosing unchecked rendering. This report adds:

1. A reader can follow overview, diagram, decision, area, and evidence links.
2. Deep links open the necessary disclosure controls.
3. Search can reveal text inside collapsed sections.
4. Keyboard focus is visible and controls have meaningful labels.
5. Print exposes all substantive content, including collapsed evidence.
6. Reader notes export with report identity and do not imply approval.

## Stop condition

Deliver once consequential claims are grounded, required relationships are complete, meaningful checks are sufficient for the report's scope, and usable output has been inspected. Do not keep adding diagrams, tests, or review passes without a concrete remaining risk.
