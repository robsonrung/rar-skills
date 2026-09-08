# The development workflow

The standard path is:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

Each skill has one job. The next skill receives an artifact from the previous
one. The routing rules live in
[`workflow-stage-routing.md`](../skills/shared/references/workflow-stage-routing.md).
Current model and effort choices live in
[`task-shaped-model-routing.md`](../skills/shared/references/task-shaped-model-routing.md)
and [`model-roster.md`](../skills/shared/references/model-roster.md).

## 1. `interview-me`

Use this when the request needs decisions before it can become a specification.
It reads the relevant code, glossary, and existing decisions first. When five
independent decisions exist and the interface can show them, it asks exactly
five questions in one turn. Otherwise it asks fewer, never more. A question
with an answer that can be found in the repository is investigated instead of
asked.

It records settled decisions, assumptions, exclusions, security decisions, and
observable success conditions in `.ai-workflow/work/<slug>/decision-record.md`.

Use `security-gate` here when the change has a security surface. Use one broad
engineering lens only when it changes the next question or prevents a false
assumption. Record observable behavior, but reserve `test-lens` for a real
test-design decision during task design or implementation. Use `to-prototype`
only when running a small experiment is the only way to settle a decision that
changes the specification.

## 2. `to-prd`

Use this after the interview closes. It accepts only a decision record marked
`ready-for-prd`, then synthesizes it into `.ai-workflow/work/<slug>/prd.md`.
It does not restart the interview.

The PRD starts as `draft`. It becomes `approved` only after the user reviews
the product scope, behavior, constraints, and acceptance expectations. It
includes security decisions and observable success conditions. Task planning
uses `test-lens` only when a real test-design decision is needed.

## 3. `to-tasks`

Use this after an approved PRD. It creates
`.ai-workflow/work/<slug>/tasks-draft.md` with small, dependency-aware tasks.
Each task has acceptance evidence, affected areas, dependencies, risks, and the
engineering checks selected by the stage-routing rules.

The user approves or changes the task breakdown. Only then does the skill
publish the slice files under `.ai-workflow/work/<slug>/tasks/` with status
`ready-for-agent`.

Task approval approves the work definition. It does not approve the models or
reasoning effort that will be used to implement it.

## 4. `implement-tasks`

Use this only with an approved task queue. Before it starts a worker, it checks
the available model seats and presents an implementation plan. The plan names,
for every task or task group, the role, exact model and runner, reasoning
effort, model-verification policy, and any unavailable seat. The user can
approve the plan or change it.
A missing preferred seat stops the run or requires an explicit approved
replacement. It never silently downgrades a model or effort.

A requested or configured model name is not proof that it served a run. Each
approved route records `model_verification` as `required` or
`allow_unverified`. `required` needs `model_receipt.status: verified` from a
native or provider event. The current Astra and Fable wrappers can lack an
observed serving-model ID, so an `allow_unverified` route needs explicit
approval and the final report labels that limit clearly.

The routing plan binds each approved task input by `content_sha256`. It ignores
only an exact standalone task status line, so a status change does not revoke
approval. Any other input change requires a new model-plan approval.

After model-plan approval, `implement-tasks` delegates bounded work to native
subagents. It uses isolated worktrees only when the user authorizes integration
work. Otherwise it works sequentially and produces a local, verified diff. It
does not create user-owned tasks or require sidebar naming, pinning, or goals.

The implementation path is selected by the task shape:

| Moment | Skills used when applicable |
| --- | --- |
| Design each task slice | `design-gate` once, `security-gate` for the security classification, and `test-lens` only for a real test-design decision |
| An unresolved implementation shape | `coding-design-plan`; reuse inherited gate constraints and reroute only for a changed design surface |
| New or changed behavior | `tdd`; use `test-lens` only when a test-design decision is needed |
| Untested legacy code | `safe-incremental-coding` before broad edits |
| A failure that is not immediately understood | `diagnose` |
| While improving a verified change | `clean-code` and `coding-review-simplify` |
| Final task and feature review | Approved scoped review; `full-review` for integration seams or named risks, plus `browser-smoke` for affected web flows |

Reuse captured checks when the relevant code, dependencies, environment, and
acceptance contract still match. Rerun affected checks and those explicitly
required fresh. A complete single-task review does not need a duplicate panel.
Routine design and code review do not call `models-consensus`.

## Optional council

`models-consensus` is for a user who explicitly wants more opinions on a
decision. It is user-invoked only and is not an automatic workflow escalation.
No workflow or model invokes it. Before it starts, it shows the mode, selected model seats, exact models and
transports, roles, reasoning effort, call budget, and unavailable seats. The
user approves or changes that roster. The council is deliberation only. It does
not implement code or replace normal review.

## Delivery boundary

`implement-tasks` produces a local, verified result by default. Committing,
pushing, opening or updating a pull request, and creating or changing a tracker
item each require explicit user authorization. A verified local result remains
reviewable when no delivery action is authorized.

## Optional tools

`brainstorm` can clarify a broad idea before the interview. `to-prototype` can
answer one runnable uncertainty during discovery or planning. These are detours,
not extra mandatory stages.
