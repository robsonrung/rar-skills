# Idea Basis Contract (generated-options mode)

An optional mode for Phase 2. Invoke it when the user wants **generated options** — "give me ideas for X", "what could we do with this area", a field of candidates to choose from — rather than refinement of an idea they already brought. The failure mode this contract prevents is generic "AI-slop" ideas that sound plausible but carry nothing the user can verify.

## The contract: no basis, no idea

Every generated idea carries a **verifiable basis tag**, or it does not surface — regardless of how plausible it sounds:

- `direct:` — a quoted line, specific `file:line`, named issue/PR, or explicit user-supplied context. A `direct:` basis must cite something actually read this session, never a guessed citation.
- `external:` — named prior art, domain research, or an adjacent pattern, with its source.
- `reasoned:` — an explicit first-principles argument for why this move likely applies, written out — not a gesture.

Each idea is returned as:

- **title**
- **summary** (2-4 sentences)
- **basis** (required, tagged as above)
- **why it matters** — connects the basis to the move's significance for this user

## Generation rules

- Treat the first few ideas as warm-up — they will be the obvious ones. Keep only those that still earn their place after the non-obvious ideas exist. If an idea would appear in a generic listicle about the topic, sharpen it with grounding evidence or drop it.
- Stay within the subject's identity, and honor the asked scope: when the user named one slice (a flow, a page, a feature), ideate at full ambition *inside* that slice — widening the surface is a scope mismatch, not big thinking.
- Vary the angle: pain and friction; inversion/removal/automation; assumption-breaking; leverage and compounding; cross-domain analogy; constraint-flipping (what if the budget were 10x or 0?). Use these as starting biases, not fences.

## Critique and rank before presenting

Never hand the user the raw list. Critique every candidate against its own basis, the user's constraints, and the codebase reality, then present:

1. The **ranked survivors** (typically 3-7), each with its basis tag visible so the user can check it.
2. The **rejected ideas with explicit rejection reasons** — one line each ("rejected: basis didn't survive a read of `auth/session.ts`", "rejected: violates the stated no-new-infra constraint"). Silent drops are forbidden; the rejects teach the user the shape of the space as much as the survivors do.

Survivors then feed the normal Phase 2/3 flow: alternatives on the table, trade-offs surfaced, convergence together.

## Optional: multi-model fleet

For a high-stakes ideation where one model's biases would narrow the field, the generation step can fan out across the repo's runner seats (`claude-runner`, `codex-runner`, `gemini-runner`, `kimi-runner`, `glm-runner`, ...) — same contract per seat, merged and deduped before critique. Basis tags are what make cross-model merging safe: an idea without a checkable basis cannot be deduplicated honestly. Keep the fleet small (2-3 seats) unless the user asks for more.

---
*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
