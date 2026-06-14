---
name: feature-models-roundtable
description: End-to-end feature pipeline that chains models-roundtable (multi-model consensus answer) into implement-feature (multi-model task breakdown + TDD build). Thin orchestrator — it runs models-roundtable to reach a consensus understanding/plan for a feature request, resolves any open caveats with the user, then hands the settled answer to implement-feature, which breaks it into tasks and builds each with implement-and-review (cross-model review + full-review). Use when you want a feature taken from multi-model consensus understanding straight through to an implemented, reviewed, tested change ("roundtable then build", "consensus then implement", full multi-model feature pipeline). Distinct from models-roundtable (answer only, no code), implement-feature (build a plan, no consensus step), and implement-and-review (one task).
---

# Feature Models Round Table

Take a feature request from a **multi-model consensus** on what to build, straight through to an **implemented, reviewed, tested change**. This skill is intentionally **thin**: it sequences two existing skills and passes their artifacts. It does not re-implement either — to change how consensus or building works, change `models-roundtable` or `implement-feature`, not this skill.

Pipeline: **`models-roundtable` (answer → consensus) → `implement-feature` (decompose + build).**

## Steps

1. **Consensus understanding/plan.** Run **`models-roundtable`** on the feature request — frame the task for *it* as scoping/approach, e.g. *"Determine what this feature requires and the best approach: `<request>`."* Do **not** pre-analyze the request yourself; the bias-free fan-out is the point of `models-roundtable`. It returns a *Consensus answer* + *Agreements* + *Open caveats*, written to `.ai-workflow/roundtable/<id>/report.md`.

2. **Resolve caveats (gate).** If the report has *Open caveats* (low-confidence or orchestrator-decided points), settle them with the user before any code — unless `--auto`, then record an assumption per caveat. This satisfies `implement-feature`'s intake gate.

3. **Build.** Invoke **`implement-feature`** with the settled consensus as the plan (`--from-roundtable .ai-workflow/roundtable/<id>/report.md`). It takes the *Consensus answer* as the plan, breaks it into `to-tasks` vertical-slice tasks, runs `implement-and-review` per task (independent tasks in parallel, FE/BE cross-reviewed TDD), integrates in dependency order, then runs the feature-wide `full-review`, leaving tests/build green.

4. **Report.** Relay `implement-feature`'s final report, prefaced with the consensus summary and how any caveats were resolved. Return both report paths.

## Rules

- **Stay thin.** No duplicated logic. This skill only orchestrates the two and carries the handoff artifact (the roundtable report path).
- **Honor the handoff contract.** `models-roundtable` *Consensus answer* → the plan; *Open caveats* → a hard gate resolved before code.
- **Writes stay gated.** `models-roundtable` is read-only; `implement-feature` gates writes at its own Phase 0 approval (the task breakdown). Don't bypass either.
- **Degrade:** if the consensus shows the request needs no code (it's a question/decision), stop after step 1 and return the `models-roundtable` answer. If the work is a single task, `implement-feature` will just call `implement-and-review`. If build prerequisites are missing, the build skill degrades on its own — relay that.

## Gotchas

- Frame the request for `models-roundtable` as the *task to answer*; never paste your own interpretation in — let the seats answer blind.
- One session id threads both skills (`.ai-workflow/roundtable/<id>/` → `--from-roundtable`), so the build consumes exactly the consensus that was produced.
- This skill does not itself spawn seats, judges, or implementers — those live in the skills it calls (`models-roundtable` → seats/judges; `implement-feature` → `implement-and-review` → implementers).
