# Model roster — the single source of truth for seat → model ids

Every multi-model skill references this table instead of inlining model ids. When a provider ships a new model, update **this file** (and the runner script defaults it names) — prose in individual skills must say "the Claude seat", "the Codex seat", etc., and point here.

Seat ids live here; task assignments do not. Read `task-shaped-model-routing.md` for the shared routing and evaluation contract.

Aliases are preferred over pinned ids in invocations where the CLI supports them (`claude --model opus`); the envelope's `effective_model` receipt records what actually served, which is what agreement weighting uses (never the request, never a self-claim).

| Seat | Transport | Requested model / alias | Pinned id (current) | Notes |
| --- | --- | --- | --- | --- |
| opus | native `Agent` tool, fallback `claude-runner` | `opus` | `claude-opus-5` | Claude flagship. Orchestrator, organizer/synthesizer, judge seats. |
| fable | native `Agent` tool, fallback `claude-runner` | `fable` | `claude-fable-5-1` | Escalation-only Claude seat, not a default. Anthropic's own guidance: start with Opus, escalate to Fable only when Opus at `high`/`xhigh` still falls short. ~2x Opus price ($10/$50 vs $5/$25 per 1M). See `task-shaped-model-routing.md` for when to reach for it. |
| sonnet | native `Agent` tool, fallback `claude-runner` | `sonnet` | `claude-sonnet-5` | Fast Claude seat; maintainability lens. |
| codex | `codex-runner` (`codex` CLI) | — | `gpt-5.6-sol` | Default OpenAI seat: logic, security. |
| codex-code | `codex-runner` (`codex` CLI) | `--model gpt-5.6-terra` | `gpt-5.6-terra` | Secondary OpenAI seat for review-shaped work (regression, security review) — a distinct, cheaper model from the default Sol seat. Used by `diverse-plan` and `full-review`. `gpt-5.3-codex` is retired under ChatGPT auth (verified 2026-09-03); do not re-pin it. |
| gemini | `gemini-runner` (`agy` CLI) | — | `gemini-3.8-flash` | Cross-file consistency lens. The probe checks `agy`, not a `gemini` binary. |
| grok | `grok-runner` (`grok` CLI) | — | `grok-4.6` | xAI seat; execution-path verification. |
| kimi | `pi-runner --seat kimi` → `pi` CLI (OpenRouter) | — | `moonshotai/kimi-k3` | Single K3 id — no `-code`/`-thinking` variants. Long-horizon coding, 1M context. Served via OpenRouter (`OPENROUTER_API_KEY`). |
| glm | `pi-runner --seat glm` → `pi` CLI (OpenRouter) | — | `z-ai/glm-5.3-flash` | Edge-case lens; outsider stance default. Served via OpenRouter (`OPENROUTER_API_KEY`) — the old cline-gateway slug `zai/glm-5.3-flash` is retired. |
| qwen | `pi-runner --seat qwen` → `pi` CLI (OpenRouter) | — | `qwen/qwen3.8-max` | Council seat (optional tier). Qwen3.8 Max — Alibaba's flagship, 2.4T MoE, 1M context; coding- and long-horizon-agentic-strong (Code Arena WebDev #1 overall as of the `-0902` refresh). Served via OpenRouter (`OPENROUTER_API_KEY`). |
| muse | `cline-runner --seat muse` → `cline` CLI | — | `meta/muse-spark-1.3` | Council seat (optional tier). Meta multimodal agentic-reasoning model, 1M context — agent-orchestration, tool-use, and computer-use lens. OpenRouter limits access to users in the United States. |
| gemma | `pi-runner --seat gemma` → `pi` CLI (OpenRouter) | — | `google/gemma-4-31b-it` | Council seat (optional tier). Cheapest roster seat ($0.10/$0.34 per 1M on OpenRouter); Google DeepMind dense 31B multimodal, 140+ languages, LiveCodeBench v6 80. Served via OpenRouter (`OPENROUTER_API_KEY`). |
| minimax | `cline-runner --seat minimax` → `cline` CLI | — | `minimax/minimax-m2.7` | Backup seat. |

Seat availability is probed by `shared/scripts/discover_runners.py` — always probe; never assume a CLI exists. Quorum floors: light = 2, quality = 3 distinct available seats (the probe's `summary.light_quorum_met` / `quality_quorum_met` are advisory; multi-seat skills stop below 3 distinct seats unless they declare a degraded posture).
