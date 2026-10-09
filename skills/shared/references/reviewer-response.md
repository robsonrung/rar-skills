# Reviewer response contract

Read this before an independent review or recheck. Use the supplied acceptance
contract, current snapshot and hash, requirements, prior records, and captured
evidence. Inspect the actual source and affected interactions. Assess evidence
independently: a passing command or matching hash does not establish correct
behavior, complete scope, or an equivalent environment.

Return one JSON object as the entire final response. The coordinator records
that response unchanged. Remain read only and use the approved task, role,
route, and tools. The coordinator owns preparation, capture, transfer, and
verification through [review-evidence.md](review-evidence.md).

## Initial response

```json
{
  "snapshot_sha256": "SHA-256 of snapshot.json",
  "coverage": [
    {"path": "src/example.ts", "outcome": "reviewed", "reason": "Checked behavior and affected callers."}
  ],
  "findings": [],
  "checks": {"tests": "/absolute/path/to/checks/tests/result.json"},
  "observations": [],
  "summary": "No defect found."
}
```

These are the exact fields, with the conditional scope or batch fields and packet
substitution below. Use the supplied `response-contract` output for required
paths, check IDs, observation IDs, fresh observations, and prior findings.

1. `coverage` has exactly one row per changed path, including both paths of a
   rename. Each row has `path`, `outcome`, and `reason`. `outcome` is `reviewed`
   or `excluded`. Exclusions and reasons must exactly match requirements.
   Missing, duplicate, or extra rows are invalid.
2. Each finding has exactly `id`, `path`, `severity`, `status`, and `evidence`.
   IDs are unique. Severity is P0, P1, P2, or P3. Status is `open`, `fixed`,
   `rejected`, `deferred`, or `disputed`. Evidence explains the defect or supports
   its resolution. Retain prior IDs, paths, and severity; assess each resolution.
   Map CRITICAL to P0, HIGH to P1, MEDIUM to P2, and LOW to P3.
3. `checks` maps required IDs to original captured result paths. Read the actual
   results and logs. Prose, generic validation statuses, and execution claims
   cannot replace captures. Preserve failures and required failing regression
   evidence; do not turn a skipped or failed result into a pass.
4. Each observation has exactly `id`, `result`, and `evidence`. IDs match
   requirements. Result is `pass`, `fail`, or `skipped`. Evidence is a nonempty
   list of objects with absolute `path` and file `sha256`. Assess actual driver
   output or screenshots. File integrity alone does not prove the observed result.

When requirements declare `review_scope`, inspect its declared dependency inputs
and exact prospective changes. Add `scope_approval` with the digest supplied by
`response-contract` only after accepting that scope and those changes. Include
this field in full, recheck, and addendum responses for such snapshots; omit it
otherwise. A digest is an explicit review judgment, not a value to copy without
assessment. Report an unsupported scope as a blocker to the coordinator.

## Evidence packet substitution

A complete prepared packet can replace both `checks` and `observations` with
`"evidence_packet": {"path": "/absolute/packet.json", "sha256": "file hash"}`.
Supply either form, never both. All coverage, findings, summary, and conditional
scope approval fields remain required. Inspect the linked captures before using
the reference. A scoped unit packet must first be combined into a complete
packet. Exported validation packets use this same contract; they still need
independent coverage and findings.

The recorder expands the packet, preserves the original response, and checks
all references again. A complete packet replaces prior checks and observations
on a recheck. Inline updates merge with prior evidence. Neither form removes
unresolved findings. The coordinator must correct a bad packet before dispatch;
it cannot edit your response to repair a hash or close a finding.

## Recheck

Use the current snapshot's bound prior review. Inspect the change and state why
retained conclusions still apply. Identical file hashes alone do not establish
semantic independence. A changed acceptance contract requires a full response.

```json
{
  "mode": "recheck",
  "snapshot_sha256": "current snapshot file hash",
  "previous_review": {"path": "/absolute/prior/review.json", "sha256": "file hash"},
  "reuse_assessment": "Why retained coverage and observations still apply, including affected callers.",
  "affected_paths": ["src/caller.ts"],
  "coverage": [
    {"path": "src/changed.ts", "outcome": "reviewed", "reason": "Checked the repaired behavior."},
    {"path": "src/caller.ts", "outcome": "reviewed", "reason": "Checked the affected interaction."}
  ],
  "findings": [],
  "checks": {},
  "observations": [],
  "summary": "Focused recheck result."
}
```

Supply fresh coverage for changed files, affected callers within the snapshot
scope, new scope, and changed exclusions. Other coverage is inherited only with
your explicit `reuse_assessment`. The expanded record must still cover every
current changed path. `findings` contains new findings and changed dispositions
using the same five fields. Omitted findings retain their earlier status,
including open status. IDs, paths, and severity cannot change.

Inline checks and observations contain replacement or additional entries. The
expanded record must satisfy all current requirements. Prior checks must match
source, contract, environment, and commands or pass the explicit transfer
protocol. Assess transfer evidence for runtime, dependencies, external state,
and changed base interactions. A changed environment identity requires fresh
observations. Version 2 context notes do not change identity. Changed declared
observation inputs require fresh captures; unscoped observations need fresh
captures after any source content change. Require new observations whenever old
behavior or runtime no longer represents the change.

Two reviewers can identify one defect. Retain both finding IDs and each
reviewer's resolution. One common repair does not let one reviewer close the
other's finding. A recheck may identify new supported defects.

## Prose correction

Use the recheck fields with `mode: addendum` only when source and requirements
are unchanged. `affected_paths`, `coverage`, `checks`, and `observations` must
be empty. Correct finding evidence or the summary only. No finding may be
added, removed, closed, lowered, or otherwise change disposition. This remains
a reviewer call within the approved limits. It cannot repair source or evidence.

## Completion

The helper preserves and re-expands the response against immutable prior
records. Only its final `ready` result establishes readiness: complete coverage,
passing required checks and observations, no open or disputed finding, and no
deferred P0, P1, or P2. Deferred P3 findings need a reason. There is no approval
field that overrides these conditions. Execution success alone is insufficient.

## Batch endorsement

When `response-contract` returns `batch`, inspect every linked canonical task,
prior review, current evidence packet, environment assessment, and named
interaction. Use each task's `observation_baseline` and `fresh_observations`
reasons to assess reuse. Check transfers must preserve the declared dependency,
command, contract, and environment bindings. Require fresh results for affected
or explicitly fresh checks and for observations whose inputs or environment
changed. Unknown observation inputs require fresh captures after source changes.
Use a full response. Batch recheck and addendum forms are rejected.
Add these three exact fields to the initial response:

1. `batch_approval`: the supplied digest of the full batch declaration, after
   assessing its complete scope.
2. `endorsements`: an object keyed by exactly the declared task IDs. Each value
   has `snapshot_sha256`, a nonempty `acceptance` assessment of that complete
   task contract, and the exact sorted `coverage_paths` from its
   `endorsement_contracts` entry. Inspect those paths, including historical and
   changed-base interactions outside the current diff. Report unknown scope as
   a blocker; partial endorsement cannot approve a batch.
3. `interactions`: an object keyed by exactly the declared interaction names.
   Each value is your nonempty assessment of that interaction and its evidence.

Keep all prior findings in the shared `findings` array with their stable IDs,
paths, and severity. Add supported defects on any declared task coverage path,
even when a new base makes the combined diff empty. An open or disputed finding
blocks readiness. Assess each resolution from evidence. Endorsement is one
reviewer's judgment over a bounded task set; it is not several independent
opinions. The combined contract's own check and observation requirements still
apply. Dependency release does not establish final feature acceptance by itself.
