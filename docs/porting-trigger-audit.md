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

---

# Successor record — pipeline consolidation (2026-07-30)

A repo-wide restructuring pass. Goal: one workflow, the fewest user-called skills per step, no duplicated knowledge. Every skill below was checked against the surviving set for routing collisions before landing; de-confliction lives in each skill's own `description:`.

## New skills

| New skill | Nearest existing triggers | De-confliction |
|---|---|---|
| interview | brainstorm (frame/verdict), to-spec (writes the PRD), collaborative discovery (now brainstorm's panel mode) | Description scopes to the interactive requirements interview *between* framing and the PRD: brainstorm decides WHETHER to build, `interview` pins down WHAT to build, `to-spec` synthesizes it without interviewing. Fills the role previously routed to the absent `grill-with-docs`. |
| tdd | safe-incremental-coding (legacy net), test-lens (judges tests), clean-code (tidies tested code), diagnose (root-cause) | Description scopes to the red-green-refactor execution loop and states the entry rule (untested legacy → `safe-incremental-coding` first, then return). Negative-triggers test-after backfilling. Replaces the previously external `tdd`. |
| diagnose | fable-mindset (diagnosis posture), tdd (the loop), full-review (finds issues in a diff) | Description scopes to procedural root-causing of a specific failure; `fable-mindset` owns the epistemic posture, this skill owns the steps. Carries a non-interactive `mode:pipeline` contract for autonomous callers. Replaces the previously external `diagnose`. |
| prototype | coding-design-plan (holds the tracer-vs-prototype rule), brainstorm, tdd | Description scopes to throwaway spikes that answer a design question only running code can settle, and states the throw-it-away rule; the tracer-bullet alternative is decided in `coding-design-plan`. Replaces the previously external `prototype`. |
| fable-mindset | the five former `fable-*` skills; coding-design-plan, clean-code, tdd, diagnose, summarize | One skill covering five moments of a working turn (intake, diagnosis, decision, implementation, reporting). Description states it governs posture, not procedure, and negative-triggers each procedural counterpart. Replaces five separate trigger surfaces with one. |

## Merges and dissolutions (no new trigger surface)

| Change | Rationale |
|---|---|
| `models-roundtable` + `council` + `decision-council` → `models-consensus` (modes `poll` / `debate` / `personas`, plus `clarify` and `decider_context: report_only` flags) | Four skills ran the same five-stage pipeline with six differing knobs, four copies of the seat roster, and a trigger collision on "council this". `poll` (the former roundtable protocol) is the default and the pipeline-facing mode; `personas` is also the degradation path below quorum. The merged skill never auto-executes — the old `council --auto` implementation race is gone. |
| `collaborative_discovery` → `brainstorm` panel mode; `collaborative_specification` → `to-spec` panel mode; `collaborative_task_design` → `to-tasks` panel mode | Each pair produced the same artifact for the same pipeline step, differing only in how many models participated. Panel mode is now an opt-in section of the canonical skill, so the multi-model path inherits the Slice Contract, the security-gate handshake, and the approval gate it previously lacked. Shared panel scripts and engineering rules moved to `_shared/`. |
| `design-integrity` → `software-design-philosophy` | Every workflow step had a stronger owner in the Ousterhout lens; the surviving payload was the vocabulary (`conceptual integrity`, `change ownership`, `smallest coherent shape`), which moved verbatim with its CI guard. |
| `architecture_session_review` dissolved | Its lens selection duplicated `design-gate`, its scope classifier duplicated `coding-design-plan`, and its only inbound reference was a fallback row it could not legally serve (it instructed implementation inside a read-only gate). References harvested into `architecture-lens` (risk pass, C4 guidance, verification menu), `macro-architecture` (Least Worst Rule, three missing styles), and `coding-review-simplify` (team checklists). |
| `coding-implementation-guard` deleted | A lossy recombination of `clean-code`, `data-systems-coding-lens`, `coding-review-simplify`, and `safe-incremental-coding`, with four near-verbatim duplications. Its output contract and scope gotchas moved into `tdd`. |
| `pragmatic-coding-session` deleted | Six of its seven phases handed off to the skill that owned them. Relocated: the `smallest reversible move` leitwort and loop rules → `tdd`; tracer/prototype and estimation rules → `coding-design-plan`; process-resource ownership and hidden time ordering → `data-systems-coding-lens`. |
| `feature-models-roundtable` deleted | Fully contained in `implement-feature`'s Phase 0, which already documents the consensus handoff. Its three unique rules moved there. |
| `codex-mission-control` → `dynamic-harness` | The two shared their preflight, agent contract, write-scope rules, and ledger discipline; the merged skill keeps the six-pattern selector and adds a manager-mode section plus `start_mission.py`. |

## Deferred names still reserved

watch-pr, feedback-sweep, refresh-learnings, product-strategy, metric-optimize, product-pulse, launch-copy, recording-feedback.

---

# Successor record — gated review port (2026-08-14)

Methodology ported from a private review-orchestrator service and fully generalized; no upstream-specific vocabulary retained. Both skills were checked against the surviving set for routing collisions before landing; de-confliction lives in each skill's own `description:`.

| New skill | Nearest existing triggers | De-confliction |
|---|---|---|
| review-gate | full-review (PR/diff review, verdicts), code-review (standards/spec axes), design-gate / security-gate (gate family, pre-implementation), models-consensus (multi-seat fan-out, deliberation-only) | Description states full-review is the deep human-facing review (bughunt, security audit, ultrareview); review-gate is the merge gate — declared coverage contract with honesty accounting, persona fan-out with an adversarial refutation pass, and a machine-consumable result JSON an automated follow-up run can consume. The gate family's other members run before implementation; review-gate gates the finished diff. It never publishes to the code host. |
| verify-changes | tdd (owns the implementation loop), diagnose (fixes failures), browser-smoke (browser leg), harness `run` (launches the app), full-review Phase 4 (verifies findings, not repo gates) | Description scopes to deterministic execution of the repo's own discovered checks with captured evidence — it never fixes (failures route to diagnose), never judges code, and never launches the app interactively. Named as review-gate's pipeline verification phase, mirroring how browser-smoke names ship. |

---

# Successor record — distributed-systems-patterns (2026-08-18)

Book-grounded design lens from Burns, *Designing Distributed Systems*. Checked against the surviving set for routing collisions before landing; de-confliction lives in the skill's own `description:`.

| New skill | Nearest existing triggers | De-confliction |
|---|---|---|
| distributed-systems-patterns | macro-architecture (style / decomposition), event-driven-microservices (adopt Kafka/streams as SSoT), data-systems-coding-lens (retries / migrations / idempotent writes), design-patterns (GoF), agent-architecture-lens (LLM control flow) | Description scopes to *naming and reviewing Burns container/multi-node topologies* — sidecar, ambassador, adapter, replica, shard, scatter/gather, FaaS fit, ownership election, work queues, coordinated batch. It names all four nearest lenses: macro-architecture picks monolith vs microservices; event-driven-microservices decides whether streams are the source of truth; data-systems-coding-lens implements retries and migrations at the code level; design-patterns is in-process GoF. A "should this be many services" ask without container/replica/shard/queue/election language stays on macro-architecture. |

---

# Successor record — software-design-philosophy full-book pass (2026-08-18)

Material revision of the existing Ousterhout lens against *A Philosophy of Software Design*, 2nd ed. (Kindle ASIN B09B8LFKQL). Not a new trigger surface: same skill name, expanded routes (`design` / `improve` / `review`) so the lens can develop and maintain, not only review. Design-gate invocation stays read-only.

| Change | Nearest existing triggers | De-confliction |
|---|---|---|
| software-design-philosophy (full 2nd ed.) | clean-code (local smell refactor), tdd (red-green), architecture-lens (connascence / layers), design-patterns (GoF), coding-review-simplify (post-impl tidy) | Description now fronts develop/improve/maintain but still negative-triggers local cleanup (`clean-code`), the test loop (`tdd`), GoF (`design-patterns`), and code-level coupling (`architecture-lens`). New body covers the chapters the old lens skipped (comments 12–15, modifying 16, consistency 17, obvious 18, trends 19, performance 20, decide what matters 21) via progressive-disclosure references. |
