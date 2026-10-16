# Independent task review

Use for standalone/legacy task mode or a policy-classified critical feature task. A critical result remains provisional until final feature acceptance. Deferred feature tasks use [deferred-task.md](deferred-task.md).

For critical work, load `Policy and authority`, `One check plan`, and `Provisional dependency release` in `shared/references/feature-review.md`. Load `Scoped critical review reuse` only when the bound policy declares `reuse_scope`. Keep its original reviewer approval, complete dependency closure, latest finding ancestry, actual receipt, and current focused evidence. Reuse can release a dependency; it never accepts the feature. After integration, load `Batch evidence refresh` only when refreshing eligible evidence together.

The implementer captures its last green required checks on the final unchanged source and returns the snapshot and original result paths. The coordinator follows [evidence-strategy.md](evidence-strategy.md), confirms current source and environment, and uses `select-checks` with `--from-snapshot <worker-snapshot>` and the original capture map before running verification. For unchanged source and context, pass the same worker snapshot to `--snapshot`. Reuse only validated captures; execute every affected, fresh, or missing check. Build the complete evidence packet with `prepare-packet` and resolve invalid references before dispatch. Before preparing the review brief, read and apply [review-brief.md](review-brief.md). Give the independent reviewer the selected response sections, the snapshot, check result paths, prior findings, and named risk. Launch the exact reviewer recorded in the plan:

```bash
SKILL_DIR="<absolute path of the loaded implement-and-review skill>";
python3 "$SKILL_DIR/scripts/launch.py" review \
  --session-id <session-id> \
  --task-id <task-id> \
  --track <track-name> \
  --review-brief <review-brief.md> \
  --review-snapshot <snapshot.json> \
  --evidence-packet <packet.json>
```

The review command reloads the approved plan, verifies the saved route still matches it, and uses a read-only reviewer. It does not accept a route from the mutable manifest alone. Rechecks reuse the recorded reviewer context.

## Record, repair, and finish

After recording the execution receipt, run `record-review` with the same manifest,
track, and cycle. It stores the structured reviewer response and rejects missing
coverage or evidence. For later turns, use the incremental recheck or prose addendum
in `shared/references/incremental-review.md`; the expanded record still needs complete coverage. Before completion, run `verify-review --manifest
<launch-manifest.json> --track <track-name> --base <current-review-base>`.
Only `ready` meets the review acceptance contract. A successful `poll` reports
execution status only. Link the snapshot, review record, and verifier result
from `report.md`. Legacy reviews without these records cannot establish readiness.

1. Apply valid findings through the same approved implementer route and its recorded context. Persist each review/fix cycle before dispatch. The default is three cycles; use the reviewer route's approved `recovery.review_cycles` when present. If evidence is missing, reserve recovery within the approved allowance before dispatch. Exhaustion of the approved recovery or cycle allowance stops the task. Retain the implementer and reviewer until their fixes, rechecks, and evidence work are complete.
2. Use `full-review` only when the user selected it in the reviewer plan. Recommend it when the change crosses a seam, carries high risk, or needs feature-level reconciliation. Its scope and routes must remain proportional to the task.
3. Validate the required task acceptance captures with `select-checks`. Keep validated `reuse` references, execute `run` entries, and assess explicit `transfer` candidates before transfer. Required fresh checks always run. Preserve failing regression evidence. **Only captured command results count as evidence**; prose cannot be converted into a capture after execution.
4. Return the common output contract with the ready verifier and linked review record, or the remaining blocker. A critical task stays provisional until final feature acceptance.
