# Workflow measurement report

The repository now supports a read-only comparison of recorded workflow runs.
Deterministic tests establish arithmetic, unknown handling, identity checks, and
safe refusal. No full workflow provider performance benchmark was run. There is
no measured speed, token, cost, or quality improvement claim.

Source baseline: `9a8876caf7fa6816197b6528674ea61578537e58`.
The candidate is the local workflow change set based on that revision. Record
its final commit or resource hashes before a future runtime comparison. Route
defaults were not changed by this work.

## Method

Use the existing call ledger and receipt normalization. Add the optional
measurement metadata described in the
[run-state contract](../skills/shared/references/run-state-contract.md#compare-workflow-cost).
The comparison helper reads two run states without creating another ledger,
starting workers, or changing acceptance state:

```bash
python3 skills/shared/scripts/workflow_comparison.py \
  --baseline <baseline-run-state.json> --candidate <candidate-run-state.json>
```

Before any future execution, bind the same source start revision, requirements,
independent acceptance cases, and environment identity for each pair. Cover a
bounded fix, routine feature, UI change, permission-sensitive change, and
migration or concurrency change. Use the same fixtures and defect observation
protocol. Keep baseline and candidate workflow resource revisions distinct in
execution provenance. Reserve any paid calls only under explicit approved
routes and limits.

Measure whole workflow elapsed time separately from the sum of worker durations.
Record approval wait intervals and coordinator usage directly. Count failed calls,
repairs, and repeated command executions. Include input, cached input, cache write,
output, reasoning output, and reported cost. Missing values remain unknown;
cached input remains part of input and is not priced as free. Total reported cost
requires complete worker and coordinator cost coverage.

The helper compares supplied identity hashes; it does not verify the underlying
acceptance evidence. Inspect that evidence independently. Cost deltas require
matching identities, passed acceptance in both runs, and equal observed defect
counts. Missing quality observations block deltas. A matching result remains a
bounded observation, not proof of equivalent quality or a reason to change routes.

## Local results

The synthetic arithmetic fixture records two overlapping worker calls of 8,000 ms
each within a 10,000 ms workflow. It produces a 16,000 ms worker duration sum and
10,000 ms elapsed time. Two overlapping approval waits produce 4,000 ms of waiting.
Worker input totals are 200 tokens, including 160 cached input tokens. Worker cost
is USD 0.50; a separate coordinator receipt adds USD 0.25. These are fixture values,
not provider measurements.

| Check | Result |
| --- | --- |
| `test_workflow_comparison.py` | 18 tests passed; arithmetic, missing metrics, partial coverage, all five case kinds, identity and quality mismatches, inconsistent ledger event times, malformed statuses, and read-only CLI behavior |
| `test_run_state.py` | 15 tests passed; existing ledger and normalization consumers |
| `test_stream_capture.py` | 4 tests passed; receipt capture compatibility |
| `test_council_state.py` | 39 tests passed; existing usage and budget accounting |
| `test_skill_paths.py` | 1 test passed; resource path compatibility |

The measurement tests are included in the existing workflow guards. Missing
receipts preserve partial measured sums and unknown-call counts. Pending calls,
missing coordinator usage, and incomplete ledger coverage cannot establish total
cost. Available ledger reservation and completion times must fit the workflow
interval and retain their order. Missing event times remain unknown. Malformed
status values return `invalid` without a traceback. Changed source, requirement,
check, runtime, or observation identities block
comparison. Failed acceptance and unequal defect counts block cost deltas.

## Workflow changes and limits

The [workflow guide](workflow.md) describes immutable scoped dependency-release
proof, reuse of final passing captures, compact confirmed native continuations,
the focused reviewer response contract, decision and source-index handoffs,
scoped design routing, and inherited comparison bases. Existing small-task and
combined approval paths remain available. Independent final review, fresh checks,
source identity, current evidence, and approval boundaries remain required.

These are contract and implementation changes. Static file sizes, if collected,
are bytes or words only; they cannot establish runtime savings. Runtime usage,
elapsed time, acceptance rates, and missed defects for baseline versus candidate
remain unmeasured. Installation sync, paid trials, and route changes are outside
this work.
