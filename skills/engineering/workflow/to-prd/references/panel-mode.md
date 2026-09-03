# to-prd — Panel mode

Opt-in multi-model drafting for `to-prd`. SKILL.md decides _when_ panel mode runs and what it replaces; this file is _how_. Paths are relative to the repository root.

Read `shared/collaborative-panel-runner.md` before running any panel phase — it holds the routing contract, the flags, the status taxonomy, and the completion gate.

**Phases.** Run all seven in order:

`repo_read` → `product_definition` → `domain_definition` → `interface_definition` → `backend_definition` → `risk_review` → `convergence`

```bash
python3 shared/scripts/panel_round.py \
  --phase repo_read \
  --routing to-prd/assets/panel-routing.toml \
  --goal "the feature being specified" \
  --context-file .ai-workflow/panel/prd/request.md \
  --out .ai-workflow/panel/prd \
  --fail-on-incomplete
```

`repo_read` comes first for a reason: map existing patterns before inventing new ones. Look for similar routes, components, services, use cases, repositories, tests, permissions, validators, migration patterns, and error handling. The resulting PRD must be **constrained by the repository, not only by ideal product design**.

**Read gate.** Read `shared/references/engineering-rules.md` before the `domain_definition` and `backend_definition` phases, so those contracts follow the spec-driven, domain-driven design, clean architecture, and test-driven development rules. This is a gate, not a suggestion: the domain and backend contracts are the two artifacts downstream tasks cannot renegotiate.

**Roles.** The seat behind each role is editable in `to-prd/assets/panel-routing.toml`:

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

**Artifacts.** Panel mode writes to `.ai-workflow/panel/prd`. `prd.md` is the primary output — the same PRD as the template in SKILL.md; copy it to `.ai-workflow/work/<feature-slug>/prd.md` exactly as step 4 does. Alongside it:

1. `codebase_fit.md` — how the feature lands in the existing repository.
2. `domain_notes.md` — concepts, invariants, bounded contexts, ubiquitous language.
3. `interface_contract.md` — journeys, states, validation, accessibility, component contracts.
4. `backend_contract.md` — APIs, use cases, persistence, permissions, observability, failure behavior.
5. `decision_log.md` — decisions plus preserved disagreements; record dissent rather than hiding it.
6. `panel_summary.json` — written by the runner; the participation record.

This list is mirrored in `to-prd/assets/panel-routing.toml` `required_outputs`, the machine-read source consumed by `shared/scripts/validate_artifacts.py`. Before finalizing:

```bash
python3 shared/scripts/validate_artifacts.py \
  --routing to-prd/assets/panel-routing.toml \
  --artifact-dir .ai-workflow/panel/prd
```

**Bounds.** Panel mode stops before task breakdown; `to-tasks` is still the next step. Do not produce implementation patches — where a code snippet is needed, keep it illustrative and mark it as non-authoritative (the prototype-snippet exception in Implementation Decisions is the one case where a snippet is load-bearing, and it stays scoped to the decision it encodes). The quality bar is unchanged: a separate agent must be able to create a task plan from this PRD without asking what the feature means.

**Honesty rules.** A phase is complete only when every required role reached `ok` or `native_response_recorded`. `dry_run` is not participation. `fallback_used` means independence was lost, so do not report that seat as the configured model. A generated native prompt is never enough by itself.
