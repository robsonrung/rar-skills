---
name: to-spec
description: Turn the current conversation into a PRD and publish it to the project issue tracker — no interview, just synthesis of what you've already discussed, with the security-gate threat-model-lite folded in so the spec answers everything the autonomous phases would otherwise ask. Use when the user wants a spec/PRD from the current discussion, or when a pipeline specify phase needs the PRD before task breakdown. The PRD it produces is the input to to-tasks.
disable-model-invocation: true
---

# To Spec

Synthesize the current conversation and codebase understanding into a PRD, then publish it. Do NOT interview the user — work from what you already know. This PRD is the **autonomy contract**: it is the last artifact written while the human is in the room, so every decision the downstream autonomous phases (`to-tasks` → `implement-and-review`) would otherwise have to ask about must be captured here.

## Process

1. **Explore the repo** to understand the current state, if you haven't already. Use the project's domain glossary vocabulary (`CONTEXT.md`) throughout the PRD, and respect ADRs in `docs/adr/` for the area you're touching. If `CONTEXT.md` / `docs/adr/` don't exist, synthesize from the code and note the gap — don't block on it.

2. **Sketch the seams** at which you'll test the feature, applying the `test-lens` rule: test observable external behavior at the **highest** seam possible, never implementation detail. Prefer existing seams to new ones; propose any new seam at the highest point you can. The fewer seams, the better — the ideal is one. Each seam you name here becomes a testable behavior `to-tasks` lifts into a slice's acceptance contract, so name the **observable behavior** at each seam, not just its location.

   Check with the user that these seams match their expectations.

3. **Settle the `security-gate` threat-model-lite** so the spec answers what the autonomous phases can't ask later. **Synthesize first:** if the conversation already covered the security surface (e.g. a `grill-with-docs` interview ran the checklist), just distill those answers — don't re-ask. Only the rows the feature exposes that are still **unanswered** get asked now, while the human is here; security is the one area you may break the no-interview rule for, because a missing answer becomes an unanswerable gap in an autonomous phase. Record the result in the **Security Decisions** section below — this is the `security_decisions` artifact `security-gate` expects, and it pre-marks which surfaces are security-sensitive so `to-tasks` can set each slice's `security: deep|standard` flag as a lift, not a re-derivation.

4. **Write the PRD** using the template below, then publish it to the project issue tracker. Apply the `ready-for-agent` triage label — no need for additional triage. If no tracker is configured, write the PRD to a file at the repo root and tell the user where.

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a mobile bank customer, I want to see balance on my accounts, so that I can make better informed decisions about my spending
</user-story-example>

This list of user stories should be extremely extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

Exception: if a prototype produced a snippet that encodes a decision more precisely than prose can (state machine, reducer, schema, type shape), inline it within the relevant decision and note briefly that it came from a prototype. Trim to the decision-rich parts — not a working demo, just the important bits.

## Security Decisions

The answered `security-gate` threat-model-lite checklist — only the rows the feature exposes. For each: the decision (who can invoke, what input is validated/rejected, what data is sensitive and must never be logged, where secrets live, new dependencies and their blast radius, tenancy boundary, abuse limits, failure-exposure handling). Note which surfaces are security-sensitive so `to-tasks` marks those slices `security: deep`. Omit this section only when the feature exposes no security surface at all, and say so explicitly.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- The seams from step 2 and the observable behavior tested at each — these become the acceptance-contract behaviors in `to-tasks`
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>

## Next

The PRD is the input to **`to-tasks`**, which breaks it into tracer-bullet vertical slices with acceptance contracts and gate flags. The Security Decisions and the named seams above let `to-tasks` set each slice's `security` flag and acceptance behaviors directly from this PRD.

## Gotchas

1. Do not interview the user for new requirements — synthesize what's already been discussed. The one exception is an *unanswered* security-gate row (step 3): security answers can only be collected while the human is present, so ask the gaps rather than letting an autonomous phase hit them.
2. Do not skip the Security Decisions section to save time — a dropped security question becomes a mid-flight question (or a silent gap) in an autonomous phase that can no longer ask.
3. Do not put file paths or code snippets in the PRD; they go stale (the prototype-snippet exception aside).
