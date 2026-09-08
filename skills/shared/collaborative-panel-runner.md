# Collaborative panel runner (shared scaffolding)

This file is the single source for the multi-model **panel** scaffolding: the routing contract, the panel scripts, the status taxonomy, and the completion gate. Each panel-capable skill keeps only its own description, purpose, phase list, role list, and required outputs, and points here for everything below.

## Caller

`collaborative-delivery` uses this engine when the user explicitly requests its panel workflow. Its routing file is `assets/routing.toml` in that skill and its artifacts live under `.ai-workflow/panel/delivery`.

The standard `brainstorm`, `to-prd`, and `to-tasks` workflows do not run panels. Additional opinions go through an explicitly requested `models-consensus` run, which owns its model approval and council protocol.

Before any panel dispatch, the caller shows all roles, resolved model IDs, effort levels, and scope for approval. Reuse an unchanged approved plan; changes require approval. The panel engine is not a substitute for that gate.

## Inputs

1. User goal or task prompt.
2. Relevant repository context, linked files, previous workflow artifacts, or an explicit statement that none exist.
3. Constraints around security, permissions, architecture, data, user experience, delivery timeline, and verification.

## Routing and configurability

The caller owns its routing file; the default model mapping is editable there. Model ids come from `shared/references/model-roster.md` — when a provider ships a new model, update the roster and the routing files that name it.

Do not hardcode model choices in the workflow. Use the role names the calling skill declares (always including `synthesis_anchor` and `adversarial_anchor`). Resolve the mapping with the shared task-shaped routing reference, then bind the actual role/model/effort assignments to the user-approved plan. Read [host-model-execution.md](references/host-model-execution.md) before selecting a native or runner transport.

Read `shared/references/task-shaped-model-routing.md` before changing a model assignment. It defines the shared task categories, prompt shape, effort policy, and evaluation contract.

Every configured phase must run through `shared/scripts/panel_round.py` unless the user explicitly disables model collaboration. A phase is complete only when every required role has status `ok` or `native_response_recorded` in `panel_summary.json`. A generated native prompt is not participation; the host-native response must be recorded under the skill's artifact directory at `native_responses/<phase>_<role>.md` or passed with `--native-response`. If a specialist role is not relevant to the current work item, it still participates and states why it has no material concern.

### Core rule

Every phase must include the synthesis anchor and the adversarial anchor, and every role listed for that phase must produce a real response before the phase is complete. These are role requirements, not model names; change the mapping in the skill's routing file when you want different models. Phase-specific anchor pairings (for example interface + adversarial, or backend + synthesis) are stated in the calling skill's own steps.

## Local panel runner

The three panel scripts are shared, not per-skill: they live in `shared/scripts/` and are pointed at a skill's routing file with `--routing`. External roles run through the repo-local runner skills with fallback disabled, so a missing model cannot be silently replaced by another provider. Native roles use the active host's allowed delegation mechanism and are recorded as response artifacts after real execution.

Set `kind = "native"` for host-native roles. The legacy `kind = "native_codex"` value remains accepted for existing routing files. A pending native result includes `native_handoff` metadata for host, provider, transport, requested model, requested effort, and effort control. The host performs the call, chooses a persistent subagent or task context when available, and records the response. Prompt generation and configured metadata do not prove the serving model.

A routing file does not prove that the active host exposes a native seat. Before dispatch, bind the approved route to the active host. When that exact model is native, use `kind = "native"`; when it is foreign or the host lacks the required control, use the approved runner route. A failed native route does not authorize an automatic runner switch.

