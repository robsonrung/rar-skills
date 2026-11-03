# Dependency release and integration

A worker's success label never releases a dependent. Release follows evidence about the current combined source.

**Feature mode** (a bound `review_policy`, `shared/references/feature-review.md`): after each task, the policy helper checks its focused captures, regression evidence, and dependency contract tests. A deferred task releases its consumers only when it returns `dependency_release: true`; a critical task also needs its own independent review. This is provisional `implemented` progress: keep the task active until the final feature gate accepts it. After later integration changes, refresh each affected task's evidence through `review_evidence.py select-checks` and transfer, and reuse scoped critical reviews instead of re-reviewing each task.

**Task mode** (no policy): link an immutable snapshot for each integrated task under `integration_evidence` in `run-state.json`. The controller checks it with `review_evidence.assess` against the current combined source and the task's contract, and the review must come from an approved reviewer route bound to that contract. A carry-forward checkpoint or a batch review can release several tasks without a new review each; both follow `shared/references/review-evidence.md`, and neither replaces the final combined review.

**Integration:** check interactions at changed boundaries and rerun affected acceptance on the combined state. Before an authorized merge, record the pending effect; after a crash, inspect the repository before retrying it. Reuse a review only while its route, contract, acceptance, and snapshot still match the combined source.

**Resume:** reconcile each pending call before resending it, and continue each role in its recorded context. A lost context is rebuilt only from that role's artifacts under the unchanged route.
