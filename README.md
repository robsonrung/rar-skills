# rar-skills

Claude Code skills that compose into **one development workflow** in four steps — interview → PRD → tasks → implement — with every human decision collected in the first three steps and the fourth running autonomously while still optimizing architecture, tests, simplicity, and security.

## The workflow

Four skills you type, one after the other. Each ends by naming the next; each is also usable on its own.

| Step | Skill | What it does | Accessory skills that run inside it |
| --- | --- | --- | --- |
| 1. Interview | `interview-me` | Grill the idea against the code, the glossary (`CONCEPTS.md`), and past decisions (`docs/adr/`) in frontier rounds until spec-ready, writing glossary entries and ADRs as decisions settle. | `security-gate` (threat-model-lite checklist), `test-lens` (naming the test seams), `to-prototype` (detour for a question only running code can settle) |
| 2. PRD | `to-prd` | Synthesize the PRD from the interview, security decisions and test seams included. No second interview. | `security-gate`; optional multi-model panel mode |
| 3. Tasks | `to-tasks` | Cut tracer-bullet vertical slices, each with a machine-checkable acceptance contract and design/security gate flags. **The last human gate.** | `design-gate`'s routing table and `security-gate`'s trigger list, to set the flags |
| 4. Implement | `implement-tasks` | Build the slice DAG with `implement-and-review` per slice in parallel worktrees, integrate in dependency order, review the seams, make residual findings durable, open the PR. | per slice: `coding-design-plan` → `design-gate` (the lenses) → `tdd` (+ `safe-incremental-coding`, `clean-code`, `test-lens`, `diagnose`) → `coding-review-simplify` → `full-review`; then `open-pr` |

`implement-tasks` is a **thin conductor**: each slice builds in its own `implement-and-review` run, and what crosses back is a report on disk plus a short envelope — _hand off the path, not the payload_. Progress lives in a run state on disk, so a run survives compactions and restarts. After the step-3 approval nothing asks you anything: contested decisions go to `models-consensus`, and only destructive or irreversible operations hard-stop for a human.

Full narrative, design principles, and conventions: [docs/workflow.md](docs/workflow.md). Skill catalogue and call map, a snapshot taken before this four-step consolidation: [docs/skills-atlas.html](docs/skills-atlas.html).

Supporting casts: **design lenses** (`architecture-lens`, `macro-architecture`, `domain-driven-design`, `software-design-philosophy`, `design-patterns`, `data-systems-coding-lens`, `distributed-systems-patterns`, `agent-architecture-lens`, `advanced-react`, `ui-ux-pro-max`) are routed by `design-gate` rather than chosen by hand; **`models-consensus`** answers contested questions with a multi-model council (modes `poll` / `debate` / `personas`) and is what the autonomous step escalates to instead of asking the user; **`fable-mindset`** governs turn-level posture; **knowledge** is kept current by `interview-me` (writes glossary entries and ADRs as decisions settle) and `capture-learning` (records solved problems); the **`*-runner`** family provides the model seats.

## Repository layout

```
engineering/           the workflow and everything it calls
  workflow/            the engineer's toolbox — brainstorm · interview-me · to-prd · to-tasks · implement-tasks
                       models-consensus · to-prototype; which tool you reach for depends on the task
  engine/              implement-and-review · coding-design-plan · worktree
  gates/               security-gate · design-gate
  lenses/              architecture-lens · macro-architecture · domain-driven-design · software-design-philosophy
                       design-patterns · data-systems-coding-lens · distributed-systems-patterns
                       agent-architecture-lens · advanced-react · ui-ux-pro-max
  practice/            tdd · safe-incremental-coding · clean-code · test-lens · diagnose · frontend-design
  review/              coding-review-simplify · full-review
  deliver/             open-pr · capture-learning · session-handoff · summarize · resolve-pr-feedback
  seats/               claude-runner · codex-runner · gemini-runner · grok-runner
                       pi-runner (--seat kimi|glm|qwen|gemma) · cline-runner (--seat muse|minimax) · dcode-runner · opencode-runner
visualization/         skills whose deliverable is a rendered page: explain-architecture (orientation page)
                       · html-explainer (drill-down) · consensus-summary-html — all load
                       shared/references/html-page-conventions.md
extras/                standalone skills the workflow does not call: diverse-plan, collaborative-delivery,
                       review-gate, verify-changes, browser-smoke, knowledge-graph, dynamic-harness,
                       peer-sessions, cmux-cli, fable-mindset, skill-expert, agents-md-craft,
                       decide-about-disagreements
shared/                contracts, references, runner scripts, hooks, and tests every skill loads by path
```

