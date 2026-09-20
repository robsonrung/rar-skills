# Run control and evidence

Use one run directory outside any source or runtime fingerprint root. It contains immutable plan and evidence files, plus one mutable `run-state.json`. Resolve `SHARED_DIR` and `SKILL_DIR` to absolute paths before commands. The controller uses the shared POSIX lock and atomic write helper. Windows hosts need a compatible environment or an equivalent checked controller; do not silently remove locking.

The plan contains:

| Field | Contract |
| --- | --- |
| `version`, `run_id`, `mode` | Version 1, unique run ID, `assess` or `repair` |
| `approval` | `status: approved`, actual user decision `reference`; includes approved scope, routes, and budgets |
| `inputs` | Nonempty array of acceptance source `{path, sha256}`; absolute paths, current hashes |
| `scope` | `requirements`: unique IDs; `discovery_closed`: boolean; also record base, revision, operation identities, exclusions and scope meaning |
| `units` | Nonempty array: unique `id`, nonempty `requirements`, `required` boolean, nonempty unique `checks`, positive `max_attempts`; every requirement maps to a required unit |
| `routes` | Exact selected route rows from model-selection.md; empty is valid when no worker is needed |
| `call_limits` | Positive `total_role_calls` plus every route ID and its positive ceiling; no worker calls are possible with an empty routes list |
| `budgets` | Positive `total_attempts`, positive `max_parallel`, absolute UTC `deadline`; also record command timeouts and any host enforced spend or token ceiling |

Propose 12 test attempts, 12 role calls, at most 3 calls per role, 2 attempts per unit, 2 concurrent workers, and a 90 minute deadline for one bounded feature. These are editable starting values, not evidence that a larger feature can finish. Required work that exceeds them is split into explicit accepted scopes or reported incomplete. Do not reset counters through renaming a unit or starting a successor run for the same unresolved work. Carry prior consumption and remaining allowance into an explicitly approved extension.

Keep the denominator finite before runtime work. `discovery_closed: false` permits bounded preparation, but blocks an overall pass. Put human policy questions and known unavailable source in the plan as named blockers. Do not use “no unknown external writer exists” as a requirement.

Initialize after route and budget selection:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" init --plan "$RUN_DIR/validation-plan.json"
```

Before each test unit, save a small immutable input snapshot with the relevant code, test, fixture, dependency and environment identities. Check those identities against current files before reuse. Capture per file hashes, not only one aggregate digest. Reserve before any command or browser mutation:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" reserve --unit U1 --attempt U1-A1 \
  --input "$RUN_DIR/U1-input.json"
```

Only `reservation: new` permits a new execution. `existing` means inspect the recorded process, browser state, raw output or receipt and reconcile it. Do not resend an uncertain operation. Use a stable command/process handle and an external command timeout. Observation timeouts do not mean the test failed or should restart. A second attempt requires `--reason` with its changed input or new hypothesis. Failed and interrupted attempts still consume their reservation.

Finish with a result file:

```json
{
  "attempt_id": "U1-A1",
  "input_sha256": "<SHA256 of reserved input snapshot>",
  "checks": {"behavior": "passed", "runtime": "failed"},
  "reason": "One required native diagnostic remains.",
  "evidence": [{"path": "/absolute/run/U1-raw.json", "sha256": "<SHA256>"}]
}
```

Check keys must equal the planned unit check IDs. Values are `passed`, `failed`, `blocked`, or `skipped`. Every result has captured evidence; every nonpass has a reason. A blocked preflight can use its actual failure log. Historical evidence can satisfy a unit only after current identity and environment checks; record `reused_from` and that assessment in its result, without rewriting the old evidence.

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" finish --attempt U1-A1 --result "$RUN_DIR/U1-result.json"
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" summary
```

The controller prevents missing checks, evidence drift, duplicate execution reservations, unlimited attempts, and a pass with unresolved required units. It verifies hashes and accounting, not the truth of a test assertion. The coordinator must assess actual commands, expected behavior, result provenance, current source identity, route receipts, and pending blockers before accepting a check. Give those obligations explicit check IDs when required.

## Model calls

Read `shared/references/run-state-contract.md` and the selected host execution contract once. The controller initializes the shared call ledger in the same state file. Reserve each model turn through the wrapper so deadline and concurrency apply too:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" reserve-role --route unit-author \
  --call unit-author-1 --brief "$RUN_DIR/unit-brief.md" --phase unit-tests
```

Then use the approved native transport or runner. Save actual completion and receipt, verify route fidelity, and reconcile with `shared/scripts/run_state.py ... reconcile --call ... --receipt ...`. It checks call/input/model/effort/context bindings. Serving-model receipt policy remains an additional host/runner check. Keep an independent review context separate; never use a worker's completion text as that review.

The helpers enforce reservation counts and refuse new work after the deadline. They do not launch, cancel, sandbox, or meter an active provider call, and cannot prevent calls made outside the workflow. Host limits and command timeouts enforce active execution bounds. If a hard monetary or token cap is requested, require an actual provider/host mechanism; report missing capability instead of calling these counters a spend cap. An optional estimated cost warning is not a hard cap.

## Recovery and reporting

One coordinator writes state. Preserve the approved plan bytes; changed authority requires a recorded amendment and a deliberate migration that keeps consumed counters. The controller rejects edited plans. It does not silently generate a successor or migrate approval.

On resume, reconcile pending effects first, then finish or retry under the remaining allowance. A process may have completed before the checkpoint. Captured evidence establishes that fact; replay does not. The shared ledger has offline crash recovery tests. The skill's tests cover reserved tests, result confirmation, ceilings, drift and incomplete coverage using disposable files.

Map report status to shared state when checkpointing: `passed` to `complete`; `failed` to `failed`; `blocked` to `awaiting_human` only when a decision is needed, otherwise `failed` with dependency reason; `ceiling_hit` to `ceiling_hit`; active `partial` to `running`. An incomplete run is never `complete`. Keep controller summaries and final evidence references in `steps`.

Metrics include every role and failed attempt. Sum unique per response usage records once. Input already includes cached input; output already includes reasoning output. Keep cached reads, cache writes, unknown usage, reported cost, calculated estimates, and subscription limits separate. Use `shared/scripts/execution_metrics.py` for compatible receipts. Record coordinator usage where exposed; role call counts do not count each hidden model response. A feature with missing usage cannot establish a total token saving.
