# Run control and evidence

Use one run directory outside any source or runtime fingerprint root. It contains
immutable plan and evidence files, plus one mutable `run-state.json`. Resolve
`SHARED_DIR` and `SKILL_DIR` to absolute paths before commands. The controller
uses the shared POSIX lock and atomic write helper. Windows hosts need a compatible
environment or an equivalent checked controller; do not silently remove locking.

The plan contains:

| Field | Contract |
| --- | --- |
| `version`, `run_id`, `mode` | Version 1, unique run ID, `assess` or `repair` |
| `approval` | `status: approved`, actual user decision `reference`; includes approved scope, routes, and budgets |
| `inputs` | Nonempty array of acceptance source `{path, sha256}`; absolute paths, current hashes |
| `review_snapshot` | Required for a new plan: the initial shared `snapshot.json` as exact absolute `{path, sha256}` |
| `working_dir` | Absolute project path, required when a unit declares `browser_mechanism` or a worker has a browser route |
| `scope` | `requirements`: unique IDs; `discovery_closed`: boolean; also record base, revision, operation identities, exclusions and scope meaning |
| `units` | Nonempty array: unique `id`, nonempty `requirements`, `required` boolean, nonempty unique `checks`, positive `max_attempts`; each check is a declared shared check or observation ID. Required units together cover the complete shared check and observation scope. Every requirement maps to a required unit. Browser units declare `browser_mechanism` and `preflight_required: true`. |
| `routes` | Exact selected route rows from model-selection.md, including required provider controls. Empty is valid when no worker is needed. External CLI browser workers bind `browser: {mechanism, preflight: {path, sha256}}`. |
| `call_limits` | Positive `total_role_calls` plus every route ID and its positive ceiling; no worker calls are possible with an empty routes list |
| `budgets` | Positive `total_attempts`, positive `max_parallel`, absolute UTC `deadline`; also record command timeouts and any host enforced spend or token ceiling |

The initial snapshot must still validate when the plan initializes. Its
requirements context identifies runtime, dependencies, and external state or
services. It binds the source root, intended base, acceptance contract, required
checks, and browser observations. Each reservation records the current source,
dependency, environment, and requirement identity. A legacy plan without this
binding remains context only and cannot produce an overall passed validation result.

Propose a total of 12 test and repair attempts, 12 role calls, at most 3 calls per role, 2 validation attempts per unit, 2 concurrent workers, and a 90 minute deadline. Allocate recovery categories inside those totals before approval. These are editable starting values, not evidence that a larger feature can finish. Required work that exceeds them is split into explicit accepted scopes or reported incomplete. Do not reset counters through renaming a unit or starting a successor run for the same unresolved work. Carry prior consumption and remaining allowance into an explicitly approved extension.

Keep the denominator finite before runtime work. `discovery_closed: false` permits bounded preparation, but blocks an overall pass. Put human policy questions and known unavailable source in the plan as named blockers. Do not use “no unknown external writer exists” as a requirement.

Initialize after route and budget selection:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" init --plan "$RUN_DIR/validation-plan.json"
```

For a new plan, reserve the initial shared snapshot before any command or browser
mutation. For a repair after source or environment change, reserve a current shared
snapshot that has the same source root, resolved base, acceptance contract, and
requirement fields as the initial snapshot. Its context may change. Do not mutate
the approved plan or counters for this replacement. The reserved snapshot captures
source, requirement, dependency, and environment identity. Reserve it as the
controller input. Set `SNAPSHOT` to that absolute current snapshot path:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" reserve --unit U1 --attempt U1-A1 \
  --input "$SNAPSHOT"
```

Only `reservation: new` permits a new execution. `existing` means inspect the
recorded process, browser state, raw output, or receipt and reconcile it. Do not
resend an uncertain operation. Use a stable command or process handle and an
external command timeout. Observation timeouts do not mean the test failed or
should restart. A second attempt requires `--reason` with a changed input or new
hypothesis. Failed and interrupted attempts still consume their reservation.

