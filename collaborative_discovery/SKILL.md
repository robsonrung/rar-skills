---
name: collaborative_discovery
description: Multi-model discovery interview and brainstorming. Use for product ambiguity, feature exploration, scenario discovery, tradeoff exploration, or when the user is not yet sure what should be built.
---

# Collaborative discovery

Turn an ambiguous idea into a clear problem frame through real multi-model brainstorming and user interview.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

This skill is self contained. Its routing file is `assets/routing.toml` inside this skill folder. Read `references/workflow_contract.md` when porting or reconfiguring this skill.

Do not hardcode model choices in the workflow. Use role names such as `synthesis_anchor`, `adversarial_anchor`, `broad_context`, `feasibility`, and `user_advocate`. The default routing maps the native OpenAI seat to the synthesis anchor and Anthropic to the adversarial anchor, with Gemini and Kimi assigned to specialist roles, but the mapping is editable in `assets/routing.toml`.

Every configured phase must run through `scripts/panel_round.py` unless the user explicitly disables model collaboration. A phase is incomplete when `panel_summary.json` shows `prompt_only`, `awaiting_native_execution`, `dry_run`, `fallback_used`, a missing runner, or a failed required role; the full status taxonomy is in `references/output_contract.md`. A generated native prompt is not participation; the native Codex response must be recorded in `.codex_workflow/discovery/native_responses/<phase>_<role>.md` or passed with `--native-response`. If a specialist role is not relevant to the current idea, it still participates and states why it has no material concern.

## Workflow

Use this skill as a dialogue loop, not as a one shot planner. The goal is to make the problem crisp before any PRD, task plan, or implementation begins.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete. The skill refers to roles, not model names. Change the mapping in `assets/routing.toml` when you want different models.

### Steps

1. Capture the user idea exactly, then rewrite it as a neutral problem statement.
2. Identify ambiguity categories, users, jobs to be done, constraints, known non goals, and likely missing decisions.
3. Run the configured panel phases in order: `intake`, `divergence`, `user_interview`, `cross_critique`, and `convergence`. Use `user_interview` to decide which questions matter; it may conclude that no more questions are needed. Treat every role response as advisory until reconciled.
4. Ask the user only the questions that would materially change the direction. Group questions by product risk, user workflow, data, permissions, user interface, and delivery constraints.
5. Repeat the interview loop until the remaining ambiguity is explicit and acceptable.
6. Run a cross critique round. Each role should critique the strongest option, not the weakest option.
7. Produce a converged discovery brief with options preserved. Do not erase minority views. Mark each unresolved point as decision needed, assumption accepted, or deferred.

### Quality bar

The final brief must be usable as input to the specification skill without the user repeating context. It must include the problem, target users, value proposition, constraints, non goals, scenarios, key tradeoffs, accepted assumptions, rejected options, risks, and recommended next step.

Do not write production code in this skill. Do not create implementation tasks in this skill. If implementation details appear, keep them as feasibility notes only. The feasibility role may consult `references/engineering_rules.md` when judging implementation risk.

## Local panel runner

Use the local runner for each model-panel phase. External roles run through the repo-local runner skills with fallback disabled, so a missing model cannot be silently replaced by another provider. Native Codex roles stay native, but must be executed by the host agent or an allowed native Codex subagent and then recorded as a response artifact.

Example (`<skill_root>` is this skill's directory; the scripts self-locate, so any install location works):

```bash
python3 <skill_root>/scripts/panel_round.py \
  --phase intake \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out .codex_workflow/discovery
```

For each native role, read the generated prompt in `.codex_workflow/discovery/prompts/`, produce the native response, then record it with the helper:

```bash
python3 <skill_root>/scripts/record_native_response.py \
  --phase intake \
  --role synthesis_anchor \
  --from-file /tmp/native-response.md
```

The helper also accepts response text on stdin. It writes `.codex_workflow/discovery/native_responses/<phase>_<role>.md` and updates the matching entry in `panel_summary.json` when a panel run exists. Use `--dry-run` only after changing routing; dry runs do not count as model participation.

## Required outputs

Read `references/output_contract.md` before writing phase artifacts (audit fields, status taxonomy, transcript handling).

Create these files under `.codex_workflow/discovery` unless the user asks for another path:

1. `discovery_brief.md`
2. `option_map.md`
3. `open_questions.md`
4. `decision_log.md`
5. `panel_summary.json`

This list is mirrored in `assets/routing.toml` `required_outputs`, the machine-read source consumed by `scripts/validate_artifacts.py`.

## Completion gate

Before finalizing, run `python3 <skill_root>/scripts/validate_artifacts.py --artifact-dir .codex_workflow/discovery`. If it fails, either complete the missing panel/artifact work or report the failure honestly.
