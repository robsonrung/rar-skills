# rar-skills

`rar-skills` is an engineering skill library. Its main workflow turns a
well-understood request into a verified local result through four clear stages:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

The full contract is in [docs/workflow.md](docs/workflow.md). It is the current
source for workflow behavior.

## Workflow

| Stage | Output | Main responsibility |
| --- | --- | --- |
| `interview-me` | `decision-record.md` | Read the repository first, then ask exactly five independent questions when five exist and the interface can show them. Otherwise ask fewer, never more. Record decisions, assumptions, exclusions, security decisions, and observable success conditions. The record becomes `ready-for-prd` only when the interview closes. |
| `to-prd` | `prd.md` | Turn a `ready-for-prd` decision record into a draft PRD. The user reviews it before it becomes approved. |
| `to-tasks` | `tasks-draft.md`, then task slices | Create dependency-aware tasks with acceptance evidence and applicable engineering checks. The user approves the task breakdown before slices become `ready-for-agent`. |
| `implement-tasks` | Verified local result | Show the proposed roles, exact implementation and review models, runners, reasoning effort, and model-verification policy before dispatch. Start work only after the user approves or changes that model plan. |

Task approval and model-plan approval are separate. A task queue defines what
will be built. The model plan defines who will implement and review it.

`implement-tasks` checks model availability, chooses the strongest suitable
model for each task shape, and uses the lowest sufficient reasoning effort. It
reports unavailable seats and never silently replaces a preferred model or
effort. It delegates bounded work to native subagents. Isolated worktrees and
integration happen only when the user authorizes that work. Without delivery
authorization, the result stays local and verified.

A requested or configured model is not proof that it served a run. Each route
records `model_verification` as `required` or `allow_unverified`. `required`
needs `model_receipt.status: verified` from a native or provider event. The
current Astra and Fable wrappers can lack an observed serving-model ID, so an
`allow_unverified` route needs explicit approval and reports that limit clearly.

The stage rules are in
[workflow-stage-routing.md](skills/shared/references/workflow-stage-routing.md).
Model choices are in
[task-shaped-model-routing.md](skills/shared/references/task-shaped-model-routing.md)
and [model-roster.md](skills/shared/references/model-roster.md).

### Engineering practices in the workflow

| Moment | Skills |
| --- | --- |
| Discover risk and behavior | `security-gate`, a broad lens only when it changes the next question, and `to-prototype` when a runnable question blocks a decision |
| Plan a task slice | `design-gate` once, `security-gate` for the security classification, and `test-lens` only for a real test-design decision |
| Change the design during implementation | `coding-design-plan` and the inherited gate constraints |
| Build new behavior | `tdd`, then `clean-code` for a refactor decision and `test-lens` for a test-design decision |
| Change untested legacy code | `safe-incremental-coding` before broad edits |
| Investigate an unexpected failure | `diagnose` |
| Verify a completed change | `coding-review-simplify`, `full-review`, and `browser-smoke` for affected web flows |

Routine reviews use the normal design and review skills. They do not start a
council.

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

There are 59 installable skills. The following map keeps every skill
discoverable while leaving detailed instructions in each `SKILL.md`.

| Domain | Skills |
| --- | --- |
| Workflow | `brainstorm`, `interview-me`, `to-prd`, `to-tasks`, `implement-tasks`, `to-prototype`, `models-consensus` |
| Engine | `coding-design-plan`, `implement-and-review`, `worktree` |
| Gates | `design-gate`, `security-gate` |
| Lenses | `advanced-react`, `agent-architecture-lens`, `architecture-lens`, `data-systems-coding-lens`, `design-patterns`, `distributed-systems-patterns`, `domain-driven-design`, `macro-architecture`, `software-design-philosophy`, `ui-ux-pro-max` |
| Practice | `clean-code`, `diagnose`, `frontend-design`, `safe-incremental-coding`, `tdd`, `test-lens` |
| Review | `coding-review-simplify`, `full-review` |
| Delivery | `capture-learning`, `open-pr`, `resolve-pr-feedback`, `session-handoff`, `summarize` |
| Model seats | `claude-runner`, `cline-runner`, `codex-runner`, `dcode-runner`, `gemini-runner`, `grok-runner`, `opencode-runner`, `pi-runner` |
| Independent utilities | `agents-md-craft`, `browser-smoke`, `cmux-cli`, `collaborative-delivery`, `decide-about-disagreements`, `diverse-plan`, `dynamic-harness`, `fable-mindset`, `knowledge-graph`, `peer-sessions`, `review-gate`, `skill-expert`, `verify-changes` |
| Visualizations | `consensus-summary-html`, `explain-architecture`, `html-explainer` |

## Install

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
Runner-backed work requires only the local CLIs for the seats selected for that
run. Check availability before selecting a model:

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
