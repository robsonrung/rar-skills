# Collaborative panel runner (shared scaffolding)

This file is the single source for the scaffolding shared by the staged
`collaborative_*` pipeline (`collaborative_discovery` → `collaborative_specification`
→ `collaborative_task_design` → `collaborative_delivery`). Each stage skill keeps
only its own description, purpose, phase list, role list, and required outputs, and
points here for everything below.

Throughout, `<skill_root>` is the calling skill's own install directory. The bundled
scripts self-locate their routing from that directory, so any install path works.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

Each collaborative skill is self contained. Its routing file is `assets/routing.toml`
inside that skill's folder; the default model mapping is editable there. Read the
skill's `references/workflow_contract.md` when porting or reconfiguring it.

Do not hardcode model choices in the workflow. Use the role names the calling skill
declares (always including `synthesis_anchor` and `adversarial_anchor`). The default
routing maps the native OpenAI seat to the synthesis anchor and Anthropic to the
adversarial anchor, with other seats (such as Gemini and Kimi) assigned to specialist
roles, but the mapping is editable in `assets/routing.toml`.

Every configured phase must run through `scripts/panel_round.py` unless the user
explicitly disables model collaboration. A phase is complete only when every required
role has status `ok` or `native_response_recorded` in `panel_summary.json`. A generated
native prompt is not participation; the native Codex response must be recorded under the
skill's artifact directory at `native_responses/<phase>_<role>.md` or passed with
`--native-response`. If a specialist role is not relevant to the current work item, it
still participates and states why it has no material concern.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role
listed for that phase must produce a real response before the phase is complete. These
are role requirements, not model names; change the mapping in `assets/routing.toml` when
you want different models. Phase-specific anchor pairings (for example interface +
adversarial, or backend + synthesis) are stated in the calling skill's own steps.

## Local panel runner

Use the local runner for each model-panel phase. External roles run through the
repo-local runner skills with fallback disabled, so a missing model cannot be silently
replaced by another provider. Native Codex roles stay native, but must be executed by
the host agent or an allowed native Codex subagent and then recorded as a response
artifact.

Run one panel phase (replace `<phase>`, `<artifact-dir>`, and goal/context with the
calling skill's values):

```bash
python3 <skill_root>/scripts/panel_round.py \
  --phase <phase> \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out <artifact-dir> \
  --fail-on-incomplete
```

`panel_round.py` flags (all verified present and identical across the four
collaborative skills' bundled scripts):

- `--phase` (required) — the phase name from `assets/routing.toml`.
- `--goal` (required) — short statement of the current goal.
- `--context-file` — repeatable; one or more context files to feed the panel.
- `--out` — artifact directory (defaults to the skill's configured `artifact_dir`).
- `--working-dir` — working directory (defaults to the current directory).
- `--dry-run` — checks the command shape only. Use it ONLY after changing routing;
  dry runs do not count as model participation and produce `dry_run` status.
- `--roles` — comma-separated role override for this phase. The mandatory anchor roles
  (`mandatory_presence` in `assets/routing.toml`) are always added back at the front,
  so a role override cannot drop the required anchors.
- `--native-response ROLE=PATH` — repeatable; supply a native role's response inline
  instead of recording it separately.
- `--fail-on-incomplete` — makes the per-phase gate deterministic: the script exits with
  code `2` when any required role is missing, pending, or failed, instead of relying on
  parsing `panel_summary.json`.

### Native response helper

For each native role, read the generated prompt in `<artifact-dir>/prompts/`, produce
the native response, then record it:

```bash
python3 <skill_root>/scripts/record_native_response.py \
  --phase <phase> \
  --role synthesis_anchor \
  --from-file /tmp/native-response.md
```

The helper also accepts response text on stdin. It writes
`<artifact-dir>/native_responses/<phase>_<role>.md`, refuses to overwrite an existing
non-empty response unless `--replace` is passed, and updates the matching entry in
`panel_summary.json` when a panel run exists.

## Panel status taxonomy

A phase is complete only when every required role is `ok` or `native_response_recorded`.
Any other status blocks the phase. The full semantics live in each skill's
`references/output_contract.md`; the blocking statuses are:

- `ok` — the role actually executed and produced a response (completing).
- `native_response_recorded` — a native role's response artifact was recorded (completing).
- `prompt_only` / `awaiting_native_execution` — the native prompt exists but the native
  model has not participated yet.
- `dry_run` — the command shape was checked only; not participation.
- `fallback_used` — independence was lost; do not count it as the configured model.
- `error`, `exception`, `runner_unavailable`, `missing_provider`, `disabled` — block phase
  completion. If the user explicitly accepts the gap, report it as an accepted exception
  rather than claiming a complete model panel.

A generated native prompt or handoff file is never enough on its own.

## Completion gate

Before finalizing, run:

```bash
python3 <skill_root>/scripts/validate_artifacts.py --artifact-dir <artifact-dir>
```

If it fails, either complete the missing panel/artifact work or report the failure
honestly. For a partial in-progress run, `validate_artifacts.py` accepts
`--allow-missing-phases` to validate only the required files.
