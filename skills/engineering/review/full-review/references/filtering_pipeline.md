# Filter review findings

Use this after the selected routes return findings. It filters evidence; it does not select routes, raise severity because several reviewers agree, or authorize a fix.

## Defaults

Use a confidence threshold of `0.75`. Keep all findings at or above it. Keep at most five `MEDIUM` or `LOW` findings after the threshold. Do not cap `CRITICAL` or `HIGH` findings.

An explicit request may set a threshold from `0.60` to `0.90` or a different nonblocking cap. State either change in the report. Scope alone never changes a default.

## Steps

1. Normalize the path, line range, category, severity, and confidence. Drop malformed findings from the candidate list, but report their count and missing coverage. A malformed route return is not a completed review. The helper's processing status does not establish review completion.
2. Require a path, line range, and concrete code or document evidence. Drop a claim without them. Convert an unclear concern into a low severity question only when its location and evidence are clear.
3. Merge exact duplicates with the same path, range, category, problem, and severity. Combine their evidence and source labels, keeping the highest original confidence. Keep distinct problems and conflicting severity assessments separate for evidence review. Agreement never increases severity or adds confidence.
4. Apply the active confidence threshold to every finding. Severity describes impact; confidence describes proof. A serious but unproven claim is not a blocker.
5. Keep every surviving `CRITICAL` and `HIGH` finding. Sort the remaining findings by confidence and include only the active nonblocking cap. State how many nonblocking findings were suppressed.
6. Write each retained finding with consequence, smallest useful fix, and verification. Suppress cosmetic preference, general refactor wishes, and pre-existing issues outside the scope contract.

Run `scripts/findings_mechanics.py` when route results are available as JSON. Its defaults are the defaults above. It validates, normalizes, deduplicates, filters, and applies the nonblocking cap. It never changes a route, severity, or fix authority.

An independent challenge runs only when the approved plan selects it. Its result adds evidence to the report but does not produce an automatic confidence or severity boost.
