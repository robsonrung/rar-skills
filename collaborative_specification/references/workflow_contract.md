# Workflow contract

This skill is the unit of portability. It must be usable when copied by itself into any `.agents/skills` location.

Principles

1. Keep the skill focused on one job.
2. Keep all default routing, scripts, contracts, and references inside the skill folder.
3. Treat any top level repository agent profile as optional optimization, never as a required dependency.
4. Use roles in instructions and routing. Keep model names in editable config values only.
5. Run independent role rounds before reconciliation.
6. Preserve dissent in the decision log.
7. Record the mandatory anchor participation for every phase.
8. Do not count prompt generation, handoff creation, or fallback output as the configured model participating; record native Codex output as a response artifact (prefer `scripts/record_native_response.py`, which keeps the artifact and `panel_summary.json` synchronized) before marking a phase complete. The authoritative panel status rules live in `references/output_contract.md`.
9. Use external runner wrappers with fallback disabled when a role is mapped to a local CLI model. Providers may alternatively use `kind = "cli"` with `command`, `args`, and optional `prompt_transport = "stdin"` in `assets/routing.toml` for direct CLI invocation without a runner wrapper; no default provider uses this path.

Primary output: `prd.md`. The artifact directory and full required-output list live under `[skill]` in `assets/routing.toml` (mirrored in SKILL.md's Required outputs section).
