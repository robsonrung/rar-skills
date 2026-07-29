# Trigger-collision audit — compound-engineering-plugin ports

Phase A governance record (2026-07-22). Every new skill or graft from the porting effort was checked against the repo's existing skills and the installed user-level (`~/.claude/skills`) set for routing collisions before landing. De-confliction lives in each skill's own `description:`; this file records the audit outcome. Re-run this audit for any future addition (rule: a new skill may not land without a row here or in a successor record).

| New skill | Nearest existing triggers | De-confliction |
|---|---|---|
| open-pr | ship (full pipeline), implement-and-review (never pushes/PRs), git-guardrails-claude-code | Description scopes to composing/opening PRs and PR-description-only flows; ship delegates PR composition here. |
| resolve-pr-feedback | full-review, /review builtin, resolving-merge-conflicts | Description states full-review *finds* issues and never resolves threads; merge-conflicts skill is git conflicts, not review threads. |
| capture-learning | lesson-learned, summarize, context-compress | Description contrasts with lesson-learned (ephemeral, chat-only, no store) and session-continuity skills. |
| session-handoff | summarize, context-compress, installed `handoff` | Description covers store+resume; context-compress delegates its save step; installed single-slot handoff superseded (retired at install). |
| worktree | implement-and-review (internal worktree flow) | Description scopes to user-initiated isolation/attach; implement-and-review keeps its internal flow. |
| browser-smoke | qa-execution, qa, full-review | Description states qa-execution is whole-product release QA; browser-smoke is diff-scoped PR smoke only. |
| agent-architecture-lens (2026-07-28) | data-systems-coding-lens (retries/idempotency), macro-architecture (system shape), knowledge-graph (agent-facing graphs), dynamic-harness / codex-mission-control (orchestration skills, not lenses) | Description scopes to the control flow of an LLM agent the user is *building* — loop vs state graph, agent state, bounded retries, termination ceilings. It names all three nearest lenses explicitly: data-systems-coding-lens covers retries and idempotency for stored state (databases, queues, caches) rather than agent steps; macro-architecture decomposes services and assigns data ownership; knowledge-graph builds a graph an agent *reads*, not the graph an agent *runs on*. The orchestration skills are not competitors — they are consumers, and now cite this lens's leitwörter via `_shared/references/run-state-contract.md`. |

Grafts (no new trigger surface): full-review (findings mechanics + doc-review dimension), skill-expert (authoring references), ship (residual-findings, local-only, evidence gate, routing carriers), coding-design-plan (test-scenario contract, scoping gate), to-tasks (stable U-IDs), decision-council (POV contracts), coding-review-simplify (personas), brainstorm (blindspot pass, idea-basis mode), systematic-debugging/diagnosing-bugs (pipeline-mode contract), visual-recap/teach (retention mechanics), qa-execution (dogfood skeleton).

Deferred names reserved (no skill yet, gated per plan): watch-pr, feedback-sweep, refresh-learnings, product-strategy, metric-optimize, product-pulse, launch-copy, recording-feedback.
