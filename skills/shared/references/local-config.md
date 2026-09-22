# Local config: `.rar-skills/config.local.yaml`

Per-checkout, user-local preferences for model previews. Committed example:
`.rar-skills/config.local.example.yaml`. The real file is gitignored.

## Contract

- **Every key is optional.** A missing file, missing key, or invalid value uses the central routing recommendation before approval. It cannot change an approved route.
- **Never credentials.** Auth stays with each CLI's own login; this file carries preferences only. Raw CLI flags don't belong here either.
- **Chat wins.** A direct instruction in the conversation ("use only codex and gemini") overrides anything in this file for that run.
- **Preview only.** Read this file while forming a direct invocation preview through [model-preview.md](model-preview.md). Nested skills reuse the parent selection. Do not read it again for dispatch, fallback, retry, or resume.

## Keys

| Key | Consumed by | Meaning |
| --- | --- | --- |
| `profile` | Direct invocation previews | Central profile name, such as `economy` or `balanced`. A missing or invalid value uses the central default. This is a preference, not a duplicate model mapping. |
| `seats.preferred` / `seats.excluded` | Direct invocation previews, including models-consensus | Seat ids to propose or exclude before approval. Resolve them from `shared/model-routing.json`; use native capability checks or external CLI discovery for the selected execution path. |

## Migration

`quorum`, `work_engine_preferences`, and `runner_base_path` are no longer read.
Remove them from local files. Legacy `models` entries are ignored and reported. Move maintained model or
effort settings to `shared/model-routing.json`. Explicit user selections belong
in the proposed run snapshot, never a second default roster.

## Reading it

Use `model_routing.py resolve <route> --profile default`. Add
`--local-profile <name>` for a validated local `profile`; otherwise the configured
central default applies. An explicit user `--profile economy` or `balanced`
wins over the local preference. Pass per role changes through
`--role ROLE=SEAT[:EFFORT]`; `runtime` selects null effort where supported.
A bare legacy resolver call does not select the new workflow profile.

Skills should treat parsing failures as "no config" and report the ignored file
once. State when a preference changes the proposed seat. After approval,
the saved routing plan controls dispatch; local preferences never authorize a
substitution or a new call. An explicit user change creates a replacement snapshot
for unresolved work only. Completed evidence retains its original selection.

_Pattern adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
