---
name: brainstorm
description: "Creative exploration of half-baked ideas, plans, designs, and bugs. Acts as a creative thinking partner: digs into the motivation behind a request, explores the codebase, expands the solution space with alternatives the user hasn't considered, and closes with a strategic BUILD/DEFER/REDUCE SCOPE/REJECT verdict. Use when the user wants to brainstorm, shares a half-baked idea and wants help sharpening it, asks 'should we build this' or 'sharpen this idea', or wants to play devil's advocate on an idea (poke holes, challenge this, what am I missing)."
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
│ Next step: spec workflow   [if BUILD or REDUCE]             │
│ Revisit when: <condition>  [if DEFER]                       │
└─────────────────────────────────────────────────────────────┘
```

**Options:**
1. `Agree — proceed with this verdict`
2. `Adjust scope — I want to change what's included`
3. `Override — I want to proceed regardless`

If the user agrees and the verdict is BUILD or REDUCE SCOPE, suggest running the collaborative_specification skill (the repo's spec/PRD workflow) with the refined description. If DEFER, note the revisit condition. If REJECT, acknowledge and move on.

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

Once these hold, move to Phase 4 for the decision-tree summary and verdict.

---
*Blindspot pass, idea-basis contract, and verify-before-claiming adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
