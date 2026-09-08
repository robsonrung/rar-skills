---
name: models-consensus
description: Run a read-only council of model opinions after the user approves its model plan. Use only when the user invokes this skill or explicitly asks for extra model opinions; never use as an automatic escalation.
disable-model-invocation: true
---

# Models Consensus

Produce a decision report for a user who wants more than one model's opinion. The next consumer is the user. Done means the report names the recommendation, dissent, evidence limits, one next step, configured and observed seats, and receipt limits.

This is a user-controlled, read-only workflow. A council is justified only when the user decides that independent opinions are worth its time and cost.

## Entry and approval

Run only after the user explicitly invokes `models-consensus` or explicitly asks for extra model opinions. Another skill may suggest this workflow as a manual next step, but must not invoke it.

Before dispatching any model:

1. Choose `poll` by default, `debate` for a contested direction, or `personas` when the user wants five angles from one chosen model.
2. Read [references/role-routing.md](references/role-routing.md), resolve the current seat and requested-model mapping from `shared/references/model-roster.md`, and make read-only transport checks. If `.rar-skills/config.local.yaml` exists, read its advisory `seats` and `models` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and runner, let direct user instructions win, and never reread it after approval.
3. Show the approval preview below and ask: **"Approve this council plan, or specify changes."**
4. Wait for a clear approval. Silence, a timeout, a prior general approval, an `auto` request, or another skill's instruction is not approval.

The preview must show every planned and conditional call:

| Field | Required content |
| --- | --- |
| Question and mode | The neutral question and `poll`, `debate`, or `personas` |
| Seats | Seat id, requested model label, provider, and transport for each opening seat |
| Roles | Organizer, each judge, and synthesizer or chairman, with their seat and requested model label |
| Effort | Exact configured effort or runtime-controlled effort for every model call |
| Serving receipt | `required` or `explicitly allowed unverified`, with status, source, and observed model for every seat |
| Budget | Base call count, conditional calls, validation-retry ceiling, hard maximum, and output cap |
| Tools | The shared read-only tool profile |
| Evidence | Which transport checks passed and that serving-model receipts are still pending |

Use **seat fidelity**: an approved seat is that exact requested-model label, receipt requirement, and transport. Every runner call uses `--disable-fallback`. If a selected seat, model label, receipt requirement, transport, effort, or role changes after the preview, stop and show a revised preview. A pending receipt becoming verified for the approved model is new evidence and needs no new approval. An observed model mismatch or an unmet required receipt blocks that route; never weaken the receipt requirement to continue. Do not substitute, downgrade, add a seat, switch mode, or degrade to personas without new approval.

Use this preview shape after resolving the roster:

```text
Council plan: awaiting approval
Mode: <mode>
Opening: <seat> / <requested model> / <receipt status and source> / <transport> / <effort or runtime-controlled>
Organizer: <seat> / <requested model> / <effort or runtime-controlled>
Judges: <seat> / <requested model> / <effort or runtime-controlled>; <seat> / <requested model> / <effort or runtime-controlled>
Synthesis or chairman: <seat> / <requested model> / <effort or runtime-controlled>
Budget: <base> base, <conditional> conditional, <retry ceiling> retries, <hard maximum> maximum calls
Tools: <read-only profile>
Evidence: <transport checks>; serving-model receipts pending
Serving receipt: required | explicitly allowed unverified

Approve this council plan, or specify changes.
```

## Council modes

| Mode | Use when | Protocol |
| --- | --- | --- |
| `poll` | The user needs independent answers and a reconciled recommendation | [references/poll-protocol.md](references/poll-protocol.md) |
| `debate` | The user wants competing directions pressure-tested | [references/stance-rotation-schedule.md](references/stance-rotation-schedule.md) |
| `personas` | The user wants five thinking lenses from one selected model | [references/personas.md](references/personas.md) |

All modes are read-only for the target project. They may write only their local state, response artifacts, and final report under `.ai-workflow/consensus/`. They do not edit product files, run write-capable tools, or start implementation.

## Preflight

Use [references/operations.md](references/operations.md) for the approval record, artifact state, response validation, and recovery rules. Use [references/runner-invocations.md](references/runner-invocations.md) only after approval. Use [references/cmux-transport.md](references/cmux-transport.md) only when the approved preview selects `cmux`.

Probe a transport before the preview. A successful probe proves only that a route may start. A native or provider-observed serving-model receipt proves the serving model. A wrapper-echoed `effective_model` label does not. A response without a verified receipt may inform the report but cannot increase diversity confidence.

For `poll` and `debate`, require three approved, distinct opening seats. If the probe cannot support the plan, report the blocker and offer a revised plan. For `personas`, the preview must name the single model used for all advisor, reviewer, and chairman calls.

## Execution

After approval, keep contexts separate: orchestrator, opening seats, organizer, judges, synthesizer, advisors, reviewers, and chairman are fresh contexts. Give every opening seat the same neutral brief, read-only sources, tool profile, and output budget.

In `poll`, run blind openings, organizer analysis, at most one gap-repair round, two judges, then synthesis. In `debate`, run the approved number of rounds, with the anonymized digest and fixed ceiling. In `personas`, run five lenses, anonymized peer review when the preview includes it, then the chairman.

If an approved call fails, retain the failure in the state and report it. Do not use another model in its place. A material loss of quorum ends the run with the evidence collected and a clear revised-plan option.

## Output

Return or write `.ai-workflow/consensus/{session_id}.md` with:

1. Question, mode, approved preview, and actual run record.
2. Recommendation and one next step.
3. Agreements, dissent, blind spots, and evidence gaps.
4. Answer confidence and diversity confidence, separately.
5. Seat receipts: requested, configured, effective, and observed model fields; receipt status and source; provider, transport, effort control, and any failure.

For an adoption decision, use one plain-language grade: Adopt, Trial, Hold, Reject, or Not-our-problem. If the evidence is insufficient, return "Hold: insufficient evidence" and list what to inspect.

The council never implements its recommendation. A user can later choose a separate implementation workflow.
