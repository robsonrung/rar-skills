# Leitwörter, leading words in decisions

A Leitwort, plural Leitwörter, is a recurring term that anchors a decision. This package follows the authoring convention supplied with the request. It makes no empirical claim that repeating words improves a model's accuracy.

## Operational rule

At a material checkpoint, state a concise decision that names the main applicable concept. Repeat the exact canonical term in the action or verification criterion so that the concept constrains what happens next. A heading or glossary entry alone is insufficient. Definitions and source attribution live in `terminology.md`; do not redefine the term inconsistently in each section.

Use a visible decision summary, not an internal reasoning transcript. Do not narrate every inference, repeat a mantra, or turn every word into a capitalized concept. A normal checkpoint needs one anchor; a finding usually needs no more than two concepts.

## Checkpoint grammar

“[Canonical term] applies to [specific subject], supported by [evidence]. Therefore [decision or action]. Verify [observable criterion].”

When evidence is missing: “[Canonical term] is not established because [specific gap]. Inspect or test [specific evidence] before deciding.”

When a pattern is unnecessary: “[Canonical term] is not applicable because [contextual reason]. Preserve [simpler alternative] and reconsider when [trigger].”

## Route real decisions through the anchor

| Decision | Main anchor | Required consequence |
| :--- | :--- | :--- |
| Is the system already sufficient? | fit for purpose | Name the requirement and evidence, or the unknown that blocks the conclusion. |
| Where does the model change meaning? | Bounded Context | Identify language, invariants, ownership, and the boundary contract. |
| Does policy depend on details? | The Dependency Rule | Name the actual source import, distinguish runtime calls, and specify a boundary check. |
| How can legacy behavior be isolated? | seam | Identify the point and its enabling point, then name the substitution to test. |
| Is a restructuring safe? | behavior-preserving | State the preserved contract and tests; separate deliberate behavior changes. |
| Can retries corrupt the business result? | end-to-end correctness | Trace the final effect and state across failure and recovery. |
| Can an agent verify success? | deterministic oracle | Name the independent assertion and controlled state, not a success narrative. |
| Which migration step should come first? | smallest reversible move | Define the minimal step, rollback or forward recovery, and stop condition. |
| Is a diagnosis supported? | evidence before opinion | Search for counterevidence before escalating a risk. |

Use more specific terms when they do the work: Common Closure Principle (CCP) for shared reasons to change, connascence for a named agreement dependency, deep module for interface-to-implementation complexity, Read-After-Write for a writer's stale read. Precision matters more than a large vocabulary.

## Model decisions

“The seam is the ERP gateway call; the composition root is its enabling point. Use this seam to inject a timeout without calling production.”

“The Common Reuse Principle (CRP) exposes Billing dependence on unused Order internals, E004. Apply the Common Reuse Principle (CRP) by publishing the narrow pricing contract and checking forbidden imports.”

“The deterministic oracle checks the order record and protected ERP effect after replay. Keep the deterministic oracle independent of the agent's explanation and record every attempt.”

“The smallest reversible move is a compatible adapter, not a service extraction. Verify the smallest reversible move against the existing contract before switching callers.”

## Structured report contract

Every finding has a `leitwort` term ID and a `decision_statement` containing the canonical term. The term also appears in its recommendation, validation, or acceptance text. Add a `concept_applications` record for each material decision, with applicability, evidence, action, verification, sources, and related findings. Findings require a linked applied decision for the same term.

The validator checks names, references, and repetition. It cannot prove that the concept was used correctly or materially affected the decision. The critical review must reject empty repetition, unsupported diagnoses, and terminology used with the wrong meaning.

## Anti-patterns

Heading-only terms are inert. Synonym drift obscures meaning. Filler such as “review carefully” lacks a decision. Forced use of every concept creates irrelevant work. Copying an example without system evidence fabricates a finding. A repeated term with an unrelated action is cosmetic, even if structural validation passes.
