---
name: models-consensus
description: Run a read-only council of model opinions after the user approves its model plan. Use only when the user invokes this skill or explicitly asks for extra model opinions; never use as an automatic escalation.
disable-model-invocation: true
---

# Models Consensus

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Produce a decision report for a user who wants more than one model's opinion. The next consumer is the user. Done means the report names the recommendation, dissent, evidence limits, one next step, configured and observed seats, and receipt limits.

This is a user-controlled, read-only workflow. A council is justified only when the user decides that independent opinions are worth its time and cost.

## Entry and approval

Run only after the user explicitly invokes `models-consensus` or explicitly asks for extra model opinions. Another skill may suggest this workflow as a manual next step, but must not invoke it.

Before dispatching any model:

1. Choose `poll` by default, `debate` for a contested direction, or `personas` when the user wants five angles from one chosen model.
2. Read [references/role-routing.md](references/role-routing.md), `shared/references/model-roster.md`, `shared/references/task-shaped-model-routing.md`, and `shared/references/host-model-execution.md`. Check a native host route before an external runner. If `.rar-skills/config.local.yaml` exists, read its advisory `seats` and `models` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and selected execution path, let direct user instructions win, and never reread it after approval.
3. Show the approval preview below and ask: **"Approve this council plan, or specify changes."**
4. Wait for a clear approval. Silence, a timeout, a prior general approval, an `auto` request, or another skill's instruction is not approval.

The preview must show every planned and conditional call:

| Field | Required content |
| --- | --- |
| Question and mode | The neutral question and `poll`, `debate`, or `personas` |
| Seats | Seat id, requested model label, provider, and execution path for each opening seat |
| Roles | Organizer, each judge, and synthesizer or chairman, with their seat, requested model label, and continuity key |
| Effort | Exact configured effort or runtime-controlled effort for every model call |
| Host and session | Checked host or runner, per-role session policy, and whether the role can resume by its recorded id |
| Serving receipt | `required` or `explicitly allowed unverified`, with status, source, and observed model for every seat |
| Budget | Base call count, conditional calls, validation-retry ceiling, hard maximum, and output cap |
| Tools | The shared read-only tool profile |
| Evidence | Which native or runner checks passed and that serving-model receipts are still pending |

Use **seat fidelity**: an approved seat is that exact requested-model label, receipt requirement, execution path, effort, and role continuity policy. Every runner call uses `--disable-fallback`; a native route has no runner fallback. If a selected seat, model label, receipt requirement, host, execution path, effort, role, or session policy changes after the preview, stop and show a revised preview. A pending receipt becoming verified for the approved model is new evidence and needs no new approval. An observed model mismatch or an unmet required receipt blocks that route; never weaken the receipt requirement to continue. Do not substitute, downgrade, add a seat, switch mode, or degrade to personas without new approval.

Use this preview shape after resolving the roster:

```text
Council plan: awaiting approval
Mode: <mode>
Opening: <seat> / <requested model> / <receipt status and source> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Organizer: <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Judges: <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key>; <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Synthesis or chairman: <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Budget: <base> base, <conditional> conditional, <retry ceiling> retries, <hard maximum> maximum calls
Tools: <read-only profile>
Evidence: <native or runner checks>; serving-model receipts pending
Sessions: <persistent per-role policy and resume limit>
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

Probe the selected execution path before the preview. A successful native capability check or runner probe proves only that a route may start. A native or provider-observed serving-model receipt proves the serving model. A wrapper-echoed `effective_model` label does not. A response without a verified receipt may inform the report but cannot increase diversity confidence.

For `poll` and `debate`, require three approved opening seats with distinct requested model labels. Three providers are not a requirement. Count model diversity only when distinct observed models verify it; verified provider diversity is supporting evidence, not a seat-count rule. If preflight cannot support a route, report the blocker and offer a revised three-seat plan. `personas` is the separate single-model mode; its preview must name the model used for all advisor, reviewer, and chairman calls.

## Execution

After approval, create one isolated, persistent context per task and role. Give every opening seat the same neutral brief, read-only sources, tool profile, and output budget. An opening seat can resume only its own context for a schema retry or approved gap repair. The organizer, each judge, synthesizer, advisor, reviewer, and chairman has a separate context. Judges begin without opening-seat or organizer history and do not share a context with each other.

In `poll`, run blind openings, organizer analysis, at most one gap-repair round, two judges, then synthesis. In `debate`, run the approved number of rounds, with the anonymized digest and fixed ceiling. In `personas`, run five lenses, anonymized peer review when the preview includes it, then the chairman.

If an approved call or session resume fails, retain the failure and its recorded context id in the state and report it. Reconcile a pending call before sending it again. Do not use another model or an unapproved new context in its place. A material loss of quorum ends the run with the evidence collected and a clear revised-plan option.

## Output

Return or write `.ai-workflow/consensus/{session_id}.md` with:

1. Question, mode, approved preview, and actual run record.
2. Recommendation and one next step.
3. Agreements, dissent, blind spots, and evidence gaps.
4. Answer confidence and diversity confidence, separately.
5. Seat receipts: requested, configured, effective, and observed model fields; receipt status and source; provider, host, execution path, effort control, role context status, and any failure.

For an adoption decision, use one plain-language grade: Adopt, Trial, Hold, Reject, or Not-our-problem. If the evidence is insufficient, return "Hold: insufficient evidence" and list what to inspect.

The council never implements its recommendation. A user can later choose a separate implementation workflow.
