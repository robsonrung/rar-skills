# Deferred feature task

Use only when the queue and approved routing plan bind the same policy and this task is `deferred`. Keep the complete task implementation and focused evidence obligations from [task-implementation.md](task-implementation.md).

Validate the current snapshot and focused packet through `assess-task` as specified in `Provisional dependency release` in `shared/references/feature-review.md`. Return `implemented` with the immutable snapshot, original captures, packet, base, implementation receipt, and launch manifest. The parent validates provisional dependency release. Keep the task active until final feature acceptance.

This branch launches no task reviewer and performs no task `record-review` or `verify-review`. It cannot supply reviewer judgment or feature acceptance. A newly found material risk needs a current policy decision; never silently remove an approved review or change an active plan.

After later integration changes, load only `Batch evidence refresh` in the shared feature reference to refresh selected provisional evidence. Preserve its guarded apply, current evidence, required fresh checks, and recovery rules. Refresh cannot accept the feature. Final review belongs to [final-feature-review.md](final-feature-review.md), loaded by the feature coordinator when the combined work is ready.
