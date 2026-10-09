# Workflow measurement report

Operational measurement now uses the existing run ledger. Capture records early
workflow start, immutable identity facts, named stages, approval waits, commands
and evidence, repairs, coordinator receipts, coverage, and terminal observations.
Deterministic tests check these records through the actual capture and comparison
CLI. No provider benchmark was run. There is no measured workflow speed, token,
cost, or quality improvement claim.

Source baseline: `f1d5548c99756490c4ceeb91513f2b4e246c98da`.
The candidate is the local change set based on that revision. Route defaults are
unchanged. The local pair below exercises the same candidate helper twice; it does
not compare execution of the baseline and candidate workflow implementations.

## Method

Use [the capture hook](../skills/shared/references/workflow-measurement.md) and the
[comparison contract](../skills/shared/references/run-state-contract.md#compare-workflow-cost).
Capture `start` before the first stage with known identity fields. Add facts through
`identity` events when requirements, checks, and environment become fixed. A bound
field cannot change. Missing identity blocks comparison deltas. Route approval
and ledger initialization can occur later without losing early stage or wait times.

Initialization records its ledger boundary. Reservation and reconciliation capture
call boundaries and receipt usage. Explicit events fill externally observed facts.
Writes use the existing file lock and atomic replacement. An identical event retry
keeps its original timestamp. Changed facts under the same ID, invalid timestamps,
bad evidence hashes, malformed fields, and attempts to reopen a terminal measurement
are rejected. Measurement leaves acceptance authority and call counters intact.

The receipt normalizer uses the invocation total when available. It does not add
the final response subtotal again. Cache reads and writes are part of input.
Failed and resumed invocations retain separate call records. Missing reasoning,
duration, cost, and native usage remain unknown. The producer reports an aggregate
field only when every counted request has a valid value for that field. Tests pass
actual producer totals through receipt reconciliation and comparison, including
missing cost, missing token fields, absent usage, and invalid numeric values.
No prices are inferred.

After terminal observation, attest complete coverage only for areas actually
captured. Partial capture is not evidence of zero activity. Coordinator receipts
must be distinct from worker receipts. Record independent acceptance and defect
observations with file hashes. Comparison checks recorded identities and outcomes;
it cannot certify the quality of their evidence or release work.

```bash
python3 skills/shared/scripts/workflow_comparison.py \
  --baseline <baseline-run-state.json> --candidate <candidate-run-state.json>
```

## Local fixture results

Run the repeatable local fixture through the real CLI:

```bash
python3 skills/shared/tests/test_workflow_capture.py \
  --fixture-dir /tmp/workflow-measurement-20261009
```

Use a fresh directory for another run. It writes both run states, captured command
output, synthetic receipts and outcome evidence, and `comparison.json`. The pair
uses actual local timestamps. Worker usage, reported cost, worker duration, and
outcomes are synthetic test inputs. No provider requests occur.

Observed on 2026-10-09:

| Measurement | Baseline fixture | Candidate fixture |
| --- | ---: | ---: |
| Whole workflow elapsed, ms | 1085.458 | 1076.649 |
| Approval wait union, ms | 128.603 | 124.508 |
| Worker calls | 3 | 3 |
| Failed calls | 1 | 1 |
| Repair calls | 1 | 1 |
| Command executions | 2 | 2 |
| Repeated command executions | 1 | 1 |
| Synthetic input tokens, including cache | 300 | 300 |
| Synthetic worker plus coordinator reported cost, USD | 0.035 | 0.035 |
| Reasoning tokens | Unknown | Unknown |

Each run captures four stages and overlapping worker calls and approval waits.
The repeated command is a real second execution. An idempotent command event retry
adds no execution; evidence reuse adds no event. The comparison reports matching
identity and outcome observations with status `incomplete`, because the producer
does not report separate reasoning tokens. Its reasoning delta is null. Its quality
equivalence remains `not-established`. The elapsed difference reflects this local
fixture run and supports no workflow performance claim.

| Check | Result |
| --- | --- |
| `test_workflow_capture.py` | 10 tests passed: actual CLI pair, separate stage authority and receipt deduplication, missing stage data, explicit zero repair coverage, early partial identity binding, conflicts, authority preservation, unknown coverage, evidence checks, concurrent writes, receipt normalization and actual producer partial-request coverage |
| `test_workflow_comparison.py` | 18 tests passed: arithmetic, unknowns, identity and outcome mismatches, timing, read-only behavior |
| `test_run_state.py` | 15 tests passed: existing ledger, call budgets, contexts, receipt and normalization consumers |

The capture tests are registered in the existing workflow guards. They test
observable behavior, including failure and repair, and do not compare instruction
wording. Identity mismatch blocks deltas. Missing usage remains visible through
unknown-call counts.

## Limits

A runtime performance claim still needs bounded, repeated comparisons across a
bounded fix, routine feature, UI change, permission change, and migration or
concurrency change. Bind equal source, requirements, independent checks, runtime
facts, and defect observation protocol. Record different workflow resource
revisions in execution provenance. Obtain approval for paid routes and bounds
only when existing authorization does not cover the proposed experiment.

Whole workflow elapsed time differs from summed worker duration. Overlapping
approval waits count once. Repeated commands can be required after repair.
Missing coordinator usage prevents total cost. A zero defect observation means
none found under the recorded protocol. It does not prove that no defects exist.
Independent final review and every required fresh check remain necessary.
