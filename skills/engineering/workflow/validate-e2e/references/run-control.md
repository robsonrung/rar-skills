# Run control and evidence

Keep one run directory outside every source, build, and dependency scan root. It holds the immutable plan and evidence files and one mutable `run-state.json`. Set `SKILL_DIR`, `SHARED_DIR`, and `RUN_DIR` to absolute paths. The controller rejects an edited plan, a duplicate reservation, a missing check, evidence drift, and a pass with an unresolved required unit; it never dispatches work.

## Plan

`validation-plan.json` fields:

| Field | Contract |
| --- | --- |
| `version`, `run_id`, `mode` | `1`, a unique ID, `assess` or `repair` |
| `approval` | `status: approved` and the actual user decision `reference` |
| `inputs` | Acceptance sources as absolute `{path, sha256}` |
| `review_snapshot` | The initial shared `snapshot.json` as absolute `{path, sha256}` |
| `working_dir` | Absolute project path; required for a browser unit or browser worker |
| `scope` | Unique `requirements`, `discovery_closed`, plus base, operations, exclusions, and what coverage means |
| `units` | Unique `id`, `requirements`, `required`, `checks` (shared check or observation IDs), `max_attempts`; optional `recovery_attempts` for `test_repair`, `evidence_repair`, `product_repair` (repair mode only). Browser units add `browser_mechanism` and `preflight_required: true`. |
| `routes` | Approved route rows; empty when no worker runs |
| `call_limits` | `total_role_calls` and a ceiling per route ID |
| `budgets` | `total_attempts`, `max_parallel`, UTC `deadline`; optional `max_preflights` |

Required units together cover every check and observation the snapshot declares, and every requirement maps to a required unit. `discovery_closed: false` allows preparation but blocks an overall pass. Propose 12 attempts, 12 role calls, 3 per role, 2 per unit, 2 workers, and a 90-minute deadline as editable starting values. Recovery allowances sit inside those totals.

The counters enforce reservations and refuse new work after the deadline. They do not meter or stop a running call, so they are not a spend cap.

## Commands

```bash
C="python3 $SKILL_DIR/scripts/validation_control.py --shared-dir $SHARED_DIR --state $RUN_DIR/run-state.json"
$C init --plan "$RUN_DIR/validation-plan.json"
$C preflight --unit U1 --id P1 --input "$SNAPSHOT" --result "$RUN_DIR/P1.json"
$C reserve --unit U1 --attempt U1-A1 --input "$SNAPSHOT" [--kind test_repair --reason "<changed input>"]
$C reserve-role --route unit-author --call unit-author-1 --brief "$RUN_DIR/unit-brief.md" --phase unit-tests
$C finish --attempt U1-A1 --result "$RUN_DIR/U1-result.json"
$C summary
$C evidence-packet --output "$RUN_DIR/validation-evidence-packet.json"
```

`SNAPSHOT` is the initial snapshot, or after a source or environment change a current one with the same root, base, contract, and requirements. Only `reservation: new` permits execution; `existing` means reconcile what already ran, never resend it. A second attempt needs `--reason`. Failed and interrupted attempts still count.

A preflight result is `{status: ready|blocked, reason, evidence: [{path, sha256}]}` with matching `mechanism` and `working_dir`; for `playwright-cli` and `agent-browser` capture it with `shared/scripts/browser_preflight.py`. A blocked preflight prevents reservation and consumes no business attempt.

Build each unit's scoped packet, then finish the unit with a result whose `checks` keys equal its planned IDs:

```bash
python3 "$SHARED_DIR/scripts/review_evidence.py" prepare-packet --snapshot "$SNAPSHOT" \
  --observations "$RUN_DIR/U1-observations.json" --id behavior --id runtime \
  --output "$RUN_DIR/U1-evidence-packet.json"
```

```json
{"attempt_id": "U1-A1", "input_sha256": "<reserved snapshot sha256>",
 "checks": {"behavior": "passed", "runtime": "failed"},
 "reason": "One required native diagnostic remains.",
 "evidence_packet": {"path": "/abs/U1-evidence-packet.json", "sha256": "<sha256>"}}
```

Statuses are `passed`, `failed`, `blocked`, or `skipped`; every nonpass has a reason and browser units repeat their `browser_mechanism`. The controller compares each status with the packet's captured result. A browser observation is `{id, result, evidence: [{path, sha256}]}`.

For a worker, reserve each turn with `reserve-role`, then reconcile its receipt with `python3 "$SHARED_DIR/scripts/run_state.py" --state "$RUN_DIR/run-state.json" reconcile --call <id> --receipt <path>`. A route with `provider_routing` also needs a matching provider policy receipt.

When checkpointing to shared run state, map `passed` to `complete`, `failed` to `failed`, `blocked` to `awaiting_human` when a decision is needed (otherwise `failed`), `ceiling_hit` to `ceiling_hit`, and an active `partial` to `running`.
