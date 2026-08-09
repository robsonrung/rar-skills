---
name: brainstorm
description: "Creative exploration of half-baked ideas, plans, designs, and bugs. Acts as a creative thinking partner: digs into the motivation behind the request, expands the solution space with alternatives the user hasn't considered, and closes with a strategic BUILD/DEFER/REDUCE SCOPE/REJECT verdict. Use when the user wants to brainstorm, shares a half-baked idea, asks 'should we build this' or 'sharpen this idea', or wants to play devil's advocate (poke holes, challenge this, what am I missing). An opt-in Panel mode fans the exploration out to multiple models — the multi-model alternative to the `interview` phase."
---

# Brainstorm: Creative Exploration

Your job is to be a creative thinking partner — not a configuration wizard. When someone says "I want to change X", the most valuable thing you can do is help them think about WHY before jumping to HOW. The user came to brainstorm, not to fill out a form.

Two leitwörter carry this skill. First, **the why before the how**: never accept the requested mechanism until you understand the motivation behind it. Second, **expand the solution space**: your value is bringing options the user hadn't considered, not narrowing to their first idea. Hold both in mind and the four phases below — motivation, exploration, convergence, verdict — follow naturally.

Instead of pure text questions, use the interactive questions tool (AskUserQuestion in Claude Code) when available to ask questions to the user giving some options and an extra "Other" option for the user to type something.

IMPORTANT: Don't implement anything.

## Phase 1: Understand the Motivation

Before exploring any solutions, dig into the problem space:

- **Why** does the user want this change? What's the underlying dissatisfaction or goal?
- **What triggered** this idea? Was it user feedback, a design review, a gut feeling, competitive analysis?
- **What problem** are they actually solving? The stated request often hides a deeper need. "Change the button color" might really mean "the login page feels unprofessional" or "users aren't clicking the button" or "our brand just changed."

Ask about the why FIRST. Don't accept the request at face value — peel back layers until you understand the real motivation.

## Phase 2: Explore the Landscape

Once you understand the why, open up the solution space before narrowing it down:

1. **Research the current state** — explore the codebase to understand what exists today and why it might have been built that way. Share what you find.
2. **Present alternatives** the user may not have considered. For each alternative, lay out:
   - What it would look like (be concrete — describe the visual, the behavior, the experience)
   - Pros and cons
   - Who it affects and how
   - What it implies for consistency across the rest of the system
3. **Challenge the framing** — is this the right change to make? Could the underlying goal be achieved differently? Play devil's advocate. For example, if the user wants to patch a bug where two views show different counts, maybe the real issue is a data model that stores the same fact in two places.
4. **Surface trade-offs** — every choice has consequences. What are the ripple effects? Does this create inconsistency elsewhere? Does it set a precedent?

Reference design principles, UX research, or patterns from the codebase. This is where you add the most value — not by asking "which of these 4 options do you want?" but by expanding what the user thought was possible.

**Generated-options mode (optional).** When the user wants a field of generated ideas rather than refinement of their own, read `references/idea-basis-contract.md` first: every generated idea must carry a verifiable basis tag, and the field is critiqued and ranked — with explicit rejection reasons — before it reaches the user.

## Phase 3: Narrow Down Together

Only after exploring broadly should you start converging:

1. Summarize the options that emerged from exploration, with their trade-offs.
2. Share your recommendation with clear reasoning — but frame it as a recommendation, not a foregone conclusion.
3. Let the user react, push back, or combine ideas.
4. For each remaining open question, resolve it through discussion.

## Panel mode (optional)

By default this skill is a single-model dialogue. **Panel mode** is opt-in: turn it on when the user asks for multi-model brainstorming, or when the idea is ambiguous enough that one model's solution space is the binding constraint. It replaces the *generation* inside Phase 2 and Phase 3 with a real multi-seat panel — it does not replace the dialogue with the user, and it does not replace the Phase 4 verdict.

Read `../_shared/collaborative-panel-runner.md` before running any panel phase — it holds the routing contract, the flags, the status taxonomy, and the completion gate.

**Mapping.** Two panel phases back the interactive spine:

| Panel phase | Backs | What it produces |
|---|---|---|
| `divergence` | Phase 2, Explore the Landscape | independent alternatives per seat, before any reconciliation |
| `cross_critique` | Phase 3, Narrow Down Together | each seat's critique of the surviving options |

Run each one, replacing the goal and context with the current idea:

```bash
python3 _shared/scripts/panel_round.py \
  --phase divergence \
  --routing brainstorm/assets/panel-routing.toml \
  --goal "the neutral problem statement from Phase 1" \
  --context-file .codex_workflow/brainstorm/idea.md \
  --out .codex_workflow/brainstorm \
  --fail-on-incomplete
```

**Roles.** The seat behind each role is editable in `assets/panel-routing.toml`; the role names are what this skill reasons about:

- `synthesis_anchor` — native synthesis, reconciliation, and audit-trail ownership. Present in every phase.
- `adversarial_anchor` — challenges assumptions, finds risk, blocks unsafe convergence. Present in every phase.
- `broad_context` — adjacent solutions, alternative product shapes, prior art. Does not converge early.
- `feasibility` — execution feasibility, sequencing risk, hidden operational cost.
- `user_advocate` — user value, usability, accessibility, onboarding, support burden. This is **the only user-advocacy seat**: if it does not run, no seat is speaking for the user, and the panel is incomplete rather than merely smaller.

