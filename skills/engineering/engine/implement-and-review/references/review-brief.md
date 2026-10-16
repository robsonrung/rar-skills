# Review brief

Give the approved reviewer:

1. The review scope and acceptance contract: task scope for standalone or critical dependency review, complete feature scope for final feature review.
2. The changed paths and relevant diff.
3. Test evidence and any no-test exception.
4. The named task risk and triggered lens conclusions.
5. The selected response contract from `shared/references/reviewer-response.md`. For an initial review, load its introduction, `Initial response`, `Evidence packet substitution`, and `Completion`. The launcher embeds these selected sections for every transport; use that text without reading the full manual again. `--response-mode auto` adds recheck rules when prior evidence is bound; select `full`, `recheck`, or `addendum` when the response form is known. The initial section includes conditional scope acknowledgement. Add `Batch endorsement` only when `response-contract` declares a batch; that path requires a full response. For a source recheck, also load `Recheck`; for a prose addendum, load `Recheck` and `Prose correction`. A changed acceptance contract requires a full response. Fresh and reconstructed reviewers receive every section needed for their selected response, with the full acceptance contract.

Include these review constraints in the brief: the reviewer is read only and independent from the implementer. It checks **observable behavior**, scope, evidence, and the named risk. It assesses whether simplification edits are behavior-preserving, whether removed safeguards were required, and whether changed code creates a material maintenance trap. Severity follows the consequence. A confirmed P2 whose fix is outside scope remains blocking pending the existing user decision process; it cannot become a deferred P3 to fit the scope. The reviewer consumes the approved snapshot and does not choose a different model, effort, task scope, or worker.

For confirmed role continuation, send changed facts, finding IDs, evidence
locators, and the unchanged boundaries through the launcher. The launcher validates
the prior contract, route, context, receipt, and input before omitting repeated
contract text. It keeps the full rendering when it is smaller. Fresh or reconstructed roles receive the full contract. A compact
prompt does not reduce required review coverage or the approved call limits.