The grouping is for reading the repository. Installed, every skill is a flat sibling under `.agents/skills/<name>/` (and `.claude/skills/<name>/`), with `shared/` next to them, so the paths skills use at runtime (`.agents/skills/shared/...`, `.agents/skills/pi-runner/...`) never change. Scripts that run from a source checkout locate `shared/` and sibling skills by name through `shared/scripts/skill_paths.py`.

## Quickstart

```bash
# Add the collection (pick skills interactively)
npx skills@latest add robsonrung/rar-skills

# Install every skill
npx skills@latest add robsonrung/rar-skills --skill '*'
```

Skills install under `.agents/skills/` in the target repo. The runner scripts and shared assets (`shared/`) are expected at `.agents/skills/shared/...` once installed.

To install straight from a local checkout (symlinks by default, so edits here flow through):

```bash
scripts/install-skills.sh /path/to/your-project
```

## Other harnesses

`.agents/skills/` is the AgentSkills location, so the collection is not Claude Code-only. [docs/openhands.md](docs/openhands.md) walks through running the whole pipeline on **OpenHands**, including a CLI-only mode that needs no API keys — OpenHands drives your existing Claude Code or Codex CLI over ACP, so the run bills against the CLI subscription:

```bash
scripts/install-skills.sh /path/to/your-project
scripts/run-pipeline-acp.py /path/to/your-project \
  -t "Read .claude/skills/interview-me/SKILL.md and follow it for: <feature idea>"
```

The `*-runner` seats are CLI-backed already, so a host with the runner CLIs installed keeps the full multi-model council with no API key anywhere.

`pipeline-board/` serves a live kanban of in-flight runs, one column per pipeline station, read from the durable run state:

```bash
python3 pipeline-board/serve.py /path/to/your-project
```

## Prerequisites

Most skills here are **pure-prompt** (the design lenses, reviews, and planning skills — e.g. `design-gate`, `architecture-lens`, `clean-code`, `tdd`, `coding-design-plan`). They need nothing beyond Claude Code itself, and the pipeline is self-contained: every skill the four steps invoke lives in this collection.

The prerequisites below apply to the **multi-model and runner skills** — `models-consensus`, `diverse-plan`, `implement-and-review`, `implement-tasks`, `full-review`, `collaborative-delivery`, the panel modes of `brainstorm` / `to-prd` / `to-tasks`, and the `*-runner` skills they drive. You only need the pieces for the seats you actually want; these skills run on a **quorum** (typically ≥3 seats) and degrade gracefully when a CLI is missing — they report the absent seat rather than faking it (_seat fidelity_). Seat → model ids live in one place: [`shared/references/model-roster.md`](shared/references/model-roster.md).

### 1. Runtime

| Requirement | Why |
| --- | --- |
| **Python 3** (`python3` in `PATH`) | All runner wrappers, the shared background-jobs CLI (`shared/scripts/runner_jobs.py`), `ui-ux-pro-max`, and the leitwörter check are Python 3 scripts. |
| **Claude Code** | Host for every skill; provides the native `Agent` subagent used for Opus/Sonnet seats without a CLI fallback. |

### 2. Installed CLIs we rely on

Each model seat is backed by a local CLI. Install only the ones whose seats you want. None are required individually — missing CLIs just drop that seat.

