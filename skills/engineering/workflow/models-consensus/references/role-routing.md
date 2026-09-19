# Council Role Routing

Resolve exact model ids, effort support, and execution paths through
`shared/references/model-roster.md`,
`shared/references/task-shaped-model-routing.md`, and
`shared/references/host-model-execution.md`. This file selects council roles
and their independence boundaries. Its result is a recommendation for the user
approval preview, never a dispatch instruction.

For `poll` and `debate`, require three opening seats that name distinct
requested models. Provider diversity can strengthen the evidence, but it is not
a requirement. A native-only panel still has model diversity when receipts show
distinct observed models. `personas` is the separate scope-limited mode for one
model and reports low diversity by construction.

Every opening, organizer, judge, synthesizer, advisor, reviewer, and chairman
gets a separate `continuity_key`. Reuse that key only for the same role's retry,
gap repair, or later debate turn. An organizer may use the same selected model
as an opening seat, but it starts as a separate context. Judges start isolated
from openings and from each other.

## Default poll and debate panels

All opening, organizer, judge, and synthesis selections live in
`councils` in `shared/model-routing.json`. Select the technical, analysis, routine,
or security council by question shape. Run `scripts/model_routing.py council
<name>` from the resolved shared skill to produce exact preview values without
starting any calls. A council remains optional and user invoked.

Use the task route's conditions and escalation policy when more reasoning is
needed. Record changes as exact proposed roles before approval. More reasoning
does not add seats or change the call ceiling. A reviewer of an existing artifact
must be independent of its writer when the role requires that independence.

## Defensive security panel

Use the configured security council. `conditional_models` records specialist
candidates that cannot be dispatched until their exact model ID, entitlement,
effort, tools, and receipt policy are established. An ordinary model does not
satisfy a specialist selection. Any proposed specialist or alternate panel must
appear in the approval preview; unavailable capability never permits substitution.

## Budgets and diversity

For a poll, the base plan is three openings, one organizer, two judges, and one
synthesis: seven calls. The organizer can request one gap-repair round with up
to three same-seat calls. Each planned or conditional call has one same-route
validation retry. State `base: 7`, `conditional gap repair: 3`, and `hard
maximum: 20` in the preview.

For a debate, use the selected opening seats in each approved round. The preview
lists the fixed round ceiling, moderator, stance assignment from
[stance-rotation-schedule.md](stance-rotation-schedule.md), base calls, and
hard maximum after each same-route validation retry.

Distinct requested labels establish planned coverage. Distinct verified observed
models establish verified model diversity. A provider difference is additional
independence evidence when receipts prove it. Unverified, duplicate, missing,
or failed seats do not increase diversity confidence.

## Personas

Use one selected model for all five advisors, five reviewers, and the chairman.
Select the task route and exact effort from the central configuration before the preview. Advisors and chairman use
the route's primary effort; reviewers use a lower supported effort only when the
approved plan says so.

The preview states whether peer review is included and lists the resulting base
call count. Personas provide angle diversity, not model or provider diversity.
