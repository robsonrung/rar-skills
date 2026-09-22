# rar-skills

`rar-skills` is an engineering skill library. Its main workflow turns a
well-understood request into a verified local result through four clear stages:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

The full contract is in [docs/workflow.md](docs/workflow.md). It is the current
source for workflow behavior.

## Workflow

| Stage | Output | Main responsibility |
| --- | --- | --- |
| `interview-me` | `decision-record.md` | Use relevant repository facts, then ask at most five independent questions in one turn. With `--auto`, keep two isolated role contexts: resolve the product or technical interview roles from the central routing configuration. The respondent can provide evidence and alternatives, but cannot settle a material user decision. Record settled decisions and scope; the record becomes `ready-for-prd` when the interview closes. |
| `to-prd` | `prd.md` | Turn a `ready-for-prd` decision record into a draft PRD. The user reviews it before it becomes approved. |
| `to-tasks` | `tasks-draft.md`, then task slices | Create dependency-aware tasks with acceptance evidence and applicable engineering checks. The user approves the task breakdown before slices become `ready-for-agent`. |
| `implement-tasks` | Verified local result | Show the proposed roles, exact implementation and review models, execution paths, reasoning effort, and model-verification policy before dispatch. Use the shared preview decision, including an explicit request to use defaults and run for the unchanged setup. |

Task approval and model selection are separate. A task queue defines what
will be built. The model plan defines who will implement and review it. Every
directly invoked skill uses the [shared preview](skills/shared/references/model-preview.md).
It names the actual coordinator, exact worker routes, tools, privacy controls,
fallbacks, and limits. A skill that runs only commands starts no additional worker.
Nested skills reuse the selected snapshot without another prompt. A request to
use defaults and run permits the unchanged resolved setup within existing source
sharing authority and accepted receipt limits; silence cannot approve it.

Updated workflow callers select the central `saver` profile by default: cheap
seats (GLM 5.3 Flash, DeepSeek V4.1 Flash, with Grok and Gemini alternates)
implement and explore, while frontier seats (Astra, Opus 5.5) keep every
reviewer role. `economy` (cheap reviewers too), `balanced`, and explicit
legacy family routes remain selectable. Local preferences
select a profile name, while model and effort defaults remain in
`skills/shared/model-routing.json`. No local quality or savings comparison has
been run for the new selection.

`implement-tasks` checks native host capability before external runner
availability, chooses the route for each task shape, and uses the approved
effort. It reports unavailable seats and never silently replaces a preferred
model or effort. An exact native model uses an isolated persistent subagent or,
when supported and authorized, a task thread. A runner serves a foreign model
or an exact route the host cannot provide. Workspace selection and integration
follow the engine's
[isolation and integration contract](skills/engineering/engine/implement-and-review/references/worktree-and-integration.md).
Without delivery authorization, the result stays local and verified.

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
| Plan a task slice | `design-gate` once, `security-gate` for the security classification, and `test-lens` only for a real test-design decision |
| Resolve an implementation shape | `coding-design-plan` when the shape is unresolved; reuse inherited gate constraints |
| Build new behavior | `tdd`, then `clean-code` for a refactor decision and `test-lens` for a test-design decision |
| Change untested legacy code | `safe-incremental-coding` before broad edits |
| Investigate an unexpected failure | `diagnose` |
| Review a completed change | Approved scoped review; `full-review` for integration seams or named risks, `coding-review-simplify` for a useful simplification, and `browser-smoke` for affected web flows |

Reuse captured checks when the relevant code, dependencies, environment, and
contract still match; rerun affected checks and any required fresh checks.
Routine reviews do not start a council.

## Feature validation

[`validate-e2e`](skills/engineering/workflow/validate-e2e/SKILL.md) validates an
existing feature against a finite acceptance contract. It previews editable model
routes and runner choices, reuses current evidence, and records bounded test and
model attempts. Required behavior and runtime gates remain separate. It returns
a scoped result without opening a pull request or changing production.

## Optional council

`models-consensus` is for a user who explicitly asks for more opinions. It is
user-invoked only. No workflow or model invokes it. Before it runs, it presents the mode, selected model seats,
exact models and transports, roles, reasoning effort, call budget, and
unavailable seats. The user approves or changes the roster. It provides
deliberation only and never implements code.

## Delivery

The workflow stops at a local, verified result unless the user explicitly asks
to commit, push, open or update a pull request, or create or change a tracker
item. Those actions are never implied by task or model-plan approval.

## Library map

There are 58 installable skills. The following map keeps every skill
discoverable while leaving detailed instructions in each `SKILL.md`.

| Domain | Skills |
| --- | --- |
| Workflow | `brainstorm`, `interview-me`, `to-prd`, `to-tasks`, `implement-tasks`, `to-prototype`, `models-consensus`, `pre-pr-review`, `validate-e2e` |
| Engine | `coding-design-plan`, `implement-and-review`, `worktree` |
| Gates | `design-gate`, `security-gate` |
| Lenses | `advanced-react`, `agent-architecture-lens`, `architecture-lens`, `data-systems-coding-lens`, `design-patterns`, `distributed-systems-patterns`, `domain-driven-design`, `macro-architecture`, `software-design-philosophy`, `ui-ux-pro-max` |
| Practice | `clean-code`, `diagnose`, `frontend-design`, `safe-incremental-coding`, `tdd`, `test-lens` |
| Review | `coding-review-simplify`, `full-review` |
| Delivery | `capture-learning`, `open-pr`, `resolve-pr-feedback`, `session-handoff`, `summarize` |
| Model seats | `claude-runner`, `codex-runner`, `gemini-runner`, `grok-runner`, `pi-runner` |
| Independent utilities | `agents-md-craft`, `browser-smoke`, `cmux-cli`, `collaborative-delivery`, `decide-about-disagreements`, `diverse-plan`, `dynamic-harness`, `fable-mindset`, `knowledge-graph`, `peer-sessions`, `review-gate`, `skill-expert`, `verify-changes` |
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

The roster is the only source of model identifiers. Do not copy model IDs into
workflow instructions. A successful probe confirms a transport, not the model
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
python3 skills/shared/scripts/model_routing.py resolve code-exploration --family gpt
python3 skills/shared/scripts/model_routing.py resolve routine-implementation --family claude
python3 skills/shared/scripts/model_routing.py resolve isolated-implementation --family gpt --risk high
python3 skills/shared/scripts/model_routing.py validate
```

Resolution is read only. It does not dispatch workers or change an approved plan.
Bounded tasks use smaller workers with evidence requirements; implementation
routes include an independent stronger reviewer. Risk and escalation rules stay
in the same configuration. These are task defaults, not measured savings or a
guarantee of equal results.
