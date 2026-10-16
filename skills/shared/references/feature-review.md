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

A passing focused packet permits provisional dependency release for a deferred task. It never accepts the feature. A critical task also needs the existing ready independent review and its approved dispatch binding. Status labels and a claimed check result cannot replace captured evidence.

When later integration changes the source, prepare a current snapshot. Use the existing check selection and transfer protocol for passing captures with unchanged declared inputs, command definitions, acceptance scope, and environment. Unknown dependencies use the whole source. A changed dependency closure, contract, or environment requires new evidence. Preserve original captures and supply the required current environment assessment. Run only affected checks after a repair; checks marked `fresh` require a new command execution.

## Final acceptance

Complete combined simplification before the final source snapshot. Prepare final requirements from the same check plan and collect every required acceptance command and observation, including relevant task interactions. Review the full behavior against the feature acceptance contract and task contracts. A review limited to integration seams is incomplete.

Reserve the final reviewer through `run_state.py reserve --root ROOT` with the prepared `--review-snapshot`. Complete the actual reviewer call through the existing receipt path. The queue records `feature_review` with `snapshot`, `base`, and `call_id`; the call ID selects the actual ledger call.

Final acceptance requires the complete passing evidence, a ready review result, the approved final route, its intact execution receipt, matching snapshot and review checksums, a separate recorded context, and no pending calls. Checks alone cannot accept the feature. The root controller alone can promote provisional tasks after this gate passes.

The helper reports `final_review_ready`. The queue controller also proves that every task has current implementation evidence before it reports feature acceptance.

Use `feature_review.py validate --policy PATH --root ROOT` to inspect policy errors. Use `assess-task` with `--task`, `--snapshot`, `--packet`, and `--base` for focused evidence. Use `assess-feature` with `--snapshot`, `--base`, `--ledger`, and `--call` for final evidence. These commands validate local records and make no model calls.
