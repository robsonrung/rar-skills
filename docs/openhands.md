# Running the pipeline on OpenHands

How to run the full delivery relay from [pipeline.html](pipeline.html) — brainstorm → interview-me → to-prd → to-tasks → approval gate → design-gate → implement-and-review → verify → open-pr — on OpenHands instead of Claude Code, with a live kanban of every run.

OpenHands (v1.x: the `openhands` CLI plus `openhands-sdk`) loads Agent Skills in exactly the format this repo uses — `SKILL.md` with `name`/`description` frontmatter, discovered from `.agents/skills/` in the project and `~/.agents/skills/` for the user, with progressive disclosure. Skills invoke each other by name in prose, run state is plain JSON, the runner skills wrap CLIs, and `open-pr` needs only `gh` — so the collection ports without rewrites.

**Two ways to supply the model**, and the choice changes the setup:

|  | Who runs the model | Billing |
| --- | --- | --- |
| **[CLI-only](#cli-only-no-api-keys)** (default here) | a CLI you already have — Claude Code or Codex — spawned over ACP | your CLI subscription; no API key anywhere |
| [Direct API](#alternative-direct-api) | OpenHands calls the provider itself via LiteLLM | metered `LLM_API_KEY` |

## 1. Install

```bash
uv tool install openhands --python 3.12
```

Install the skills into the target project (symlinks by default, `--copy` for self-contained):

```bash
scripts/install-skills.sh /path/to/your-project
```

This writes **both** skill layouts, because under CLI-only mode the CLI — not OpenHands — is what discovers skills:

- `.agents/skills/` — read by OpenHands' own agent and by the Codex CLI.
- `.claude/skills/` — read by the Claude Code CLI.

Each skill is linked individually and `shared/` ships alongside them, matching the `.agents/skills/shared/...` convention the skills already document. Use `--layout agents` or `--layout claude` to write just one.

> Do not shortcut this by symlinking the `skills` directory itself. Claude Code does not follow a symlinked skills root — it silently reports zero project skills. The installer links each skill separately for exactly this reason.

A root `AGENTS.md` or `CLAUDE.md` in the target repo is picked up automatically as repo context.

Verify discovery — OpenHands: run `openhands` in the target repo and type `/skills`. Claude CLI: `claude -p "list your available skills"` from the target repo.

Verified on 2026-07-31 against `openhands` 1.16.0 (which bundles `openhands-sdk` 1.21.0), standalone `openhands-sdk` 1.39.1, Claude Code 2.1.220, and the ACP adapter `@agentclientprotocol/claude-agent-acp` 0.64.0:

- `load_project_skills()` returns all 56 with no load failures, no truncation, and no phantom always-on skills, in both symlink and `--copy` mode.
- A live API-mode headless run shows every pipeline station in the runtime `<available_skills>` block with full descriptions.
- A live **CLI-only** ACP run with `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`/`LLM_API_KEY` removed from the environment reaches the Claude Code CLI, reports `interview=Y to_tasks=Y design_gate=Y full_review=Y browser_smoke=Y`, and read the then-current ship conductor correctly (since retired in favor of implement-tasks; its phase 4 → `implement-and-review`). OpenHands metered $0.00 for it — the CLI subscription carried the run.

Two things the port had to fix, both now guarded by `skills/shared/scripts/validate_skill_frontmatter.py`:

- **Frontmatter must be strict YAML.** Claude Code tolerated unquoted descriptions containing `": "`; OpenHands parses with PyYAML and silently drops those skills (five of them, including `implement-and-review`). They now use `>-` block scalars. Skill names must also be lowercase-with-hyphens — `collaborative_delivery` was renamed `collaborative-delivery`.
- **Descriptions are truncated at 1024 characters.** Seven skills exceeded it, so the "Use when … / Do not use …" tail that routing depends on was being cut. All seven were shortened — provenance and redundant prose came out, every trigger phrase and `Distinct from …` clause stayed — and the validator now warns if a description grows back over the limit.

`shared/SKILL.md` is a marker, not a skill. Without it, every file under `shared/references/` loads as an always-on legacy skill — roughly 32 KB pinned into the system prompt on every request. The marker makes hosts treat the directory as one unit and skip the tree.

## 2. CLI-only (no API keys)

The `openhands` CLI always calls a provider API directly — its own `acp` subcommand is the _reverse_ direction (OpenHands serving as an ACP agent to Zed/Toad), so there is no flag that makes it consume a CLI. Driving a CLI as the agent needs the SDK, which is what [`scripts/run-pipeline-acp.py`](../scripts/run-pipeline-acp.py) wraps:

```bash
scripts/run-pipeline-acp.py /path/to/your-project \
  -t "Read .claude/skills/interview-me/SKILL.md and follow it for: <feature idea>"
```

It spawns the CLI over ACP (`npx @agentclientprotocol/claude-agent-acp`, or `--agent codex` for `@zed-industries/codex-acp`), and the CLI brings its own model and subscription auth. The launcher strips `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `LLM_API_KEY` from the environment before starting, so a stray key cannot quietly turn the run into a metered one; pass `--keep-api-keys` to opt out. Conversations persist under `.ai-workflow/openhands/`, and the script prints a `--resume <id>` line for long runs.

**Invoke entry-point skills by file path, not by name.** A skill carrying `disable-model-invocation: true` (for example `resolve-pr-feedback`) is user-invocable only and never appears in the model's own skill list — asking the agent to "use the X skill" finds nothing. Telling it to read `.claude/skills/<name>/SKILL.md` works and is equivalent. Of the workflow steps, only `to-tasks` is model-invocable (`implement-tasks` calls it to decompose a bare plan); `brainstorm`, `interview-me`, `to-prd`, and `implement-tasks` are entry points, so name them by file path in a task prompt as shown above.

What you give up under ACP: the external CLI owns its tools and model, so OpenHands' custom tools, MCP configuration, condensers, and critics do not apply. That matters in one place in this pipeline — `browser-smoke` expects a browser MCP, so under ACP it falls back to whatever browser tooling the CLI itself provides. Sandbox-level features (`.openhands/setup.sh`, hooks) are unaffected.

## 3. The interactive half (steps 1–3)

Run these where you can answer, since the approval gate is here:

```bash
scripts/run-pipeline-acp.py /path/to/your-project \
  -t "Read .claude/skills/interview-me/SKILL.md and follow it for: <feature idea>"
```

Then continue through `to-prd` and `to-tasks` with `--resume <id>`. Questions arrive as numbered options in chat (the skills' documented fallback when a native question tool is absent). `to-prd`/`to-tasks` write markdown only: the PRD to `.ai-workflow/work/<feature-slug>/prd.md` and one file per slice under `.ai-workflow/work/<feature-slug>/tasks/`. The to-tasks approval quiz is the last human gate; `implement-tasks` records it in the run state's `gates`.

## 4. The autonomous half (step 4)

Run `implement-tasks` in the same or a fresh session — its run state at `.ai-workflow/impl-review/<session-id>/run-state.json` carries the approval past restarts:

```bash
scripts/run-pipeline-acp.py /path/to/your-project \
  -t "Use implement-tasks on the queue under .ai-workflow/work/<feature-slug>/tasks/"
```

Nothing after the gate asks a human: contested decisions go to `models-consensus`, and a genuine hard-stop surfaces as `status: awaiting_human` in the run state (the board highlights it) for you to resume. Approval prompts here come from the CLI's own permission mode, not from OpenHands' confirmation policy, since the CLI executes the tools.

For a machine-enforced completion gate in headless runs, add a Stop hook in the target repo — OpenHands blocks task completion until it exits 0:

```json
// .openhands/hooks.json
{
  "hooks": {
    "Stop": [{ "command": ".openhands/hooks/quality_gate.sh" }]
  }
}
```

Point `quality_gate.sh` at the slice's acceptance commands (and `.agents/skills/shared/scripts/validate_artifacts.py`).

Parallel slices: OpenHands sub-agents are sequential, so skip `implement-tasks`'s 3-in-flight default at first. When needed, launch one `run-pipeline-acp.py` process per slice worktree from a shell loop — the run-state contract (side-effect keys, per-slice run ids) and the `worktree` skill's `git worktree add` fallback make that safe.

## 5. The kanban board

Each pipeline station is a column; cards are runs and task slices, placed by the `phase` their run state reports:

```bash
python3 pipeline-board/serve.py /path/to/your-project
```

Open http://localhost:8642. Columns: `00 Frame · 01 Specify · 02 Plan (gate) · 03 Design gate · 04 Implement · 05 Verify · 06 Deliver · Done`. Card color tracks `status` — `awaiting_human` is highlighted as _needs you_, `failed`/`ceiling_hit` red, `complete` lands in Done. The board is read-only over `.ai-workflow/**/run-state.json` (plus consensus session files and launch manifests); it polls every 3 s and needs no skill changes, because the run-state contract already records every phase transition.

## 6. Model seats — also CLI-only

The seats the pipeline escalates to were already CLI-based: every `*-runner` skill shells out to a local CLI in headless mode (`claude -p`, `codex exec`, `cline` headless NDJSON, `agy`, `grok`), using that CLI's own auth. Nothing there needs an API key either.

Check what the host offers:

```bash
python3 skills/shared/scripts/discover_runners.py probe --native-agent no
```

On a machine with Claude Code, Codex, Antigravity, Grok, and Cline installed, that reports **7 available seats** — `opus` and `sonnet` via `claude`, `codex`, `gemini` via `agy`, `grok`, and `kimi` + `glm` via `cline` — comfortably past the ≥3 quorum, so `models-consensus` runs at full strength rather than degrading to single-model personas mode. Pass `--native-agent no` so the opus/sonnet seats route through `claude-runner` instead of expecting a host-native subagent tool.

Seat fidelity still applies: a missing CLI is reported as `seat_unavailable`, never silently substituted.

## Differences from Claude Code

| Claude Code feature | On OpenHands | Consequence |
| --- | --- | --- |
| `Agent` tool (parallel subagents) | `task` tool exists but is sequential | design-gate / full-review lens fan-out runs sequentially; or route opus/sonnet seats through `claude-runner` (`discover_runners.py probe --native-agent no`) |
| `AskUserQuestion` | plain chat | skills already fall back to numbered options |
| `EnterWorktree` | none | `worktree` skill falls back to `git worktree add` |
| `mcp__Claude_Browser__*` | Playwright MCP | `browser-smoke`'s documented fallback |

`allowed-tools` frontmatter is ignored by OpenHands — harmless. `disable-model-invocation` is ignored by OpenHands too, but **is** honored by the Claude Code CLI, which is what runs the skills in CLI-only mode: entry points marked with it stay user-invocable, hence the read-the-file invocation above.

## Alternative: direct API

If you would rather have OpenHands call the provider itself — which buys back MCP config, custom tools, condensers, and critics — set the model and run the stock CLI:

```bash
export LLM_MODEL="anthropic/claude-sonnet-4-5-20250929"
export LLM_API_KEY="sk-ant-..."
openhands --headless --override-with-envs --json -t "Use implement-tasks on the queue under .ai-workflow/work/<feature-slug>/tasks/"
```

Two behaviors will trip you up here:

- **Those env vars are ignored without `--override-with-envs`.** The CLI prints `Environment variable(s) LLM_API_KEY, LLM_MODEL detected but will be ignored` and uses stored settings instead.
- **`--headless` refuses to start until settings exist** (`Headless mode requires existing settings`) — run `openhands` interactively once, or always pass `--override-with-envs`.

This path bills per token. In this mode OpenHands loads the skills itself from `.agents/skills/`.

## Caveats

- OpenHands is mid-restructure (the `OpenHands/OpenHands` repo is now the Agent Canvas UI; the agent lives in `OpenHands/software-agent-sdk`). Pin versions — the CLI carries its own SDK, so `openhands` 1.16.0 ships `openhands-sdk` 1.21.0 while the standalone SDK is already at 1.39.1; they behave identically for skill loading, but don't assume a CLI upgrade and an SDK upgrade are the same thing. Use docs.openhands.dev — `docs.all-hands.dev` and `python -m openhands.core.main` are legacy.
- Agent Canvas has no built-in kanban; that is what `pipeline-board/` is for. It could later be packaged as a Canvas plugin, or mirrored to a GitHub Projects board via `gh`.
