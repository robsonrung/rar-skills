# Workflow controller

Use `shared/scripts/workflow_controller.py` when a host adapter can save worker observations and actual receipt files. It consumes a local append-only JSONL file, checks receipts through `run_state.reconcile`, and calls `task_queue.schedule` for readiness and integration evidence. It returns proposed host actions. The host executes approved dispatches and sidebar changes through its supported tools.

The controller performs local deterministic work. It makes no provider requests, starts no workers, and executes no command from event data. It does not edit task contracts, queues, routing plans, or active project plans. Its only writes are the selected ledger and controller checkpoint during `apply`.

## Use

All paths are relative to `--root` unless absolute. Select a new checkpoint path separate from the ledger, queue, routing plan, event file, and other workflow inputs.

```sh
python3 "$SHARED_DIR/scripts/workflow_controller.py" preview \
  --root "$PROJECT_ROOT" --queue queue.json --routing-plan routing-plan.json \
  --ledger run-state.json --checkpoint controller.json --events events.jsonl
```

Use the same arguments with `apply` to reconcile receipts and save cursors and the action outbox. `preview` validates changes on copies and leaves all files unchanged. A new preview proposal has `persisted: false`; apply must save it before the host acts. An unchanged preview and apply use the same occurrence IDs. Preview withholds ready actions when its receipt changes still need apply. Apply first saves reconciled receipts, then schedules from the actual ledger. Queue acceptance remains owned by the existing integration evidence checks.

After processing a saved proposal, acknowledge its exact ID. Repeat `--id` to acknowledge a batch:

```sh
python3 "$SHARED_DIR/scripts/workflow_controller.py" ack \
  --checkpoint "$PROJECT_ROOT/controller.json" --id ACTION_ID
```

Acknowledge an action after its host effect succeeds or its observation is delivered to its consumer. Use the occurrence ID to deduplicate repeated delivery. Repeating an acknowledgement is safe. An ID that was never saved in the checkpoint is rejected. Acknowledgement changes only the checkpoint.

Use `wait` with the same arguments and `--timeout 30` after processing and acknowledging an apply result. The wait checks local file changes and returns on an actionable change or after at most 60 seconds. It does not save a checkpoint. It reads complete event lines only. An incomplete final line waits for the producer to finish it. A timeout returns `status: timeout` and empty action lists; it needs no model turn or user notification. Time-based usage changes are checked again at the wait bound. A new wait can follow immediately through the host's deterministic adapter.

`--limit` bounds each batch to 1 through 1000 event lines. A `more: true` result needs another apply before waiting. Unchanged file checks do not rerun queue projection. The controller keeps source cursors and stores each changed proposal once. Pending proposals are returned until acknowledged; after acknowledgement, unchanged status adds no payload. `--help` contains command flags. Results use a JSON status envelope; invalid inputs return `status: blocked` with exit code 2.

## Event producer contract

The adapter writes one complete JSON object per line. Every event has exactly these common fields: `id`, `kind`, `source`, and `cursor`. Each value is a nonempty string. IDs are unique within a source. Cursors are opaque host values retained for the next host read. An unchanged status may have a new ID and cursor; it causes no repeated action.

Each kind adds exactly these fields:

| Kind | Fields | Meaning |
| --- | --- | --- |
| `status` | `call_id`, `status` | Observe `running`, `completed`, `failed`, `cancelled`, or `waiting_user` for a ledger call. |
| `receipt` | `call_id`, `receipt` | Reconcile an actual file, with `receipt: {"path": "receipt.json", "sha256": "..."}`. |
| `decision` | `task_id`, `status` | Record `waiting` or `resolved` for a task with a stable `T<N>` ID. |
| `wake` | None | Request a new projection after saved queue or usage evidence changes. |

```json
{"id":"finished-1","kind":"status","source":"host","cursor":"cursor-1","call_id":"call-1","status":"completed"}
{"id":"receipt-1","kind":"receipt","source":"host","cursor":"cursor-2","call_id":"call-1","receipt":{"path":"receipts/call-1.json","sha256":"64 lowercase hexadecimal characters"}}
```

Save and verify a receipt before appending its event. Its checksum, call ID, input revision, exact route, outcome, and role context must pass the existing receipt checks. Completion status alone returns `receipt_required` with `retry_allowed: false`. A missing or invalid receipt returns `receipt_invalid` and stops the byte offset before that event. Later events stay pending. Restore the expected receipt and apply again. A reused event ID with different facts, a replaced source file, a truncated history, or a changed checkpoint anchor blocks processing.

The producer saves usage observations through the usage accounting interface, then appends a `wake` event. The controller calls `evaluate_budget` after receipt reconciliation and before proposing ready work. A usage block permits completion reconciliation. Call reservations and their approved ceilings remain owned by `run_state`.

## Host actions and recovery

1. `actions` contains pending readiness, receipt, completion, failure, decision, integration, queue blocker, and usage budget observations. A `cleared` action names a previous observation that no longer applies. Each action has a stable occurrence ID for host deduplication. A later transition back to the same state gets a new ID. Only proposals with `persisted: true` can be processed by the host.
2. `sidebar_actions` proposes status changes and an order. Waiting tasks use `❓`, active tasks use `🧑‍💻`, and integrated tasks use `✅`. The order is waiting, active, complete, then task number within each group. A blocked dependency alone does not mean a user decision is pending. The host binds task IDs to its own chat IDs and preserves task titles.
3. A completed worker receipt is execution evidence. It never marks a queue task complete. A successful reviewer receipt without its recorded review returns `review_completion_required`; the owning host uses `run_state.complete` to finalize the bound review, then projects again. The controller's preview does not publish review evidence. A queue with a bound
feature policy can return provisional `implemented` tasks and
`feature_review_required`. Keep those tasks active. Only a ready feature gate
moves them into integrated acceptance and completed sidebar status. Read
[feature-review.md](feature-review.md) for the policy contract.
4. `apply` locks the checkpoint, then the ledger, and publishes each with the existing atomic writer. Other controller callers must use the same lock order. A crash after ledger publication can replay the event safely. Receipt reconciliation does not add another step or consume another call. The checkpoint saves the projection and outbox together. A crash after that save and before output delivery leaves all pending action IDs available on the next apply, preview, or wait.
5. The outbox retains unacknowledged proposals. A state change marks an old proposal as superseded; that proposal stays out of `actions` and `sidebar_actions`. Its ID appears in `superseded_action_ids`. The host can acknowledge those IDs after it cancels or records them. A superseded readiness proposal cannot become active again. A new ready transition gets a distinct occurrence ID.
6. Saving the outbox does not prove that a sidebar mutation or dispatch happened. The host processes saved proposals, deduplicates their occurrence IDs, and calls `ack` after success. If the host stops after the effect and before acknowledgement, delivery repeats with the same ID. Readiness remains a proposal; approved reservation and dispatch checks still apply.

Use one event producer per append-only file or serialize its appends. Keep one controller checkpoint per workflow. Existing ledgers are extended only through valid receipts; legacy fields and counters remain intact. A legacy ledger that lacks dispatch authority produces queue errors and requires its normal migration path.
