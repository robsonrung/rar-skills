# Workflow contract

This skill is the unit of portability. It must be usable when copied into any `.agents/skills` location, together with the shared `shared/` directory it depends on for the panel scripts, the panel runner contract, and the engineering rules.

Principles

1. Keep the skill focused on one job.
2. Keep this skill's phase and role template, contracts, and references inside the skill folder. Model and effort values are resolved from `shared/model-routing.json`. The panel scripts (`shared/scripts/panel_round.py`, `record_native_response.py`, `validate_artifacts.py`) and the engineering rules (`shared/references/engineering-rules.md`) are shared, single-copy dependencies — do not re-bundle them per skill.
3. Treat any top level repository agent profile as optional optimization, never as a required dependency.
4. Use roles in instructions and routing. Read `shared/references/task-shaped-model-routing.md`, `shared/references/model-roster.md`, and `shared/references/host-model-execution.md` before binding a role to its exact model, effort, and execution path.
5. Run independent role rounds before reconciliation.
6. Preserve dissent in the decision log.
7. Record the anchor participation that the SKILL.md core rule requires for every phase.
8. Do not count prompt generation, handoff creation, or fallback output as the configured model participating.
9. Use an exact native model in an isolated persistent host role when the active host supports it. Use an external runner only for a foreign route or an approved native-route limitation. Runner routes use fallback disabled. Set `RUNNER_BASE_PATH` when the runner skills are not installed under `.agents/skills/`.
10. Record each native host response as an artifact before marking a phase complete.
11. Prefer `shared/scripts/record_native_response.py` for native host responses so the artifact and `panel_summary.json` stay synchronized.
12. Keep one context per task and role through later panel phases. Capture a runner session ID before a later phase, or record the native task context. Different roles and blind perspectives never share a context.

Delivery-specific obligations

1. The panel is not optional in this skill. Every one of the seven phases is a gate. The synthesis and adversarial anchors are required in all of them; `delivery_review` is required at intake, review, and handoff. Add `backend` or `interface` through a phase role override when that surface is material to the slice.
2. Code edits belong to the host session. Foreign runner roles review, challenge, and shape decisions unless the routing explicitly changes that.
3. Red, green, refactor is the execution shape. Do not record a green phase whose failing test was never observed failing for the expected reason.
4. Verification evidence is an artifact, not a claim: record commands, outputs, skipped checks, and the reason for each skip.

Routing file: `assets/routing.toml`

Primary output: `execution_log.md`

Artifact directory: `.ai-workflow/panel/delivery`
