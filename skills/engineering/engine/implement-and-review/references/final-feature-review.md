# Final feature review

Apply `Authority and common rules` and `Output contract` in [the skill entry](../SKILL.md). Use when the queue and routing plan bind a feature policy and combined implementation is ready. This is the final gate for all provisional tasks, including critical tasks with valid earlier reviews. A task check, scoped reuse, or batch refresh cannot pass this gate.

## Prepare the combined evidence

1. Read the bound policy and `Policy and authority`, `One check plan`, and `Final acceptance` in `shared/references/feature-review.md`. Reuse loaded sections. Derive final requirements from the approved check plan without `--task`. Keep every required check and interaction.
2. Finish one combined behavior-preserving simplification pass before the final source snapshot. Use `coding-review-simplify` when a candidate needs its method. Make edits through the original approved implementation routes and contexts. Include all task contracts, shared interfaces, security decisions, migration order, deferred behavior, and named interactions in review scope.
3. Follow `Capture the final implementation checks` in [evidence-strategy.md](evidence-strategy.md), using the feature contract and complete final requirements. Read its bounded shared capture sections. Run all missing, affected, invalid, and required fresh checks. Assess transfers with current environment and base evidence. Keep original captures and findings; only captured command results count.
4. Confirm every task has current implementation evidence. When integration made several task records stale, load `Batch evidence refresh` in the feature reference. For critical reuse, also load `Scoped critical review reuse`. Neither operation removes the final gate or its required observations.

## Dispatch and assess

Read [review-brief.md](review-brief.md). Give the final reviewer every task contract, current combined checks, interaction evidence, prior findings, and all author identities. It must assess the complete feature behavior; a review of seams alone is insufficient. Use `full-review` once on the combined change under the approved reviewer plan, with `security_focus=true` for deep security exposure. It does not select new routes.

Use the policy's exact final reviewer route and its separate persistent context, independent from every feature author. Reserve through `run_state.py reserve --root ROOT` with the prepared `--review-snapshot`. The final reviewer is a ledger-managed feature scope, not an extra per-task launcher pair. Complete the actual call through the existing receipt path. Read only `Reviewer response` and `Record and verify` in `shared/references/review-evidence.md`; give the reviewer the exact response sections selected by the review brief.

Record `feature_review` with snapshot, base, and actual call ID. Run the shared verifier and the policy assessment. The helper's `final_review_ready` is necessary; the queue also proves all current task implementation evidence and no pending calls. Only the controller's accepted result completes the feature and promotes provisional tasks. Preserve independent execution receipts, current source and intended base, complete coverage, check records, and review checksums. Open P2 findings, skipped required checks, or missing observations block acceptance.

## Repair or recheck

Batch confirmed fixes through original implementation contexts. Prepare a new snapshot with prior reviews bound, preserve findings and failing captures, then select affected checks. Required fresh checks still run. Use one scoped recheck through the same approved reviewer context and `shared/references/incremental-review.md`; preserve valid coverage elsewhere. Broaden when a changed boundary, failure, or required scope demands it. Reconcile pending calls before retry; all call, cycle, time, and recovery limits remain in force. An exhausted allowance stops the affected work with its missing evidence recorded.

Use the common output contract and the loaded `implement-tasks` reference `completion.md`, section `Deliver and report`. That section governs residual findings, task statuses, final evidence links, cost reporting, and separately authorized delivery. Keep blocked findings visible; recording one does not complete the feature.
