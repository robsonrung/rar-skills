---
name: to-tasks
description: Break an approved plan, spec, or PRD into autonomously executable tasks — tracer-bullet vertical slices that each carry a machine-checkable acceptance contract and design/security gate flags, so an agent can complete them without asking the user anything. Use when the user wants to break a plan into tasks, convert a spec or PRD into a work queue, create implementation tasks for autonomous agents, or when a pipeline planning phase needs the task breakdown. Use whenever tasks will be executed by agents; for human-executed tickets without contracts, plain tracker issues suffice. An opt-in Panel mode drafts the breakdown with a multi-model panel.
---

# To Tasks

Break a plan into independently-grabbable tasks using vertical slices (tracer bullets). Every task carries a Slice Contract — machine-checkable acceptance plus gate flags — so the user approves the breakdown once and is never asked anything afterwards.

## Process

### 1. Gather context

Work from whatever is already in the conversation context. If the user passes a reference (issue number, URL, or path to a PRD/spec), fetch and read its full body and comments.

### 2. Explore the codebase

If you have not already explored the codebase, do so. Task titles and descriptions should use the project's domain glossary vocabulary (`CONCEPTS.md`) and respect ADRs in the area being touched. Also identify the repo's real verification commands (test, lint, build, typecheck) — the acceptance contracts below must use commands that actually exist.

### 3. Draft vertical slices

Break the plan into **tracer bullet** tasks. Each task is a thin vertical slice that cuts through ALL integration layers end-to-end, NOT a horizontal slice of one layer.

<vertical-slice-rules>
- Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)
- A completed slice is demoable or verifiable on its own
- Prefer many thin slices over few thick ones
</vertical-slice-rules>

Assign each slice a stable ID (`T1`, `T2`, …) at draft time. **IDs are never renumbered.** Reordering leaves IDs in place (T1, T3, T5 in their new order is correct; renumbering to T1, T2, T3 is not). Splitting keeps the original ID on the original concept and gives the new slice the next unused number. Deleting leaves a gap — gaps are fine. Executors and "Blocked by" references cite slices by T-ID, so the IDs must survive every later reorder, split, or delete of the breakdown.

Classify each slice **HITL** or **AFK**. HITL slices require human interaction — irreversible migrations, externally visible contract sign-off, design approval. AFK slices run unattended. Prefer AFK; schedule HITL slices first so human involvement clusters at the start.

### 4. Attach the Slice Contract

Add two fields to every slice while the user is still present:

