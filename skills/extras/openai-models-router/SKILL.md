---
name: openai-models-router
description: Recommend the lightest OpenAI model and reasoning effort that still gives a great result for a task, session, or subagent, and say when a bigger model would change the outcome. Use when choosing among GPT-6 Luna, Terra, Sol, and Astra, or stretching a ChatGPT or Codex subscription's usage limits. Routes for this collection's own workflows come from shared/model-routing.json.
---

# OpenAI models router

Return one model and effort level for each step of the work, the reason, what the next tier would add, and the next rung if the pick falls short. This is a **recommendation, not survey**: name the pick, and mention a runner-up only when a measurement could flip it.

The skill recommends. It changes a model setting, an agent definition, or a config only when the user asks. A model the user names wins. A role this collection dispatches takes its model from `shared/model-routing.json`, and changing that file is a separate request.

Name models, not model IDs. OpenAI's own pages disagree on some IDs, so take them from the host's model list.

The skill assumes a subscription, where the budget is the usage window and not a token price. OpenAI publishes no single selection framework. The starting points, effort notes, and usage estimates are OpenAI's, read on 2026-11-10. The signs and the ladder are this skill's synthesis, so say which kind of claim decides a recommendation. Plan limits change without notice, so `/status` is the authority on what is left.

## Lightest sufficient pick

Result quality comes first. Decide what a great result is for the task, then make the **lightest sufficient pick**: the lightest model and effort that reaches it, where the next tier would not change the result in a way the user would notice. Never accept a visibly worse result to save usage. A failed attempt is the most expensive outcome in a usage window, because the retry pays for the work twice.

The next tier changes the result when:

- nobody will check the output, so a wrong judgment ships;
- the cause is unknown or the evidence conflicts;
- an early mistake compounds, as in a migration, an architecture decision, or a long unattended run;
- the last attempt failed on a wrong idea, not on a missed check.

It rarely does when a test, build, or diff checks the output, when the scope is one spec or a few files, when the task repeats a well-defined one, or when the last attempt failed for missing context. Supply the context or the check instead.

State the pick in those terms: _"Sol at `medium` is the **lightest sufficient pick**: the regression tests decide correctness, so Astra would not change the result."_

## Starting point

Start on Sol at `medium`, the model Codex recommends on paid plans, unless a row below fits better.

| Work | Model | Effort |
| --- | --- | --- |
| Fine-grained edits, well-scoped problems, simple data extraction | Luna | `low` |
| Finding current context across several apps, prioritizing work, problems with clear constraints | Luna | `xhigh` |
| Concise writing from supplied material, computer use with a defined outcome, scoped code fixes | Terra | `medium` |
| Complex technical work, coordinated deliverables | Sol | `medium` |
| Polished deliverables, connected visual systems, decisions from conflicting evidence | Sol | `xhigh` |
| Concise writing and content adaptation that must keep facts and nuance | Astra | `low` |
| Ambitious projects that need broad context and complete results | Astra | `medium` |
| Demanding analysis with exacting requirements | Astra | `xhigh` |

A small model at high effort is a pick in its own right here: the table pairs Luna and Sol with `xhigh` for harder work before the next model appears.

Set effort explicitly. Codex defaults Sol and Terra to `low`, and Sol's predecessor was weak below `medium`, so an unset effort can cost the result.

## Escalation ladder

When the pick falls short, climb the **escalation ladder** one rung at a time:

1. Give the model a way to verify its own work: regression tests for code, the rendered page for UI, reopening the saved record for computer use.
2. Raise effort one level with the model and inputs held fixed. Go to `xhigh` or beyond only while the result visibly improves.
3. Move to the next model up, starting at a lower effort than the smaller model used.

The rungs are not equally sized. By OpenAI's usage estimates, Terra draws about ten times what Luna does, Sol about twice Terra, and Astra three to five times Sol. Use up a model's effort range before a large step, and take the two-fold step from Terra to Sol sooner. The ladder also runs down, since one effort level lower may still pass.

Say which rung the recommendation is on: _"This is rung two of the **escalation ladder**: the regression tests already run, so raise Sol to `high` before moving to Astra."_

## Usage window

On Plus and Business a five-hour limit applies, and a weekly limit may apply on any plan. ChatGPT Work and Codex share them, and so do local and cloud tasks. These levers save usage without lowering the result:

- Keep the session lean. A long session that holds more context uses much more per message, so start a fresh one at a natural break.
- Give verbose reading to a subagent on a lighter model. A subagent workflow uses more tokens in total than a single agent, so delegate only reading and independent work.
- Prefer a local task to a cloud task, which can draw more.
- Leave Fast and Ultrafast off. They draw 2.5 and 8 times the usage for the same result.

## References

| Need | Read |
| --- | --- |
| Model facts, usage estimates, effort values and evidence, and how to compare two models | [references/models.md](references/models.md) |
| Subagent models and switching mid-task in Codex | [references/mixing-models.md](references/mixing-models.md) |
