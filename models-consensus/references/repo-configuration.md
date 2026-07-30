# Repository Configuration

Consensus-specific configuration: where runner scripts live, which seats count as "core", where artifacts are written, and which local overrides apply. Adapt the paths if using this skill in another project.

## Seat → model mapping (not here)

The seat roster — every seat id, its transport, its requested alias, its current pinned model id, and the CLI it depends on — lives in **`_shared/references/model-roster.md`**, the single source of truth. Read it before building the seat table; never inline pinned model ids here, in SKILL.md, or in a command. When a provider ships a new model, the roster (and the runner script default it names) is the only place that changes.

Availability is never assumed: `_shared/scripts/discover_runners.py probe` reports `available`, `cli_path`, `version`, `blocked_reason`, and `depends_on` per seat, and that envelope *is* the seat table. A seat whose CLI is missing, whose credentials are absent, or whose cheap headless smoke test fails is a **blocker**, not a soft warning — drop the seat, lower confidence, say so. Per-seat auth and transport rules (Claude's `--bare` caveat, the `agy` model picker, `grok login`, the shared `cline` provider for Kimi/GLM, and the mandatory `--disable-fallback`) live in [runner-invocations.md](runner-invocations.md).

## Runner Base Path

In an installed deployment, all runner scripts live under:

```
.agents/skills/{runner-name}/scripts/run_{runner-name}.py
```

When running from the skills source repo itself, skills live at the repo root — drop the `.agents/skills/` prefix (e.g. `codex-runner/scripts/run_codex.py`). The same rule applies to schema paths passed via `--output-schema` (`models-consensus/schemas/…` from the source repo, `.agents/skills/models-consensus/schemas/…` when installed). When adapting this skill to another project, update the base path or set a `RUNNER_BASE_PATH` variable.

## Core Seats Definition

"Core seats" is the highest-diversity non-duplicate set available on the current host, and is the recommended startup choice in non-`--auto` runs (cost-conscious default, see [operations.md#cost-governance](operations.md#cost-governance)):

1. the native Codex seat (on a Codex host)
2. the native Claude seats (on a Claude Code host)
3. Gemini
4. Grok
5. Kimi
6. GLM

Prefer a native path over a runner script for any seat that has one. Two seats resolving to the same effective provider and model are **one** independent source — label the duplicate.

## Quorum

`poll` and `debate` need **≥ 3 distinct seats**. Below that, `poll` first tries labeled self-pairing to reach quorum; if the run still cannot reach 3 distinct seats, both modes degrade to `personas` on the strongest available model rather than running a thin table. The probe's `summary.light_quorum_met` / `quality_quorum_met` flags are advisory only — the mode rules above are normative.

## Artifact Directory

Persisted council artifacts (state, report, per-round seat outputs) write to:

```
.ai-workflow/consensus/
```

In this repo, `.ai-workflow/` is guaranteed writable, so runs default to `persisted`. When that directory is not writable, the run switches to `inline` and returns `report_path=null` / `state_path=null` ([operations.md#artifact-policy](operations.md#artifact-policy)).

## Local Overrides

Optional repo-local settings are read per `_shared/references/local-config.md`. The keys that affect this skill:

- `seats.preferred` / `seats.excluded` — seat ids to favor or never launch (ids per `discover_runners.py`). An excluded seat never appears in the startup picker and never counts toward quorum.