Finish with a result file:

```json
{
  "attempt_id": "U1-A1",
  "input_sha256": "<SHA256 of the reserved current shared snapshot>",
  "checks": {"behavior": "passed", "runtime": "failed"},
  "reason": "One required native diagnostic remains.",
  "evidence_packet": {
    "path": "/absolute/run/evidence-packet.json",
    "sha256": "<SHA256>"
  }
}
```

Check keys must equal the planned unit check and observation IDs. Values are
`passed`, `failed`, `blocked`, or `skipped`. A unit can finish with a scoped shared
packet that covers its planned IDs exactly. The controller compares every declared
status to the packet's actual command result or browser observation. A full packet
can also satisfy a unit when it already covers that unit's IDs. Every nonpass has a
reason. A browser unit result includes `browser_mechanism` with exactly the value
selected in its plan. A blocked preflight can use its actual failure log.

Use `review_evidence.py run-check` for direct commands. It writes the real
stdout, stderr, exit status, timeout result, command definition, and source
identity. Record browser work with this exact shared observation shape:

```json
{
  "id": "checkout",
  "result": "pass",
  "evidence": [
    {"path": "/absolute/run/checkout.png", "sha256": "<SHA256>"}
  ]
}
```

Create one scoped packet for each unit through the shared evidence helper, then
include its returned link in that unit result. Pass every check and observation ID
owned by the unit with repeated `--id` options. For example:

```bash
python3 "$SHARED_DIR/scripts/review_evidence.py" prepare-packet \
  --snapshot "$SNAPSHOT" --observations "$RUN_DIR/U1-observations.json" \
  --id behavior --id runtime --output "$RUN_DIR/U1-evidence-packet.json"
```

The scoped packet rejects an ID outside the frozen requirements and an omitted or
altered capture in its scope. After every required unit passes from the same current
compatible snapshot, the controller's `evidence-packet --output <path>` command
merges their scoped packets into one complete checked packet for shared review and
pre PR stages. The final packet preserves raw output, command provenance, source,
dependency, environment, and requirement identity, runtime gates, and browser
observations. It does not replace independent reviewer judgment.

The bridge and readiness decision reject an unbound, stale, mismatched, failed,
skipped, incomplete, or altered record. A prose pass never executes a command.
Historical generic results remain context only. They cannot be upgraded into shared
evidence or establish readiness after the fact.

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" finish --attempt U1-A1 --result "$RUN_DIR/U1-result.json"
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" summary
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" evidence-packet \
  --output "$RUN_DIR/validation-evidence-packet.json"
```

The controller prevents missing checks, evidence drift, duplicate execution
reservations, unlimited attempts, and a pass with unresolved required units. It
verifies captured check and observation facts plus hashes and accounting; it does
not replace the independent review of their meaning. The coordinator assesses
actual commands, expected behavior, result provenance, current source identity,
route receipts, and pending blockers before accepting a check. Give those
obligations explicit check IDs when required.

## Model calls

Read `shared/references/run-state-contract.md` and the selected host execution
contract once when a worker is needed. Command only validation has no model
preview or worker reservation. The controller initializes the shared call ledger
in the same state file. Bind the worker brief to the exact approved route snapshot
and reserved current review snapshot, then reserve each model turn through the wrapper so
deadline and concurrency apply too:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" reserve-role --route unit-author \
  --call unit-author-1 --brief "$RUN_DIR/unit-brief.md" --phase unit-tests
```

Then use the approved native transport or runner. Save actual completion and receipt, verify route fidelity, and reconcile with `shared/scripts/run_state.py ... reconcile --call ... --receipt ...`. It checks call/input/model/effort/context bindings. For a route with `provider_routing`, a successful call also needs an enforced provider policy receipt whose gateway, digest, and request count match the selected policy. A missing or mismatched receipt blocks reconciliation. This is adapter enforcement evidence, not independent proof of the inference provider. Serving-model receipt policy remains an additional host/runner check. Keep an independent review context separate; never use a worker's completion text as that review.

