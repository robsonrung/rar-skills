---
name: collaborative_delivery
description: Multi-model panel-gated delivery workflow with mandatory anchor review at every phase. Use when an approved task plan exists and the user explicitly wants multi-model collaborative delivery — panel-reviewed implementation, bug fixing, refactoring, tests, code review, or controlled delivery — or auditable red-green-refactor with recorded model participation in the repository.
---

# Collaborative delivery

Execute approved tasks through red green refactor loops with real multi-model collaboration, review gates, and verification evidence.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

This skill is self contained. Its routing file is `assets/routing.toml` inside this skill folder.

Do not hardcode model choices in the workflow. Use role names such as `synthesis_anchor`, `adversarial_anchor`, `implementation`, `interface`, `backend`, `testing`, `review`, and `simplification`. The default routing keeps the native OpenAI synthesis anchor and Anthropic adversarial anchor mandatory, with Gemini and Kimi assigned to specialist roles when configured, but the mapping is editable in `assets/routing.toml`.

Every configured phase must run through `scripts/panel_round.py` unless the user explicitly disables model collaboration. A phase is incomplete when `panel_summary.json` shows `prompt_only`, `awaiting_native_execution`, `dry_run`, `fallback_used`, a missing runner, or a failed required role. A generated native prompt is not participation; the native Codex response must be recorded in `.codex_workflow/delivery/native_responses/<phase>_<role>.md` or passed with `--native-response`. If a specialist role is not relevant to the current implementation slice, it still participates and states why it has no material concern.

Read `references/output_contract.md` before writing any phase artifact or interpreting `panel_summary.json` statuses. It defines the per-phase presence audit, the full panel-status semantics, and external transcript handling.

## Workflow

Use this skill to implement approved tasks in controlled loops. It must keep tests, review, and architecture visible throughout the work.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete. For interface implementation, the interface role and adversarial anchor jointly define and review the interface contract. For backend implementation, the backend role and synthesis anchor jointly define and implement the backend path. These requirements are role based, and the model mapping is editable in `assets/routing.toml`.

### Steps

1. Choose exactly one task unless the task plan explicitly says a group is safe to parallelize.
2. Restate the task, acceptance criteria, expected files, and tests to write first.
3. Run the configured panel phases as gates: `task_intake`, `red`, `green`, `refactor`, `review`, `verification`, and `handoff` (the same list enforced by `[skill].required_phases` in `assets/routing.toml`). The Codex host owns code edits; external roles review, challenge, and shape decisions unless the routing explicitly changes that.
4. Red phase. Read `references/engineering_rules.md` before starting the red, green, and refactor phases. Add or update the failing test first. Run the narrowest command that proves the test fails for the expected reason.
5. Green phase. Implement the smallest code change to pass the test while preserving clean architecture and domain boundaries.
6. Refactor phase. Simplify only while tests are green. Do not change behavior silently.
7. Review phase. Use the review role, plus required anchors, to inspect the diff for correctness, security, maintainability, performance, accessibility, data safety, and consistency with the task plan.
8. Verification phase. Run targeted tests, then broader checks when warranted. Record commands, outputs, skipped checks, and reasons.
9. Handoff phase. Summarize changed files, behavior changes, tests, known limitations, and next recommended task.

### Quality bar

A delivery is complete only when the diff is reviewed, verification evidence is recorded, and every accepted exception is explicit. If tests cannot run, explain why and provide the best available static or manual verification.

Do not combine unrelated tasks. Do not bypass red, green, refactor for production changes unless the user explicitly asks and the risk is documented.

## Local panel runner

Use the local runner for each model-panel phase. External roles run through the repo-local runner skills with fallback disabled, so a missing model cannot be silently replaced by another provider. Native Codex roles stay native, but must be executed by the host agent or an allowed native Codex subagent and then recorded as a response artifact.

Commands below write `<skill folder>` for this skill's installation directory (for example `.agents/skills/collaborative_delivery`); adjust the prefix to wherever this skill is actually installed. The scripts resolve their own skill root, so only the invocation path varies.

Example:

```bash
python3 <skill folder>/scripts/panel_round.py \
  --phase task_intake \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out .codex_workflow/delivery
```

For each native role, read the generated prompt in `.codex_workflow/delivery/prompts/`, produce the native response, then record it with the helper:

```bash
python3 <skill folder>/scripts/record_native_response.py \
  --phase task_intake \
  --role synthesis_anchor \
  --from-file /tmp/native-response.md
```

The helper also accepts response text on stdin. It writes `.codex_workflow/delivery/native_responses/<phase>_<role>.md` and updates the matching entry in `panel_summary.json` when a panel run exists. Use `--dry-run` only after changing routing; dry runs do not count as model participation.

## Required outputs

Create these files under `.codex_workflow/delivery` unless the user asks for another path:

1. `execution_log.md`
2. `test_evidence.md`
3. `review_notes.md`
4. `changed_files.md`
5. `decision_log.md`
6. `panel_summary.json`

This list matches `[skill].required_outputs` in `assets/routing.toml`, which is what `scripts/validate_artifacts.py` enforces.

## Completion gate

Before finalizing, run `python3 <skill folder>/scripts/validate_artifacts.py --artifact-dir .codex_workflow/delivery`. If it fails, either complete the missing panel/artifact work or report the failure honestly.
