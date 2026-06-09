---
name: collaborative_specification
description: Multi-model PRD and technical specification workflow. Use after discovery, or when the user asks for a PRD, product spec, technical spec, acceptance criteria, codebase fit analysis, or feature definition before task planning.
---

# Collaborative specification

Create a PRD and codebase fit analysis from a clarified idea with real multi-model product, domain, interface, security, and delivery review.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

This skill is self contained. Its routing file is `assets/routing.toml` inside this skill folder. Read `references/workflow_contract.md` when copying this skill elsewhere or editing `assets/routing.toml`.

Do not hardcode model choices in the workflow. Use role names such as `synthesis_anchor`, `adversarial_anchor`, `product`, `domain`, `interface`, `backend`, `security`, and `delivery_review`. The default routing keeps the native OpenAI synthesis anchor and Anthropic adversarial anchor mandatory, with Gemini and Kimi assigned to specialist roles when configured, but the mapping is editable in `assets/routing.toml`.

Every configured phase must run through `scripts/panel_round.py` unless the user explicitly disables model collaboration. A phase is complete only when every required role has status `ok` or `native_response_recorded` in `panel_summary.json`; read `references/output_contract.md` for the full panel status rules and native response recording requirements. If a specialist role is not relevant to the current spec, it still participates and states why it has no material concern.

## Workflow

Use this skill to produce the specification that future coding work must obey. It must connect the user request to the existing repository before tasks are created.

Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete. The interface definition phase must include the interface role and the adversarial anchor together. The backend definition phase must include the backend role and synthesis anchor together. These are role requirements, and the default model mapping is editable in `assets/routing.toml`.

Workflow

1. Read the user request, any discovery brief, and the relevant repository files in read only mode.
2. Map existing patterns before inventing new ones. Look for similar routes, components, services, use cases, repositories, tests, permissions, validators, migration patterns, and error handling.
3. Run the configured panel phases in order: `repo_read`, `product_definition`, `domain_definition`, `interface_definition`, `backend_definition`, `risk_review`, and `convergence`. Read `references/engineering_rules.md` before the `domain_definition` and `backend_definition` phases so the contracts follow the spec driven, domain driven design, clean architecture, and test driven development rules.
4. Reconcile the outputs into one specification. Record disagreements in decision_log.md rather than hiding them.
5. Define acceptance criteria as testable statements.
6. Define non goals and out of scope behavior.
7. Define data contracts, permissions, validations, observability, rollout, migration, and rollback expectations where relevant.
8. Stop before task breakdown. Link to the task design skill as the next step.

Quality bar

The PRD must be detailed enough that a separate agent can create a task plan without asking what the feature means. It must be constrained by the repository, not only by ideal product design.

Do not produce implementation patches in this skill. If code snippets are needed, keep them illustrative and mark them as non authoritative.

## Local panel runner

Use the local runner for each model-panel phase. External roles run through the repo-local runner skills with fallback disabled, so a missing model cannot be silently replaced by another provider. Native Codex roles stay native, but must be executed by the host agent or an allowed native Codex subagent and then recorded as a response artifact.

In the examples below, `<skill_root>` is this skill's install folder, wherever the skill was copied (for example `collaborative_specification/` at this repository's root, or an `.agents/skills/collaborative_specification/` location elsewhere).

Example:

```bash
python3 <skill_root>/scripts/panel_round.py \
  --phase repo_read \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out .codex_workflow/specification
```

For each native role, read the generated prompt in `.codex_workflow/specification/prompts/`, produce the native response, then record it with the helper:

```bash
python3 <skill_root>/scripts/record_native_response.py \
  --phase repo_read \
  --role synthesis_anchor \
  --from-file /tmp/native-response.md
```

The helper also accepts response text on stdin. It writes `.codex_workflow/specification/native_responses/<phase>_<role>.md` and updates the matching entry in `panel_summary.json` when a panel run exists. Use `--dry-run` only after changing routing; dry runs do not count as model participation.

## Required outputs

Read `references/output_contract.md` when writing these phase artifacts or interpreting `panel_summary.json` statuses.

Create these files under `.codex_workflow/specification` unless the user asks for another path:

1. `prd.md`
2. `codebase_fit.md`
3. `domain_notes.md`
4. `interface_contract.md`
5. `backend_contract.md`
6. `risk_register.md`
7. `decision_log.md`
8. `panel_summary.json`

## Completion gate

Before finalizing, run `python3 <skill_root>/scripts/validate_artifacts.py --artifact-dir .codex_workflow/specification`. If it fails, either complete the missing panel/artifact work or report the failure honestly. For a partial in-progress run, pass `--allow-missing-phases` to validate only the required files.