The helpers enforce reservation counts and refuse new work after the deadline. They do not launch, cancel, sandbox, or meter an active provider call, and cannot prevent calls made outside the workflow. Host limits and command timeouts enforce active execution bounds. If a hard monetary or token cap is requested, require an actual provider/host mechanism; report missing capability instead of calling these counters a spend cap. An optional estimated cost warning is not a hard cap.

## Recovery and reporting

One coordinator writes state. Preserve the approved plan bytes; changed authority requires a recorded amendment and a deliberate migration that keeps consumed counters. The controller rejects edited plans. It does not silently generate a successor or migrate approval.

On resume, reconcile pending effects first, then finish or retry under the remaining allowance. A process may have completed before the checkpoint. Captured evidence establishes that fact; replay does not. The shared ledger has offline crash recovery tests. The skill's tests cover reserved tests, result confirmation, ceilings, drift and incomplete coverage using disposable files.

Map report status to shared state when checkpointing: `passed` to `complete`; `failed` to `failed`; `blocked` to `awaiting_human` only when a decision is needed, otherwise `failed` with dependency reason; `ceiling_hit` to `ceiling_hit`; active `partial` to `running`. An incomplete run is never `complete`. Keep controller summaries and final evidence references in `steps`.

Metrics include every role and failed attempt. Sum unique per response usage records once. Input already includes cached input; output already includes reasoning output. Keep cached reads, cache writes, unknown usage, reported cost, calculated estimates, and subscription limits separate. Use `shared/scripts/execution_metrics.py` for compatible receipts. Record coordinator usage where exposed; role call counts do not count each hidden model response. A feature with missing usage cannot establish a total token saving.

## Recovery categories and preflight

A unit can declare `recovery_attempts`, a map with positive counts for `test_repair`,
`evidence_repair`, and `product_repair`. Product repair requires `mode: repair`.
Use `reserve --kind <category> --reason <changed input or new evidence>` for those attempts.
Each recovery result still accounts for every planned check with captured outcomes; a repair alone
does not prove that validation passed. Category allowances are part of the approved plan. They do not increase `total_attempts`,
role call limits, or the deadline. Missing categories grant no allowance. Legacy plans retain their limits.

For a browser or service dependent unit, set `preflight_required: true`. Capture a JSON result
with `status: ready|blocked`, a `reason`, and actual evidence `{path, sha256}` entries.

A browser unit selects one `browser_mechanism`: `playwright-test`,
`playwright-cli`, `agent-browser`, `playwright-mcp`, or `native`. Its plan needs
an absolute `working_dir`; its preflight records matching `mechanism` and
`working_dir`. Its final result records the same `browser_mechanism`. A missing
or changed mechanism or workspace blocks the affected step.

For `playwright-cli` and `agent-browser`, record the observed capabilities and
captured artifacts through `shared/scripts/browser_preflight.py` as
`browser-smoke` describes. Readiness also binds driver identity. A version check
alone is insufficient. A CLI worker's immutable `browser` route binds that
preflight file and hash; the controller checks it before reserving worker dispatch.
Other mechanisms retain their actual driver evidence under the same unit and
workspace checks. Existing suites run directly without a model worker.

Record the unit preflight with:

```bash
python3 "$SKILL_DIR/scripts/validation_control.py" --shared-dir "$SHARED_DIR" \
  --state "$RUN_DIR/run-state.json" preflight --unit U1 --id P1 \
  --input "$SNAPSHOT" --result "$RUN_DIR/P1.json"
```

A blocked or changed preflight prevents reservation. The result does not claim that a business test ran.
`budgets.max_preflights` bounds these records; its default is `total_attempts`. Reusing the same ID
and evidence is idempotent. All model calls still consume their recorded call limits.
After an environment change, capture a new preflight within the allowance. Ask only for an unresolved
human action, changed authority, or exhausted approved limits.
