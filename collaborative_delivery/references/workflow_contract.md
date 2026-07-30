# Workflow contract

This skill is the unit of portability. It must be usable when copied into any
`.agents/skills` location, together with the shared `_shared/` directory it
depends on for the panel scripts, the panel runner contract, and the engineering
rules.

Principles

1. Keep the skill focused on one job.
2. Keep this skill's routing, contracts, and references inside the skill folder. The panel scripts (`_shared/scripts/panel_round.py`, `record_native_response.py`, `validate_artifacts.py`) and the engineering rules (`_shared/references/engineering-rules.md`) are shared, single-copy dependencies — do not re-bundle them per skill.
3. Treat any top level repository agent profile as optional optimization, never as a required dependency.
4. Use roles in instructions and routing. Keep model names in editable config values only; the ids themselves come from `_shared/references/model-roster.md`.
5. Run independent role rounds before reconciliation.
6. Preserve dissent in the decision log.
7. Record the anchor participation that the SKILL.md core rule requires for every phase.
8. Do not count prompt generation, handoff creation, or fallback output as the configured model participating.
9. Use external runner wrappers with fallback disabled when a role is mapped to a local CLI model. Set `RUNNER_BASE_PATH` when the runner skills are not installed under `.agents/skills/`.
10. Record native Codex output as a response artifact before marking a phase complete.
11. Prefer `_shared/scripts/record_native_response.py` for native Codex responses so the artifact and `panel_summary.json` stay synchronized.

Delivery-specific obligations

1. The panel is not optional in this skill. Every one of the seven phases is a gate, and `delivery_review` is required in all of them.
2. Code edits belong to the host session. External roles review, challenge, and shape decisions unless the routing explicitly changes that.
3. Red, green, refactor is the execution shape. Do not record a green phase whose failing test was never observed failing for the expected reason.
4. Verification evidence is an artifact, not a claim: record commands, outputs, skipped checks, and the reason for each skip.

Routing file: `assets/routing.toml`

Primary output: `execution_log.md`

Artifact directory: `.codex_workflow/delivery`
