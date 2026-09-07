# Model roster

This is the canonical seat to model mapping. Workflow prose names a seat and
reads task selection rules from `task-shaped-model-routing.md`. A routing plan
records the exact model and effort before work starts.

## Availability evidence

- `shared/scripts/discover_runners.py` proves that a transport CLI is present.
  It does not prove account access to a model.
- An envelope separates `requested_model`, `configured_model`, and an observed
  `effective_model`. Only `model_receipt.status: verified` proves which model
  served a run. A configured label is not a serving receipt.
- A user may explicitly approve `model_verification: allow_unverified` when a
  transport cannot expose a serving-model receipt. Reports must label that
  route unverified. A route with `model_verification: required` blocks without
  a matching verified receipt.
- The task-fit notes below are routing guidance from current provider material.
  They are not a benchmark ranking and do not replace local acceptance evidence.

## Current primary sources

Checked 2026-09-06:

- [Astra model guidance](https://developers.openai.com/api/docs/models/gpt-6-astra/)
- [Astra release note](https://openai.com/index/gpt-6-astra/)
- [Fable 5.1 overview](https://www.anthropic.com/claude/fable)
- [Fable 5.1 model documentation](https://platform.claude.com/docs/en/models/fable-5-1/overview)
- [Gemini 3.8 Flash model documentation](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- [Grok 4.6 announcement](https://x.ai/news/grok-4-6)
- [Qwen3.8 Max model guide](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max)

These sources support the capability claims. The routes and effort defaults are
this library's recommendations. Local acceptance evidence can change a route.

## Seats

| Seat | Transport | Approved model | Task fit |
| --- | --- | --- | --- |
| astra | `codex-runner` | `gpt-6-astra` | Primary route for systems, security, difficult diagnosis, multistep tool work, integration, and final reconciliation. |
| fable | `claude-runner` | `claude-fable-5-1` | Primary route for repository-scale implementation, high-fidelity interface work, performance work, long-running coding, and code review. |
| opus | `claude-runner` | `claude-opus-5` | Focused precision judgment when the approved task needs a second Claude perspective. |
| sonnet | `claude-runner` | `claude-sonnet-5` | Bounded maintainability and test-quality review when the plan selects it. |
| sol | `codex-runner` | `gpt-5.6-sol` | Available only when the user selects it or local evidence shows equal acceptance at a better elapsed cost. |
| terra | `codex-runner` | `gpt-5.6-terra` | Available only when the user selects it or local evidence shows equal acceptance at a better elapsed cost. |
| grok | `grok-runner` | `grok-4.6` | Independent execution-path and tool-flow perspective. |
| gemini | `gemini-runner` | `gemini-3.8-flash` | Independent wide cross-file perspective. Its runner cannot set effort. |
| kimi | `pi-runner --seat kimi` | `moonshotai/kimi-k3` | Long-context pragmatic feasibility perspective. |
| glm | `pi-runner --seat glm` | `z-ai/glm-5.3-flash` | Boundary and failure-case perspective. |
| qwen | `pi-runner --seat qwen` | `qwen/qwen3.8-max` | Optional independent perspective for complex engineering and long-horizon coding. |
| muse | `cline-runner --seat muse` | `meta/muse-spark-1.3` | Optional agent, tool-use, and computer-use perspective. |
| gemma | `pi-runner --seat gemma` | `google/gemma-4-31b-it` | Optional broad document-grounded perspective. |
| minimax | `cline-runner --seat minimax` | `minimax/minimax-m2.7` | Optional additional perspective. |

`codex` and `codex-code` remain accepted runner aliases for old callers. New
routing plans use `astra`, `sol`, or `terra` so the selected model is clear.

## Effort support

An approved plan names an effort when the selected transport can set it. A
runtime-controlled route records a null effort. Use `medium` for a bounded
route, `high` for complex work, and `xhigh` only for unresolved high-risk work.
`low` requires local evidence that the same acceptance contract still passes.
`ultra` needs an explicit reason in the plan.

`gpt-6-astra`, `gpt-5.6-sol`, and `gpt-5.6-terra` accept `low` through
`ultra`. The current Fable CLI accepts `low` through `max`. The Grok runner
enforces at most `high`. Codex, Claude, Grok, Pi, and Cline use
`effort_control: "runner"`. Gemini uses `effort_control: "runtime"` with a
null effort because its wrapper cannot set it. Runtime-controlled routes are
not default implementation routes.

Pi forwards its selected effort setting. That is runner behavior, not evidence
that every model behind Pi supports the same provider reasoning mode. Keep a
Pi route only when its run report records the configured setting.

Dcode is a standalone manual runner. Its wrapper does not forward `--model`,
so it cannot appear in an approved implementation or review route.
