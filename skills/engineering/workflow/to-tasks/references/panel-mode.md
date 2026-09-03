# to-tasks — Panel mode

Opt-in multi-model drafting for `to-tasks`. SKILL.md decides _when_ panel mode runs and what it replaces; this file is _how_. Paths are relative to the repository root.

Read `shared/collaborative-panel-runner.md` before running any panel phase — it holds the routing contract, the flags, the status taxonomy, and the completion gate.

**Phases.** Run all five in order:

`architecture_mapping` → `test_strategy` → `task_slicing` → `dependency_review` → `convergence`

```bash
python3 shared/scripts/panel_round.py \
  --phase architecture_mapping \
  --routing to-tasks/assets/panel-routing.toml \
  --goal "the plan or PRD being broken down" \
  --context-file .ai-workflow/panel/tasks/source.md \
  --out .ai-workflow/panel/tasks \
  --fail-on-incomplete
```

**`architecture_mapping`** maps the target architecture before anything is sliced: domain layer, application use cases, ports, adapters, infrastructure, presentation, data boundaries, and dependency direction. Slicing against an unmapped architecture is how horizontal slices sneak back in.

**`test_strategy`** designs the tests before any code is planned, across the taxonomy that applies: unit, integration, contract, component, end-to-end, regression, and security. **Every task must trace back to a spec item and must define tests before code** — a slice whose tests are decided after its implementation is not a slice this skill emits.

**`task_slicing`** produces the vertical slices. **`dependency_review`** hardens the ordering and the parallelization claims. **`convergence`** reconciles.

**Roles.** The seat behind each role is editable in `to-tasks/assets/panel-routing.toml`:

- `synthesis_anchor` — native synthesis, reconciliation, audit-trail ownership. Present in every phase.
- `adversarial_anchor` — challenges assumptions, finds risk, blocks unsafe convergence. Present in every phase.
- `architecture` — bounded contexts, use cases, ports, adapters, dependency direction, transaction boundaries, integration seams.
- `testing` — the test taxonomy above, designed before implementation.
- `interface` — interface slicing by user value, component boundaries, state, accessibility, responsiveness, visual regression risk.
- `backend` — backend slicing by use cases, domain rules, storage, API contracts, permissions, jobs, events, observability.
- `delivery` — safe increments, merge risk, parallelizable tracks, and verification commands that exist in this repo.

A specialist role that is not relevant to the current plan still participates and states why it has no material concern.

**Read gate.** Read `shared/references/engineering-rules.md` before `architecture_mapping` and `task_slicing`; it holds the spec-driven development, domain-driven design, clean architecture, and test-driven development rules this skill applies.

**Missing inputs.** If the PRD and codebase-fit artifacts do not exist, do not stall and do not invent requirements: create a minimal assumptions section and explicitly mark the missing inputs. The approval quiz then surfaces those assumptions to the user, which is the only place they can be corrected.

**Artifacts.** Panel mode writes to `.ai-workflow/panel/tasks`:

1. `tasks.md` — the drafted slices, each with the complete Slice Contract from step 4 plus the rollback note, expected review focus, and parallelization statement from the task template.
2. `architecture_plan.md` — the mapped architecture from `architecture_mapping`.
3. `test_plan.md` — the test strategy across the taxonomy.
4. `parallelization_plan.md` — which tracks may run concurrently, and the merge plan wherever slices touch shared ground.
5. `risk_register.md` — sequencing, merge, migration, and security risk.
6. `decision_log.md` — decisions plus preserved disagreements; record dissent rather than hiding it.
7. `panel_summary.json` — written by the runner; the participation record.

This list is mirrored in `to-tasks/assets/panel-routing.toml` `required_outputs`, the machine-read source consumed by `shared/scripts/validate_artifacts.py`. Before presenting the breakdown:

```bash
python3 shared/scripts/validate_artifacts.py \
  --routing to-tasks/assets/panel-routing.toml \
  --artifact-dir .ai-workflow/panel/tasks
```

`tasks.md` under the artifact directory is the panel's draft, not the published queue. Step 5 (the approval quiz) and step 6 (the publication contract — one markdown file per slice under `.ai-workflow/work/<feature-slug>/tasks/`, T-ID prefixed, in dependency order) run exactly as in SKILL.md.

**Bounds.** Do not implement code in panel mode, and do not change files outside the artifact directory unless the user explicitly asks for repository scaffolding. The no-file-paths rule from the task template still applies to every slice a panel drafts — a slice describes end-to-end behavior, not the files it expects to touch.

**Honesty rules.** A phase is complete only when every required role reached `ok` or `native_response_recorded`. `dry_run` is not participation. `fallback_used` means independence was lost, so do not report that seat as the configured model. A generated native prompt is never enough by itself.
