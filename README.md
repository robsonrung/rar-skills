# rar-skills

`rar-skills` is an engineering skill library. Its feature workflow turns a
request into a verified local result through four stages:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

For one bounded, specified change with clear acceptance and no unresolved
material decision, use `implement-and-review` directly. It retains exact worker
approval and independent review without a feature PRD or task graph.
See [docs/workflow.md](docs/workflow.md) for the workflow guide and owning contracts.

## Workflow

| Stage | Output | Main responsibility |
| --- | --- | --- |
| `interview-me` | `decision-record.md` | Use relevant repository facts, then ask at most five independent questions in one turn. With `--auto`, keep two isolated role contexts: resolve the product or technical interview roles from the central routing configuration. The respondent can provide evidence and alternatives, but cannot settle a material user decision. Record settled decisions and scope; the record becomes `ready-for-prd` when the interview closes. |
| `to-prd` | `prd.md` | Turn a `ready-for-prd` decision record into a draft PRD. The user reviews it before it becomes approved. |
| `to-tasks` | Canonical task files, compact `tasks-draft.md`, and `queue.json` | Write each complete task contract once. The index links contracts and dependencies. Task-only approval is the default. When execution is requested, one explicit response can approve the queue and exact worker plan. Drafts cannot run. |
| `implement-tasks` | Verified local result | Dispatch ready tasks through `implement-and-review` with the approved implementation, independent review, and integration routes. Verify the combined state before releasing dependents. |

Task approval defines the work. Model approval defines the exact worker routes
and controls. They remain separate decisions even when one response covers both.
The [shared preview](skills/shared/references/model-preview.md) first selects the
branch. Coordinator work, inline methods, and deterministic commands need no
worker selection. Actual dispatch needs one concrete preview with roles, tools,
privacy controls, receipt policy, fallbacks, and budgets. Nested skills reuse
the approved snapshot. A request to use defaults and run permits the unchanged
resolved setup within source sharing authority and accepted receipt limits.
Silence cannot approve it.

[`model-routing.json`](skills/shared/model-routing.json) owns profile names,
exact models, and effort defaults. Workflow previews resolve `--profile default`,
with a validated local preference or explicit override when supplied. Profiles
include `saver`, `economy`, and `balanced`; the configuration selects the default.
Legacy family routes remain selectable. Approved snapshots retain their exact routes when configuration
changes. Static checks do not prove model quality, latency, or cost savings.

`implement-tasks` checks native host capability before external runner
availability and preserves the approved route and effort. Each task has an
isolated implementer and an independent reviewer. Each role retains its own
context for permitted fixes and rechecks. An unavailable route blocks its work
unless its exact fallback was approved. Workspace selection and integration
follow the engine's
[isolation and integration contract](skills/engineering/engine/implement-and-review/references/worktree-and-integration.md).
Without delivery authorization, the result stays local and verified. The
[read-only queue controller](skills/engineering/workflow/implement-tasks/references/queue-controller.md)
projects readiness from bound contracts, manifests, and the existing call ledger.
It starts no worker and changes no state. The conductor reserves each call before
dispatch, keeps write ownership through pending calls and integration, and
enforces dependency and concurrency limits.

A requested or configured model is not proof that it served a run. Each route
records `model_verification` as `required` or `allow_unverified`. `required`
needs `model_receipt.status: verified` from a native or provider event. An
`allow_unverified` route needs explicit approval and reports that limit clearly.

The stage rules are in
[workflow-stage-routing.md](skills/shared/references/workflow-stage-routing.md).
Model choices are in
[task-shaped-model-routing.md](skills/shared/references/task-shaped-model-routing.md)
and [model-roster.md](skills/shared/references/model-roster.md). The host and
session rules are in
[host-model-execution.md](skills/shared/references/host-model-execution.md).

### Engineering practices in the workflow

| Moment | Skills |
| --- | --- |
| Discover risk and behavior | `security-gate`, a broad lens only when it changes the next question, and `to-prototype` when a runnable question blocks a decision |
| Plan a task slice | `design-gate` once with at most three inline lenses, `security-gate` for the security classification, and `test-lens` for a real test-design decision |
| Resolve an implementation shape | `coding-design-plan` when the shape is unresolved; reuse inherited gate constraints |
| Build new behavior | `tdd`, then `clean-code` for a refactor decision and `test-lens` for a test-design decision |
| Change untested legacy code | `safe-incremental-coding` before broad edits |
| Investigate an unexpected failure | `diagnose` |
| Review a completed change | Approved scoped review; `full-review` for integration seams or named risks, `coding-review-simplify` for a useful simplification, and `browser-smoke` for affected web flows |

Routine lenses are read-only procedures in the assigned role. A material risk
or unresolved question can require an approved independent specialist. The final
code review remains independent. Routine reviews do not start a council.

The [shared evidence contract](skills/shared/references/review-evidence.md)
selects affected checks from declared inputs. It retains matching captures,
requires an explicit transfer assessment for changed source identity, and runs
affected or required fresh checks. Unknown dependencies use whole-source scope.
Keep original logs and immutable snapshots. A passing command or completion
label alone cannot establish review readiness.

## Feature validation

[`validate-e2e`](skills/engineering/workflow/validate-e2e/SKILL.md) validates an
existing feature against a finite acceptance contract. Command-only work runs
directly. Worker work uses the exact approved routes and reserved budgets.
Validation exports current captured checks and browser observations through the
same evidence packet used by review. Required behavior and runtime gates remain
separate. `pre-pr-review` reuses evidence only after the shared verifier accepts
it. Approved recovery allowances retain total limits across native and runner
resumes. A scoped pass does not prove universal coverage.

