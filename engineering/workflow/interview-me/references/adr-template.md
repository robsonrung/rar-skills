# ADR file shape (runtime mirror)

> `architecture-lens/references/adr-template.md` is the repo-canonical ADR template; read it there for the significance discussion and writing tips. This file mirrors the part `interview-me` needs at write time — the file shape, numbering, and the supersede rule — so the skill stays self-contained. Keep the two consistent: when the canonical template changes, mirror it here.

## Where and how it is named

- One file per decision in `docs/adr/`, versioned with the code.
- **Match the directory's existing shape first.** If `docs/adr/` already has files, copy their naming and heading conventions exactly (some repos use `YYYYMMDD_slug.md`; the canonical shape is `NNNN-short-title.md`).
- **Numbering:** scan `docs/adr/` for the highest existing number and add one; zero-pad to four digits. Never reuse or skip a number.
- Create `docs/adr/` lazily, when the first ADR is ready to write.

## Template

```markdown
# ADR-NNNN: <short imperative title>

- Status: Proposed | Accepted | Superseded by ADR-XXXX | Deprecated
- Date: YYYY-MM-DD
- Deciders: <names / team>

## Context

The situation forcing a decision: the constraints, the forces in tension, the architecture characteristics that matter here. Facts, not opinions.

## Decision

The choice, stated plainly and actively: "We will …".

## Consequences

The trade-off, both signs:

- What this gains / makes easier.
- What this costs / makes harder, and what is being accepted.
- Follow-ups, risks, or fitness functions needed to keep this true.

## Alternatives considered (optional)

Each rejected option + the one-line reason it lost.
```

## Rules

- Keep it to a screen; it is read months later by someone without the context.
- Consequences must contain a real cost. Only upsides means the analysis is not done.
- ADRs are immutable once accepted. To change a decision, write a _new_ ADR that supersedes the old one and link both ways (`Superseded by ADR-XXXX` on the old, a Context sentence on the new). Never edit history.
