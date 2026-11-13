# Mixing Claude models

Use more than one model only when the result is as good as the main model alone would give. The gain is usage: the main model's context stays small, and the reading happens at a lighter model's rate.

## Subagents on smaller models

A subagent runs in its own context window and returns a summary. Its requests still draw on the plan's limits, at its own model's rate. Give it work whose mistakes are cheap to spot: finding files, running tests, reading logs.

In Claude Code:

- Set `model: haiku` or `model: sonnet` in the subagent definition. `CLAUDE_CODE_SUBAGENT_MODEL` sets the default for subagents that name none. A subagent that names none inherits the session's model, including after a `/model` switch.
- The built-in Explore subagent runs on the session's model. To keep exploration light, define a subagent named `Explore` with `model: haiku`.
- The `opusplan` alias plans on Opus and executes on Sonnet, which puts the code edits on the smaller model. Compare its results with Opus alone before making it a default.

## Switch at a natural break

The prompt cache belongs to the model that wrote it, so the first turn on a new model rereads the whole conversation uncached. Shrink that turn first: run `/compact`, or start a fresh session from a short written plan.

A thinking block records its model, and a model reads only blocks from its own tier or below:

| Model | Reads thinking blocks from |
| --- | --- |
| Fable 5.2 | Opus 5.5, Sonnet 5.5, Haiku 5.5 |
| Opus 5.5 | Sonnet 5.5, Haiku 5.5 |
| Sonnet 5.5 | Haiku 5.5 |

Moving down a tier therefore loses the earlier reasoning, and so does any move away from Fable 5.2. The loss is silent, and it can lower the result on the rest of the task.

## A lead with lighter workers

For work larger than one context window, a top-tier lead can split the task, hand the pieces to lighter workers in parallel, and merge the results. On a defect search over about 22 million tokens of source, an Opus 5.5 lead with up to 25 Sonnet 5.5 workers scored about the same as Opus 5.5 alone and cost about a third less at API prices.

Skip it for one chain of dependent steps, or for work that fits in one context window. There the planning and merging use more than they save.

## Settings

- `/model` switches the model. Enter saves it as the default, and `s` applies it to the session only. `/effort <level>` sets effort, and `/effort auto` clears a saved level.
- Aliases: `default` and `best` resolve to Opus 5.5 on paid plans, and `opus`, `sonnet`, `haiku`, and `fable` to the current model of each tier.
- When a request is flagged by a safety classifier, Claude Code can rerun it on an older model, and a transcript notice names that model. Fable 5.2 falls back to Opus 4.8 for cybersecurity content and to Opus 5 for biology. A result from a fallback is not the routed model's result.
