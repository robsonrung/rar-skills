# Mixing OpenAI models in Codex

Use more than one model only when the result is as good as the main model alone would give. A subagent workflow uses more tokens in total than a single agent, so the gain comes from running the reading at a lighter model's rate and keeping the main session's context small.

## Subagent models

A subagent inherits the parent's model and effort unless something sets them. In order of precedence:

1. A custom agent file that sets `model` or `model_reasoning_effort`.
2. A model named in the spawn request.
3. `agents.default_subagent_model` and `agents.default_subagent_reasoning_effort` in `config.toml`.

A spawn that names a model and no effort gets that model's default effort, which is `low` for Sol and Terra. Name the effort too.

OpenAI suggests Sol for most subagent tasks and Luna for lighter ones. Give the lighter model work whose mistakes are cheap to spot, and keep code edits and judgment calls on the main model.

Astra can delegate less often than wanted. Say in the prompt when to delegate and how much.

## Switching mid-task

A switch to another model family drops the earlier reasoning, which can lower the result on the rest of the task. Prefer raising effort on the same model where that is enough, and switch models at a natural break with a short written summary of the work so far.
