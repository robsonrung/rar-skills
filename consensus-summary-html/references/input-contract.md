# Consensus input contract

Read this reference when a result contains both a Markdown report and a JSON state file, or when the result is incomplete.

## Source precedence

Use sources in this order:

1. The final report for the question, verdict, agreement points, divergence summary, recommendation, next step, and confidence rationale.
2. The state file for status, mode, artifact mode, session id, round count, seat table, independence accounting, and recorded confidence values.
3. Round digests for a missing divergence, resolution, or convergence detail.
4. Seat outputs only for a missing point that is required by the page. Keep the source seat label beside the claim.

Do not derive a new verdict from seat votes. The page presents the council result; it does not deliberate again.

## Stable state fields

The state may contain these fields. Missing fields are evidence gaps, not permission to guess:

| Field | Page use |
|---|---|
| `session_id` | Session badge and source label |
| `question` | Page heading when the report heading is not clearer |
| `status` | Status badge and partial result treatment |
| `mode` | Mode badge: `poll`, `debate`, or `personas` |
| `artifact_mode` | Note whether the result was persisted or returned inline |
| `selected_seats` | Selection count and seat coverage |
| `omitted_seats` | Omission notes and diversity caveats |
| `preflight.seat_table` | Seat table, execution path, effective provider, effective model, and blocked reason |
| `preflight.independence_accounting` | Independent providers and shared transport or provider caveats |
| `rounds` | Round timeline, stances, outputs, and convergence |
| `recommendation_log` | Final recommendation, amendments, next step, and confidence band |
| `report_path` | Primary source link or label |

## Report sections

The persisted report normally contains these ideas even when headings differ:

* question and status;
* preflight or run configuration;
* seats and judges;
* consensus answer or recommendation;
* agreements;
* disagreement resolutions;
* blind spots and partial coverage;
* attribution or evidence map;
* confidence;
* open caveats.

Map the ideas, not only exact heading text. Keep the report's wording when it is a precise claim, and shorten repeated prose for the visual page.

## Incomplete results

Use a visible status such as `Awaiting human input`, `Ceiling hit`, `Failed`, or `Cancelled`. Keep the recommendation in a separate “provisional” note if one exists. Put the missing prerequisite in `limits` and in the evidence panel. Never label the page “complete” from a non-complete state.

If there is no seat table, add one row with `Not reported` in the seat table and explain the gap near it. If there is no confidence value, show `Not reported` for both answer and diversity confidence and explain that the source did not record them.

## Attribution and safety

Use only effective provider and model values recorded in the state. Label shared provider or shared transport caveats. Do not copy secrets, tokens, private prompts, or full raw outputs into the page. Link or label source files without exposing sensitive values.
