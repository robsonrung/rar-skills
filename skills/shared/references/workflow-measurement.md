# Capture workflow measurements

Use **the ledger, not the transcript**: record observed facts in the existing run
state at their boundary. Measurement records do not grant approval, certify
acceptance, release tasks, or reset call ceilings.

```bash
python3 <shared-dir>/scripts/run_state.py --state <run-state.json> capture --event <event.json>
```

The Python API is `capture(state, event)`. Use it inside `locked(path)` when writing
a file. The CLI supplies the lock and atomic write. `--dry-run` before `capture`
validates without writing. Each event has `id`, `kind`, and the fields below.
Use a stable ID for retries. Reusing an ID with changed facts is an error.
Optional `at` is an observed ISO 8601 timestamp with timezone. If omitted, the
helper records current time once. An identical retry keeps that time.

| Kind | Required fields |
| --- | --- |
| `start`, `identity` | `identity`, containing the known fields from the [comparison contract](run-state-contract.md#compare-workflow-cost) |
| `stage-start`, `stage-end` | `stage`, the stable stage instance name |
| `wait-start`, `wait-end` | `wait`, the stable approval wait instance name |
| `command` | `key`, `evidence`, `started_at`, integer `exit_code`; `at` is command completion |
| `repair` | `call_id`, an existing reserved call |
| `stage-ledger` | `stage` and `ledger`, an intact completed stage run-state reference |
| `coordinator` | `receipt`, an intact receipt reference |
| `terminal` | `status`: `complete`, `failed`, `ceiling_hit`, or `cancelled` |
| `coverage` | `areas`, a list drawn from `workers`, `coordinator`, `commands`, `waits`, `repairs` |
| `outcome` | `acceptance: {passed, evidence}` and `missed_defects: {count, evidence, observation_window}` |

An evidence or receipt reference is `{"path": "<file>", "sha256": "<digest>"}`.
The helper checks its current hash. Keep source evidence available for independent
review. Use the same command key scheme in both runs, including command arguments,
working directory, and relevant environment. Each actual execution gets one event
ID. A rerun gets a new ID and the same key. Reusing captured evidence does not
execute a command and adds no command event.

Capture `start` before the first stage, even before a route plan exists. Include
only known identity fields; `{}` is valid and omitted fields remain unknown. Use
`identity` events to bind requirements, checks, and environment hashes when those
facts become fixed. Existing fields cannot change. Comparison needs all six fields. For an
existing run, provide its actual earlier start timestamp; do not substitute the
capture time. Initialization records when the ledger begins. Reservation and
reconciliation record call boundaries and normalized usage automatically.
The route plan and call ceilings remain required before reservation.

The feature stage callers record their own `stage-start` and `stage-end` events
with names `interview-me`, `to-prd`, `to-tasks`, and `implement-tasks`. Record
`validate-e2e` when that execution branch is selected. Give repeated stage
instances distinct names. Record actual approval waits at request and response.
Do not infer waits from gaps between calls. Select the feature measurement state
once before the first stage and pass its exact path through stage handoffs. Use the
feature implementation run-state location, created early by `capture start`; later
`init` adds its approved implementation route ledger. Stage callers write measurement
events there. Each stage keeps its own route ledger and approved plan unchanged.

For a separate automatic interview or other stage ledger, finish and reconcile its
calls, preserve its completed snapshot, then capture:

```json
{"id": "interview-ledger", "kind": "stage-ledger", "stage": "interview-me", "ledger": {"path": "<completed-stage-state.json>", "sha256": "<digest>"}}
```

Import before feature `terminal`. The source stage must have terminal status
recorded by its owner. Every source call must be resolved and every
receipt hash must match. Import stores a bound snapshot of call measurements; it
does not rebind the source plan or counters. A stage name binds once. Comparison
qualifies imported call IDs by stage and counts each receipt hash once across local
and imported calls. Imported repairs use their stage ledger's explicit repair IDs.
Complete repair coverage with no repair IDs means observed zero. Without that
coverage, absent repair IDs remain unknown. Do not import the feature's own local
ledger. Declare worker coverage only when the local ledger and all required stage
imports cover every call. Missing stage data leaves worker coverage unknown.

After all observed stages and waits close and pending calls reconcile, capture
`terminal`. This stores measurement terminal status and time without changing the
execution owner's status or acceptance. New reservations are blocked after this
measurement boundary; existing reservations can still be read and reconciled.
Record `coverage` after terminal only for areas captured in full. An empty area
means observed none only when that area has complete coverage. Missing coverage
remains unknown. Record coordinator coverage only when actual receipts cover the
whole run; unknown native usage remains unknown. Record independent outcome
observations separately, with intact evidence. Later coverage and outcome events
can complete capture, but cannot replace prior facts or reopen the workflow.

Example stage boundary:

```json
{"id": "prd-start", "kind": "stage-start", "stage": "to-prd"}
```

For receipt usage, the invocation aggregate takes precedence over the final
message subtotal. An aggregate field stays unknown if any counted request lacks
a valid value for that field. Cache reads and writes remain part of total input. Each resumed
invocation has a separate call reservation and receipt. Failed calls retain
reported usage. Absent reasoning, duration, or cost remains unknown; no prices or
native token counts are inferred.
