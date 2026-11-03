# Concepts

Terms with a meaning specific to this repository. Each entry names the file that
owns the rule; read that file for the details. `capture-learning` may add a term
when a learning needs one.

## Models and runners

### Seat

One model's place in a run or a council, such as "the Kimi seat". A seat is an
identity, not a transport. A **native seat** runs through the host's own agent
tool; a **runner seat** calls a local CLI through `cli-runner`, `pi-runner`, or
`muse-runner`. Native comes first:
[host-model-execution.md](skills/shared/references/host-model-execution.md).

### Seat fidelity

A seat never answers with a different model. A missing CLI, failed login, or
different reported model leaves the seat unanswered.
Owner: [runner-common.md](skills/shared/references/runner-common.md#seat-fidelity).

### Model receipt

The serving backend's own report of which model ran (`model_receipt`), kept
apart from the requested and configured model. A route with
`model_verification: required` blocks without a matching receipt. Owners:
[runner-common.md](skills/shared/references/runner-common.md#approved-routes)
and [model-roster.md](skills/shared/references/model-roster.md).

### Envelope

The JSON the Pi and Muse wrapper scripts return, including `agent_message`,
`effective_runner`, and `model_receipt`. Schema:
`skills/shared/runner-envelope.schema.json`. Not the same as the handoff
envelope below.

### Seat tier

Whether a seat joins a default probe (`default`) or only when named (`frontier`,
`backup`, and others). Set in `discovery` in
[model-routing.json](skills/shared/model-routing.json).

### Seat admission and effort scaling

A seat enters the routing configuration only with a verified zero-retention
provider. `effort_scaling` records whether more reasoning effort helps a seat.
Owner: [model-roster.md](skills/shared/references/model-roster.md).

## Running the work

### Work state

A feature's files under `.ai-workflow/work/<feature>/`. Progress lives in
**the ledger, not the transcript**: `tasks.md` and the task reports.
Owner: [work-state.md](skills/shared/references/work-state.md).

### Ceiling and the three exits

A limit counted outside the model's judgment: review cycles, attempts, or calls.
Every task ends `accepted`, `blocked`, or `ceiling_hit`.
Owner: [work-state.md](skills/shared/references/work-state.md).

### Handoff

**Hand off the path, not the payload.** A step gets a brief, writes a report,
and returns a short envelope naming the paths and the verdict.
Owner: [handoff-contract.md](skills/shared/references/handoff-contract.md).

### Thin conductor

An orchestrator that owns routing, scheduling, integration, and delivery, and
leaves each task's work to a subagent. `implement-tasks` is one.
Owner: [implement-tasks](skills/engineering/workflow/implement-tasks/SKILL.md).

### Mode selection

How a skill with modes picks one: the named mode, else a safe default, asking
only when the choice changes scope, cost, or effects.
Owner: [model-preview.md](skills/shared/references/model-preview.md#mode-selection).

### Local config

Per-checkout preferences in `.rar-skills/config.local.yaml` (gitignored, never
credentials). Chat instructions win.
Owner: [local-config.md](skills/shared/references/local-config.md).

## Repository conventions

### `shared/`

The library every skill may load by path: references, model routing, runner
scripts, and tests. A path such as `shared/references/...` is relative to the
installed skills, not the project.
Owner: [skills/shared/SKILL.md](skills/shared/SKILL.md).

### Leitwort (plural leitwörter)

A short phrase a skill has the agent repeat while acting, so the phrase steers its
behavior. Registered in `leitworter.json` and checked by `scripts/check_leitworter.py`.
Owner: [leitworter.md](skills/extras/skill-expert/references/leitworter.md).

### Learning

One verified solution to a past problem, written by `capture-learning` under
`docs/solutions/`. Owner: [docs/solutions/README.md](docs/solutions/README.md).

## Provenance

Material adapted from Every's compound-engineering-plugin (MIT) carries a
provenance line and is credited in `NOTICE`. Upstream names (`ce-*`) appear only
in provenance notes, never as skill names.
