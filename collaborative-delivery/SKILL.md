---
name: collaborative-delivery
description: >-
  Multi-model panel-gated delivery workflow with mandatory anchor review at every phase — the panel-audited alternative to `implement-and-review`'s default build. Use when an approved task plan exists and the user wants multi-model collaborative delivery: auditable red-green-refactor with recorded model participation left in the repository. Choose it over `implement-and-review` when the audit trail of who reviewed what is itself a requirement; choose `implement-and-review` when you want the fastest correct build.
disable-model-invocation: true
---

# Collaborative delivery

Execute approved tasks through red green refactor loops with real multi-model collaboration, review gates, and verification evidence.

Shared scaffolding (inputs, routing and configurability, local panel runner and flags, native response helper, panel status taxonomy, completion gate) lives in `../_shared/collaborative-panel-runner.md`. Read it before running any panel phase. This file keeps only what is specific to delivery.

The panel scripts are shared, not bundled here: they live in `_shared/scripts/` and read this skill's routing file. Because that file is at the default `assets/routing.toml` location, `--routing` is optional for this skill — pass it anyway when running from outside the skill's own directory:

```bash
python3 _shared/scripts/panel_round.py \
  --phase <phase> \
  --routing collaborative-delivery/assets/routing.toml \
  --goal "the task being delivered" \
  --context-file <task-file> \
  --out .codex_workflow/delivery \
  --fail-on-incomplete
```

Record native responses with `_shared/scripts/record_native_response.py` and run the completion gate with `_shared/scripts/validate_artifacts.py`, both with the same `--routing` value.

## Roles

Delivery uses the role names `synthesis_anchor`, `adversarial_anchor`, `implementation`, `interface`, `backend`, `testing`, `review`, `simplification`, and `delivery_review`. The mapping to models is editable in `assets/routing.toml`.

`delivery_review` reviews delivery risk, sequencing, hidden coupling, rollout impact, and whether the current slice remains safe to ship. It is listed in all seven phases in `assets/routing.toml`, so it is required in every one of them.

## Phases

Run the configured panel phases as gates in order: `task_intake`, `red`, `green`, `refactor`, `review`, `verification`, and `handoff` (the same list enforced by `[skill].required_phases` in `assets/routing.toml`). Artifacts and prompts live under `.codex_workflow/delivery`.

## Workflow

Use this skill to implement approved tasks in controlled loops. It must keep tests, review, and architecture visible throughout the work.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete (see the shared Core rule). For interface implementation, the interface role and adversarial anchor jointly define and review the interface contract. For backend implementation, the backend role and synthesis anchor jointly define and implement the backend path. If a specialist role is not relevant to the current implementation slice, it still participates and states why it has no material concern.

### Steps

1. Choose exactly one task unless the task plan explicitly says a group is safe to parallelize.
2. Restate the task, acceptance criteria, expected files, and tests to write first.
3. Run the configured panel phases as gates: `task_intake`, `red`, `green`, `refactor`, `review`, `verification`, and `handoff`. The Codex host owns code edits; external roles review, challenge, and shape decisions unless the routing explicitly changes that.
4. Red phase. Read `../_shared/references/engineering-rules.md` before starting the red, green, and refactor phases. Add or update the failing test first. Run the narrowest command that proves the test fails for the expected reason.
5. Green phase. Implement the smallest code change to pass the test while preserving clean architecture and domain boundaries.
6. Refactor phase. Simplify only while tests are green. Do not change behavior silently.
7. Review phase. Use the review role, plus required anchors, to inspect the diff for correctness, security, maintainability, performance, accessibility, data safety, and consistency with the task plan.
8. Verification phase. Run targeted tests, then broader checks when warranted. Record commands, outputs, skipped checks, and reasons.
9. Handoff phase. Summarize changed files, behavior changes, tests, known limitations, and next recommended task.

### Quality bar

A delivery is complete only when the diff is reviewed, verification evidence is recorded, and every accepted exception is explicit. If tests cannot run, explain why and provide the best available static or manual verification.

Do not combine unrelated tasks. Do not bypass red, green, refactor for production changes unless the user explicitly asks and the risk is documented.

## Required outputs

Read `references/output_contract.md` before writing any phase artifact or interpreting `panel_summary.json` statuses. It defines the per-phase presence audit, the full panel-status semantics, and external transcript handling.

Create these files under `.codex_workflow/delivery` unless the user asks for another path:

1. `execution_log.md`
2. `test_evidence.md`
3. `review_notes.md`
4. `changed_files.md`
5. `decision_log.md`
6. `panel_summary.json`

This list matches `[skill].required_outputs` in `assets/routing.toml`, which is what `_shared/scripts/validate_artifacts.py` enforces.
