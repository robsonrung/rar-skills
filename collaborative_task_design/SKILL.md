---
name: collaborative_task_design
description: Multi-model engineering task design and test planning. Use when a PRD, technical spec, bug description, or accepted discovery brief must become implementation tasks, test plans, architecture decisions, or delivery phases.
---

# Collaborative task design

Convert a PRD into sequenced engineering tasks using real multi-model review, spec driven development, domain driven design, clean architecture, and test driven development.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

This skill is self contained. Its routing file is `assets/routing.toml` inside this skill folder.

Do not hardcode model choices in the workflow. Use role names such as `synthesis_anchor`, `adversarial_anchor`, `architecture`, `testing`, `interface`, `backend`, and `delivery`. The default routing keeps the native OpenAI synthesis anchor and Anthropic adversarial anchor mandatory, with Gemini and Kimi assigned to specialist roles, but the mapping is editable in `assets/routing.toml`.

Every configured phase must run through `scripts/panel_round.py` unless the user explicitly disables model collaboration. A phase is incomplete when `panel_summary.json` shows `prompt_only`, `awaiting_native_execution`, `dry_run`, `fallback_used`, a missing runner, or a failed required role. A generated native prompt is not participation; the native Codex response must be recorded in `.codex_workflow/task_design/native_responses/<phase>_<role>.md` or passed with `--native-response`. If a specialist role is not relevant to the current plan, it still participates and states why it has no material concern.

## Workflow

Use this skill to convert specification into executable engineering work. The output is not a PRD and not a patch. It is the bridge between product intent and implementation.

Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete. Every task must trace back to a spec item and must define tests before code. The default model mapping is editable in `assets/routing.toml`.

Workflow

1. Read the PRD and codebase fit artifacts. If they do not exist, create a minimal assumptions section and mark missing inputs.
2. Map the target architecture. Identify domain layer, application use cases, ports, adapters, infrastructure, presentation, data boundaries, and dependency direction.
3. Run the configured panel phases in order: `architecture_mapping`, `test_strategy`, `task_slicing`, `dependency_review`, and `convergence`.
4. Slice tasks by user visible value and architectural seam. Avoid tasks that are too broad, such as implement backend, and tasks that are too tiny, such as rename one variable, unless that variable is a blocking domain concept.
5. For each task, include goal, files likely touched, tests to write first, implementation notes, acceptance criteria, verification commands, dependencies, rollback note, and expected review focus.
6. Identify work that can be parallelized safely. Do not parallelize tasks that write the same files, migrations, shared contracts, or security sensitive paths unless there is an explicit merge plan.
7. Produce a task sequence that supports red, green, refactor execution.

Quality bar

A task is ready only when another agent can execute it without reinterpreting the product requirement. Each task must have a clear test first entry point and a bounded diff surface.

Do not implement code in this skill. Do not change files outside the workflow artifact directory unless the user explicitly asks for repository scaffolding.

## Local panel runner

Use the local runner for each model-panel phase. External roles run through the repo-local runner skills with fallback disabled, so a missing model cannot be silently replaced by another provider. Native Codex roles stay native, but must be executed by the host agent or an allowed native Codex subagent and then recorded as a response artifact.

Example:

```bash
python3 .agents/skills/collaborative_task_design/scripts/panel_round.py \
  --phase architecture_mapping \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out .codex_workflow/task_design
```

For each native role, read the generated prompt in `.codex_workflow/task_design/prompts/`, produce the native response, then record it with the helper:

```bash
python3 .agents/skills/collaborative_task_design/scripts/record_native_response.py \
  --phase architecture_mapping \
  --role synthesis_anchor \
  --from-file /tmp/native-response.md
```

The helper also accepts response text on stdin. It writes `.codex_workflow/task_design/native_responses/<phase>_<role>.md` and updates the matching entry in `panel_summary.json` when a panel run exists. Use `--dry-run` only after changing routing; dry runs do not count as model participation.

## Required outputs

Create these files under `.codex_workflow/task_design` unless the user asks for another path:

1. `architecture_plan.md`
2. `tasks.md`
3. `test_plan.md`
4. `parallelization_plan.md`
5. `risk_register.md`
6. `decision_log.md`
7. `panel_summary.json`

## Completion gate

Before finalizing, run `python3 .agents/skills/collaborative_task_design/scripts/validate_artifacts.py --artifact-dir .codex_workflow/task_design`. If it fails, either complete the missing panel/artifact work or report the failure honestly.
