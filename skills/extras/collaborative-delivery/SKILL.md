---
name: collaborative-delivery
description: Deliver an approved task through an auditable multi-model panel with test, review, and verification evidence. Use when the user requires a recorded panel trail for implementation. For the normal fast path, use implement-and-review or implement-tasks.
disable-model-invocation: true
---

# Collaborative Delivery

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Use this only after an approved task plan exists and a panel audit trail is required. It is intentionally more expensive than the normal implementation path. The panel is mandatory once this skill is chosen.

Read `shared/collaborative-panel-runner.md` and
`shared/references/host-model-execution.md` before starting. They define the
panel runner, real-participation rule, status taxonomy, completion check, native
delegation, and session rules. `assets/routing.toml` is an editable default for
one host. Before any role starts, bind it to the approved route described in
`shared/references/task-shaped-model-routing.md`. Show its exact model,
execution path, effort, and verification policy to the user. A configured model
label is not a serving-model receipt.

## Outcome

Deliver one task with a recorded red, green, refactor, review, verification, and handoff trail. A phase is complete only when its required roles have real recorded responses. A generated prompt is not participation.

## Workflow

1. Select one task and restate its acceptance contract, expected files, and narrowest verification command.
2. Run the phases in order: `task_intake`, `red`, `green`, `refactor`, `review`, `verification`, and `handoff`. Keep one isolated context per task and role across those phases. An implementer, reviewer, synthesizer, and adversarial role never share a context.
3. Every phase includes the synthesis and adversarial anchors. The configured specialist roles add their independent response. Add `backend` or `interface` as a phase role only when the current slice touches that surface.
4. In `red`, add or update the failing test and record the expected failure. In `green`, make the smallest change that passes it. In `refactor`, simplify only while tests stay green.
5. In `review`, inspect correctness, data and security risk, maintainability, and fit with the task. In `verification`, record commands, results, skipped checks, and reasons.
6. In `handoff`, record changed files, behavior, evidence, decisions, limitations, and the next task.

For an exact model available through the active host, use a persistent native
subagent or supported task context. Use a runner only for a foreign model or an
exact route the host cannot provide. The host owns code changes. Panel roles
challenge, review, and shape decisions unless the routing explicitly delegates
an implementation role. Preserve dissent in the decision log. A missing role
blocks a complete panel; report the gap as an accepted exception only when the
user explicitly accepts it.

## Artifacts

Write these files under `.ai-workflow/panel/delivery` unless the user selects another location:

1. `execution_log.md`
2. `test_evidence.md`
3. `review_notes.md`
4. `changed_files.md`
5. `decision_log.md`
6. `panel_summary.json`

Read [references/output_contract.md](references/output_contract.md) before interpreting panel status or finalizing. Read [references/workflow_contract.md](references/workflow_contract.md) before changing the routing or portability boundary.
