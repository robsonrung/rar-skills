---
name: capture-learning
description: Capture a verified, reusable solution in docs/solutions. Use when asked to document a solved problem or when a delivery workflow selects learning capture; use session-handoff for work continuity.
---

# Capture Learning

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Create one source-grounded solution document that a later engineer can find and use. The next consumer is someone facing the same problem. Done means the document is written, validated, and does not state an unverified claim as fact.

## Scope

Capture one learning per run. It must describe a solved, verified, and non-obvious problem. If the evidence does not meet that bar, do not write a weak document. In `mode:headless`, return `Documentation skipped` with the reason. In an interactive run, ask only when the solved problem itself is unclear.

This skill writes only the solution document. When an existing `CONCEPTS.md` has a qualifying missing term, update that entry too. Do not create a glossary, edit project instructions, search unrelated memory, or turn this run into a documentation audit.

## Workflow

1. Read the relevant conversation evidence, changed source, verification results, and nearby solution documents. Source and captured command results outrank session recollection.
2. Read `references/schema.yaml` and `references/yaml-schema.md` to classify the learning and choose its destination. Read `references/resolution-template.md` for the required body shape.
3. Check for an existing document about the same problem. Update it when the problem, cause, and solution materially match; otherwise create one new document. Keep the path stable when updating.
4. Ground every behavior claim in current source with a `file:line` reference. Describe merge state only when it is verified. Attribute or remove claims that cannot be verified.
5. Read `references/concepts-vocabulary.md` only when an existing glossary may need a qualifying term. Keep the glossary change within the learning's domain.
6. Run `scripts/validate-frontmatter.py` and `scripts/validate-doc-claims.py` from this skill's directory. Read `references/grounding-validation.md` to adjudicate flags. Fix, annotate, or confirm each flag; never silently ignore one. If a validator cannot run, perform its documented manual checks and report that fallback.

## Headless mode

`mode:headless` means no questions and no optional expansion. Use it only when the caller supplies a verified fix and enough context to identify one learning. End with one of these exact terminal lines:

```text
Documentation complete
```

```text
Documentation skipped
```

## Output

Report the mode, created or updated path, classification, validation result, glossary result, and any grounded limitation. Lead with the outcome. A headless report also states the skip reason when no document was written.

The acceptance contract is simple: a later reader can identify the problem, recognize when the solution applies, follow the verified resolution, and distinguish evidence from history.
