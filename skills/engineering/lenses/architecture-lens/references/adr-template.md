# Architecture Decision Record (ADR) — lightweight template

An ADR captures _one_ architecturally significant decision: the context, the choice, and the consequences. Write one only when the decision is significant (see test below) — not for routine choices.

## When to record a decision

Use **all three or no ADR**. The decision must be:

1. Hard to reverse.
2. Surprising without its context.
3. A real tradeoff among viable choices.

Structure, dependencies, public interfaces, or cross-cutting qualities can expose such a decision, but touching one does not by itself require an ADR. If the three conditions do not hold, keep the reason in the task or review note. **Record on settle** when they do; accepted decisions remain inputs to later work.

## Storage

- Keep ADRs in the repo (e.g. `docs/adr/`), versioned with the code, one file per decision: `NNNN-short-title.md`, numbered sequentially.
- ADRs are immutable once accepted. To change a decision, write a _new_ ADR that **supersedes** the old one and link both ways. Don't edit history.

## Template

```markdown
# ADR-NNNN: <short imperative title>

- Status: Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
- Date: YYYY-MM-DD
- Deciders: <names / team>

## Context

What's the situation forcing a decision? The constraints, the forces in tension, the architecture characteristics that matter here. Facts, not opinions.

## Decision

The choice, stated plainly and actively: "We will …".

## Consequences

The trade-off, both signs:

- What this gains / makes easier.
- What this costs / makes harder, and what we are accepting.
- Follow-ups, risks, or fitness functions needed to keep this true.

## Alternatives considered (optional)

Each rejected option + the one-line reason it lost.
```

## Tips

- The **Consequences** section is the most valuable part — it must contain a real cost. A consequences section with only upsides means the analysis isn't done.
- Keep it to a screen. ADRs are read months later by people without the context; brevity helps.
- The point is the _reasoning_, captured once, so the team doesn't re-litigate it ("Groundhog Day" anti-pattern).
