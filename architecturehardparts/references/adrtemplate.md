# ADR Template

Use this template when a coding session creates a durable architecture decision.

This file is the canonical template source. `scripts/newadr.py` loads the fenced markdown block below at runtime, so edit the template here only.

Path convention: see SKILL.md and the `scripts/newadr.py` defaults.

## Template

```markdown
# ADR: short noun phrase for the decision

Status: proposed

Date: YYYYMMDD

## Context

Describe the problem in one or two short paragraphs. Include the current code shape, data ownership, runtime workflow, constraints, and the alternatives considered.

## Decision

State the choice clearly. Explain why this option best fits the current forces and what implementation move will enforce it.

## Consequences

Describe the accepted tradeoffs. Include what gets easier, what gets harder, what coupling is introduced or removed, and what future change would make this decision worth revisiting.

## Fitness Functions

List the tests, static checks, contract checks, monitors, migration checks, or review checks that protect the decision.

## Validation

List the commands, runtime checks, or evidence used to verify the implementation.
```

## ADR Writing Rules

1. Keep the decision short enough to read during a code review.
2. Name rejected alternatives without turning the ADR into a research paper.
3. Use current repo evidence instead of broad claims.
4. Include consequences even when the decision is obviously right.
5. Add a fitness function whenever the decision can drift silently.
