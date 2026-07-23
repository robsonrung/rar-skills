# Local config: `.rar-skills/config.local.yaml`

Per-checkout, user-local preferences for multi-model skills (councils, roundtables, review panels, implementation pipelines). Committed example: `.rar-skills/config.local.example.yaml`. The real file is gitignored.

## Contract

- **Every key is optional.** A missing file, missing key, or invalid value falls through to the skill's built-in default — never an error.
- **Never credentials.** Auth stays with each CLI's own login; this file carries preferences only. Raw CLI flags don't belong here either.
- **Chat wins.** A direct instruction in the conversation ("use only codex and gemini") overrides anything in this file for that run.
- **One home.** Seat preference/exclusion tables previously duplicated across skill references belong here; skills read this file instead of maintaining their own copies.

## Keys

| Key | Consumed by | Meaning |
|---|---|---|
| `seats.preferred` / `seats.excluded` | council, models-consensus, models-roundtable, full-review, diverse-plan | Seat ids to favor / never launch (ids per `discover_runners.py`). |
| `models.<seat>` | runner-backed seats | Per-seat model override forwarded to the runner's `--model` when supported. |
| `quorum.light` / `quorum.quality` | seat-discovery consumers | Advisory quorum thresholds (defaults 2 / 3). |
| `work_engine_preferences` | implement-and-review, implement-feature, ship | Ordered harness+model candidates with `mode: off\|prefer\|require` and `skip_if_equivalent_to_host`. |
| `runner_base_path` | any skill invoking runner scripts from another checkout | Overrides the default repo-root-relative runner script location. |

## Reading it

Skills should treat parsing failures as "no config" (log one line, continue with defaults) and must state in their output when a config value changed seat selection, so the user can see why a seat was skipped.

*Pattern adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
