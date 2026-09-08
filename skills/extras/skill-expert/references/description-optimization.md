# Description Optimization

Use when discovery fails, nearby skills compete, or a description needs refinement.

## Write for selection

Use one or two short sentences: what the skill does and the concrete request that should select it. Front-load its distinctive purpose. Keep only exclusions that separate real neighbouring skills.

The repository's 1,024-character limit is a ceiling, not a recommended size. Avoid keyword catalogues, workflow steps, book summaries, and output templates. Do not append every missed query to the description.

## Inspect the boundary

Compare representative intended requests with adjacent requests that belong elsewhere. Include terse requests, explicit invocation, and a realistic near miss. Use the existing task history when available; do not manufacture a large query set for a simple wording change.

Check description truncation and invocation metadata in the actual host when discovery behavior is the issue. An explicit-only skill must remain explicit-only even if its description matches a request.

## Measure only when needed

For a requested trigger benchmark or an unresolved activation failure, use the bounded procedure in `references/evaluation.md`. Set the case and call limits before execution. Repeat a case only when variance matters to the decision; there is no default three-run requirement.

Use the intended host and model, with observable skill selection. Include held-out near misses when tuning against a set. Distinguish a skill that was not selected from one that was selected and executed badly.

Without activation-observation tooling, inspect the boundary and report a qualitative rationale. Do not claim measured trigger accuracy.

## Report

For a description change, give the reason and any remaining ambiguity. Include old/new wording when useful for review. Add scores only when they come from actual measured runs.
