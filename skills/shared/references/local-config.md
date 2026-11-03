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
| `profile` | Direct invocation previews | Central profile name, such as `saver`, `economy`, or `balanced`. A missing or invalid value uses the central default. This is a preference, not a duplicate model mapping. |
| `seats.preferred` / `seats.excluded` | Direct invocation previews, including models-consensus | Seat ids to propose or exclude before approval. Resolve them from `shared/model-routing.json`; use native capability checks or external CLI discovery for the selected execution path. |
| `route_overrides` | Direct invocation previews | Per-route role changes, keyed by route id then role: `route_overrides: {diagnosis: {worker: "grok:high"}}`. Validate every seat and effort against `shared/model-routing.json` exactly as `--role ROLE=SEAT[:EFFORT]` does; `runtime` selects null effort where supported. Invalid entries are ignored and reported once. Applied at preview time only; never changes an approved route. |

## Migration

`quorum`, `work_engine_preferences`, and `runner_base_path` are no longer read.
Remove them from local files. Legacy `models` entries are ignored and reported. Move maintained model or
effort settings to `shared/model-routing.json`. Explicit user selections belong
in the proposed plan, never a second default roster.

## Reading it

[model-preview.md](model-preview.md) shows how `profile` and `route_overrides` become `--local-profile` and `--role` arguments. Treat a file that fails to parse as no config and report it once. Say when a preference changed a proposed seat. After approval the saved plan controls dispatch; a preference never authorizes a substitution or a new call.

_Pattern adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