| CLI binary | Provides seat(s) | Used by | Auth / config |
| --- | --- | --- | --- |
| `claude` | Claude (runner fallback for the native `Agent` seats) | `claude-runner` | Logged-in CLI (OAuth/keychain), **or** `ANTHROPIC_API_KEY` / `ANTHROPIC_AUTH_TOKEN` for bare/headless mode |
| `codex` | Codex (`gpt-5.6-sol`) | `codex-runner` | `codex` CLI authenticated |
| `agy` (Antigravity CLI) | Gemini / Google | `gemini-runner` | `agy` authenticated; model selected via `/model` or `~/.gemini/antigravity-cli/settings.json` |
| `grok` | Grok (`grok-4.6` — Grok 4.6) | `grok-runner` | `grok` CLI logged in (`grok login`, grok.com account) |
| `pi` | Kimi (`moonshotai/kimi-k3`), GLM (`z-ai/glm-5.3-flash`), Qwen (`qwen/qwen3.8-max`), and Gemma (`google/gemma-4-31b-it`), all served via OpenRouter | `pi-runner` (`--seat kimi\|glm\|qwen\|gemma`) | `pi` CLI (`npm install -g @mariozechner/pi-coding-agent`) + `OPENROUTER_API_KEY` |
| `cline` | Muse (`meta/muse-spark-1.3`) and Minimax | `cline-runner` (`--seat muse\|minimax`) | Cline provider authenticated via `cline auth`; Muse access is limited to users in the United States |
| `opencode` (optional) | OpenCode | `opencode-runner` | Its own auth; no bundled wrapper — runs through the host approval flow |

> Kimi, GLM, Qwen, and Gemma are seats of `pi-runner` (`--seat <name>` pins the provider and model per invocation — no shared provider state). Muse and Minimax are seats of `cline-runner`. Seat → model ids: `shared/references/model-roster.md`.

### 3. Cloud / provider configuration

Every CLI seat is an external model call — it sends prompt text, prompt files, and any files the model reads to that provider's cloud. You need an account and credentials with each provider whose seat you enable:

- **Anthropic** — for `claude` (and the native Opus/Sonnet seats running inside Claude Code).
- **OpenAI / Codex** — for `codex`.
- **Google** — for `agy` (Gemini).
- **xAI** — for `grok` (Grok 4.6 seat).
- **Pi-backed seats (OpenRouter)** — Kimi (`moonshotai/kimi-k3`), GLM (`z-ai/glm-5.3-flash`), Qwen (`qwen/qwen3.8-max`), and Gemma (`google/gemma-4-31b-it`), pinned per invocation through the `pi` CLI. One credential: `OPENROUTER_API_KEY`. Note these seats share the OpenRouter dependency, so an outage or key problem drops them together.
- **Cline-backed seats** — Muse (`meta/muse-spark-1.3`) and Minimax (`minimax/minimax-m2.7`). Authenticate a Cline provider via `cline auth` that can resolve each model ID. OpenRouter limits Muse access to users in the United States.

### 4. Environment variables

| Variable | When you need it |
| --- | --- |
| `ANTHROPIC_API_KEY` _or_ `ANTHROPIC_AUTH_TOKEN` | Only for `claude-runner` in bare/headless mode (bare mode disables OAuth/keychain). Not needed when the `claude` CLI is interactively logged in. |
| `RUNNER_BASE_PATH` | Override the runner-script base path when skills are **not** installed at the default `.agents/skills/` location (e.g. running from a source checkout). |

### 5. External skills

None are required. The pipeline is self-contained — the five steps that used to depend on external installs are now in-repo: `tdd`, `interview-me` (the requirements interview), `to-prototype`, `diagnose`, and `session-handoff`.

Two optional integrations are used when present and skipped when not: a code-review plugin (the `/review` builtin or an equivalent) and driving the real app after a build — handled here by `browser-smoke` for web-facing changes, or the host's run-the-app check otherwise.

If a referenced skill is absent, the calling skill notes it and continues with the lenses it can apply — the pipeline degrades, it does not break.

### 6. Command guard (optional, recommended)

Runner skills launch CLI seats headless with auto-approve flags. `shared/hooks/` ships an opt-in guard that blocks catastrophic commands (rm on `/`/`~`, raw-disk writes, fork bombs, `curl | sh`, remote-history rewrites, `gh repo delete`, token exfiltration) before any seat runs them, while leaving recoverable commands alone. Install is manual — no skill ever wires it for you:

```bash
mkdir -p ~/.agents/hooks && cp shared/hooks/deny-dangerous.sh shared/hooks/dangerous-patterns.txt ~/.agents/hooks/
```

Then register `~/.agents/hooks/deny-dangerous.sh` as a `PreToolUse` (matcher `Bash`) hook in each CLI that supports hooks — wiring details and per-CLI gotchas are in [`shared/references/runner-common.md`](shared/references/runner-common.md) under "Guardrails". After editing the patterns file, run `~/.agents/hooks/test-guard.sh` (copy it too) — it must end `failed: 0`.

## License

See [LICENSE](LICENSE).
