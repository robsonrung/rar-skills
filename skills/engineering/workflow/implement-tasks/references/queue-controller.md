# Read-only queue controller

Use `shared/scripts/task_queue.py` to inspect canonical task inputs and project readiness. Resolve `shared/` from the loaded collection. The controller reads contracts, approved routing scope, task launch manifests, the call ledger, and structured integration evidence. It writes no state, starts no worker, and runs no acceptance command.

```bash
SHARED_DIR="<absolute path of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/task_queue.py" --help
```

## Approved scheduling inputs

Keep stable scheduling metadata in `queue.json`, referenced from `tasks-draft.md`. Paths resolve from the project root. The task's `manifest` is its canonical Markdown contract; `launch_manifest` locates the existing execution manifest, which is absent before first dispatch.

```json
{
  "schema_version": 1,
  "id": "feature",
  "parent_prd": ".ai-workflow/work/feature/prd.md",
  "approval_record": ".ai-workflow/impl-review/run/combined-approval.json",
  "concurrency": {"max_active": 3, "isolation": "worktree"},
  "tasks": [
    {
      "id": "T1",
      "manifest": ".ai-workflow/work/feature/tasks/T1-example.md",
      "launch_manifest": ".ai-workflow/impl-review/run/T1/launch-manifest.json",
      "blocked_by": [],
      "write_paths": ["src/example.py"],
      "shared_surfaces": ["interface:example"]
    }
  ],
  "merge_plans": []
}
```

List owned files or directory scopes explicitly. Name shared migration, interface, and security surfaces with `migration:`, `interface:`, and `security:` keys. Shared files or surfaces serialize tasks unless their approved merge plan permits overlap. A merge plan has `id`, `tasks`, `write_paths`, and `shared_surfaces`; it names every permitted overlap. Its inclusion in the approved scope makes acceptance explicit. The member task contracts define combined acceptance, and current immutable ledger integration records prove it. Keep future snapshots and manifest state out of this static plan. An unbound prose plan cannot permit concurrency.

Include the queue file, parent PRD, and all canonical task contracts in the approved routing plan's `scope.inputs`. Route rows bind to their task with `input_path`. Include immutable policy inputs for call/time budgets and tools when these controls are not represented in the route schema. The queue is scheduling metadata, not task acceptance or execution state. Changing dependencies, ownership, concurrency, or merge plans requires a replacement approved input binding.

`concurrency.isolation` is `working-tree` or `worktree`. Omission selects `working-tree` and one writer, even when `max_active` permits more. Active launch manifests must match the approved isolation. A worktree still needs nonconflicting ownership or an accepted merge plan.

Set `approval_record` before preview for a new combined approval. It locates the immutable decision envelope shown below. Task-only approvals and existing legacy plans keep their separate approval records; absence of this field never grants model approval. Do not add the decision record itself to `scope.inputs`, because its decision-time content would make the prospective approval digest recursive. Its fixed locator is already bound through the queue configuration.

The controller also reads a `json task-queue` fenced block in a legacy index and legacy heading queues. An index-only draft must first become canonical task files before combined approval or fresh execution. Existing published task contracts and started execution records stay intact. Missing machine ownership or approval must be supplied and bound before dispatch. For new queues, prefer a separate `queue.json`; live approval links and index status cannot then change its binding.

## Inspect draft identities

```bash
SHARED_DIR="<absolute path of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/task_queue.py" approval-inputs \
  --queue <queue.json> --root <project-root> \
  --routing-plan <draft-routing-plan.json>
```

The output includes `queue.file_sha256` and each task's `current_file_sha256`, `current_content_sha256`, and `prospective_ready_content_sha256`. The optional routing plan adds `prospective_routing` with normalized `scope_inputs`, `scope_digest`, and `routes_digest`, retaining all non-task inputs. The prospective content changes only the exact draft status to ready status, then applies the launcher's canonical content rule. This supports combined approval while drafts remain unexecutable. The helper never records approval or promotes files.

Save the preview before the decision. After an actual combined response, write one immutable shared evidence envelope at `approval_record`:

