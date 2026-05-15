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
8. Do not count prompt generation, handoff creation, or fallback output as the configured model participating.
9. Use external runner wrappers with fallback disabled when a role is mapped to a local CLI model.
10. Record native Codex output as a response artifact before marking a phase complete.
11. Prefer `scripts/record_native_response.py` for native Codex responses so the artifact and `panel_summary.json` stay synchronized.

Primary output: `discovery_brief.md`

Artifact directory: `.codex_workflow/discovery`