1. **`acceptance`** — exact commands that must pass (the repo's real test, lint, build commands plus any app-level check a verification skill can run) and the observable behaviors that prove the slice works. When the source is a `to-spec` PRD, lift the behaviors from its Testing Decisions / named seams; name each at the **highest seam** as external behavior (`test-lens`), never an implementation detail — these become the test-first targets when `implement-and-review` builds the slice. Done must be machine-checkable; never invent commands — verify each one exists in the repo. A slice with no behavioral change (pure config, scaffolding, styling) states the mandatory line `Test expectation: none — [reason]` in place of behaviors; a feature-bearing slice with blank behaviors flags the breakdown incomplete — the none-annotation is never valid there.
2. **`gates`** — which design lenses apply, selected from the routing table in `design-gate` by the surfaces the slice touches, and `security: deep|standard`, set from `security-gate`'s deep-pass trigger list (when the source PRD has a Security Decisions section pre-marking security-sensitive surfaces, lift the flag from there instead of re-deriving). Do not copy those tables here — read them and record only the resulting flags.

### 5. Quiz the user — the approval gate

Present the proposed breakdown as a numbered list. For each slice, show:

- **Title**: T-ID plus short descriptive name (`T3: …`)
- **Type**: HITL / AFK
- **Blocked by**: which other slices by T-ID (if any) must complete first
- **Acceptance**: the contract commands and observable behaviors
- **Gates**: lens flags and security level, with the matched trigger
- **Parallel-safe**: whether it can run alongside other slices, and which
- **User stories covered**: which user stories this addresses (if the source material has them)

Ask the user:

- Does the granularity feel right? (too coarse / too fine)
- Are the dependency relationships correct?
- Should any slices be merged or split further?
- Are the correct slices marked HITL and AFK?
- Are the acceptance contracts complete — would passing these commands genuinely mean done?

Iterate until the user approves. This is the last required human touchpoint before delivery.

### 6. Publish the work queue

If an issue tracker is configured, publish each approved slice as an issue using the template below, titled with its T-ID prefix (`T3: <title>`), with the `ready-for-agent` triage label, in dependency order (blockers first) so real identifiers can be referenced in "Blocked by". If no tracker is configured, write the approved breakdown to a `TASKS.md` at the repo root using the same template, one section per task headed `## T<N>. <Title>`, with a status line (`todo | in-progress | done | blocked`). The T-ID stays authoritative across plan edits even after tracker identifiers exist.

<task-template>
## Parent

A reference to the parent issue or PRD (omit if none).

## What to build

A concise description of this vertical slice. Describe the end-to-end behavior, not layer-by-layer implementation. Avoid file paths or code snippets — they go stale. Exception: a prototype snippet that encodes a decision more precisely than prose (state machine, reducer, schema, type shape) — inline the decision-rich parts and note their origin.

## Acceptance contract

- Commands: each exact command that must pass
- Behaviors: each observable behavior that must hold, or `Test expectation: none — [reason]` for a non-feature slice

## Gates

- Lenses: the design-gate lens flags for this slice
- Security: deep | standard (with the matched trigger)

## Rollback note

How to undo this slice if it lands badly: the revert shape (plain revert, feature flag off, down-migration, cache purge), and anything that makes it *not* a plain revert — data written, external calls made, contracts published. Say "plain revert, no side effects" when that is genuinely true.

## Expected review focus

Where a reviewer should spend their attention on this slice — the one or two things most likely to be wrong here (a boundary, an error path, a permission check, a migration order, a state transition). Not a generic checklist; the specific risk this slice carries.

## Parallelization

Whether this slice is safe to run alongside others, and which. Never parallelize tasks that write the same files, migrations, shared contracts, or security-sensitive paths — unless there is an explicit merge plan stated here. When in doubt, serialize: a stated dependency costs less than a merge conflict in a migration.

## Blocked by

A reference to each blocking task by T-ID (plus tracker identifier when published), or "None - can start immediately".
</task-template>

Do NOT close or modify any parent issue.

## Panel mode (optional)

By default this skill drafts the breakdown with a single model. **Panel mode** is opt-in: turn it on when the user asks for a multi-model task plan, or when the architecture and test strategy are consequential enough to be worth independent seats. It replaces **step 3 and step 4** — the drafting of slices and their contracts — and nothing else. The output still carries the full Slice Contract, and it still ends at the step-5 approval quiz: **the panel replaces drafting, never the gate.**

Read `../_shared/collaborative-panel-runner.md` before running any panel phase — it holds the routing contract, the flags, the status taxonomy, and the completion gate.

**Phases.** Run all five in order:

`architecture_mapping` → `test_strategy` → `task_slicing` → `dependency_review` → `convergence`

```bash
python3 _shared/scripts/panel_round.py \
  --phase architecture_mapping \
  --routing to-tasks/assets/panel-routing.toml \
  --goal "the plan or PRD being broken down" \
  --context-file .codex_workflow/tasks/source.md \
  --out .codex_workflow/tasks \
  --fail-on-incomplete
```

**`architecture_mapping`** maps the target architecture before anything is sliced: domain layer, application use cases, ports, adapters, infrastructure, presentation, data boundaries, and dependency direction. Slicing against an unmapped architecture is how horizontal slices sneak back in.

**`test_strategy`** designs the tests before any code is planned, across the taxonomy that applies: unit, integration, contract, component, end-to-end, regression, and security. **Every task must trace back to a spec item and must define tests before code** — a slice whose tests are decided after its implementation is not a slice this skill emits.

**`task_slicing`** produces the vertical slices. **`dependency_review`** hardens the ordering and the parallelization claims. **`convergence`** reconciles.

**Roles.** The seat behind each role is editable in `assets/panel-routing.toml`:

- `synthesis_anchor` — native synthesis, reconciliation, audit-trail ownership. Present in every phase.
- `adversarial_anchor` — challenges assumptions, finds risk, blocks unsafe convergence. Present in every phase.
- `architecture` — bounded contexts, use cases, ports, adapters, dependency direction, transaction boundaries, integration seams.
- `testing` — the test taxonomy above, designed before implementation.
- `interface` — interface slicing by user value, component boundaries, state, accessibility, responsiveness, visual regression risk.
- `backend` — backend slicing by use cases, domain rules, storage, API contracts, permissions, jobs, events, observability.
- `delivery` — safe increments, merge risk, parallelizable tracks, and verification commands that exist in this repo.

A specialist role that is not relevant to the current plan still participates and states why it has no material concern.

**Read gate.** Read `../_shared/references/engineering-rules.md` before `architecture_mapping` and `task_slicing`; it holds the spec-driven development, domain-driven design, clean architecture, and test-driven development rules this skill applies.

**Missing inputs.** If the PRD and codebase-fit artifacts do not exist, do not stall and do not invent requirements: create a minimal assumptions section and explicitly mark the missing inputs. The approval quiz then surfaces those assumptions to the user, which is the only place they can be corrected.

**Artifacts.** Panel mode writes to `.codex_workflow/tasks`:

1. `tasks.md` — the drafted slices, each with the complete Slice Contract from step 4 plus the rollback note, expected review focus, and parallelization statement from the task template.
2. `architecture_plan.md` — the mapped architecture from `architecture_mapping`.
3. `test_plan.md` — the test strategy across the taxonomy.
4. `parallelization_plan.md` — which tracks may run concurrently, and the merge plan wherever slices touch shared ground.
5. `risk_register.md` — sequencing, merge, migration, and security risk.
6. `decision_log.md` — decisions plus preserved disagreements; record dissent rather than hiding it.
7. `panel_summary.json` — written by the runner; the participation record.

This list is mirrored in `assets/panel-routing.toml` `required_outputs`, the machine-read source consumed by `_shared/scripts/validate_artifacts.py`. Before presenting the breakdown:

```bash
python3 _shared/scripts/validate_artifacts.py \
  --routing to-tasks/assets/panel-routing.toml \
  --artifact-dir .codex_workflow/tasks
```

`tasks.md` under the artifact directory is the panel's draft, not the published queue. Step 5 (the approval quiz) and step 6 (the publication contract — tracker issues or a repo-root `TASKS.md`, T-ID prefixed, in dependency order) run exactly as above.

**Bounds.** Do not implement code in panel mode, and do not change files outside the artifact directory unless the user explicitly asks for repository scaffolding. The no-file-paths rule from the task template still applies to every slice a panel drafts — a slice describes end-to-end behavior, not the files it expects to touch.

**Honesty rules.** A phase is complete only when every required role reached `ok` or `native_response_recorded`. `dry_run` is not participation. `fallback_used` means independence was lost, so do not report that seat as the configured model. A generated native prompt is never enough by itself.

## Gotchas

1. Do not publish a slice whose acceptance commands you have not confirmed exist and run in this repo.
2. Do not inline the design-gate routing table or security-gate trigger list — reference them and record only the flags.
3. Do not let a slice's acceptance be "tests pass" alone when the slice promises observable behavior — name the behavior.
4. Do not mark a slice AFK if completing it requires a decision the contract does not answer.
5. Do not renumber T-IDs when reordering, splitting, or deleting slices — new slices take the next unused number and gaps are fine.

---
*Stable-ID and test-expectation contracts adapted from Every's compound-engineering-plugin (`ce-plan`).*
