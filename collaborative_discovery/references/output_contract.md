# Output contract

Required artifacts

1. `discovery_brief.md`
2. `option_map.md`
3. `open_questions.md`
4. `decision_log.md`
5. `panel_summary.json`

Presence audit

Each phase artifact must include:

1. Phase name.
2. Roles consulted.
3. Synthesis anchor contribution.
4. Adversarial anchor contribution.
5. Other role contributions.
6. Disagreements and resolution.
7. Decision status.
8. Verification or next action.

Panel status rules

1. `ok` means the role actually executed and produced a response.
2. `awaiting_native_execution` means the native prompt exists but the native model has not participated yet.
3. `dry_run` means the command shape was checked only; it is not participation.
4. `fallback_used` means independence was lost; do not count it as the configured model.
5. `error`, `exception`, `runner_unavailable`, `missing_provider`, and `disabled` block phase completion. If the user explicitly accepts the gap, report it as an accepted exception instead of claiming a complete model panel.
6. A generated native prompt or handoff file is never enough by itself. Native roles need a non-empty response under `native_responses/` or a path passed with `--native-response`.

Native response helper

Use `scripts/record_native_response.py` after a native Codex role has produced its response. The helper writes the response to `native_responses/<phase>_<role>.md`, refuses to overwrite existing non-empty responses unless `--replace` is passed, and updates the matching `panel_summary.json` result when that phase run exists.

External transcript handling

1. Store raw CLI outputs in the artifact directory when available.
2. Summarize them in human readable Markdown.
3. Do not paste secrets into prompts.
4. If a CLI fails, record the command preview, exit status, and fallback decision.
5. Runner-backed roles must use fallback-disabled wrappers so a missing model cannot be credited to another provider.
