---
name: to-spec
description: Turn the current conversation into a PRD and publish it to the project issue tracker — no interview, just synthesis of what you've already discussed, with the security-gate threat-model-lite folded in so the spec answers everything the autonomous phases would otherwise ask. Use when the user wants a spec/PRD from the current discussion, or when a pipeline specify phase needs the PRD before task breakdown. The PRD it produces is the input to to-tasks.
---

# To Spec

Synthesize the current conversation and codebase understanding into a PRD, then publish it. Do NOT interview the user — work from what you already know. This PRD is the **autonomy contract**: it is the last artifact written while the human is in the room, so every decision the downstream autonomous phases (`to-tasks` → `implement-and-review`) would otherwise have to ask about must be captured here.

## Process

1. **Explore the repo** to understand the current state, if you haven't already. Use the project's domain glossary vocabulary (`CONCEPTS.md`) throughout the PRD, and respect ADRs in `docs/adr/` for the area you're touching. If `CONCEPTS.md` / `docs/adr/` don't exist, synthesize from the code and note the gap — don't block on it.

2. **Sketch the seams** at which you'll test the feature, applying the `test-lens` rule: test observable external behavior at the **highest** seam possible, never implementation detail. Prefer existing seams to new ones; propose any new seam at the highest point you can. The fewer seams, the better — the ideal is one. Each seam you name here becomes a testable behavior `to-tasks` lifts into a slice's acceptance contract, so name the **observable behavior** at each seam, not just its location.

   Check with the user that these seams match their expectations.

3. **Settle the `security-gate` threat-model-lite** so the spec answers what the autonomous phases can't ask later. **Synthesize first:** if the conversation already covered the security surface (e.g. an `interview` run already worked the checklist), just distill those answers — don't re-ask. Only the rows the feature exposes that are still **unanswered** get asked now, while the human is here; security is the one area you may break the no-interview rule for, because a missing answer becomes an unanswerable gap in an autonomous phase. Record the result in the **Security Decisions** section below — this is the `security_decisions` artifact `security-gate` expects, and it pre-marks which surfaces are security-sensitive so `to-tasks` can set each slice's `security: deep|standard` flag as a lift, not a re-derivation.

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

## Panel mode (optional)

By default this skill is a single-model synthesis. **Panel mode** is opt-in: turn it on when the user asks for a multi-model PRD, or when the feature's domain, interface, and backend contracts are consequential enough to be worth independent seats. It replaces the *drafting* of the PRD with a real multi-seat panel. Everything else above still holds — the autonomy-contract framing, the seam sketch, the no-file-paths rule, the Security Decisions section, and tracker publication.

Read `../shared/collaborative-panel-runner.md` before running any panel phase — it holds the routing contract, the flags, the status taxonomy, and the completion gate.

**Phases.** Run all seven in order:

`repo_read` → `product_definition` → `domain_definition` → `interface_definition` → `backend_definition` → `risk_review` → `convergence`

```bash
python3 shared/scripts/panel_round.py \
  --phase repo_read \
  --routing to-spec/assets/panel-routing.toml \
  --goal "the feature being specified" \
  --context-file .codex_workflow/spec/request.md \
  --out .codex_workflow/spec \
  --fail-on-incomplete
```

`repo_read` comes first for a reason: map existing patterns before inventing new ones. Look for similar routes, components, services, use cases, repositories, tests, permissions, validators, migration patterns, and error handling. The resulting PRD must be **constrained by the repository, not only by ideal product design**.

**Read gate.** Read `../shared/references/engineering-rules.md` before the `domain_definition` and `backend_definition` phases, so those contracts follow the spec-driven, domain-driven design, clean architecture, and test-driven development rules. This is a gate, not a suggestion: the domain and backend contracts are the two artifacts downstream tasks cannot renegotiate.

**Roles.** The seat behind each role is editable in `assets/panel-routing.toml`:

