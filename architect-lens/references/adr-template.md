# Architecture Decision Record (ADR) — lightweight template

An ADR captures *one* architecturally significant decision: the context, the choice, and the consequences. Write one only when the decision is significant (see test below) — not for routine choices.

## When a decision is "architecturally significant"
Write an ADR if the decision affects **any** of:
- Structure (a new component, boundary, layer, or service).
- A cross-cutting characteristic (security, scalability, availability…).
- Dependencies between parts of the system, or a new external dependency.
- A public interface or contract others rely on.
- …or it was hard-won and likely to be questioned again later ("why did we do it this way?").

If none apply, skip the ADR — a one-line code comment or PR note is enough.

## Storage
- Keep ADRs in the repo (e.g. `docs/adr/`), versioned with the code, one file per decision: `NNNN-short-title.md`, numbered sequentially.
- ADRs are immutable once accepted. To change a decision, write a *new* ADR that **supersedes** the old one and link both ways. Don't edit history.

## Template

```markdown
# ADR-NNNN: <short imperative title>

- Status: Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
- Date: YYYY-MM-DD
- Deciders: <names / team>

## Context
What's the situation forcing a decision? The constraints, the forces in tension,
the architecture characteristics that matter here. Facts, not opinions.

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
- The point is the *reasoning*, captured once, so the team doesn't re-litigate it ("Groundhog Day" anti-pattern).
