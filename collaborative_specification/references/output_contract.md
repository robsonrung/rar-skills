# Output contract

Required artifacts: see `required_outputs` in `assets/routing.toml` (the list `validate_artifacts.py` enforces, mirrored in SKILL.md's Required outputs section).

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

1. `ok` means the role actually executed and produced a response. `native_response_recorded` means a native role's response was recorded after the run. These are the only statuses that count toward phase completion.
2. `awaiting_native_execution` means the native prompt exists but the native model has not participated yet; the entry carries participation `prompt_only`.
3. `dry_run` means the command shape was checked only; it is not participation.
4. `fallback_used` means independence was lost; do not count it as the configured model.
5. `error`, `exception`, `runner_unavailable`, `missing_runner_script`, `missing_provider`, and `disabled` block phase completion. If the user explicitly accepts the gap, report it as an accepted exception instead of claiming a complete model panel.
6. A generated native prompt or handoff file is never enough by itself. Native roles need a non-empty response recorded in `native_responses/<phase>_<role>.md` or a path passed with `--native-response`.

Native response helper

Use `scripts/record_native_response.py` after a native Codex role has produced its response. The helper writes the response to `native_responses/<phase>_<role>.md`, refuses to overwrite existing non-empty responses unless `--replace` is passed, and updates the matching `panel_summary.json` result when that phase run exists.

External transcript handling

1. Store raw CLI outputs in the artifact directory when available.
2. Summarize them in human readable Markdown.
3. Do not paste secrets into prompts.
4. If a CLI fails, record the command preview, exit status, and fallback decision.
5. Runner-backed roles must use fallback-disabled wrappers so a missing model cannot be credited to another provider.
