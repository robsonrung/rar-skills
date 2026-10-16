# Feature review

Read this reference when a new queue and its approved routing plan both select a `review_policy` file. An absent selection preserves the existing task review flow. An active plan changes only through a new explicit approval.

## Policy and authority

The policy is a JSON file with this shape:

```json
{
  "schema_version": 1,
  "mode": "feature",
  "queue": ".ai-workflow/work/example/tasks.json",
  "feature_contract": ".ai-workflow/work/example/prd.md",
  "check_plan": ".ai-workflow/work/example/check-plan.json",
  "tasks": {
    "T1": {
      "contract": ".ai-workflow/work/example/tasks/T1.md",
      "review": "deferred",
      "reason": "Local behavior has a bounded regression surface.",
      "focused_checks": ["focused-regression"]
    }
  },
  "final_review": {
    "scope": ".ai-workflow/work/example/prd.md",
    "route": {"...": "complete approved reviewer route"}
  }
}
```

Paths are relative to the explicit source root. The queue must select this exact policy. The policy must name every queue task and its exact acceptance contract. The approved `scope.inputs` binds the queue, policy, check plan, feature contract, and all task contracts. This keeps a second policy file from silently changing the selected review mode.

Feature mode uses one combined repository root. Every focused and final snapshot must name that root. A queue spanning repositories retains task review mode or splits into independently reviewed feature units.

Classify each task as `deferred` or `critical` with a semantic reason. Security, migrations, public contracts, difficult changes, uncertain validation, and other critical behavior retain independent task review. File separation alone does not prove low risk. A deferred task needs focused regression and dependency checks before it can release a dependent.

The final route has role `reviewer`, takes the feature acceptance contract as `input_path`, and has its own role identity. Its approved model and fallback models differ from implementation models. Its recorded execution context is separate from implementation contexts.

## One check plan

The check plan contains three fields:

1. `requirements` is the existing `review_evidence.py` requirements object. It contains actual commands, exact input scopes, runtime and external context, captured observations, and explicit exclusions.
2. `required_checks` maps every command ID to a boolean. At least one command is required for final acceptance.
3. `interactions` lists the required observation IDs that cover relevant combined behavior. Each ID also appears in `requirements.observations`.

Use `feature_review.py requirements --policy PATH --root ROOT --task T1` to derive focused snapshot requirements. Omit `--task` to derive the final requirements. Save that output for `review_evidence.py prepare`. This derives command definitions from one plan and binds their exact definitions, required flags, acceptance contracts, and environment identity.

The derived `check_contract` binds the feature contract and canonical scope hashes for the complete policy input set. Snapshot review contracts remain task specific until final review. This common check contract permits exact captured commands to transfer from task evidence to final evidence. The validator derives the entire declaration from the policy; an omitted input or unrelated review contract fails validation. Canonical task hashes ignore only the existing exact workflow status line. Workflow files may remain in ignored directories because the immutable snapshot requirements bind them separately from source files.

## Provisional dependency release

Capture the task implementation and focused commands with the existing source snapshot and packet APIs. Record the snapshot, packet, base, and task launch manifest in the ledger through the queue controller protocol. The helper validates the current combined source, the task acceptance contract, exact requirements, command capture checksums, logs, and command outcomes.

A passing focused packet permits provisional dependency release for a deferred task. It never accepts the feature. A critical task also needs a ready independent review and its approved dispatch binding. Use the scoped reuse protocol below when a later change leaves its approved dependency closure intact. Status labels and a claimed check result cannot replace captured evidence.

When later integration changes the source, prepare a current snapshot. Use the existing check selection and transfer protocol for passing captures with unchanged declared inputs, command definitions, acceptance scope, and environment. Unknown dependencies use the whole source. A changed dependency closure, contract, or environment requires new evidence. Preserve original captures and supply the required current environment assessment. Run only affected checks after a repair; checks marked `fresh` require a new command execution.

## Scoped critical review reuse

For a new approved feature policy, a critical task can declare `reuse_scope`:

```json
{
  "inputs": ["src/shared.ts", "src/shared.test.ts", "package-lock.json"],
  "independent_paths": ["src/unrelated.ts"],
  "complete": true,
  "reason": "The inputs include the complete dependency closure; the other file has no effect on this contract."
}
```

Declare the scope before the original review. `inputs` includes implementation,
callers, dependencies, configuration, and focused check inputs that can affect the
**acceptance contract**. `independent_paths` names exact files whose later edits
cannot affect it. Use exact repository file paths; absent future paths are allowed.
Existing files must be captured. Globs, directories, symbolic links, and ignored
files cannot define this scope. Keep the sets disjoint and independent paths outside the task's
write ownership. Unknown dependencies require a current review. Path separation alone does not establish independence.

