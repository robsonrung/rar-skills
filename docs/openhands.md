# Running the workflow on OpenHands

OpenHands can host the same four-stage workflow:

`interview-me` → `to-prd` → `to-tasks` → `implement-tasks`

The workflow rules stay in the skills. OpenHands does not change approval,
model-routing, or delivery boundaries. Read [workflow.md](workflow.md) before
starting a run.

## Install and discover the skills

Install the collection in the target repository:

```bash
scripts/install-skills.sh /path/to/your-project
```

Start OpenHands in that repository and confirm that the installed skills are
visible. The install location is `.agents/skills/`. A root `AGENTS.md` or
`CLAUDE.md` remains normal repository context.

When a host hides a user-invoked skill from the model's normal skill list, tell
the agent to read its installed file directly:

```text
Read .agents/skills/interview-me/SKILL.md and follow it for: <feature idea>
```

Use the same form for `to-prd`, `to-tasks`, and `implement-tasks`. A user can
use it for `models-consensus` only after directly requesting the council.

## Stages 1 through 3

Run `interview-me` where the user can answer questions. It reads the repository
before asking. When five independent decisions exist and the interface can show
them, it asks exactly five questions in one turn. Otherwise it asks fewer,
never more. It writes `.ai-workflow/work/<slug>/decision-record.md`. Run
`to-prd` only after that record has status `ready-for-prd`.

Then run `to-prd`. It creates `prd.md` as a draft. The user reviews the PRD
before it becomes approved.

Then run `to-tasks`. It creates `tasks-draft.md`, and the user reviews the task
breakdown before the task slices are published as `ready-for-agent`.

The task approval defines the work. It does not approve the implementation or
review model choices.

## Stage 4

Invoke `implement-tasks` only for an approved task queue. Before it creates a
worker, it probes available model seats and shows the planned role, exact
implementation and review model, runner, reasoning effort, model-verification
policy, and any unavailable seat. The user must approve or change this plan
before work starts. A missing preferred seat is reported. It is never replaced
silently.

A requested or configured model name is not proof that it served the task. Each
route records `model_verification` as `required` or `allow_unverified`.
`required` needs `model_receipt.status: verified` from a native or provider
event. The current Astra and Fable wrappers can lack an observed serving-model
ID, so an `allow_unverified` route needs explicit approval and the report
labels that limit clearly.

Use native subagents for bounded work when the host supports them. Run tasks
sequentially when isolated integration is not authorized. Worktrees and
integration require user authorization. Otherwise the expected output is a
local, verified result.

## Optional council

`models-consensus` is not part of automatic planning or implementation. Use it
only when the user explicitly requests more opinions. No workflow or model
invokes it. It previews its selected
seats, exact models and transports, roles, reasoning effort, and call budget,
then waits for roster approval. It provides a decision record only. Normal
design and code review still use `design-gate`, the selected lenses, and
`full-review`.

## Model seats

Runner-backed seats use the installed local CLIs and their existing
authentication. Probe them before choosing a model:

```bash
python3 .agents/skills/shared/scripts/discover_runners.py probe --native-agent no
```

The current model identifiers are in
`.agents/skills/shared/references/model-roster.md`. The task-shaped selection
rules are in `.agents/skills/shared/references/task-shaped-model-routing.md`.
Do not copy model identifiers into an OpenHands prompt or configuration file.
A successful probe confirms only that a transport may start. The serving-model
receipt provides the model provenance.

## Delivery

OpenHands may run commands needed to build and verify the approved task. It
must not commit, push, create or update a pull request, or create or modify a
tracker item unless the user explicitly authorizes that action. The normal
completion point is a local, verified result with evidence.

## Run state

The workflow stores its decision, PRD, task, and implementation artifacts under
`.ai-workflow/`. Those files let a later session continue from the approved
stage. The routing plan records each input `content_sha256` and ignores only an
exact standalone task status line. These files do not replace the separate task
and model-plan approvals.
