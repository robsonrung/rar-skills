# Poll Protocol

Use this protocol only after the user approves a `poll` preview. It gathers independent answers, identifies agreement and disagreement, then produces a traced recommendation. It is read-only.

## Preconditions

- The approval record names the question, every seat, requested model, receipt requirement, role, effort, transport, tool profile, and call budget.
- At least three approved opening seats have distinct serving-provider plans.
- Every runner call uses `--disable-fallback`; every context is fresh.
- The shared tool profile and output budget are identical for every opening seat.

A failed or missing approved seat is an **observable failure**. Keep its record, do not replace it, and do not continue below the approved quorum.

## Phases

1. **Blind openings.** Launch the approved opening seats in parallel. Each receives the same neutral question, selected read-only context, output schema, and no peer output or moderator view.
2. **Organizer.** Send all valid openings to the approved organizer. It returns agreement, contradictions, partial coverage, unique insights, blind spots, and `material_gaps`.
3. **Gap repair.** Run once only when `material_gaps` is true. Send each approved opening seat a neutral digest of each open point. This is repair, not a new vote.
4. **Judges.** Send the remaining open points and the organizer record to both approved judges. They rule independently.
5. **Synthesis.** Send the complete record to the approved synthesizer. It writes the recommendation and traces each material claim to the record.

If the judges disagree, preserve both rulings and require the synthesis to explain the confidence limit. Do not invent an extra arbitration call.

## Schemas

Validate each response before it enters the next phase. Retry the same approved seat once with a compact schema reminder. A second invalid response is a failed seat, not a partial vote.

| Phase | Schema | Required result |
| --- | --- | --- |
| Opening | [../schemas/opening-answer.schema.json](../schemas/opening-answer.schema.json) | `answer`, `key_points`, `assumptions`, `confidence` |
| Organizer | [../schemas/organizer-analysis.schema.json](../schemas/organizer-analysis.schema.json) | five-dimension analysis and `material_gaps` |
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

Use **seat fidelity** in the report: requested, configured, effective, and observed model fields, plus receipt status and source, are visible. Count independent corroboration only when verified provider or native receipts differ as planned. A failed, duplicate, or unverified seat lowers diversity confidence.
