# Filter review findings

Use this after the selected routes return findings. It filters evidence; it does not select routes, raise severity because several reviewers agree, or authorize a fix.

## Defaults

Use a confidence threshold of `0.75`. Retain every confirmed finding at or above it in the durable record, including every `MEDIUM` finding. Limit only the human summary to five non-security `MEDIUM` or `LOW` entries. Keep all `CRITICAL`, `HIGH`, and security findings in that summary.

An explicit request may set a threshold from `0.60` to `0.90` or a different nonblocking cap. State either change in the report. Scope alone never changes a default.

## Steps

1. Normalize the path, line range, category, severity, and confidence. Drop malformed findings from the candidate list, but report their count and missing coverage. A malformed route return is not a completed review. The helper's processing status does not establish review completion.
2. Require a path, line range, and concrete code or document evidence. Drop a claim without them. Convert an unclear concern into a low severity question only when its location and evidence are clear.
3. Merge exact duplicates with the same path, range, category, problem, and severity. Combine their evidence and source labels, keeping the highest original confidence. Keep distinct problems and conflicting severity assessments separate for evidence review. Agreement never increases severity or adds confidence.
4. Apply the active confidence threshold to every finding. Severity describes impact; confidence describes proof. A serious but unproven claim is not a blocker.
5. Keep all surviving findings in the machine record. For the human summary, apply the presentation cap to eligible non-security `MEDIUM` and `LOW` entries, ordered by confidence. Link the complete record and name omitted IDs and count. A display limit cannot close, lower, or hide a confirmed P2 from the final gate.
6. Write each retained finding with consequence, smallest useful fix, and verification. Suppress cosmetic preference, general refactor wishes, and pre-existing issues outside the scope contract.

Run `scripts/findings_mechanics.py` when route results are available as JSON. Its defaults are the defaults above. It validates, normalizes, deduplicates, and filters durable findings independently of the summary cap. `findings` is the complete eligible record; `summary_findings` is presentation only. `summary_omitted_ids` and `summary_omitted_count` identify entries absent from the summary. The compatibility field `suppressed_by_cap` is always zero. It never changes a route, severity, or fix authority.

An independent challenge runs only when the approved plan selects it. Its result adds evidence to the report but does not produce an automatic confidence or severity boost.

Preserve supplied IDs across rechecks. For initial entries without IDs, the helper derives stable IDs from the normalized finding identity. Exact duplicates retain alternate IDs in `related_ids`. An ID or alias bound to distinct normalized findings fails the whole filter with exit code 2 before confidence filtering or summary selection. Correct the conflicting source IDs with an explicit mapping, then rerun; the helper never reassigns their meaning. Explicit `unverified` and `refuted` statuses remain in `suppressed_findings` with their IDs and evidence, even at high confidence. They cannot become confirmed through deduplication. Legacy results without status retain the existing confidence behavior; the reviewer still owns evidence verification.
