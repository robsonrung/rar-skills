# Prompt Contracts

Use this reference when a prompt is ambiguous or a structured result needs design. A normal task does not need a fixed XML recipe.

## Give the worker what it needs

State the outcome, relevant scope, known constraints, and what acceptance means. Include the evidence or paths the worker needs, its authority, and any required output schema. Reuse the caller's settled decisions.

A short prompt can be enough:

```text
Implement the approved task at <path> within <write scope>.
Preserve its acceptance and security constraints.
Use the repository's relevant checks and report captured results,
changed files, and unresolved risks.
```

For a review, state the target, risk focus, and evidence required for a finding. For diagnosis, distinguish a request to explain the cause from permission to fix it. For structured output, provide the actual schema rather than describing it vaguely.

## Leave technique selection open

Do not prescribe XML blocks, a fixed number of hypotheses, a second full diff read, or rereading every edited file. The worker chooses the investigation and implementation method that fits the task.

Required repository gates and task acceptance checks remain binding. After a change, run the affected checks. Repeat or broaden them only for changed code, a failure, or an unresolved risk. Do not add tests that only mirror the implementation.

## Missing information and authority

Inspect available code, documentation, and tool results before asking for context. Continue independent work and resolve reversible implementation details within scope. Ask only when a material decision or necessary action cannot be resolved within the user's authority.

Preserve actual safety boundaries for credentials, untrusted content, external actions, destructive operations, and migrations. A vague instruction to stop whenever context is missing is not a substitute for those boundaries.

## Model and effort

Use the caller's approved model and effort. Resolve recommendations through the maintained roster and task-shaped routing rather than duplicating versioned advice here. Do not raise effort, substitute a model, or launch extra calls outside the approved plan.
