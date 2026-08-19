# Subagent role configuration research

Checked on 2026-08-19. This document is a recommendation only. It does not change any configuration.

## Decision

Create a small user scoped role layer after a short pilot. These skills run in many repositories, so role files under `~/.codex/agents/` give them one shared role catalog. Use project scoped roles only when one repository needs different instructions or tool access. Do not use either layer to replace the repository's runner based model panels or its existing worktree isolation.

Put personal defaults in `~/.codex/config.toml`. Put repository specific limits in `.codex/config.toml` and role definitions in `.codex/agents/*.toml`. Project configuration is loaded only for trusted projects. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) [Config basics](https://learn.chatgpt.com/docs/config-file/config-basic)

## What the current documentation supports

* `[agents]` can enable multi agent tools, set a concurrent thread cap, select default model and reasoning effort, and control interruption messages. An explicit spawn setting overrides the defaults. The thread cap excludes the primary thread. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) [Sample configuration](https://learn.chatgpt.com/docs/config-file/config-sample)

* Standalone custom role files belong in `.codex/agents/` for a project or `~/.codex/agents/` for a user. Each file requires `name`, `description`, and `developer_instructions`. A role can also set model, reasoning effort, sandbox, MCP servers, and skill configuration. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

* A custom role inherits the parent sandbox, MCP servers, and `skills.config` when its file does not override them. The parent turn can still apply its live sandbox and approval settings to a child. Start all new read only roles with `sandbox_mode = "read-only"`, but keep approvals in the parent turn. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

* The official guidance favors parallel agents for independent exploration, tests, triage, log analysis, research, and summarization. It warns that parallel write work creates merge conflicts and added coordination cost. Every child also uses model and tool tokens. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

* `gpt-5.6` is the suggested starting point for demanding, ambiguous work. `gpt-5.6-terra` fits faster read heavy work. `gpt-5.6-luna` fits narrow, repeatable work. Use `high` for review and security analysis, `medium` for normal workers, and `low` only for simple speed sensitive tasks. Higher effort increases time and token use. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

* At normal intelligence levels, delegation must be requested directly or be required by applicable project or skill instructions. Current local Codex clients enable the feature by default. ChatGPT Work can delegate proactively only with Ultra on eligible accounts and supported models. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

## Repository fit

The repository is already designed around bounded delegation. The pipeline keeps the conductor small and moves noninteractive phases into subagents with file based handoffs. [Workflow](workflow.md)

The repository supports an optional, gitignored `.rar-skills/config.local.yaml` for external runner seats, quorum, and work engine preferences. When present, keep that file as the source for its runner based model routing. Do not copy its model IDs into role files. [Local configuration](../_shared/references/local-config.md) [Model roster](../_shared/references/model-roster.md)

There is no tracked `.codex/` configuration layer in this repository now. The root `docs/` directory holds architecture and workflow documentation. `docs/solutions/` is reserved for one solved problem per learning record. This document therefore belongs in `docs/`, not in `docs/solutions/`. [Documentation store convention](solutions/README.md)

## Skills that already use delegation

### Native or generic subagent fanout

* `ship` calls for one worker per autonomous station and per slice after the user approval gate. [Ship](../ship/SKILL.md)

* `design-gate` runs up to three read only lens reviewers in parallel. [Design gate](../design-gate/SKILL.md)

* `review-gate` delegates close reading to eight parallel review personas and can use native subagents for every persona. [Review gate](../review-gate/SKILL.md)

* `full-review` has a parallel review phase for bug finders, personas, conditional specialists, and external model runners. [Full review](../full-review/SKILL.md)

* `coding-review-simplify` starts three reviewer subagents in standard and deep modes. [Coding review simplify](../coding-review-simplify/SKILL.md)

* `capture-learning` uses three parallel research agents plus a read only grounding validation pass in full mode. [Capture learning](../capture-learning/SKILL.md)

* `resolve-pr-feedback` judges comments centrally, then fans approved fixes out to generic fixer subagents. [Resolve PR feedback](../resolve-pr-feedback/SKILL.md)

* `dynamic-harness` has a manager mode that creates bounded agents or separate threads, with a run state and a defined write scope. [Dynamic harness](../dynamic-harness/SKILL.md)

### Worktree and model panel orchestration

* `implement-and-review` and `implement-feature` use isolated worktrees for parallel implementation. They already define implementer and reviewer behavior, bounded repair loops, and integration rules. [Implement and review](../implement-and-review/SKILL.md) [Implement feature](../implement-feature/SKILL.md)

* `models-consensus`, `diverse-plan`, `collaborative-delivery`, `peer-sessions`, and the panel modes of planning skills depend on independent runner seats or bounded peer sessions. Preserve their existing model roster and diversity rules. A generic subagent role must not silently replace a distinct runner seat. [Models consensus](../models-consensus/SKILL.md) [Diverse plan](../diverse-plan/SKILL.md) [Peer sessions](../peer-sessions/SKILL.md)

## Roles worth adding

Use new names. Do not define a role named `explorer` or `worker`, because a custom name matching a built in role takes precedence. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

### `code_mapper`

Use for read only codebase mapping, preflight evidence, test discovery, and problem localization. It fits `ship` phase 1, `design-gate`, early `diagnose`, and browser investigation preparation.

Set a fast read focused model such as `gpt-5.6-terra`, `model_reasoning_effort = "medium"`, and `sandbox_mode = "read-only"`. Require file and symbol references, a concise result, and no fix proposal unless the parent asks.

### `risk_reviewer`

Use for correctness, security, data, compatibility, and test gap review. It fits the read only part of `review-gate`, `full-review`, `coding-review-simplify`, and `design-gate`.

Set the strongest model available in the local catalog, with `model_reasoning_effort = "high"` and `sandbox_mode = "read-only"`. Require reproducible findings, file references, and no edits.

### `docs_researcher`

Use for version specific API checks and official documentation research. It fits `capture-learning`, external library checks during `full-review`, and research tasks that can return concise citations.

Set `gpt-5.6-terra` with medium effort first. Require primary sources, direct links, and a clear distinction between verified facts and inferences. Keep it read only.

## Roles not worth adding now

Do not add a generic implementation role. The built in `worker` role exists, and `implement-and-review` already owns implementation routing, worktree boundaries, tests, review loops, and evidence.

Do not add one role per skill. `skills.config` only enables or disables named skills. It does not replace the skill's own routing, runner probing, or state contract. Leave skill configuration inherited during the pilot. Disable a skill inside a role only after a measured, role specific conflict. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Do not use parallel writes in a shared worktree. Keep the parent as the sole writer, or use the isolated worktree contract that `implement-and-review` and `implement-feature` already require.

## Proposed pilot configuration

Use a personal default that is inexpensive for common read heavy delegation. Keep the current thread cap of 10 because the skills run outside this repository and `review-gate` can use eight personas plus follow up verification.

```toml
# ~/.codex/config.toml
[agents]
enabled = true
max_concurrent_threads_per_session = 10
default_subagent_model = "gpt-5.6-terra"
default_subagent_reasoning_effort = "medium"
interrupt_message = true
```

```toml
# ~/.codex/config.toml
[agents.code_mapper]
description = "Map code paths and gather evidence without edits."
config_file = "agents/code-mapper.toml"

[agents.risk_reviewer]
description = "Find correctness, security, compatibility, and test risks without edits."
config_file = "agents/risk-reviewer.toml"

[agents.docs_researcher]
description = "Verify version specific behavior against primary documentation."
config_file = "agents/docs-researcher.toml"
```

The value `10` is the existing local setting, not a product default. It is large enough for the repository's review workflows. Individual skills still keep their own lower in flight limits. The official sample uses `6` only as an example, and the product chooses a default when no cap is set. [Sample configuration](https://learn.chatgpt.com/docs/config-file/config-sample) [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

Each user role file should contain a narrow assignment. This is the shape to use after model availability is checked:

```toml
# ~/.codex/agents/code-mapper.toml
name = "code_mapper"
description = "Read only codebase mapper for evidence gathering before changes."
model = "gpt-5.6-terra"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Trace the real execution path. Cite files and symbols.
Return concise evidence. Do not edit files or propose a fix unless asked.
"""
```

Use the same required fields for `risk_reviewer` and `docs_researcher`. Pin the reviewer to an available stronger model only after checking the current local model catalog. Role level values take precedence over global defaults. [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

## Pilot plan and exit criteria

1. Inspect the current user configuration and model catalog without changing either.

2. Add the three user role files and register them in `~/.codex/config.toml` in one isolated change. Keep the existing cap of 10 and keep the current generic effort during the first smoke tests.

3. Run three controlled, read only prompts: one code map, one PR review, and one documentation research task. Ask explicitly for the named role and a short result with evidence.

4. Update only the generic read only delegation points to request the named roles. Run `review-gate`, `full-review`, `models-consensus`, and `implement-and-review` once each. Confirm that custom roles support the first two and do not change the runner roster, model receipts, or worktree isolation of the latter two.

5. If role selection works, change the generic subagent effort from `max` to `medium`. Keep the configuration only if the results have clear evidence, the reviewer finds useful issues, the main thread stays concise, and no role starts an unauthorized write. Otherwise remove the role that failed the test rather than expanding the configuration.

6. Add per role `skills.config` overrides only after the pilot identifies an unnecessary or conflicting skill. Do not disable inherited skills without observed evidence.

## Sources

* [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

* [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

* [Sample configuration](https://learn.chatgpt.com/docs/config-file/config-sample)

* [Config basics](https://learn.chatgpt.com/docs/config-file/config-basic)