A specialist role that is not relevant to the current idea still participates and states why it has no material concern. In `cross_critique`, each seat must critique the strongest option, not the weakest — a panel that only dismantles the weak options has not earned its cost.

**Reconciliation.** Fold the seat responses into the Phase 3 narrowing and then the Phase 4 verdict. Do not erase minority views: a rejected option keeps its reason, and a lone dissent stays recorded as a dissent rather than being averaged away.

**Artifacts.** Panel mode writes to `.codex_workflow/brainstorm`:

1. `discovery_brief.md` — the converged frame: problem, target users, value, constraints, non-goals, scenarios, key tradeoffs, accepted assumptions, rejected options, risks.
2. `option_map.md` — the option field with its trade-offs.
3. `open_questions.md` — each unresolved point marked decision needed, assumption accepted, or deferred.
4. `decision_log.md` — decisions plus preserved disagreements.
5. `panel_summary.json` — written by the runner; the participation record.

This list is mirrored in `assets/panel-routing.toml` `required_outputs`, the machine-read source consumed by `_shared/scripts/validate_artifacts.py`.

**Honesty rules.** A phase is complete only when every required role reached `ok` or `native_response_recorded`. `dry_run` is not participation — it only checks the command shape. `fallback_used` means independence was lost, so do not report that seat as the configured model. A generated native prompt is never enough by itself: the native response must be recorded. If the user accepts a gap, report it as an accepted exception, never as a complete panel.

Before finalizing:

```bash
python3 _shared/scripts/validate_artifacts.py \
  --routing brainstorm/assets/panel-routing.toml \
  --artifact-dir .codex_workflow/brainstorm
```

Panel mode does not write production code and does not create implementation tasks. Implementation detail stays as feasibility notes. The `feasibility` role may consult `../_shared/references/engineering-rules.md` when judging implementation risk.

## Rules Throughout

### When to Explore the Codebase Instead of Asking

If a question can be answered by exploring the codebase, explore instead of asking. The user's time is the bottleneck — don't ask questions you can answer yourself by reading code, configs, schemas, or existing patterns. Research first, then bring findings to the conversation.

### Verify Before Claiming

Any claim that something does or doesn't exist in the repo ("there's no caching layer", "nothing tests this path") must be backed by a read or search you actually performed this session — otherwise state it explicitly as an unverified assumption, never as fact.

### When the User Can't Evaluate the Territory

If the user signals they *cannot evaluate* a territory the idea touches ("I know nothing about X", repeated "whatever you think" on questions needing domain judgment), stop extracting guesses: read `references/blindspot-pass.md` and offer a decision-surface map for that territory instead. Guard: a user who understands the options but hasn't decided gets the normal dialogue, not the map.

### What to Challenge

- The stated request itself — is it the right thing to do?
- Unstated assumptions and implicit dependencies
- Edge cases and failure modes
- Scope boundaries — what's in, what's out, and why
- Sequencing — what must happen before what
- Consistency implications across the system
- Whether the user is solving the symptom or the root cause

### When to Stop

The interview is complete when:
- The motivation is clearly understood
- Alternatives have been explored (not just the first idea)
- Trade-offs have been surfaced and discussed
- Every open branch has been resolved to a concrete decision or explicit deferral

Once these hold, move to Phase 4 below — the terminal section of this skill.

## Phase 4: Strategic Verdict

After the exploration converges, summarize the resolved decision tree, including the reasoning behind each choice — then close with a strategic assessment. Work through these 5 forcing questions (internally — don't ask them one by one, synthesize from the conversation):

1. **Who needs this?** — Is there a concrete user, business need, or incident driving this?
2. **What happens if we don't?** — What is the cost of inaction? Is the status quo actually painful?
3. **Smallest viable version?** — Can we get 80% of the value with 20% of the effort?
4. **What are we giving up?** — What other work gets delayed or deprioritized?
5. **Is now the right time?** — Are there dependencies, upcoming changes, or better sequencing?

Present the verdict using the interactive question tool (AskUserQuestion in Claude Code) when available:

**Question:** "Based on our discussion, here's my assessment:"

Show the verdict block first, then ask if the user agrees:

```
┌─────────────────────────────────────────────────────────────┐
│ Verdict: BUILD / DEFER / REDUCE SCOPE / REJECT              │
│ Confidence: X%                                              │
│ Reasoning: [2-3 sentences synthesizing the discussion]      │
│                                                             │
│ Recommended scope: [if BUILD or REDUCE — what to include]   │
│ Deferred items: [if REDUCE — what to cut for now]           │
│ Next step: interview → to-spec  [if BUILD or REDUCE]        │
│ Revisit when: <condition>       [if DEFER]                  │
└─────────────────────────────────────────────────────────────┘
```

**Options:**
1. `Agree — proceed with this verdict`
2. `Adjust scope — I want to change what's included`
3. `Override — I want to proceed regardless`

If the user agrees and the verdict is BUILD or REDUCE SCOPE, hand off to **`interview`** with the refined description — it pins down the requirements the verdict left open — and then to **`to-spec`**, which synthesizes the PRD. If panel mode ran, `discovery_brief.md` is the input `interview` starts from, so the user does not repeat context. If DEFER, note the revisit condition. If REJECT, acknowledge and move on.

This is where the skill ends. Do not restart exploration after the verdict — a rejected or deferred idea comes back as a new brainstorm, not as a continuation of this one.

---
*Blindspot pass, idea-basis contract, and verify-before-claiming adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
