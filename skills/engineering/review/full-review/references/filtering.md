# Filtering findings

Filter for **precision over volume**: a wrong finding costs more than a missed nit.

1. **Evidence.** Keep a finding only with a path, a line range, and concrete code or document evidence. An unclear concern with a clear location may stay as a LOW question.
2. **Merge.** Exact duplicates (same path, range, category, problem, severity) merge their evidence and keep the highest confidence. Distinct problems and conflicting severities stay separate. Agreement between seats never raises severity or confidence.
3. **Threshold.** Drop findings below confidence `0.75` unless the user set another value (`0.60`–`0.90`); state a changed value in the report. Severity measures impact, confidence measures proof: a serious unproven claim is not a blocker.
4. **Scope.** Drop cosmetic preference, broad refactor wishes, and pre-existing issues outside the **scope contract**.
5. **Record and summary.** The durable record keeps every surviving finding. The human summary shows every CRITICAL, HIGH, and security finding and up to five other MEDIUM or LOW, and names the IDs it omits. A display cap never closes or hides a confirmed MEDIUM.

`scripts/findings_mechanics.py` does steps 2, 3, and 5 deterministically. Feed it seat returns as a JSON array of `{"source", "comments"}` on stdin, or `--dir` with one JSON file per seat; `--threshold` and `--max-non-blockers` change the defaults. It keeps supplied IDs across rechecks, derives stable IDs for new findings, and keeps explicit `unverified` and `refuted` findings in `suppressed_findings`. Exit code 2 means one ID was bound to two different findings: fix the source IDs and rerun.