Run one panel phase (replace `<phase>`, `<routing-file>`, `<artifact-dir>`, and goal/context with the calling skill's values):

```bash
SHARED_DIR="<absolute directory of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/panel_round.py" \
  --phase <phase> \
  --routing <routing-file> \
  --goal "describe the current goal" \
  --context-file path/to/context.md \
  --out <artifact-dir> \
  --fail-on-incomplete
```

`panel_round.py` flags:

- `--phase` (required) — the phase name from the routing file.
- `--goal` (required) — short statement of the current goal.
- `--routing` — path to the skill's routing TOML. Defaults to `<skill_root>/assets/routing.toml`; pass an explicit absolute path when invoking from a project directory. The calling skill's root is taken to be the routing file's grandparent directory.
- `--context-file` — repeatable; one or more context files to feed the panel.
- `--out` — artifact directory (defaults to the routing file's `artifact_dir`).
- `--working-dir` — working directory (defaults to the current directory).
- `--dry-run` — checks the command shape only. Use it ONLY after changing routing; dry runs do not count as model participation and produce `dry_run` status.
- `--roles` — comma-separated role override for this phase. The mandatory anchor roles (`mandatory_presence` in the routing file) are always added back at the front, so a role override cannot drop the required anchors.
- `--native-response ROLE=PATH` — repeatable; supply a native role's response inline instead of recording it separately.
- `--role-session ROLE=SESSION` — repeatable; bind one recorded same-task role session or native context to that role only. Duplicate session values across roles are rejected.
- `--fail-on-incomplete` — makes the per-phase gate deterministic: the script exits with code `2` when any required role is missing, pending, or failed, instead of relying on parsing `panel_summary.json`.

For iterative runner roles, the host records the returned `session_id` and passes it back only through `--role-session`. Claude, Codex, and Grok receive `--resume`. For Pi, the host allocates a durable session path and passes it through `--role-session` on the first and later calls; Pi receives `--session`. The panel never selects a latest session and rejects unsupported runner resumes, shared provider session arguments, and duplicate role bindings. A native `--role-session` value is written to `native_handoff.context_id` for the host to resume its own role context. That context identifier is not a serving-model receipt.

### Runner-script resolution and `RUNNER_BASE_PATH`

Each runner-backed provider names a wrapper script. `panel_round.py` resolves it through this chain and uses the first path that exists:

1. the explicit `script` path in the routing file;
2. that path's `<runner-skill>/scripts/run_<x>.py` tail under `$RUNNER_BASE_PATH`;
3. `.agents/skills/<runner-skill>/scripts/run_<x>.py` — the default install layout;
4. the collection-root sibling `<runner-skill>/scripts/run_<x>.py`, resolved relative to this directory's parent — which is how a source checkout resolves.

Set `RUNNER_BASE_PATH` when the runner skills are installed somewhere other than `.agents/skills/`. The tail is derived from the configured `script` value, or rebuilt from the provider's `runner` key when `script` is omitted, so a routing file may drop `script` entirely and rely on `runner = "claude"` alone. A wrapper that cannot be found yields `runner_unavailable`, never a silent substitution.

### Native response helper

For each native role, read the generated prompt in `<artifact-dir>/prompts/`, produce the native response, then record it:

```bash
SHARED_DIR="<absolute directory of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/record_native_response.py" \
  --phase <phase> \
  --routing <routing-file> \
  --role <native-role> \
  --from-file .ai-workflow/panel/native-response.md
```

The helper also accepts response text on stdin. It writes `<artifact-dir>/native_responses/<phase>_<role>.md`, refuses to overwrite an existing non-empty response unless `--replace` is passed, and updates the matching entry in `panel_summary.json` when a panel run exists.

## Panel status taxonomy

A phase is complete only when every required role is `ok` or `native_response_recorded`. Any other status blocks the phase. The full semantics live in each skill's `references/output_contract.md` where one exists; the blocking statuses are:

- `ok` — the role actually executed and produced a response (completing).
- `native_response_recorded` — a native role's response artifact was recorded (completing).
- `prompt_only` / `awaiting_native_execution` — the native prompt exists but the native model has not participated yet.
- `dry_run` — the command shape was checked only; not participation.
- `fallback_used` — independence was lost; do not count it as the configured model.
- `session_resume_unsupported`, `shared_session_argument`, `session_policy_conflict` — block completion because the requested role context could not be resumed safely.
- `error`, `exception`, `runner_unavailable`, `missing_provider`, `disabled` — block phase completion. If the user explicitly accepts the gap, report it as an accepted exception rather than claiming a complete model panel.

A generated native prompt or handoff file is never enough by itself.

## Completion gate

Before finalizing, run:

```bash
SHARED_DIR="<absolute directory of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/validate_artifacts.py" \
  --routing <routing-file> \
  --artifact-dir <artifact-dir>
```

If it fails, either complete the missing panel/artifact work or report the failure honestly. For a partial in-progress run, `validate_artifacts.py` accepts `--allow-missing-phases` to validate only the required files.

## Engineering rules

`shared/references/engineering-rules.md` holds the spec-driven development, domain-driven design, clean architecture, and test-driven development rules the panel phases apply. It is one shared copy; the skills that gate a phase on it say so in their own steps.
