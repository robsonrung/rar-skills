---
name: feature-models-round-table
description: End-to-end feature pipeline that chains models-round-table (multi-model consensus answer) into implement-and-review (multi-model TDD build). Thin orchestrator — it runs models-round-table to reach a consensus understanding/plan for a feature request, resolves any open caveats with the user, then hands the settled answer to implement-and-review to break into tasks and build with cross-model review + full-review. Use when you want a feature taken from multi-model consensus understanding straight through to an implemented, reviewed, tested change ("round-table then build", "consensus then implement", full multi-model feature pipeline). Distinct from models-round-table (answer only, no code) and implement-and-review (build only, no consensus step).
---

# Feature Models Round Table

Take a feature request from a **multi-model consensus** on what to build, straight through to an **implemented, reviewed, tested change**. This skill is intentionally **thin**: it sequences two existing skills and passes their artifacts. It does not re-implement either — if you need to change how consensus or building works, change `models-round-table` or `implement-and-review`, not this skill.

Pipeline: **`models-round-table` (answer → consensus) → `implement-and-review` (build).**

## Steps

1. **Consensus understanding/plan.** Run **`models-round-table`** on the feature request — frame the task for *it* as scoping/approach, e.g. *"Determine what this feature requires and the best approach: `<request>`."* Do **not** pre-analyze the request yourself; that bias-free fan-out is the point of `models-round-table`. It returns a *Consensus answer* + *Agreements* + *Open caveats*, written to `.ai-workflow/roundtable/<id>/report.md`.

2. **Resolve caveats (gate).** If the report has *Open caveats* (low-confidence or orchestrator-decided points), settle them with the user before any code — unless `--auto`, then record an assumption per caveat. This satisfies `implement-and-review`'s intake gate.

3. **Build.** Invoke **`implement-and-review`** with the settled consensus as the task (`--from-roundtable .ai-workflow/roundtable/<id>/report.md`). It takes the *Consensus answer* as the settled task, breaks it into `to-tasks` vertical slices, runs the FE/BE cross-reviewed TDD build (independent slices in parallel) per slice acceptance, then the final `full-review`, leaving tests/build green.

4. **Report.** Relay `implement-and-review`'s final report, prefaced with the consensus summary and how any caveats were resolved. Return both report paths.

## Rules

- **Stay thin.** No duplicated logic. This skill only orchestrates the two and carries the handoff artifact (the round-table report path).
- **Honor the handoff contract.** `models-round-table` *Consensus answer* → the settled task; *Open caveats* → a hard gate resolved before code.
- **Writes stay gated.** `models-round-table` is read-only; `implement-and-review` gates writes at its own Phase 0 approval. Don't bypass either.
- **Degrade:** if the consensus shows the request needs no code (it's a question/decision), stop after step 1 and return the `models-round-table` answer. If `implement-and-review`'s prerequisites are missing, it degrades on its own — relay that.

## Gotchas

- Frame the request for `models-round-table` as the *task to answer*; never paste your own interpretation in — let the seats answer blind.
- One session id threads both skills (`.ai-workflow/roundtable/<id>/` → `--from-roundtable`), so the build consumes exactly the consensus that was produced.
- This skill does not itself spawn seats, judges, or implementers — those live in the two skills it calls.
