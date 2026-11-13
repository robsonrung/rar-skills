---
name: claude-models-router
description: Recommend the lightest Claude model and effort level that still gives a great result for a task, session, or subagent, and say when a bigger model would change the outcome. Use when choosing among Haiku, Sonnet, Opus, and Fable, or stretching a Claude subscription's usage limits. Routes for this collection's own workflows come from shared/model-routing.json.
---

# Claude models router

Return one model and effort level for each step of the work, the reason, what the next tier would add, and the next rung if the pick falls short. This is a **recommendation, not survey**: name the pick, and mention a runner-up only when a measurement could flip it.

The skill recommends. It switches a session's model, edits a subagent definition, or changes a config only when the user asks. A model the user names wins. A role this collection dispatches takes its model from `shared/model-routing.json`, and changing that file is a separate request.

Name tiers, not model IDs. IDs and aliases differ by platform, so take them from the host.

The skill assumes a subscription, where the budget is the usage window and not a token price. The starting points and figures are Anthropic's, published 2026-11-09, with plan rules read on 2026-11-10. The signs below are this skill's reading of them. Plan limits change without notice, so `/usage` is the authority on what is left.

## Lightest sufficient pick

Result quality comes first. Decide what a great result is for the task, then make the **lightest sufficient pick**: the lightest model and effort that reaches it, where the next tier would not change the result in a way the user would notice. Never accept a visibly worse result to save usage. A failed attempt is the most expensive outcome in a usage window, because the retry pays for the work twice.

The next tier changes the result when:

- nobody will check the output, so a wrong judgment ships;
- the cause is unknown or the evidence conflicts;
- an early mistake compounds, as in a migration, an architecture decision, or a long unattended run;
- the last attempt failed on a wrong idea, not on a missed check.

It rarely does when a test, build, or diff checks the output, when the scope is one spec or a few files, when the task repeats a well-defined one, or when the last attempt failed for missing context. Supply the context or the check instead.

State the pick in those terms: _"Sonnet 5.5 at `medium` is the **lightest sufficient pick**: the tests decide correctness, so Opus 5.5 would not change the result."_

## Starting point

Start on Opus 5.5 at `medium`, the Claude Code default on every paid plan, unless a row below fits better.

| Work | Model | Effort |
| --- | --- | --- |
| Classification, routing, tagging, high-volume extraction | Haiku 5.5 | `medium` |
| Subagents that search files, read logs, or summarize | Haiku 5.5 or Sonnet 5.5 | The model's default |
| Quick interactive replies | Sonnet 5.5 | `low` or `medium` |
| Well-scoped coding: a bug fix, a feature built against a spec | Sonnet 5.5 | `medium`, then `high` |
| Everyday documents, slides, spreadsheets | Sonnet 5.5 | `medium` |
| Repeated, well-defined agent tasks: investigation, review, drafting | Sonnet 5.5 | `medium` |
| Everyday engineering, debugging, multi-PR features | Opus 5.5 | `medium`, then `high` |
| Computer use and vision-heavy loops | Opus 5.5 | `medium` |
| Major refactors and migrations, architecture planning, leading many subagents | Fable 5.2 | `medium`, then `high` |
| Deep research, scientific or quantitative analysis | Fable 5.2 | `medium`, then `high` |

Difficulty decides the tier, not how well the work is specified. A migration or a performance fix can have a clear spec and still need Opus 5.5, or Fable 5.2 when it is major. A complex financial model, or a document built from a large pile of sources, starts on Opus 5.5.

A small model fits work whose mistakes are cheap to spot. Keep code edits and judgment calls on the main model, because a small model's misread search result sends the main model to the wrong file.

Fable 5.2 draws on its own weekly limit on Max and Ultra and needs usage credits on Pro, so keep it for work where it changes the result. Mythos 5.2 is not generally available; recommend it only to a user who has it through a verification program.

## Escalation ladder

When the pick falls short, climb the **escalation ladder** one rung at a time:

1. Give the model a way to verify its own work: a test, a build, a script that calls the endpoint. This often improves the result more than extra effort does.
2. Raise effort one level. Effort buys longer thinking, more tool calls, and self-checking. It cannot supply knowledge or skill the model lacks.
3. Move to the next model up, starting at a lower effort than the smaller model used.

Past `high` the returns are small: on Opus 5.5, `xhigh` adds about 1.4 points for about 2.5 times the usage. Test Fable 5.2 at a lower effort instead. The ladder also runs down. Opus 5.5 at `medium` scores about 2.5 points under `high` for about 70% of the usage, so `medium` is often sufficient.

Say which rung the recommendation is on: _"This is rung two of the **escalation ladder**: the tests already run, so raise Sonnet 5.5 to `high` before moving to Opus 5.5."_

## Usage window

A five-hour session limit and a weekly limit apply together, shared by the Claude apps, Claude Code, and every subagent. Model tier, effort, and conversation length all draw on them. These levers save usage without lowering the result:

- Keep the main context lean, since every turn resends it. Compact or start a fresh session at a natural break.
- Give verbose reading to a subagent on a smaller model.
- When outcomes can be checked automatically, run everything at `low` and rerun only the failures at `high`. This passed more tasks than running everything at `high`.
- Switch models at a natural break, never mid-task: the new model rereads the whole conversation uncached and can lose the earlier reasoning.

Fast mode bills to usage credits on individual plans, so leave it off.

## References

| Need | Read |
| --- | --- |
| Model facts, quality evidence, plan limits, and how to compare two models | [references/models.md](references/models.md) |
| Subagent models, switching mid-task, a lead with workers, Claude Code settings | [references/mixing-models.md](references/mixing-models.md) |