```json
{
  "payload": {
    "schema_version": 1,
    "decisions": ["task_queue", "model_plan"],
    "response_reference": "<actual user response reference>",
    "decided_at": "<decision time>",
    "queue_file_sha256": "<raw queue file hash>",
    "preview": {"path": "<saved approval-inputs JSON>", "sha256": "<raw preview hash>"},
    "scope_digest": "<prospective scope digest>",
    "routes_digest": "<routes digest>"
  },
  "sha256": "<shared canonical payload hash>"
}
```

Use the shared immutable record writer and checksum rule. The scheduler verifies both decision names, the actual response reference and time, queue and preview identities, and exact routing approval digests. It rejects a task-only record as combined approval. The host still records only real user decisions; a checksum cannot establish who gave a response.

## Integration evidence in the existing ledger

Link immutable integration records from the current feature `run-state.json`:

```json
{
  "integration_evidence": {
    "T1": {
      "snapshot": {"path": "<combined snapshot.json>", "sha256": "<file hash>"},
      "base": "<review base>",
      "launch_manifest": "<configured task launch manifest>"
    }
  }
}
```

This field stores evidence locators, not a second task status. The controller checks task and route bindings, contract identity, immutable snapshot checksum, and `review_evidence.assess(snapshot, base)`. For new ledger-managed integration, the review must match a completed exact approved reviewer route with its own scope ID and the released task's contract as `input_path`. A launcher-managed review can supply compatible manifest evidence when its approved independent reviewer and snapshot match the current combined source. A direct review-record write alone cannot prove independent execution. The snapshot must describe the relevant combined source state, with all applicable acceptance and interaction requirements. A copied `done` label or worker success cannot release dependents. Stale source, changed contracts, failed checks, missing observations, and blocking findings require integration work.

For exact independent changes approved before the original review, the entry
can add `carry_forward: {path, sha256}` from the shared `carry-forward` command.
Keep the original snapshot and reviewer dispatch links. The controller checks
the immutable checkpoint, current target source, complete declared dependency
closure, current environment evidence, and passing required captures through
`assess_carry_forward`. Read the carry forward protocol in
`shared/references/review-evidence.md` before choosing this path. An unlisted or
affected change still requires integration review. Matching file paths or hashes
does not establish independence. Pending calls retain ownership, and approved
call budgets still apply. Carry forward releases dependencies only; final
combined review remains required.

## Project the next wave

```bash
SHARED_DIR="<absolute path of the loaded shared skill>";
python3 "$SHARED_DIR/scripts/task_queue.py" schedule \
  --queue <queue.json> --routing-plan <routing-plan.json> \
  --ledger <run-state.json> --root <project-root>
```

The result has `ready`, `blocked`, and `required_integration` lists in stable task order. Invalid IDs, missing blockers, self blockers, cycles, malformed bindings, and unsafe ownership fail closed. Only ready contracts with exact approval and verified dependency integration can be selected. Existing task manifests and ledger calls retain active ownership; the approved concurrency cap also limits new selection. The projection checks existing total and route call ceilings, then accounts for the initial implementation calls of each selected task. It does not predict future review or recovery calls.

Read the result immediately before dispatch, then reserve the selected call and its input in the existing ledger before starting it. This projection does not reserve a task or consume a budget. Use one conductor to reserve work; rerun the projection after any ledger, manifest, integration, or source change. Required integration runs through the separately approved integration route and gets its own reserved call. The controller needs no mutation dry run because both commands are read only.

For ordinary later edits, an entry can instead add
`batch_review: {path, sha256}` linking a current batch snapshot. Several entries
can share this link. Keep each original task snapshot and dispatch binding;
set the entry's base to the batch's current intended base. The shared batch
protocol requires exact canonical task membership, complete valid task evidence,
prior findings, current environment and interaction assessments, and one actual
approved independent batch reviewer response. The route binds the batch contract,
not a member task contract. Its scope ID must differ from every endorsed task.
One call can release all endorsed tasks, with existing counters and ceilings.
Pending calls keep every member's ownership; missing pending snapshot evidence
blocks scheduling until reconciliation. A batch does not replace the final
feature gate. Read `shared/references/review-evidence.md` before preparation.

Each projection reuses validated immutable batch evidence within that call only.
Before returning, it rechecks current source, base, index, and all linked file
hashes. A change during projection blocks its result. No cache survives into the
next projection.
