# Selection evidence

Updated 20 September 2026. The prior research below was checked 19 September 2026. Source IDs V1 and later resolve to exact URLs in `shared/model-routing.json`, under `validation_research.sources`. The collection keeps model identifiers in that central file, including identifiers in source URLs. This is a dated research record, not a second model configuration. Exact defaults and efforts live only in `shared/model-routing.json`. Recheck changed prices and capabilities when maintaining that configuration; do not browse before every validation run.

## Current selection policy

The central `economy` profile replaces the prior validation default. It selects a
routine executor for settled implementation, test authorship, and interactive
browser work, with independent routine review and strong planning and risk roles.
The `balanced` profile retains the earlier selection as an option. Resolve exact
models and effort only from the central configuration; this record adds no second
default table. Existing tests run directly without a separate model worker.

The selection considers task completion, latency, token use, adapter controls,
and price. No local comparison has established quality or savings for the new
profile. Published maximum effort scores do not prove the same result at another
setting. Keep one initial attempt and one repair with new evidence before a
selected reasoning fallback; all attempts share the original ceilings.

## Candidate and privacy evidence, 20 September 2026

The [model catalogue](https://openrouter.ai/api/v1/models) listed GLM 5.3 Flash,
DeepSeek V4.1 Flash, Qwen 3.8 Flash, MiMo V2.5, Qwen 3.6 Plus, and Kimi K2.7 Code
with tool and image support at inspection. Their exact IDs and selectable seats
live in the central configuration. The existing Qwen Max and Kimi K3 seats keep
their meanings. Candidates are alternatives, not extra mandatory calls.

The [public ZDR endpoint catalogue](https://openrouter.ai/api/v1/endpoints/zdr)
listed GLM, DeepSeek, MiMo, and Kimi routes. It listed neither Qwen candidate.
Strict privacy therefore blocks Qwen Flash and Qwen Plus until an eligible
endpoint is verified. Catalogue presence is not account access or proof that all
selected capabilities and privacy controls work together.

The [GLM publisher model card](https://huggingface.co/zai-org/GLM-5.3-Flash)
accepts `low`, `high`, and `max`. An omitted or unrecognized value selects `max`,
so generic `medium` can defeat a selected lower setting. Verify the explicit
serialized reasoning value. Candidates without selectable effort, including the
listed MiMo, Qwen, and Kimi Code routes, need runtime controlled effort, not an
invented common level. Read each model's capability record before dispatch.

[Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
documents `zdr`, `data_collection`, `require_parameters`, provider allowlists, and
fallback controls. Carry the selected policy into actual requests and retain its
sanitized digest. Model author, gateway, and inference host are distinct facts.
[ZDR guidance](https://openrouter.ai/docs/guides/features/zdr) permits some in
memory prompt caching and does not establish browser service privacy. Account
or key guardrails need actual readback before they can be reported.

The GLM gateway page (source V7) marked its lowest
listed rate as promotional. Recheck endpoint rates for a dated estimate; do not
treat a discount, token rate, or forecast as an enforced spending cap. Compare
all coordinator, worker, reviewer, and failed attempt costs per accepted result.

## Browser evidence, 20 September 2026

[Playwright test practices](https://playwright.dev/docs/best-practices) support
isolated tests, resilient locators, web assertions, and trace based debugging.
Use an existing Playwright Test suite directly for repeatable acceptance and CI.
The [Playwright CLI repository](https://github.com/microsoft/playwright-cli) and
[MCP comparison](https://playwright.dev/mcp/introduction) explain the shell
interface and context tradeoff. CLI with its skill is the first exploration
candidate when ready; MCP needs an interface or inspection reason.
The [agent-browser repository](https://github.com/vercel-labs/agent-browser)
documents an alternative with compact references, sessions, and diagnostics.
Native tools can supply authenticated sessions or native capabilities unavailable
to an external process. These sources do not prove the lowest cost mechanism for
this repository.

Reuse the target stack and one driver per journey. Browser smoke cannot install
a missing stack. An external Pi worker needs command access, driver instructions,
and actual readiness evidence. For visual work, a synthetic artifact must reach
the adapter as typed image input; a text path is insufficient. No business browser
run or paid model comparison was performed for this documentation update.

## Prior comparison evidence, 19 September 2026

| Evidence | Finding used | Limit |
| --- | --- | --- |
| [Artificial Analysis, July 9](https://artificialanalysis.ai/articles/gpt-5-6-has-landed) | Coding Agent Index scores at maximum effort were Sol 80, Terra 77, Luna 75. Luna's task cost was about 80% below Sol. The intelligence cost frontier favored Luna and Sol over Terra. | Harness dependent coding results, not a unit test or browser ranking. July launch prices are stale. |
| Artificial Analysis, September 9 (source V1) | Astra tied Fable 5.1 in its coding index at about 60% of Fable's task cost. Lower token use offset some of its higher token price. | Averages across difficult tasks do not justify a frontier model for polling or deterministic execution. |
| [Artificial Analysis effort comparison](https://artificialanalysis.ai/models/releases/comparisons) | At inspection, Astra medium and high had intelligence scores 50 and 51; reported task costs were $1.54 and $1.72. First answer latency differed substantially. | An aggregate intelligence index cannot prove test quality. Latency includes workload and reasoning effects. |
| Sonnet provider release (source V2) | The provider reports improved computer use cost efficiency at medium effort. The current permanent price is $2 input and $10 output per million tokens. | Provider evidence, not independent proof. The page corrects earlier charts and prices. |
| [Browser Use benchmark](https://browser-use.com/benchmarks/agents) and [method report](https://browser-use.com/posts/what-model-to-use) | Browser tests evaluate complete task success, time, and cost in a specific harness. Results differ across providers and model versions. | The June method report tests older variants. A generic family label does not identify a current exact model or effort. Do not rank current Luna against Sonnet from it. |

Prices recorded on 19 September 2026, USD per million tokens, provide historical scale only:

| Candidate | Input | Output | Source |
| --- | ---: | ---: | --- |
| Luna | 0.20 | 1.20 | Provider model page (source V3) |
| Terra | 2.00 | 12.00 | Provider model page (source V4) |
| Sol | 4.00 | 20.00 | Provider model page (source V5) |
| Astra | 10.00 | 50.00 | Provider model page (source V6) |
| Sonnet | 2.00 | 10.00 | Provider release and August pricing correction (source V2) |
| Fable 5.1 | 10.00 | 50.00 | [Provider page](https://www.anthropic.com/claude/fable) |
| Grok 4.7 | 2.00 | 6.00 | [Provider documentation](https://docs.x.ai/developers/grok-4-7) |
| Gemini 3.8 Flash | 0.75 | 3.75 | [Provider release](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) |

These prices exclude tool fees and special modes. Cache reads/writes, long context, provider routing, and subscriptions change actual cost. Fable's low cache read price can matter for repeated long prompts. That does not make a long context free. Compare all attempts per accepted result, not price per output token alone.

Community evidence is mixed and receives less weight. A [July comparison](https://www.reddit.com/r/AIDiscussion/comments/1uso1sr/tested_gpt56_sol_against_claude_fable_5_on_the/) reports much lower Sol token use but better Fable quality, without a controlled task corpus. A [September agent comparison](https://www.reddit.com/r/better_claw/comments/1w74hib/gpt6_astra_vs_fable_51_vs_sonnet_5_on_real_agent/) favors cheaper models for routine work and Astra for computer use or operations. Its quoted Sonnet price is outdated. Neither anecdote supplies a general savings estimate or establishes equivalence.

The prior selection used a bounded test author, stronger integration and expected
behavior design, and a capable browser worker. It remains selectable through
`balanced`; it no longer defines the workflow default. Terra, Grok, Gemini, and
Fable remain options under a selected exact route and verified capabilities.
Price or benchmark rank alone does not justify a fallback or an extra reviewer.

Only the central routing file turns this policy into exact choices. A native route may be preferable to a runner because the required browser or repository tools exist only there. If selected tools or receipt guarantees are absent, disclose that fact before approval. Never silently switch to an available model.

For local evaluation, compare a routine UI flow, an authorization sensitive mutation, and an async or concurrency case under identical acceptance checks. Use existing baseline evidence where valid. Measure complete success, missed defects, repairs, elapsed time, every model call, uncached input, cached input, output, and reported cost. Keep the cheaper route only if independent acceptance holds. A small trial does not prove universal quality or savings. Paid comparisons need an approved scope and ceiling.
