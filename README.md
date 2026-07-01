# rar-skills

A collection of Claude Code skills for design review, multi-model orchestration, and coding workflows.

## Quickstart

```bash
# Add the collection (pick skills interactively)
npx skills@latest add robsonrung/rar-skills

# Install every skill
npx skills@latest add robsonrung/rar-skills --skill '*'
```

Skills install under `.agents/skills/` in the target repo. The runner scripts and shared assets (`_shared/`) are expected at `.agents/skills/_shared/...` once installed.

## Prerequisites

Most skills here are **pure-prompt** (the design lenses, reviews, and planning skills — e.g. `design-gate`, `architecture-lens`, `clean-code`, `tdd`, `coding-design-plan`). They need nothing beyond Claude Code itself.

The prerequisites below apply to the **multi-model and runner skills** — `models-roundtable`, `models-consensus`, `council`, `diverse-plan`, `implement-and-review`, `implement-feature`, `feature-models-roundtable`, `full-review`, the `collaborative_*` skills, and the `*-runner` skills they drive. You only need the pieces for the seats you actually want; these skills run on a **quorum** (typically ≥3 seats) and degrade gracefully when a CLI is missing — they report the absent seat rather than faking it (*seat fidelity*).

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
| `codex` | Codex (`gpt-5.5`) | `codex-runner` | `codex` CLI authenticated |
| `agy` (Antigravity CLI) | Gemini / Google | `gemini-runner` | `agy` authenticated; model selected via `/model` or `~/.gemini/antigravity-cli/settings.json` |
| `cline` | Kimi (`moonshotai/kimi-k2.7-code` — Kimi K2.7 Code) and GLM (`zai/glm-5.2` — GLM 5.2) | `kimi-runner`, `glm-runner` | Cline provider authenticated via `cline auth` |
| `qwen` (Qwen Code CLI) | Qwen, **Gemma, Minimax** (shared transport) | `qwen-runner`, `gemma-runner`, `minimax-runner` | Provider configured in `~/.qwen/settings.json` (see below) |
| `opencode` (optional) | OpenCode | `opencode-runner` | Its own auth; no bundled wrapper — runs through the host approval flow |

> The Kimi and GLM runners are thin shims over `cline-runner`, forwarding a real `--model` (`moonshotai/kimi-k2.7-code`, `zai/glm-5.2`) to the single `cline` CLI. The Gemma/Minimax runners are thin shims over `qwen-runner`, executing through the single `qwen` CLI.

### 3. Cloud / provider configuration

Every CLI seat is an external model call — it sends prompt text, prompt files, and any files the model reads to that provider's cloud. You need an account and credentials with each provider whose seat you enable:

- **Anthropic** — for `claude` (and the native Opus/Sonnet seats running inside Claude Code).
- **OpenAI / Codex** — for `codex`.
- **Google** — for `agy` (Gemini).
- **Cline-backed seats** — Kimi (`moonshotai/kimi-k2.7-code`) and GLM (`zai/glm-5.2`). Authenticate a Cline provider via `cline auth` that can resolve those model ids (the `cline-pass` gateway covers both; bring-your-own Moonshot / Z.AI entitlements also work).
- **Qwen-backed providers** — Gemma (`google/gemma-4-31b-it`), Minimax (`minimax/minimax-m2.7`), and Qwen itself. Configure each as a `modelProviders` entry in `~/.qwen/settings.json` (with its API-key env var set), or pass credentials at call time via `--openai-api-key` / `--auth-type`. *(The legacy `qwen auth` subcommand has been removed.)*

### 4. Environment variables

| Variable | When you need it |
|----------|------------------|
| `ANTHROPIC_API_KEY` *or* `ANTHROPIC_AUTH_TOKEN` | Only for `claude-runner` in bare/headless mode (bare mode disables OAuth/keychain). Not needed when the `claude` CLI is interactively logged in. |
| Provider API keys referenced by `~/.qwen/settings.json` | Whatever env vars your `modelProviders` entries reference, for the Gemma / Minimax / Qwen seats. |
| `RUNNER_BASE_PATH` | Override the runner-script base path when skills are **not** installed at the default `.agents/skills/` location (e.g. running from a source checkout). |

### 5. External skills not bundled here

A few skills reference sibling skills that are **not** part of this collection. Install them separately if you use the skills that call them:

| Referenced skill | Called by | Install |
|------------------|-----------|---------|
| `tdd` | `implement-and-review`, `ship`, coding workflows | from your TDD skill source, e.g. `npx skills@latest add <owner>/<repo> --skill tdd` |
| `adversarial-review` | cross-model review workflows | from its source collection, same `npx skills@latest add` form |
| `grill-with-docs` | `ship` phase 1 (specify interview) | from your skill source, same `npx skills@latest add` form |
| `prototype` | `ship` phase 0 (frame — design unknowns) | same |
| `diagnose` | `ship`, `pragmatic-coding-session` (bugs found mid-work) | same |
| `handoff` | `ship` (context preservation on long slices) | same |

`verify` (called by `ship` phase 5) is a **Claude Code built-in** skill — no install needed when running under Claude Code; under another host, substitute an equivalent run-the-app check.

If a referenced skill is absent, the calling skill notes it and continues with the lenses it can apply — the pipeline degrades, it does not break.

## License

See [LICENSE](LICENSE).
