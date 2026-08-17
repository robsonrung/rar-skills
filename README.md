# rar-skills

Claude Code skills that compose into **one development workflow** — idea → interview → spec → tasks → design gate → test-driven build → review → PR. Every human decision is collected in the first three phases; everything after the approval gate runs autonomously while still optimizing architecture, tests, simplicity, and security.

## The workflow

One user-called skill per step. `ship` runs the whole pipeline; each step is also usable on its own.

| Step | Skill | What it does |
|---|---|---|
| 0. Frame | `brainstorm` · `prototype` | Sharpen a fuzzy idea to a BUILD/DEFER/REDUCE-SCOPE/REJECT verdict; spike a design unknown only running code can settle. |
| 1. Specify | `interview` → `to-spec` | Grill the idea against the code, the glossary, and past decisions until spec-ready; then synthesize the PRD (security decisions and test seams included). |
| 2. Plan | `to-tasks` | Cut tracer-bullet vertical slices, each with a machine-checkable acceptance contract and design/security gate flags. **The last human gate.** |
| 3. Design gate | `coding-design-plan` → `design-gate` | Shape the plan, then run only the design lenses the slice's flags select, as parallel read-only reviewers. |
| 4. Build | `implement-and-review` (or `tdd` directly) | Test-first implementation with cross-model review; `safe-incremental-coding` first on untested legacy code; `diagnose` for bugs. |
| 5. Verify | `coding-review-simplify` → `full-review` → `browser-smoke` | Self-simplify, then the multi-model review gate on final code, then drive the real app. |
| 6. Deliver | `open-pr` · `resolve-pr-feedback` | PR with acceptance evidence and the decision log; resolve review threads. |

`ship` is a **thin conductor**: steps 3–6 each run in their own subagent, and what crosses between them is a markdown report on disk plus a short envelope — *hand off the path, not the payload*. Steps 0–2 stay in the main context because only they talk to you. That keeps the conductor's context flat across a whole run, and keeps each step's reasoning recoverable after a compaction.

Full narrative, design principles, and conventions: [docs/workflow.md](docs/workflow.md). Visual map: `workflow.html`. How a feature moves through the relay: [docs/pipeline.html](docs/pipeline.html).

Supporting casts: **design lenses** (`architecture-lens`, `macro-architecture`, `domain-driven-design`, `software-design-philosophy`, `design-patterns`, `data-systems-coding-lens`, `agent-architecture-lens`, `react-performance`) are routed by `design-gate` rather than chosen by hand; **`models-consensus`** answers contested questions with a multi-model council (modes `poll` / `debate` / `personas`) and is what the autonomous phases escalate to instead of asking the user; **`fable-mindset`** governs turn-level posture; the **`*-runner`** family provides the model seats.

## Quickstart

```bash
# Add the collection (pick skills interactively)
npx skills@latest add robsonrung/rar-skills

# Install every skill
npx skills@latest add robsonrung/rar-skills --skill '*'
```

Skills install under `.agents/skills/` in the target repo. The runner scripts and shared assets (`_shared/`) are expected at `.agents/skills/_shared/...` once installed.

To install straight from a local checkout (symlinks by default, so edits here flow through):

```bash
scripts/install-skills.sh /path/to/your-project
```

## Other harnesses

`.agents/skills/` is the AgentSkills location, so the collection is not Claude Code-only. [docs/openhands.md](docs/openhands.md) walks through running the whole pipeline on **OpenHands**, including a CLI-only mode that needs no API keys — OpenHands drives your existing Claude Code or Codex CLI over ACP, so the run bills against the CLI subscription:

```bash
scripts/install-skills.sh /path/to/your-project
scripts/run-pipeline-acp.py /path/to/your-project \
  -t "Read .claude/skills/ship/SKILL.md and follow it for: <feature idea>"
```

The `*-runner` seats are CLI-backed already, so a host with the runner CLIs installed keeps the full multi-model council with no API key anywhere.

`pipeline-board/` serves a live kanban of in-flight runs, one column per pipeline station, read from the durable run state:

```bash
python3 pipeline-board/serve.py /path/to/your-project
```

## Prerequisites

Most skills here are **pure-prompt** (the design lenses, reviews, and planning skills — e.g. `design-gate`, `architecture-lens`, `clean-code`, `tdd`, `coding-design-plan`). They need nothing beyond Claude Code itself, and the pipeline is self-contained: every skill `ship` invokes lives in this collection.

The prerequisites below apply to the **multi-model and runner skills** — `models-consensus`, `diverse-plan`, `implement-and-review`, `implement-feature`, `full-review`, `collaborative-delivery`, the panel modes of `brainstorm` / `to-spec` / `to-tasks`, and the `*-runner` skills they drive. You only need the pieces for the seats you actually want; these skills run on a **quorum** (typically ≥3 seats) and degrade gracefully when a CLI is missing — they report the absent seat rather than faking it (*seat fidelity*). Seat → model ids live in one place: [`_shared/references/model-roster.md`](_shared/references/model-roster.md).

### 1. Runtime

| Requirement | Why |
|-------------|-----|
| **Python 3** (`python3` in `PATH`) | All runner wrappers, the shared background-jobs CLI (`_shared/scripts/runner_jobs.py`), `ui-ux-pro-max`, and the leitwörter check are Python 3 scripts. |
| **Claude Code** | Host for every skill; provides the native `Agent` subagent used for Opus/Sonnet seats without a CLI fallback. |

