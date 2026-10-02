# Poll Protocol

Use this protocol only after the user approves a `poll` preview. It gathers independent answers, identifies agreement and disagreement, then produces a traced recommendation. It is read-only.

## Preconditions

- The approval record names the question, every seat, requested model, receipt requirement, role, effort, transport, tool profile, and call budget.
- A new poll preview records `poll_profile`, `risk_flags`, `poll_policy`, and
  `poll_budget`. Lean requires `poll_budget` to match its approval counts. A
  legacy standard plan can omit these fields.
- Three approved blind opening roles use distinct requested model labels. The
  seat registry can include a judge only seat.
- Every runner call uses `--disable-fallback`. Opening contexts are new and
  isolated; later turns resume only the same role context.
- The shared tool profile and output budget are identical for every opening role.

A failed or missing approved seat is an **observable failure**. Keep its record, do not replace it, and do not continue below the approved quorum.

`standard` is required for `security`, `money`, `migrations`,
`public_contracts`, `data_loss`, `deep_review`, and `high_risk`. A lean request
with one of these flags does not enter this protocol. Create a revised standard
preview before approval. Lean uses `per_call` transport. The `cmux` transport
rejects it before the approval fingerprint or terminal relay.

## Phases

1. **Blind openings.** Launch the approved opening roles in parallel. Each gets a new isolated context, the same neutral question, selected read-only context, output schema, and no peer output or moderator view.
2. **Organizer.** Send all valid openings to the approved organizer in its own context. It returns agreement, contradictions, partial coverage, unique insights, blind spots, and `material_gaps`.
3. **Gap repair.** Run once only when `material_gaps` is true. Resume each approved opening context with a neutral digest of each open point. This is repair, not a new vote; raw peer answers remain hidden.
4. **Judges.** In standard, start both approved judges. In lean, start both only when the organizer gate requires them. Judges receive the remaining open points and organizer record, rule independently, and do not receive each other's result.
5. **Synthesis.** Send the complete record to the approved synthesizer in its own context. It writes the recommendation and traces each material claim to the record.

If the judges disagree, preserve both rulings and require the synthesis to explain the confidence limit. Do not invent an extra arbitration call.

### Lean gate

Lean has three blind openings, one organizer, and one synthesis as base calls.
It records both judges and three planned optional gap repairs as conditional calls. Gap
repair needs `material_gaps: true`. Both judges are required when the validated
organizer response has any one of these facts:

1. `material_gaps: true`
2. A nonempty `contradictions` list
3. `confidence` below `poll_policy.low_confidence_threshold`
4. `high_risk: true`

The organizer depends on all openings. Each gap repair depends on the organizer
and resumes one distinct opening context. Each judge depends on the organizer
and every planned gap repair. Synthesis depends on the organizer, both judges,
and every planned gap repair. This keeps synthesis behind both judge rulings,
including after gap repair.

When gap repairs or judges are not required, run no substitute call. Before
synthesis, record every such step as `conditional-not-needed`. The recorded
decision contains the organizer step and call, a digest reference to the
validated normalized response artifact, its raw receipt reference, triggers,
and the `judges_required` and `gap_repair_required` results. The state validates
all references before synthesis. A caller supplied reason alone cannot establish
the skip.

## Schemas

Validate each response before it enters the next phase. Retry the same approved seat once with a compact schema reminder. A second invalid response is a failed seat, not a partial vote.

| Phase | Schema | Required result |
| --- | --- | --- |
| Opening | [../schemas/opening-answer.schema.json](../schemas/opening-answer.schema.json) | `answer`, `key_points`, `assumptions`, `confidence` |
| Organizer, standard | [../schemas/organizer-analysis.schema.json](../schemas/organizer-analysis.schema.json) | five-dimension analysis and `material_gaps` |
| Organizer, lean | [../schemas/organizer-analysis-lean.schema.json](../schemas/organizer-analysis-lean.schema.json) | standard analysis plus integer `confidence` from 0 through 100 and boolean `high_risk` |
| Gap repair | [../schemas/disagreement-round.schema.json](../schemas/disagreement-round.schema.json) | point responses and confidence |
| Judge | [../schemas/judge.schema.json](../schemas/judge.schema.json) | verdicts |
| Synthesis | [../schemas/synthesis.schema.json](../schemas/synthesis.schema.json) | answer, attribution, confidence rationale |

Schema reminder:

```text
Return one JSON object with exactly these top-level keys: <keys>.
Do not add markdown or text outside the object.
```

## Prompts

Opening prompt:

```text
Answer this decision independently. You cannot see other seat outputs.

QUESTION:
<neutral question>

CONTEXT:
<approved read-only paths, if any>

Return the required JSON only.
```

Gap-repair prompt names each open point and anonymized positions. It asks the seat to resolve, qualify, or reject each point with evidence. Judge prompts contain the open points, each final position, and the organizer record. The synthesizer receives the complete validated record.

## Report

The final report contains:

1. Approved plan and actual seat receipts.
2. Recommendation and one next step.
3. Agreements, conflicts, partial coverage, and blind spots.
4. Judge rulings and remaining disagreement.
5. Attribution map.
6. Answer confidence and diversity confidence, separately.
7. For lean, the policy snapshot, risk flags, judge trigger decision, and each conditional evidence record.

Use **seat fidelity** in the report: requested, configured, effective, and observed model fields, plus receipt status and source, are visible. Distinct verified observed blind opening models establish opening diversity. Verified provider diversity can strengthen that evidence, but it is not required. A conditional judge does not add opening diversity merely because it is registered. A failed, duplicate, or unverified opening role lowers diversity confidence.
