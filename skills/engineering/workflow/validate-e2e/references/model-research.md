# Selection evidence

Checked 19 September 2026. Source IDs V1 and later resolve to exact URLs in `shared/model-routing.json`, under `validation_research.sources`. The collection keeps model identifiers in that central file, including identifiers in source URLs. This is a dated research record, not a second model configuration. Exact defaults and efforts live only in `shared/model-routing.json`. Recheck changed prices and capabilities when maintaining that configuration; do not browse before every validation run.

The recommendation balances task completion, latency, token use, adapter controls, and price. There is no public benchmark that proves the best model and effort for every validation class in this repository. The proposed medium and high settings are task fit judgments. Broad coding scores often use maximum effort and do not prove the same score at a lower setting.

| Evidence | Finding used | Limit |
| --- | --- | --- |
| [Artificial Analysis, July 9](https://artificialanalysis.ai/articles/gpt-5-6-has-landed) | Coding Agent Index scores at maximum effort were Sol 80, Terra 77, Luna 75. Luna's task cost was about 80% below Sol. The intelligence cost frontier favored Luna and Sol over Terra. | Harness dependent coding results, not a unit test or browser ranking. July launch prices are stale. |
| Artificial Analysis, September 9 (source V1) | Astra tied Fable 5.1 in its coding index at about 60% of Fable's task cost. Lower token use offset some of its higher token price. | Averages across difficult tasks do not justify a frontier model for polling or deterministic execution. |
| [Artificial Analysis effort comparison](https://artificialanalysis.ai/models/releases/comparisons) | At inspection, Astra medium and high had intelligence scores 50 and 51; reported task costs were $1.54 and $1.72. First answer latency differed substantially. | An aggregate intelligence index cannot prove test quality. Latency includes workload and reasoning effects. |
| Sonnet provider release (source V2) | The provider reports improved computer use cost efficiency at medium effort. The current permanent price is $2 input and $10 output per million tokens. | Provider evidence, not independent proof. The page corrects earlier charts and prices. |
| [Browser Use benchmark](https://browser-use.com/benchmarks/agents) and [method report](https://browser-use.com/posts/what-model-to-use) | Browser tests evaluate complete task success, time, and cost in a specific harness. Results differ across providers and model versions. | The June method report tests older variants. A generic family label does not identify a current exact model or effort. Do not rank current Luna against Sonnet from it. |

Current standard text prices, USD per million tokens, provide scale only:

| Candidate | Input | Output | Source |
| --- | ---: | ---: | --- |
| Luna | 0.20 | 1.20 | Provider model page (source V3) |
| Terra | 2.00 | 12.00 | Provider model page (source V4) |
| Sol | 4.00 | 20.00 | Provider model page (source V5) |
| Astra | 10.00 | 50.00 | Provider model page (source V6) |
| Sonnet | 2.00 | 10.00 | Provider release and August pricing correction (source V2) |
| Fable 5.1 | 10.00 | 50.00 | [Provider page](https://www.anthropic.com/claude/fable) |
| Grok 4.6 | 2.00 | 6.00 | [Provider documentation](https://docs.x.ai/developers/grok-4-6) |
| Gemini 3.8 Flash | 0.75 | 3.75 | [Provider release](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/) |

These prices exclude tool fees and special modes. Cache reads/writes, long context, provider routing, and subscriptions change actual cost. Fable's low cache read price can matter for repeated long prompts. That does not make a long context free. Compare all attempts per accepted result, not price per output token alone.

Community evidence is mixed and receives less weight. A [July comparison](https://www.reddit.com/r/AIDiscussion/comments/1uso1sr/tested_gpt56_sol_against_claude_fable_5_on_the/) reports much lower Sol token use but better Fable quality, without a controlled task corpus. A [September agent comparison](https://www.reddit.com/r/better_claw/comments/1w74hib/gpt6_astra_vs_fable_51_vs_sonnet_5_on_real_agent/) favors cheaper models for routine work and Astra for computer use or operations. Its quoted Sonnet price is outdated. Neither anecdote supplies a general savings estimate or establishes equivalence.

The resulting policy is to use a cheap bounded test author, a stronger integration and oracle designer, a cost efficient interactive browser worker, and a frontier lead only for exposed risk or difficult diagnosis. Terra remains selectable, but the reviewed cost frontier does not make it the default compromise. Grok is a credible custom option with a verified receipt path; its lower sticker price alone does not prove lower repair cost. Gemini is a credible alternative, but the current collection adapter cannot pin model and effort, so it is not the default exact route. Fable remains a user selectable specialist; strong benchmark results do not justify a mandatory second frontier opinion.

Only the central routing file turns this policy into exact choices. A native route may be preferable to a runner because the required browser or repository tools exist only there. If selected tools or receipt guarantees are absent, disclose that fact before approval. Never silently switch to an available model.

For local evaluation, compare a routine UI flow, an authorization sensitive mutation, and an async or concurrency case under identical acceptance checks. Use existing baseline evidence where valid. Measure complete success, missed defects, repairs, elapsed time, every model call, uncached input, cached input, output, and reported cost. Keep the cheaper route only if independent acceptance holds. A small trial does not prove universal quality or savings. Paid comparisons need an approved scope and ceiling.
