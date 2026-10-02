# Council Role Routing

Resolve exact model ids, effort support, and execution paths through
`shared/references/model-roster.md`,
`shared/references/task-shaped-model-routing.md`, and
`shared/references/host-model-execution.md`. This file selects council roles
and their independence boundaries. Its result is a recommendation for the user
approval preview, never a dispatch instruction.

For `poll` and `debate`, require three blind opening roles that name distinct
requested models. The seat registry can include an additional organizer or judge
only seat. Provider diversity can strengthen the evidence, but it is not a
requirement. A native-only panel still has opening diversity when the three
opening receipts show distinct observed models. `personas` is the separate
scope-limited mode for one model and reports low diversity by construction.

The seat registry contains every approved role model. Every role references a
registered seat, and each registered seat supports at least one approved role.
Registering an extra conditional judge does not increase opening diversity.

Every opening, organizer, judge, synthesizer, advisor, reviewer, and chairman
gets a separate `continuity_key`. Reuse that key only for the same role's retry,
gap repair, or later debate turn. An organizer may use the same selected model
as an opening seat, but it starts as a separate context. Judges start isolated
from openings and from each other.

## Default poll and debate panels

All opening, organizer, judge, and synthesis selections live in
`councils` in `shared/model-routing.json`. Select the technical, analysis, routine,
or security council by question shape. Run `scripts/model_routing.py council
<name> --poll-profile <standard|lean> --risk-flag <flag>` from the resolved shared
skill to produce exact preview values without starting any calls. Omit the optional
arguments for standard with no flags. A council remains optional and user invoked.

Use the task route's conditions and escalation policy when more reasoning is
needed. Record changes as exact proposed roles before approval. More reasoning
does not add seats or change the call ceiling. A reviewer of an existing artifact
must be independent of its writer when the role requires that independence.

## Poll profiles

The central `council_policy` defines poll profiles, the maintained low confidence
threshold, and the full required risk flags. A resolved council
preview records `council_name`, `poll_profile`, `risk_flags`, `poll_policy`,
`poll_budget`, and `conditional_stages`. It derives every opening, organizer,
judge, synthesis, model, effort, tool, and receipt value from
`shared/model-routing.json`.

An omitted `poll_profile` is legacy `standard`. An explicit profile is either
`standard` or `lean`. Select `standard` before approval for `security`,
`money`, `migrations`, `public_contracts`, `data_loss`, `deep_review`, or
`high_risk`. A security council also selects standard. An explicit lean request
with any full required risk flag fails. Replace it with a new standard preview.

Lean is for a low risk question. Its preview still lists both judges with their
exact routes, continuity keys, effort, tool profile, receipt requirement, and
budget. It marks them conditional with
`organizer_material_conflict_or_gap_or_low_confidence_or_high_risk`. Native and
runner `per_call` execution can enforce that gate. `cmux` cannot, so a lean
preview using `cmux` is invalid.

## Defensive security panel

Use the configured security council. `conditional_models` records specialist
candidates that cannot be dispatched until their exact model ID, entitlement,
effort, tools, and receipt policy are established. An ordinary model does not
satisfy a specialist selection. Any proposed specialist or alternate panel must
appear in the approval preview; unavailable capability never permits substitution.

## Budgets and diversity

For a standard poll, the base plan is three openings, one organizer, two judges,
and one synthesis: seven calls. The organizer can request one gap repair round
with up to three same seat calls. Each planned or conditional call has one same
route validation retry. State `base_calls: 7`, `conditional_calls: 3`,
`validation_retry_ceiling: 10`, and `maximum_calls: 20` in the preview.

For a lean poll, the base plan is three openings, one organizer, and one
synthesis: five calls. It has two conditional judges and three planned optional
gap repairs. State `base_calls: 5`, `conditional_calls: 5`,
`validation_retry_ceiling: 10`, and `maximum_calls: 20`. A conditional judge
does not spend a call when the validated organizer evidence shows it is not
needed. It receives `conditional-not-needed`, never a successful execution
status. An explicit approval may use a smaller retry ceiling and matching maximum
under the generic call budget contract.

For a debate, use the selected opening roles in each approved round. The preview
lists the fixed round ceiling, moderator, stance assignment from
[stance-rotation-schedule.md](stance-rotation-schedule.md), base calls, and
hard maximum after each same-route validation retry.

Distinct requested labels for the three blind openings establish planned opening
coverage. Distinct verified observed opening models establish opening diversity.
A provider difference is additional independence evidence when receipts prove
it. Unverified, duplicate, missing, or failed opening roles do not increase
diversity confidence. A conditional judge receipt can inform the decision but
does not increase opening diversity.

## Personas

Use one selected model for all five advisors, five reviewers, and the chairman.
Select the task route and exact effort from the central configuration before the preview. Advisors and chairman use
the route's primary effort; reviewers use a lower supported effort only when the
approved plan says so.

The preview states whether peer review is included and lists the resulting base
call count. Personas provide angle diversity, not model or provider diversity.
