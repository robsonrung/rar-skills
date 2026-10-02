---
name: models-consensus
description: Run a read-only council of model opinions after the user approves its model plan. Use only when the user invokes this skill or explicitly asks for extra model opinions; never use as an automatic escalation.
disable-model-invocation: true
---

# Models Consensus

For a direct invocation, use `shared/references/model-preview.md` for the selected council scope. An explicit three-seat request selects the three blind opening roles. The preview also shows every approved organizer, judge, and synthesis role with its registered seat. A lean poll shows both conditional judge routes. Do not expand it into a routing table for unrelated task kinds. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Model IDs, effort support, and task defaults come only from
`shared/model-routing.json`. Resolve the relevant route before preview or
approval; preserve the exact saved route during dispatch, retry, and resume.

Produce a decision report for a user who wants more than one model's opinion. The next consumer is the user. Done means the report names the recommendation, dissent, evidence limits, one next step, configured and observed seats, and receipt limits.

This is a user-controlled, read-only workflow. A council is justified only when the user decides that independent opinions are worth its time and cost.

## Entry and approval

Run only after the user explicitly invokes `models-consensus` or explicitly asks for extra model opinions. Another skill may suggest this workflow as a manual next step, but must not invoke it.

Before dispatching any model:

1. Choose `poll` by default, `debate` for a contested direction, or `personas` when the user wants five angles from one chosen model. A poll with no `poll_profile` is the legacy `standard` profile. Select explicit `lean` only for a low risk question.
2. Read [references/role-routing.md](references/role-routing.md), `shared/references/model-roster.md`, `shared/references/task-shaped-model-routing.md`, and `shared/references/host-model-execution.md`. Check a native host route before an external runner. If `.rar-skills/config.local.yaml` exists, read its advisory `profile` and `seats` only while forming this preview, as `shared/references/local-config.md` defines. Validate every value against the roster and selected execution path, let direct user instructions win, and never reread it after approval.
3. Show the approval preview below and ask: **"Approve this council plan, or specify changes."**
4. Wait for a clear approval. Silence, a timeout, a prior general approval, an `auto` request, or another skill's instruction is not approval.

The preview must show every planned and conditional call:

| Field | Required content |
| --- | --- |
| Question and mode | The neutral question and `poll`, `debate`, or `personas` |
| Poll profile | For a new `poll`, `standard` or `lean`, the `risk_flags`, and the immutable `poll_policy` snapshot. A legacy standard plan may omit these fields. |
| Seats | Registry entry for every approved role: seat id, requested model label, provider, receipt, and execution path. A judge only seat can be present in addition to the three opening seats. |
| Roles | Organizer, each judge, and synthesizer or chairman, with their seat, requested model label, continuity key, dependencies, and conditional state |
| Conditional judges | For a lean poll, both exact judge routes, effort, tool policy, receipt requirement, budget, and the organizer evidence condition that can require them |
| Effort | Exact configured effort or runtime-controlled effort for every model call |
| Host and session | Checked host or runner, per-role session policy, and whether the role can resume by its recorded id |
| Serving receipt | `required` or `explicitly allowed unverified`, with status, source, and observed model for every seat |
| Budget | `poll_budget` and matching approval budget: base call count, conditional calls, validation-retry ceiling, maximum calls, advisory response cap, and any reported usage or elapsed-time limits. Lean requires `poll_budget`. |
| Tools | The shared read-only tool profile. A Codex runner seat needs `repo_read_only` with `tool_evidence: configured` and `allowed_tools: []` in its execution entry, shown as "Codex: read-only isolation configured, startup tools not observable"; see [references/runner-invocations.md](references/runner-invocations.md) |
| Evidence | Which native or runner checks passed and that serving-model receipts are still pending |

Use **seat fidelity**: an approved seat is that exact requested-model label, receipt requirement, execution path, effort, and role continuity policy. Every runner call uses `--disable-fallback`; a native route has no runner fallback. If a selected seat, model label, receipt requirement, host, execution path, effort, role, or session policy changes after the preview, stop and show a revised preview. A pending receipt becoming verified for the approved model is new evidence and needs no new approval. An observed model mismatch or an unmet required receipt blocks that route; never weaken the receipt requirement to continue. Do not substitute, downgrade, add a seat, switch mode, or degrade to personas without new approval.

The explicit council approval covers every listed role, including a lean judge
that might become `conditional-not-needed`. Conditional status controls later
dispatch. It does not approve an unlisted route or a substitute.

