# Local workflow runtime validation

On 2026-10-09, a local fixture exercised measurement capture across an automatic
interview stage and an implementation stage. It used the current working source,
the existing capture test helpers, and the actual CLI. No provider was called.
All role receipts, usage, cost, model names, and fixture approvals were synthetic.
The ledger and measurement metadata came from CLI operations, without direct
state edits.

The paired runs use `baseline` and `candidate` as comparison input names. Both
use the same current implementation. They are not a performance comparison
against the earlier source revision.

## Inputs and commands

The fixture source identity is `f1d5548c99756490c4ceeb91513f2b4e246c98da`.
`identity.json` binds that identity to hashes of the actual local requirements,
check program, and environment record. `resources.json` records hashes of the
loaded measurement scripts and fixture helper. These files and the complete
states, receipts, capture events, command outputs, and comparison remain in
`/tmp/workflow-runtime-validation-20261009/after-fix`.
Test logs and the zero repair probes remain in its parent directory.

The temporary demonstration ran with:

```bash
python3 /tmp/workflow-runtime-validation-20261009/after-fix/demonstrate.py
python3 skills/shared/scripts/workflow_comparison.py \
  --baseline /tmp/workflow-runtime-validation-20261009/after-fix/baseline/state.json \
  --candidate /tmp/workflow-runtime-validation-20261009/after-fix/candidate/state.json
```

The demonstration starts measurement with partial identity. It creates a
separate interview ledger, reserves and reconciles its three fixture calls,
records terminal status and coverage, then imports the completed ledger by hash.
It binds the remaining identity fields and initializes the implementation route
ledger in the existing feature state. Three implementation calls include a
failure, repair, and review. Actual command captures record exit codes 1 and 0
under the same command identity. The demonstration then records coordinator
coverage, terminal status, and fixture outcome observations.

The automatic interview fixture represents interviewer and respondent calls,
including a failed respondent call and its repair. It does not execute an
interview or establish real user decisions. Both ledger plans remain separate.
The feature retains three local call reservations, and the imported stage file
remains byte for byte unchanged. Measurement completion leaves execution status
`running`; it cannot certify task acceptance.

## Observed results

| Measurement | Each run |
| --- | --- |
| Captured stages | `interview-me`, `implement-tasks` |
| Calls, including the imported stage | 6 |
| Failed calls | 2 |
| Repair calls | 2 |
| Actual command executions | 2 |
| Repeated command executions | 1 |
| Checked call timing events | 12, with none missing |
| Approval waits | 0, with complete fixture coverage |
| Synthetic worker input | 600 tokens, including 420 cache reads and 120 cache writes |
| Synthetic worker output | 90 tokens |
| Synthetic worker duration | 30 ms |
| Synthetic worker plus coordinator cost | USD 0.065 |
| Unknown worker usage | Reasoning output for all 6 calls |

Invocation totals override the smaller final message usage in each fixture
receipt. Cached input remains part of total input. Comparison returns exit 1
and `incomplete` because reasoning output is unknown. Its reasoning delta is
null. The fixture outcome observations match; `quality_equivalence` remains
`not-established`.

Observed local elapsed times were 1192.626 ms and 1219.828 ms. They include local
CLI and file work. Synthetic role durations do not explain these times. These
two observations establish no latency, token, cost, or quality improvement.

A separate success fixture captures two interview calls and complete repair
coverage with no repair events. After the import fix, it reports two workers,
zero failures, and zero repairs. Reimporting the preserved original stage also
reports zero and leaves that source file unchanged. The original failing feature
state remains available; it was not rewritten to pass.

```bash
python3 /tmp/workflow-runtime-validation-20261009/zero_repair_success.py \
  /tmp/workflow-runtime-validation-20261009/zero-success-after --expect-zero
```

## Deterministic checks

The following repository checks passed:

```bash
python3 -m unittest discover -s skills/shared/tests -p 'test_workflow_capture.py' -v
python3 -m unittest discover -s skills/shared/tests -p 'test_workflow_comparison.py' -v
python3 -m unittest discover -s skills/shared/tests -p 'test_runner_prompt.py' -v
python3 -m unittest discover -s skills/shared/tests -p 'test_task_queue.py' -v
```

Capture ran 10 tests, comparison ran 18, prompt boundaries ran 3, and queue
validation ran 32. Capture
checks cover partial identity, separate ledger imports, missing and pending
stage evidence, immutable retries, concurrent writes, and unknown usage.
Comparison checks cover identity and outcome refusal rules. Prompt checks use
mocked unavailable executables and verify that dispatch records stay outside
the prompt, rendered byte counts match actual adapter text, and budget failure
prevents execution.

Four selected launcher tests also passed: complete review capture validation
before cycle reservation, full reconstruction when runner proof is missing,
selection of the smaller full input, and rejection of a changed native contract.
These checks do not execute external roles.

The existing `TaskQueueTests.batch_integration` fixture also measured calls to
`review_evidence.load_record` during one queue projection:

| Task members | Record loads | Integrated tasks |
| --- | --- | --- |
| 2 | 41 | 2 |
| 4 | 79 | 4 |
| 8 | 155 | 8 |

These counts include validation within each projection. They are not disk read,
latency, or provider measurements. They do not establish a reduction against a
baseline. Queue tests separately require current source and evidence validation
before a cached projection can return.

## Limits

The temporary artifacts are local evidence, not repository fixtures. The
[measurement reference](../skills/shared/references/workflow-measurement.md)
owns the capture API. The [workflow guide](workflow.md) owns stage integration.
Changes to either interface require a new capture run.

This proof does not establish real provider usage, role continuity at a live
host, reviewer independence, product acceptance, or missed product defects.
The synthetic outcome applies only to the fixture assertions. Final delivery
still needs the approved independent review of the current combined source and
its required acceptance evidence. Route defaults remain unchanged.