Focused checks must declare exact inputs within the dependency closure. The
derived task requirements include `critical_scope`. The original independent
reviewer must assess its completeness and return `scope_approval` through the
[reviewer response contract](reviewer-response.md). A ready review without that
acknowledgement cannot authorize reuse.

Keep the current `snapshot` and `evidence_packet` in the integration entry. Add
`critical_review: {"snapshot": {"path": "<original snapshot>", "sha256": "<hash>"}, "call_id": "<original reviewer call>"}`
to retain the original independent dispatch. Reuse requires unchanged dependency
inputs, base, index, artifact directory, environment identity, contracts, and
requirements. Every later
changed file must be in the approved `independent_paths`. Changed or unknown
inputs require a current independent review. The helper also verifies the
original receipt, review, findings, and current focused captures. Select the latest
completed task review with its full earlier review and finding ancestry, so an older
pass cannot bypass a later result or unresolved finding. When source changes, also include `critical_review.assessment: {"path": "<assessment.json>",
"sha256": "<hash>"}`. It binds `from_snapshot_sha256` and `to_source_id` with the
captured environment assessments described below. For standalone
`assess-task`, supply this link with `--critical-review <link.json>` and the actual
call ledger with `--ledger <run-state.json>`.

This protocol releases dependencies only. It cannot accept the feature or remove
required checks. Existing plans without `reuse_scope` retain their current review
requirements. The separate `review_scope` protocol for exact prospective changes
remains unchanged.

## Batch evidence refresh

Use `shared/scripts/feature_refresh.py` after integration changes to refresh
selected task evidence together. It reads the approved policy and ledger, selects
valid captured checks, and identifies missing, affected, or required fresh checks.
The refresh phase makes no reviewer calls and leaves plans and the ledger unchanged.

```bash
SHARED_DIR="<absolute path of the loaded shared skill>"
python3 "$SHARED_DIR/scripts/feature_refresh.py" \
  --policy <policy.json> --root <project-root> --base <review-base> \
  --ledger <run-state.json> --output <new-evidence-directory>
```

Selected task snapshots must share their original artifact directory. Choose a
new output directory inside it; retain that artifact boundary during refresh.
Select critical tasks only when their policy includes `reuse_scope`; other
critical tasks retain the current independent review flow.

The default is a read-only preview of tasks with existing integration evidence.
Add repeated `--task T1` options to limit the batch. The preview can omit
`--environment`; it returns `request.source_id`, `request.context_id`, and
`environment_required: true` without writing files or running commands. A supplied
environment file is validated in preview too.

Add `--execute --environment <current-environment.json>` to prepare immutable
snapshots and packets, transfer valid captures, and run required commands.
Compatible nonfresh checks can serve several task snapshots. Required fresh
checks still execute for each target snapshot.

Bind the environment evidence to the preview's current IDs using `to_source_id`
and `context_id`. Include `runtime`, `dependencies`, `external_state`, and
`base_interactions` assessments.
Each assessment needs a reason and captured evidence. The helper validates these
bindings before transfer; a claim that the environment is unchanged is insufficient.

A ready `result.json` includes a complete `integration_evidence_patch`. Apply it
with `feature_refresh.py --root <project-root> --apply-result <result.json>`.
This validates the original ledger hash, current source and environment, task
implementation receipts, and critical reviews under the ledger lock before writing.
The ledger must be outside captured source. A repeated application returns
`already-applied` only while its evidence remains valid. Project readiness after
application. Original review links and call history remain intact. The refreshed
packets establish provisional evidence only.

A failed or blocked batch keeps its captures and returns an empty patch. After repair,
use a new output directory and `--resume-from <prior/result.json>` to select still
valid captures without replacing the prior records. Run affected or missing
checks again. Complete the final gate below even when all refresh results pass.

## Final acceptance

Complete combined simplification before the final source snapshot. Prepare final requirements from the same check plan and collect every required acceptance command and observation, including relevant task interactions. Review the full behavior against the feature acceptance contract and task contracts. A review limited to integration seams is incomplete.

Reserve the final reviewer through `run_state.py reserve --root ROOT` with the prepared `--review-snapshot`. Complete the actual reviewer call through the existing receipt path. The queue records `feature_review` with `snapshot`, `base`, and `call_id`; the call ID selects the actual ledger call.

Final acceptance requires the complete passing evidence, a ready review result, the approved final route, its intact execution receipt, matching snapshot and review checksums, a separate recorded context, and no pending calls. Checks alone cannot accept the feature. The root controller alone can promote provisional tasks after this gate passes.

The helper reports `final_review_ready`. The queue controller also proves that every task has current implementation evidence before it reports feature acceptance.

Use `feature_review.py validate --policy PATH --root ROOT` to inspect policy errors. Use `assess-task` with `--task`, `--snapshot`, `--packet`, and `--base` for focused evidence. Use `assess-feature` with `--snapshot`, `--base`, `--ledger`, and `--call` for final evidence. These commands validate local records and make no model calls.
