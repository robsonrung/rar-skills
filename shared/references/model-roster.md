# Model roster — the single source of truth for seat → model ids

Every multi-model skill references this table instead of inlining model ids.
When a provider ships a new model, update **this file** (and the runner script
defaults it names) — prose in individual skills must say "the Claude seat",
"the Codex seat", etc., and point here.

Seat ids live here; task assignments do not. Read
`task-shaped-model-routing.md` for the shared routing and evaluation contract.

Aliases are preferred over pinned ids in invocations where the CLI supports
them (`claude --model opus`); the envelope's `effective_model` receipt records
what actually served, which is what agreement weighting uses (never the
request, never a self-claim).

| Seat | Transport | Requested model / alias | Pinned id (current) | Notes |
|---|---|---|---|---|
| opus | native `Agent` tool, fallback `claude-runner` | `opus` | `claude-opus-5` | Claude flagship. Orchestrator, organizer/synthesizer, judge seats. |
| sonnet | native `Agent` tool, fallback `claude-runner` | `sonnet` | `claude-sonnet-5` | Fast Claude seat; maintainability lens. |
| codex | `codex-runner` (`codex` CLI) | — | `gpt-5.6-sol` | Default OpenAI seat: logic, security. |
| codex-code | `codex-runner` (`codex` CLI) | alias `codex` | `gpt-5.3-codex` | Code-specialized secondary OpenAI seat (agentic coding, regression, security review). Used by `diverse-plan` and `full-review`; same CLI, distinct model. |
| gemini | `gemini-runner` (`agy` CLI) | — | `gemini-3.7-flash` | Cross-file consistency lens. The probe checks `agy`, not a `gemini` binary. |
| grok | `grok-runner` (`grok` CLI) | — | `grok-4.6` | xAI seat; execution-path verification. |
| kimi | `kimi-runner` → `pi` CLI (OpenRouter) | — | `moonshotai/kimi-k3` | Single K3 id — no `-code`/`-thinking` variants. Long-horizon coding, 1M context. Served via OpenRouter (`OPENROUTER_API_KEY`). |
| glm | `glm-runner` → `pi` CLI (OpenRouter) | — | `z-ai/glm-5.3-flash` | Edge-case lens; outsider stance default. Served via OpenRouter (`OPENROUTER_API_KEY`) — the old cline-gateway slug `zai/glm-5.3-flash` is retired. |
| qwen | `qwen-runner` → `pi` CLI (OpenRouter) | — | `qwen/qwen3.8-2.4t-a95b` | Council seat (optional tier). Qwen3.8 27B — the dense open-weight VLM of the Qwen3.8 Max family, 256K context; coding- and long-horizon-agentic-strong (SWE-bench Pro 61.7, CoWorkBench 70.7). Served via OpenRouter (`OPENROUTER_API_KEY`). |
| muse | `muse-runner` → `cline` CLI | — | `meta/muse-spark-1.1` | Council seat (optional tier). Meta multimodal agentic-reasoning model, 1M context — agent-orchestration, tool-use, and computer-use lens. OpenRouter limits access to users in the United States. |
| gemma | `gemma-runner` → `pi` CLI (OpenRouter) | — | `google/gemma-4-31b-it` | Council seat (optional tier). Cheapest roster seat ($0.10/$0.34 per 1M on OpenRouter); Google DeepMind dense 31B multimodal, 140+ languages, LiveCodeBench v6 80. Served via OpenRouter (`OPENROUTER_API_KEY`). |
| minimax | `minimax-runner` → `cline` CLI | — | `minimax/minimax-m2.7` | Backup seat. |

Seat availability is probed by `shared/scripts/discover_runners.py` — always
probe; never assume a CLI exists. Quorum floors: light = 2, quality = 3
distinct available seats (the probe's `summary.light_quorum_met` /
`quality_quorum_met` are advisory; multi-seat skills stop below 3 distinct
seats unless they declare a degraded posture).
