# ADR Template (runtime source for `scripts/newadr.py`)

> **This file is the runtime template source, not the canonical one.** `architecture-lens/references/adr-template.md` is the repo-canonical ADR template — read it for the "is this decision architecturally significant?" test, the storage and superseding convention, and the writing tips. This file exists because `scripts/newadr.py` loads the fenced markdown block below at runtime to draft a file, so the template text must live in a machine-readable form here. Keep the two consistent: when the canonical template changes, mirror the change here.
>
> Two constraints on edits to the fenced block: the script rewrites the `# ADR: `, `Status: `, and `Date: ` lines by regex, so those three lines must keep exactly that shape and stay at the top. Everything else in the block is free text.

Use this template when a coding session creates a durable architecture decision.

Path convention: see SKILL.md and the `scripts/newadr.py` defaults.

## Template

```markdown
# ADR: short noun phrase for the decision

Status: proposed

Date: YYYYMMDD

Deciders: names or team

## Context

Describe the situation forcing a decision, in one or two short paragraphs: the current code shape, data ownership, runtime workflow, the constraints and forces in tension, and the architecture characteristics that matter here. Facts, not opinions.

## Decision

State the choice plainly and actively — "We will …". Explain why this option best fits the current forces and what implementation move will enforce it.

## Consequences

The trade-off, both signs: what this gains and makes easier, what it costs and makes harder, what coupling is introduced or removed, what is being accepted, and what future change would make this decision worth revisiting.

## Alternatives considered

Each rejected option with the one-line reason it lost. Optional for a small decision; include it whenever the decision is likely to be revisited.

## Fitness Functions

List the tests, static checks, contract checks, monitors, migration checks, or review checks that protect the decision.

## Validation

List the commands, runtime checks, or evidence used to verify the implementation.
```

## ADR Writing Rules

1. Keep the decision short enough to read during a code review — a screen is the target.
2. Name rejected alternatives without turning the ADR into a research paper.
3. Use current repo evidence instead of broad claims.
4. Include consequences even when the decision is obviously right. A consequences section with only upsides means the analysis isn't done.
5. Add a fitness function whenever the decision can drift silently.
6. ADRs are immutable once accepted. To change a decision, write a new ADR that supersedes the old one and link both ways.
