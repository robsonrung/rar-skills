# Trigger-collision audit — compound-engineering-plugin ports

Phase A governance record (2026-07-22). Every new skill or graft from the porting effort was checked against the repo's existing skills and the installed user-level (`~/.claude/skills`) set for routing collisions before landing. De-confliction lives in each skill's own `description:`; this file records the audit outcome. Re-run this audit for any future addition (rule: a new skill may not land without a row here or in a successor record).

| New skill | Nearest existing triggers | De-confliction |
| --- | --- | --- |
| open-pr | ship (full pipeline), implement-and-review (never pushes/PRs), git-guardrails-claude-code | Description scopes to composing/opening PRs and PR-description-only flows; ship delegates PR composition here. |
| resolve-pr-feedback | full-review, /review builtin, resolving-merge-conflicts | Description states full-review _finds_ issues and never resolves threads; merge-conflicts skill is git conflicts, not review threads. |
| capture-learning | lesson-learned, summarize, context-compress | Description contrasts with lesson-learned (ephemeral, chat-only, no store) and session-continuity skills. |
| session-handoff | summarize, context-compress, installed `handoff` | Description covers store+resume; context-compress delegates its save step; installed single-slot handoff superseded (retired at install). |
| worktree | implement-and-review (internal worktree flow) | Description scopes to user-initiated isolation/attach; implement-and-review keeps its internal flow. |
| browser-smoke | qa-execution, qa, full-review | Description states qa-execution is whole-product release QA; browser-smoke is diff-scoped PR smoke only. |
| agent-architecture-lens (2026-07-28) | data-systems-coding-lens (retries/idempotency), macro-architecture (system shape), knowledge-graph (agent-facing graphs), dynamic-harness / codex-mission-control (orchestration skills, not lenses) | Description scopes to the control flow of an LLM agent the user is _building_ — loop vs state graph, agent state, bounded retries, termination ceilings. It names all three nearest lenses explicitly: data-systems-coding-lens covers retries and idempotency for stored state (databases, queues, caches) rather than agent steps; macro-architecture decomposes services and assigns data ownership; knowledge-graph builds a graph an agent _reads_, not the graph an agent _runs on_. The orchestration skills are not competitors — they are consumers, and now cite this lens's leitwörter via `shared/references/run-state-contract.md`. |

Grafts (no new trigger surface): full-review (findings mechanics + doc-review dimension), skill-expert (authoring references), ship (residual-findings, local-only, evidence gate, routing carriers), coding-design-plan (test-scenario contract, scoping gate), to-tasks (stable U-IDs), decision-council (POV contracts), coding-review-simplify (personas), brainstorm (blindspot pass, idea-basis mode), systematic-debugging/diagnosing-bugs (pipeline-mode contract), visual-recap/teach (retention mechanics), qa-execution (dogfood skeleton).

Deferred names reserved (no skill yet, gated per plan): watch-pr, feedback-sweep, refresh-learnings, product-strategy, metric-optimize, product-pulse, launch-copy, recording-feedback.

---

# Successor record — pipeline consolidation (2026-07-30)

A repo-wide restructuring pass. Goal: one workflow, the fewest user-called skills per step, no duplicated knowledge. Every skill below was checked against the surviving set for routing collisions before landing; de-confliction lives in each skill's own `description:`.

## New skills

