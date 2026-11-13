# OpenAI models: facts snapshot

Read on 2026-11-10 from OpenAI's [model selection](https://developers.openai.com/api/docs/guides/model-selection), [reasoning](https://developers.openai.com/api/docs/guides/reasoning), and [Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model) guides, and the Codex [pricing](https://learn.chatgpt.com/docs/pricing) and [models](https://learn.chatgpt.com/docs/models) pages. None shows a last-updated date. The Codex pages were read partly as a summary, so confirm a figure there before it decides anything.

## Side by side

|  | GPT-6 Luna | GPT-6.1 Terra | GPT-6.1 Sol | GPT-6 Astra |
| --- | --- | --- | --- | --- |
| Positioned for | Focused, high-volume tasks | Clear writing, visual understanding, computer use | Near-Astra results on complex work | The most complex work across code, apps, and research |
| Default effort in Codex | `medium` | `low` | `low` | `medium` |
| Effort ceiling in Codex | `max` | `ultra` | `ultra` | `ultra` |
| `none` effort | Accepted | Accepted | Rejected | Rejected |
| Knowledge cutoff | 2026-05-18 | 2026-06-01 | 2026-04-30 | 2026-04-30 |

Every model has a 1.05M-token context window and a 128K-token maximum output, and takes text and images. The Codex effort rows come from the Codex CLI model catalog (client 0.167.0, read 2026-11-10). Codex labels `low` as Light and `xhigh` as Extra High.

Codex recommends Sol on Plus, Pro, Business, Enterprise, and Edu, and Luna on Free and Go. Terra and Sol are not available in ChatGPT chat.

## Usage estimates

OpenAI's estimate of local messages per five-hour window on Plus and standard Business. They are estimates, not fixed limits:

| Model | Messages | Credits per 1M input / output tokens |
| --- | --- | --- |
| Luna | 350 to 3,000 | 2.5 / 12.5 |
| Terra | 35 to 285 | 25 / 125 |
| Sol | 15 to 160 | 50 / 250 |
| Astra | 5 to 45 | 250 / 1,250 |

- Pro plans have no five-hour limit at present. A weekly limit may apply on any plan.
- ChatGPT Work and Codex share usage. Local and cloud tasks share it too, and a cloud task can use more than a local message.
- Fast mode draws 2.5 times the included usage. Ultrafast, on Astra and Sol, draws 8 times.
- Higher effort takes longer and uses more tokens. OpenAI gives no multiplier.
- A long session that holds more context uses much more per message.
- `/status` shows the remaining limits in a session, and the usage dashboard shows reset times. A turn already running can finish after the limit is reached. Beyond that the choices are to wait or to buy credits.

## Effort

OpenAI's guidance by level:

| Effort | Use |
| --- | --- |
| `none` | Latency-critical calls, on Terra and Luna only |
| `low` | Tool use, planning, light work |
| `medium` | The default for most workloads |
| `high` | Hard debugging |
| `xhigh` | Only when evals show a clear benefit |
| `max` | Only when evals show it beats `xhigh` |

Third-party evidence, not OpenAI's: on Artificial Analysis effort curves checked 2026-09-22, Astra's pass rate rose with every effort level on AutomationBench and FrontierCode v1.1. The earlier GPT-6 Sol rose smoothly too and was weak below `medium`. GPT-6.1 Sol, Terra, and Luna have no curve on record, so treat their effort returns as unmeasured.

In Codex, set the model with `/model` or `-m`, and the effort under More reasoning in `/model` or with `model_reasoning_effort` in `config.toml`.

## Compare two models on your own work

1. Take one real task with an acceptance check: facts, audience, and voice for writing; the reopened record for computer use; regression tests and the rendered page for code.
2. Hold the model and inputs fixed and vary effort. Then run the next model up, each in a fresh session.
3. Compare the results first, counting the time spent reviewing or repairing each one. Keep the lighter setting only when the difference is one the user would not notice.
4. Then compare what `/status` reports, to learn what the heavier setting would cost in the window.