### 2. Installed CLIs we rely on

Each model seat is backed by a local CLI. Install only the ones whose seats you want. None are required individually — missing CLIs just drop that seat.

| CLI binary | Provides seat(s) | Used by | Auth / config |
|------------|------------------|---------|---------------|
| `claude` | Claude (runner fallback for the native `Agent` seats) | `claude-runner` | Logged-in CLI (OAuth/keychain), **or** `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` for bare/headless mode |
| `codex` | Codex (`gpt-5.6-sol`) | `codex-runner` | `codex` CLI authenticated |
| `agy` (Antigravity CLI) | Gemini / Google | `gemini-runner` | `agy` authenticated; model selected via `/model` or `~/.gemini/antigravity-cli/settings.json` |
| `grok` | Grok (`grok-4.6` — Grok 4.6) | `grok-runner` | `grok` CLI logged in (`grok login`, grok.com account) |
| `pi` | Kimi (`moonshotai/kimi-k3`), GLM (`z-ai/glm-5.2`), Qwen (`qwen/qwen3.8-2.4t-a95b`), and Gemma (`google/gemma-4-31b-it`), all served via OpenRouter | `pi-runner`, `kimi-runner`, `glm-runner`, `qwen-runner`, `gemma-runner` | `pi` CLI (`npm install -g @mariozechner/pi-coding-agent`) + `OPENROUTER_API_KEY` |
| `cline` | Muse (`meta/muse-spark-1.1`) and Minimax | `muse-runner`, `minimax-runner` | Cline provider authenticated via `cline auth`; Muse access is limited to users in the United States |
| `opencode` (optional) | OpenCode | `opencode-runner` | Its own auth; no bundled wrapper — runs through the host approval flow |

> The Kimi, GLM, Qwen, and Gemma runners are thin shims over `pi-runner` (provider and model pinned per invocation — no shared provider state). The Muse and Minimax runners are thin shims over `cline-runner` with their own model IDs.

### 3. Cloud / provider configuration

Every CLI seat is an external model call — it sends prompt text, prompt files, and any files the model reads to that provider's cloud. You need an account and credentials with each provider whose seat you enable:

- **Anthropic** — for `claude` (and the native Opus/Sonnet seats running inside Claude Code).
- **OpenAI / Codex** — for `codex`.
- **Google** — for `agy` (Gemini).
- **xAI** — for `grok` (Grok 4.5 seat).
- **Pi-backed seats (OpenRouter)** — Kimi (`moonshotai/kimi-k3`), GLM (`z-ai/glm-5.2`), Qwen (`qwen/qwen3.8-2.4t-a95b`), and Gemma (`google/gemma-4-31b-it`), pinned per invocation through the `pi` CLI. One credential: `OPENROUTER_API_KEY`. Note these seats share the OpenRouter dependency, so an outage or key problem drops them together.
- **Cline-backed seats** — Muse (`meta/muse-spark-1.1`) and Minimax (`minimax/minimax-m2.7`). Authenticate a Cline provider via `cline auth` that can resolve each model ID. OpenRouter limits Muse access to users in the United States.

### 4. Environment variables

| Variable | When you need it |
|----------|------------------|
| `ANTHROPIC_API_KEY` *or* `ANTHROPIC_AUTH_TOKEN` | Only for `claude-runner` in bare/headless mode (bare mode disables OAuth/keychain). Not needed when the `claude` CLI is interactively logged in. |
| `RUNNER_BASE_PATH` | Override the runner-script base path when skills are **not** installed at the default `.agents/skills/` location (e.g. running from a source checkout). |

### 5. External skills

None are required. The pipeline is self-contained — the five steps that used to depend on external installs are now in-repo: `tdd`, `interview` (the requirements interview), `prototype`, `diagnose`, and `session-handoff`.

Two optional integrations are used when present and skipped when not: a code-review plugin (the `/review` builtin or an equivalent) and, in `ship` phase 5, driving the real app — handled here by `browser-smoke` for web-facing changes, or the host's run-the-app check otherwise.

If a referenced skill is absent, the calling skill notes it and continues with the lenses it can apply — the pipeline degrades, it does not break.

### 6. Command guard (optional, recommended)

Runner skills launch CLI seats headless with auto-approve flags. `_shared/hooks/` ships an opt-in guard that blocks catastrophic commands (rm on `/`/`~`, raw-disk writes, fork bombs, `curl | sh`, remote-history rewrites, `gh repo delete`, token exfiltration) before any seat runs them, while leaving recoverable commands alone. Install is manual — no skill ever wires it for you:

```bash
mkdir -p ~/.agents/hooks && cp _shared/hooks/deny-dangerous.sh _shared/hooks/dangerous-patterns.txt ~/.agents/hooks/
```

Then register `~/.agents/hooks/deny-dangerous.sh` as a `PreToolUse` (matcher `Bash`) hook in each CLI that supports hooks — wiring details and per-CLI gotchas are in [`_shared/references/runner-common.md`](_shared/references/runner-common.md) under "Guardrails". After editing the patterns file, run `~/.agents/hooks/test-guard.sh` (copy it too) — it must end `failed: 0`.

## License

See [LICENSE](LICENSE).
