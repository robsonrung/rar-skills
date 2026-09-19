# Local config: `.rar-skills/config.local.yaml`

Per-checkout, user-local preferences for model previews. Committed example:
`.rar-skills/config.local.example.yaml`. The real file is gitignored.

## Contract

- **Every key is optional.** A missing file, missing key, or invalid value uses the central routing recommendation before approval. It cannot change an approved route.
- **Never credentials.** Auth stays with each CLI's own login; this file carries preferences only. Raw CLI flags don't belong here either.
- **Chat wins.** A direct instruction in the conversation ("use only codex and gemini") overrides anything in this file for that run.
- **Preview only.** Read this file while forming an implementation or council preview. Do not read it again for dispatch, fallback, retry, or resume.

## Keys

| Key | Consumed by | Meaning |
| --- | --- | --- |
| `seats.preferred` / `seats.excluded` | implement-tasks, models-consensus | Seat ids to propose or exclude before approval. Resolve them from `shared/model-routing.json`; use native capability checks or external CLI discovery for the selected execution path. |

## Migration

`quorum`, `work_engine_preferences`, and `runner_base_path` are no longer read.
Remove them from local files. Legacy `models` entries are ignored and reported. Move maintained model or
effort settings to `shared/model-routing.json`. Explicit user selections belong
in the proposed run snapshot, never a second default roster.

## Cline lanes

Concurrent Cline lanes deliberately do **not** live in this YAML. The built-in `kimi` and `glm` lane names remain provisionable for direct `cline-runner` use (authenticate isolated state under `~/.cline/lanes/<name>`, then pass `--lane <name>`), though the Kimi and GLM seat shims themselves now route through `pi-runner` on OpenRouter and need no lanes. For a custom lane, pass its JSON directly with `--lane-file`; it contains absolute local state paths and pool limits but never credentials. Use `cline-runner/references/cline-lanes.example.json` as the schema.

## Reading it

Skills should treat parsing failures as "no config" and report the ignored file
once. State when a preference changes the proposed seat. After approval,
the saved routing plan controls dispatch; local preferences never authorize a
substitution or a new call.

_Pattern adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
