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

| Question shape | Opening roles | Organizer and synthesis | Judges |
| --- | --- | --- | --- |
| Developer technical problem, difficult debugging, TDD, or tool-heavy repository work | Astra: executable diagnosis; Fable: assumptions and alternatives; Opus: subtle semantic risk | Astra | Fable and Opus |
| Ambiguous problem, research, architecture, or trade-off | Fable: deep reasoning; Astra: execution feasibility; Opus: precision constraints | Fable | Astra and Opus |
| Broad code review or migration | Astra: broad defect discovery; Fable: system and design impact; Opus: precision review | Astra | Fable and Opus |
| Many competing approaches | Astra: branch exploration; Fable: coherent deep path; Opus: decision precision | Astra | Fable and Opus |
| Routine, explicit change when a council is still justified | Terra: simplest correct implementation; Astra: hidden risk and acceptance; Fable: requirement ambiguity | Astra | Fable and Astra |

Use the task routing defaults for effort. In particular, use Astra `ultra` only
when parallel branch exploration is part of the approved question; it does not
add council seats by itself. A broad-review panel may use Sol in place of Astra
only when that produces a distinct approved model perspective, such as review
of an Astra-authored artifact.

When a panel selects Opus at `xhigh`, preflight must validate that the selected
native or runner adapter accepts that exact label for the selected model. If it
cannot, block the route and show a revised plan. Do not silently translate
`xhigh` to `max`.

## Defensive security panel

Use a Gemini 3.8 Flash Cyber seat at `high` only after preflight proves its
exact identifier, access, model selection, and effort control. Ordinary Gemini
Flash is not that seat. A serving-model receipt can arrive only after an
approved call; until then the preview must explicitly allow an unverified
receipt, and the result must not count Cyber toward diversity confidence. A
matching later receipt updates evidence without changing the approved plan.
Use Cyber for adversarial security analysis, Astra for attack-surface and repair
feasibility, and Opus for exploitability precision. Astra organizes and
synthesizes; Cyber and Opus judge.

If Cyber cannot meet that preflight, do not silently replace it. Show an
explicit alternate panel for approval: Astra at `max` for security analysis,
Fable at `max` for architecture and evidence gaps, and Opus at `xhigh` for
precision review. State that this is an Astra fallback, not a Cyber result.

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
For a coding or systems question, the shared routing normally selects Astra; for
ambiguous architecture, research, or product judgment, it normally selects
Fable. Resolve the exact effort before the preview. Advisors and chairman use
the route's primary effort; reviewers use a lower supported effort only when the
approved plan says so.

The preview states whether peer review is included and lists the resulting base
call count. Personas provide angle diversity, not model or provider diversity.