- `synthesis_anchor` — native synthesis, reconciliation, audit-trail ownership. Present in every phase.
- `adversarial_anchor` — challenges assumptions, finds risk, blocks unsafe convergence. Present in every phase.
- `product` — user value, acceptance criteria, rollout, analytics, support, non-goals.
- `domain` — domain concepts, invariants, bounded contexts, ubiquitous language, behavior rules.
- `interface` — user journeys, screens, state boundaries, validation messages, accessibility, component contracts.
- `backend` — APIs, application use cases, persistence boundaries, transactions, integrations, permissions, observability, failure behavior.
- `security` — authentication, authorization, data exposure, tenancy, auditability, abuse cases, privacy, rollback risk.
- `delivery_review` — implementation feasibility, rollout pressure, migration risk, sequencing, support burden, operational cost.

A specialist role that is not relevant to the current spec still participates and states why it has no material concern.

**Mandated anchor pairings.** Beyond the anchors' standing presence in every phase:

- **interface definition** = the `interface` role **and** the `adversarial_anchor`, together. The interface contract is defined and attacked in the same phase.
- **backend definition** = the `backend` role **and** the `synthesis_anchor`, together. The backend contract is defined and reconciled in the same phase.

**Security handshake.** Panel mode does not get to skip step 3. The `security` role answers the `security-gate` threat-model-lite rows the feature exposes, and those answers are recorded into the PRD's **Security Decisions** section — the same `security_decisions` artifact the single-model path produces, pre-marking which surfaces are security-sensitive so `to-tasks` lifts each slice's `security: deep|standard` flag instead of re-deriving it. A panel run whose `risk_review` completed but whose Security Decisions section is empty is an incomplete spec, not a fast one. Any row the panel cannot answer from the repository is asked of the user while they are still present.

**Artifacts.** Panel mode writes to `.codex_workflow/spec`. `prd.md` is the primary output — the same PRD as the template above, still published to the tracker. Alongside it:

1. `codebase_fit.md` — how the feature lands in the existing repository.
2. `domain_notes.md` — concepts, invariants, bounded contexts, ubiquitous language.
3. `interface_contract.md` — journeys, states, validation, accessibility, component contracts.
4. `backend_contract.md` — APIs, use cases, persistence, permissions, observability, failure behavior.
5. `decision_log.md` — decisions plus preserved disagreements; record dissent rather than hiding it.
6. `panel_summary.json` — written by the runner; the participation record.

This list is mirrored in `assets/panel-routing.toml` `required_outputs`, the machine-read source consumed by `shared/scripts/validate_artifacts.py`. Before finalizing:

```bash
python3 shared/scripts/validate_artifacts.py \
  --routing to-spec/assets/panel-routing.toml \
  --artifact-dir .codex_workflow/spec
```

**Bounds.** Panel mode stops before task breakdown; `to-tasks` is still the next step. Do not produce implementation patches — where a code snippet is needed, keep it illustrative and mark it as non-authoritative (the prototype-snippet exception in Implementation Decisions is the one case where a snippet is load-bearing, and it stays scoped to the decision it encodes). The quality bar is unchanged: a separate agent must be able to create a task plan from this PRD without asking what the feature means.

**Honesty rules.** A phase is complete only when every required role reached `ok` or `native_response_recorded`. `dry_run` is not participation. `fallback_used` means independence was lost, so do not report that seat as the configured model. A generated native prompt is never enough by itself.

## Next

The PRD is the input to **`to-tasks`**, which breaks it into tracer-bullet vertical slices with acceptance contracts and gate flags. The Security Decisions and the named seams above let `to-tasks` set each slice's `security` flag and acceptance behaviors directly from this PRD.

## Gotchas

1. Do not interview the user for new requirements — synthesize what's already been discussed. The one exception is an *unanswered* security-gate row (step 3): security answers can only be collected while the human is present, so ask the gaps rather than letting an autonomous phase hit them.
2. Do not skip the Security Decisions section to save time — a dropped security question becomes a mid-flight question (or a silent gap) in an autonomous phase that can no longer ask.
3. Do not put file paths or code snippets in the PRD; they go stale (the prototype-snippet exception aside).