Claude preflight caches only stable capability results with a current fingerprint
and a 24-hour limit. Each launch still checks local CLI identity, configuration,
launch context, authentication visibility, and installation drift. Receipts,
entitlement, quota, and request privacy remain current-run facts.

## Optional council

`models-consensus` is for a user who explicitly asks for more opinions. It is
user-invoked only. Before it runs, it presents the mode, exact seats and
transports, roles, effort, receipt policy, call budget, and unavailable seats.
The user approves that council plan separately. `poll` retains the `standard`
profile by default. Explicit `lean` is available for low-risk questions through
`per_call` transport. Both judge routes remain approved and run when validated
organizer evidence finds gaps, contradictions, low confidence, or high risk.
The council provides deliberation only.

`brainstorm` batches up to five independent decisions after its territory gate.
`to-prototype` uses the smallest experiment that can settle one question, such as
one visual fixture or two useful alternatives. Prototype code remains disposable.

## Delivery

The workflow stops at a local, verified result unless the user explicitly asks
to commit, push, open or update a pull request, or create or change a tracker
item. Those actions are never implied by task or model-plan approval.

## Library map

The following map keeps the skills discoverable while leaving detailed
instructions in each `SKILL.md`. The shared library installs beside them.

| Domain | Skills |
| --- | --- |
| Workflow | `brainstorm`, `interview-me`, `to-prd`, `to-tasks`, `implement-tasks`, `to-prototype`, `models-consensus`, `pre-pr-review`, `validate-e2e` |
| Engine | `coding-design-plan`, `implement-and-review`, `worktree` |
| Gates | `design-gate`, `security-gate` |
| Lenses | `advanced-react`, `agent-architecture-lens`, `architecture-lens`, `data-systems-coding-lens`, `design-patterns`, `distributed-systems-patterns`, `domain-driven-design`, `macro-architecture`, `software-design-philosophy`, `ui-ux-pro-max` |
| Practice | `clean-code`, `diagnose`, `frontend-design`, `safe-incremental-coding`, `tdd`, `test-lens` |
| Review | `architecture-review`, `code-deslop`, `coding-review-simplify`, `full-review` |
| Delivery | `capture-learning`, `open-pr`, `resolve-pr-feedback`, `session-handoff`, `summarize` |
| Model seats | `claude-runner`, `codex-runner`, `gemini-runner`, `grok-runner`, `pi-runner` |
| Independent utilities | `agents-md-craft`, `browser-smoke`, `cmux-cli`, `collaborative-delivery`, `decide-about-disagreements`, `diverse-plan`, `dynamic-harness`, `environment-check`, `fable-mindset`, `knowledge-graph`, `peer-sessions`, `review-gate`, `skill-expert`, `verify-changes` |
| Visualizations | `consensus-summary-html`, `explain-architecture`, `html-explainer` |

## Install

See the [machine setup checklist](docs/machine-setup.md) for required tools,
optional runners, browser setup, credentials and environment variables.
Run `bash scripts/check-environment.sh` to check local prerequisites.

```bash
npx skills@latest add robsonrung/rar-skills
```

Install every skill:

```bash
npx skills@latest add robsonrung/rar-skills --skill '*'
```

Install from a local checkout:

```bash
scripts/install-skills.sh /path/to/your-project
```

Skills install under `.agents/skills/`. Shared references and runner scripts
install next to them under `.agents/skills/shared/`.

## Model seats

Most planning, design, practice, and review skills run in a compatible host.
For an exact model available in that host, use its native delegation first.
Keep each role's session through later rounds while keeping independent roles
separate. A runner is for a foreign model or a native route that cannot meet the
approved plan. Check external runner availability before selecting one:

```bash
python3 skills/shared/scripts/discover_runners.py probe
```

Resolve model identifiers from the central configuration. A successful probe
confirms a transport, not the model
that later serves the request.

## Documentation

[docs/workflow.md](docs/workflow.md) and [workflow.html](workflow.html) describe
the current workflow.

[docs/skill-review.md](docs/skill-review.md) records the current skill-review
coverage.

[docs/pipeline.html](docs/pipeline.html),
[docs/skills-atlas.html](docs/skills-atlas.html), and
[docs/restructuring-2026-07-30.md](docs/restructuring-2026-07-30.md) are
historical records. They do not define current routing or approval behavior.

[docs/openhands.md](docs/openhands.md) explains how to run the current workflow
with OpenHands.

## License

See [LICENSE](LICENSE).

## Model routing

[`skills/shared/model-routing.json`](skills/shared/model-routing.json) is the
single maintained configuration for model IDs, aliases, reasoning levels,
runner capabilities, task routes, and council roles. Skills and adapters read
it; approved run plans preserve exact selections as immutable snapshots.

```bash
python3 skills/shared/scripts/model_routing.py resolve code-exploration --profile default
python3 skills/shared/scripts/model_routing.py resolve routine-implementation --profile default
python3 skills/shared/scripts/model_routing.py resolve isolated-implementation --profile default --risk high
python3 skills/shared/scripts/model_routing.py council routine --poll-profile lean
python3 skills/shared/scripts/model_routing.py validate
```

Resolution is read only. It does not dispatch workers or change an approved plan.
Bounded tasks use smaller workers with evidence requirements; implementation
routes include an independent stronger reviewer. Risk and escalation rules stay
in the same configuration. These are task defaults, not measured savings or a
guarantee of equal results.