Use this preview shape after resolving the roster:

```text
Council plan: awaiting approval
Mode: <mode>
Poll profile: <standard | lean>; risk flags: <none | configured flags>
Poll policy: <low confidence threshold and full required flags from the central snapshot>
Opening: <seat> / <requested model> / <receipt status and source> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Organizer: <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key>
Judges: <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key> / <required or material conflict or gap, low confidence, or high risk>; <seat> / <requested model> / <host and execution path> / <effort or runtime-controlled> / <continuity key> / <required or material conflict or gap, low confidence, or high risk>
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

For `poll` and `debate`, require three approved blind opening roles with distinct requested model labels. The seat registry can include an organizer or judge only seat. Three providers are not a requirement. Count opening diversity only when the three blind opening receipts verify distinct observed models. A registered conditional judge does not add opening diversity. Verified provider diversity is supporting evidence, not a seat-count rule. If preflight cannot support a route, report the blocker and offer a revised three-seat plan. `personas` is the separate single-model mode; its preview must name the model used for all advisor, reviewer, and chairman calls.

For a poll, resolve the central policy before approval. `security`, `money`, `migrations`, `public_contracts`, `data_loss`, `deep_review`, and `high_risk` select `standard`. An explicit lean request with any such risk flag fails before approval. Show a revised standard preview instead. Lean uses the native or runner `per_call` transport only. `cmux` cannot carry the organizer evidence gate, so it rejects lean before fingerprinting, adoption, or relay.

Preflight both lean judge routes even though their calls are conditional. An
unavailable route blocks the preview because the user must approve the exact
route before the organizer gate is known. If an approved judge route becomes
unavailable and the organizer requires it, retain the failure and do not bypass
the judge in synthesis.

## Execution

After approval, initialize the generic council CLI from the exact preview and reserve each attempt before dispatch, as [references/operations.md](references/operations.md) defines. Create one isolated, persistent context per task and role. Give every opening role the same neutral brief, read-only sources, tool profile, and output budget. An opening role can resume only its own context for a schema retry or approved gap repair. The organizer, each judge, synthesizer, advisor, reviewer, and chairman has a separate context. Judges begin without opening role or organizer history and do not share a context with each other.

In a standard `poll`, run blind openings, organizer analysis, at most one gap repair round, two judges, then synthesis. This preserves the existing seven base calls, three conditional gap repairs, one validation retry per planned step, and twenty call maximum.

In a lean `poll`, run three blind openings and the organizer, then three planned optional gap repairs. The organizer response has `confidence` and `high_risk` fields in addition to its normal analysis. Run both judges before synthesis when the validated organizer response has `material_gaps: true`, any material contradiction, confidence below the approved policy threshold, or `high_risk: true`. Both judges remain isolated and use their exact approved routes. The synthesis waits for both judge results even when gap repair ran.

When none of those judge triggers apply, record each lean judge as `conditional-not-needed`. That record is evidence, not an execution result or missing coverage. It must reference the validated organizer response artifact and its raw receipt digest. The runtime verifies that evidence before synthesis. A caller reason cannot skip a judge. The normal lean plan has five base calls, five conditional calls, one validation retry per planned step, and a twenty call maximum. An explicit approval may set a smaller retry ceiling and matching maximum.

In `debate`, run the approved number of rounds, with the anonymized digest and fixed ceiling. In `personas`, run five lenses, anonymized peer review when the preview includes it, then the chairman.

If an approved call or session resume fails, retain the failure and its recorded context id in the state and report it. Reconcile a pending call before sending it again. Do not use another model or an unapproved new context in its place. A material loss of quorum ends the run with the evidence collected and a clear revised-plan option.

## Output

Return or write `.ai-workflow/consensus/{session_id}.md` with:

1. Question, mode, approved preview, and actual run record.
2. Recommendation and one next step.
3. Agreements, dissent, blind spots, and evidence gaps.
4. Answer confidence and diversity confidence, separately.
5. Seat receipts: requested, configured, effective, and observed model fields; receipt status and source; provider, host, execution path, effort control, role context status, and any failure.
6. For a lean poll, the profile, policy snapshot, risk flags, trigger decision, and each `conditional-not-needed` evidence reference.

For an adoption decision, use one plain-language grade: Adopt, Trial, Hold, Reject, or Not-our-problem. If the evidence is insufficient, return "Hold: insufficient evidence" and list what to inspect.

The council never implements its recommendation. A user can later choose a separate implementation workflow.