| New skill | Nearest existing triggers | De-confliction |
| --- | --- | --- |
| interview | brainstorm (frame/verdict), to-prd (writes the PRD), collaborative discovery (now brainstorm's panel mode) | Description scopes to the interactive requirements interview _between_ framing and the PRD: brainstorm decides WHETHER to build, `interview` pins down WHAT to build, `to-prd` synthesizes it without interviewing. Fills the role previously routed to the absent `grill-with-docs`. |
| tdd | safe-incremental-coding (legacy net), test-lens (judges tests), clean-code (tidies tested code), diagnose (root-cause) | Description scopes to the red-green-refactor execution loop and states the entry rule (untested legacy → `safe-incremental-coding` first, then return). Negative-triggers test-after backfilling. Replaces the previously external `tdd`. |
| diagnose | fable-mindset (diagnosis posture), tdd (the loop), full-review (finds issues in a diff) | Description scopes to procedural root-causing of a specific failure; `fable-mindset` owns the epistemic posture, this skill owns the steps. Carries a non-interactive `mode:pipeline` contract for autonomous callers. Replaces the previously external `diagnose`. |
| to-prototype | coding-design-plan (holds the tracer-vs-prototype rule), brainstorm, tdd | Description scopes to throwaway spikes that answer a design question only running code can settle, and states the throw-it-away rule; the tracer-bullet alternative is decided in `coding-design-plan`. Replaces the previously external `prototype`. |
| fable-mindset | the five former `fable-*` skills; coding-design-plan, clean-code, tdd, diagnose, summarize | One skill covering five moments of a working turn (intake, diagnosis, decision, implementation, reporting). Description states it governs posture, not procedure, and negative-triggers each procedural counterpart. Replaces five separate trigger surfaces with one. |

## Merges and dissolutions (no new trigger surface)

| Change | Rationale |
| --- | --- |
| `models-roundtable` + `council` + `decision-council` → `models-consensus` (modes `poll` / `debate` / `personas`, plus `clarify` and `decider_context: report_only` flags) | Four skills ran the same five-stage pipeline with six differing knobs, four copies of the seat roster, and a trigger collision on "council this". `poll` (the former roundtable protocol) is the default and the pipeline-facing mode; `personas` is also the degradation path below quorum. The merged skill never auto-executes — the old `council --auto` implementation race is gone. |
| `collaborative_discovery` → `brainstorm` panel mode; `collaborative_specification` → `to-prd` panel mode; `collaborative_task_design` → `to-tasks` panel mode | Each pair produced the same artifact for the same pipeline step, differing only in how many models participated. Panel mode is now an opt-in section of the canonical skill, so the multi-model path inherits the Slice Contract, the security-gate handshake, and the approval gate it previously lacked. Shared panel scripts and engineering rules moved to `shared/`. |
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
| --- | --- | --- |
| review-gate | full-review (PR/diff review, verdicts), code-review (standards/spec axes), design-gate / security-gate (gate family, pre-implementation), models-consensus (multi-seat fan-out, deliberation-only) | Description states full-review is the deep human-facing review (bughunt, security audit, ultrareview); review-gate is the merge gate — declared coverage contract with honesty accounting, persona fan-out with an adversarial refutation pass, and a machine-consumable result JSON an automated follow-up run can consume. The gate family's other members run before implementation; review-gate gates the finished diff. It never publishes to the code host. |
| verify-changes | tdd (owns the implementation loop), diagnose (fixes failures), browser-smoke (browser leg), harness `run` (launches the app), full-review Phase 4 (verifies findings, not repo gates) | Description scopes to deterministic execution of the repo's own discovered checks with captured evidence — it never fixes (failures route to diagnose), never judges code, and never launches the app interactively. Named as review-gate's pipeline verification phase, mirroring how browser-smoke names ship. |

---

# Successor record — distributed-systems-patterns (2026-08-18)

Book-grounded design lens from Burns, _Designing Distributed Systems_. Checked against the surviving set for routing collisions before landing; de-confliction lives in the skill's own `description:`.

| New skill | Nearest existing triggers | De-confliction |
| --- | --- | --- |
| distributed-systems-patterns | macro-architecture (style / decomposition), event-driven-microservices (adopt Kafka/streams as SSoT), data-systems-coding-lens (retries / migrations / idempotent writes), design-patterns (GoF), agent-architecture-lens (LLM control flow) | Description scopes to _naming and reviewing Burns container/multi-node topologies_ — sidecar, ambassador, adapter, replica, shard, scatter/gather, FaaS fit, ownership election, work queues, coordinated batch. It names all four nearest lenses: macro-architecture picks monolith vs microservices; event-driven-microservices decides whether streams are the source of truth; data-systems-coding-lens implements retries and migrations at the code level; design-patterns is in-process GoF. A "should this be many services" ask without container/replica/shard/queue/election language stays on macro-architecture. |

---

# Successor record — software-design-philosophy full-book pass (2026-08-18)

Material revision of the existing Ousterhout lens against _A Philosophy of Software Design_, 2nd ed. (Kindle ASIN B09B8LFKQL). Not a new trigger surface: same skill name, expanded routes (`design` / `improve` / `review`) so the lens can develop and maintain, not only review. Design-gate invocation stays read-only.

| Change | Nearest existing triggers | De-confliction |
| --- | --- | --- |
| software-design-philosophy (full 2nd ed.) | clean-code (local smell refactor), tdd (red-green), architecture-lens (connascence / layers), design-patterns (GoF), coding-review-simplify (post-impl tidy) | Description now fronts develop/improve/maintain but still negative-triggers local cleanup (`clean-code`), the test loop (`tdd`), GoF (`design-patterns`), and code-level coupling (`architecture-lens`). New body covers the chapters the old lens skipped (comments 12–15, modifying 16, consistency 17, obvious 18, trends 19, performance 20, decide what matters 21) via progressive-disclosure references. |

---

# Successor record — interview absorbs grill-with-docs (2026-09-02)

Renamed `interview` → `interview-me` the same day (directory, frontmatter name, and every skill-name reference; earlier records above keep the old name as history). The trigger surface is unchanged.

No new trigger surface. `interview` (already the specify-phase interview) absorbed this repo's own take on mattpocock/skills' `grill-with-docs` (`grilling` + `domain-modeling`, MIT; see NOTICE). A separate `grill-to-adr` skill was drafted and merged away the same day: the ADR is the conditional part of the mechanic, not its point, and two grilling skills split "grill me" between them.

| Change | Nearest existing triggers | De-confliction |
| --- | --- | --- |
| `interview` (now `interview-me`) gains frontier rounds + record on settle | brainstorm (verdict), to-prd (synthesis, no interview), architecture-lens / macro-architecture (may flag "ADR needed"), coding-design-plan (`escalation` field), capture-learning (post-hoc CONCEPTS.md accretion), installed user-level `grilling` / `grill-me` / `grill-with-docs` / `domain-modeling` | One-question-at-a-time replaced by **the frontier** of a **design tree** asked in rounds, each question with a recommended answer. Glossary entries and ADRs are written **on settle**; an ADR only when the decision passes **all three or no ADR** (hard to reverse, surprising without context, real trade-off), so a simple feature ends with none. Description now takes "grill me on this idea or design" and "write an ADR for this decision"; brainstorm, to-prd, capture-learning, and diagnose stay negative-triggered. The installed user-level grilling trio is superseded for repos that install this collection. |

---

# Successor record — four-step workflow (2026-09-02)

A consolidation pass toward one four-step workflow: `interview-me` → `to-prd` → `to-tasks` → `implement-tasks`. No new trigger surface was added; every change below removes or merges one.

| Change | Rationale |
| --- | --- |
| `ship` → `implement-tasks` (renamed from `implement-feature`) | Two orchestrators sat above the build engine: `ship` (seven stations, its own run state) and `implement-feature` (the slice DAG). `ship` re-ran the design gate, self-simplify, and `full-review` around a build that already ran all three. The autonomous contracts only `ship` had — the evidence gate, residual-findings durability, local-only mode, the escalation ladder, and the PR contract sections — moved into `implement-tasks`; the three interactive steps are typed by the user, each closing with the next step's name. `ship/references/residual-findings.md` moved with it; `station-dispatch.md` was retired with the station model. The leitwörter guard for "thin conductor / hand off the path, not the payload / the ledger, not the transcript" moved to `implement-tasks/SKILL.md`. |
| `kimi-runner`, `glm-runner`, `qwen-runner`, `gemma-runner` → `pi-runner --seat <name>`; `muse-runner`, `minimax-runner` → `cline-runner --seat <name>` | Each shim was a SKILL.md, an `agents/` file, and a 30-line script whose only content was a pinned model id already recorded in the roster and in `discover_runners.py`. `--seat` pins the model and labels the envelope (`runner=<seat>`, `effective_runner=pi | cline`); an explicit `--model`still wins. Seat names, probe output, quorum rules, and the seat-fidelity invariant are unchanged. Panel routing files for the Kimi seat now point at`run_pi.py`with`--seat kimi`(and no longer pass the Cline-only`--data-dir`, which `run_pi.py` never accepted). |
| Muse seat `meta/muse-spark-1.1` → `meta/muse-spark-1.3` | Roster bump, applied in the three places a seat id lives: `CLINE_SEATS` in `run_cline.py`, `model-roster.md`, `SEAT_SPECS` in `discover_runners.py`. |
| `event-driven-microservices` → a route inside `distributed-systems-patterns` | The two lenses cited each other seven times and covered the same multi-node territory from two angles (container topology vs event streams as source of truth), yet only one was reachable from `design-gate`'s routing table. The Bellemare content (adopt gate, four leitwörter, event contracts, implementation styles, review-and-migrate) is now the `event-driven` route of `distributed-systems-patterns`, with its references moved under `references/edm-*.md` and its brief under `assets/edm-decision-brief.md`. `design-gate` gained the routing row for event streams. |

Deferred names still reserved: watch-pr, feedback-sweep, refresh-learnings, product-strategy, metric-optimize, product-pulse, launch-copy, recording-feedback.

## Folder layout (same pass)

Skills moved from the flat root into `engineering/<group>/<skill>` (workflow — the four steps plus `models-consensus`; engine, gates, lenses, practice, review, deliver, seats) and `extras/<skill>`; `shared/` stays at the root. No skill was renamed, so installed paths (`.agents/skills/<name>/`) are unchanged. Runtime path resolution moved to `shared/scripts/skill_paths.py` (walk up to the directory owning `shared/scripts/`, then find siblings by name), used by the runner scripts, `implement-and-review/scripts/launch.py`, `panel_round.py`, both validators, the tests, and `scripts/install-skills.sh`. The leitwörter registry's guard paths were rewritten to the new locations.

## React lens merge (same pass)

`react-performance` merged into `advanced-react`, now under `engineering/lenses/`. Both were drawn from Makarevich's _Advanced React_ and fired on the same phrases; `advanced-react` was the one carrying plan / implement / review modes and the design-gate reviewer contract, while `react-performance` (the routed one) held the nine per-chapter checklists and the cheatsheet. The checklists moved to `advanced-react/references/lenses.md` and the cheatsheet to `references/cheatsheet.md`; `design-gate`'s React row, `implement-and-review`'s frontend track, and `full-review`'s conditional specialist now name `advanced-react`. `ui-ux-pro-max` keeps its `react-performance.csv` data file (a lookup table, not the skill).

## Prototype detour (same pass)

`to-prototype` moved from `extras/` to `engineering/workflow/` as the workflow's detour rather than a step: `interview-me` gained a "Detour: prototype" rule (hand one frontier question to the spike when only running code can settle it and the answer changes the spec; record the returned decision as a settled node; resume), and `to-prototype` now hands back to its caller (`interview-me`, `coding-design-plan`, or the user). `coding-design-plan` already owned the prototype-vs-tracer-bullet rule; that is unchanged. `brainstorm` stays in `extras/`.

## Toolbox (same pass)

`brainstorm` moved from `extras/` to `engineering/workflow/`. The workflow folder is read as the engineer's toolbox — the four steps plus `brainstorm`, `to-prototype`, and `models-consensus` — rather than a fixed sequence; the task decides which tool is picked up first.

## Working files live under `.ai-workflow/` (same pass)

Convention made uniform: every skill keeps its working files under the repository's `.ai-workflow/`. Panel-mode artifacts moved from `.codex_workflow/<skill>` to `.ai-workflow/panel/<brainstorm|prd|tasks|delivery>` (routing files, panel-mode references, `panel_round.py` and `record_native_response.py` defaults); `dynamic-harness` missions from `work/harness-missions/` to `.ai-workflow/harness-missions/`; `session-handoff`'s managed store from `/tmp/rar-skills-<uid>/handoff/` to `.ai-workflow/handoff/` at the main worktree; `browser-smoke` dev-server logs to `.ai-workflow/browser-smoke/`; runner documentation examples to `.ai-workflow/prompts/` and `.ai-workflow/runs/`. Left alone: cmux's own socket (`/tmp/cmux.sock`, not ours) and test fixtures.

## Entry-point flags (same pass)

Every skill that no other skill invokes now carries `disable-model-invocation: true` with `allow_implicit_invocation: false` in `agents/openai.yaml`. Newly flagged: `brainstorm`, `interview-me`, `to-prd`, `implement-tasks` (the engineer types the toolbox steps; each hands off to the next through the user) and `cmux-cli` (no caller). `to-tasks` stays invocable because `implement-tasks` decomposes a bare plan through it; `to-prototype`, `models-consensus`, `skill-expert`, `browser-smoke`, `verify-changes`, and `peer-sessions` stay invocable because another skill names them mid-run. Trade-off accepted: a flagged skill does not auto-trigger from natural language on hosts that hide it; the slash command and the file-path route still work.
