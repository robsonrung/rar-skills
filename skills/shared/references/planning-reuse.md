# Reuse shared planning decisions

Use this path when several unstarted tasks use the same settled decision. Keep the
existing decision record, stable decision IDs, source index, and approval inputs
as the authority. A render request is a derived input artifact, not another plan.
Standalone tasks and existing approved contracts keep their recorded method.

## Assess once, then classify each task

1. Read the feature's settled decisions and source index. Verify applicable scope,
   assumptions, authority, and source revisions. Apply design lenses only to
   unresolved or changed boundaries. Keep each shared conclusion under its
   existing decision ID. Retain all findings, dispositions, and review focus.
2. For each task, record which surfaces are unchanged and which need a new
   assessment. Classify its security through `security-gate`; a shared decision
   never supplies a task's security level by inheritance. Keep its acceptance,
   focused checks, dependency tests, ownership, and review requirements.
3. Render repeated gate fields from the shared conclusions and the assessed task
   differences. Unknown applicability, changed sources, disputed decisions, or a
   changed scope require focused reassessment. Keep unrelated settled decisions.
   A change to an approved or started contract follows the existing replacement
   task and approval rules.
4. Revalidate the render inputs immediately before approval, copy the complete
   `gate_section` into the canonical draft, then run its normal gate and queue
   validation. Bind the emitted `scope_inputs` in the existing preview and route
   scope. Keep the saved request and decision records immutable after approval.
   Original implementation sources remain historical evidence; planned code edits
   do not change those immutable planning inputs.

The renderer checks structure, source revisions, scope matches, and finding
consistency. The coordinator must establish that the source index is complete,
that its authority is valid, and that the task has no omitted risks. Rendering
does not prove these judgments, grant approval, run lenses, or replace checks.

## Render current gate records

`shared/scripts/planning_reuse.py` is read only. For a new shared conclusion, put
an exact `Scope: <scope>` line and its canonical v1 `gate-result` block under
`## D1: <existing decision title>` in the existing decision record. Retain
the decision's existing source IDs, assumptions, and source-index locators. Each
selected section needs one gate block. Preserve old records; use the normal
manual gate path when their structure does not support this optional renderer.

Obtain hashes through the helper's existing approval normalization:

```bash
python3 <shared-dir>/scripts/planning_reuse.py --root <project-root> \
  --hash-input <decision-record-path> --hash-input <source-path>
```

Save a request with this shape. Replace each placeholder with current evidence.
`task.gate` is the full v1 gate result for task-specific risks, including empty
arrays when no additional lens applies. `sources` contains the complete checked
file evidence closure from the source index. An empty array is valid only when
the decision record itself supplies sufficient authority; unknown or missing
evidence prevents reuse. Paths must be canonical, relative, and free of symlinks.
Use immutable local captures for
external evidence, and assess whether that captured revision is still applicable.

```json
{
  "schema_version": 1,
  "shared": [{
    "decision_id": "D1",
    "path": "work/decision-record.md",
    "content_sha256": "<canonical hash>",
    "scope": "public API ownership"
  }],
  "sources": [{"path": "src/api.py", "content_sha256": "<canonical hash>"}],
  "task": {
    "id": "T1",
    "surfaces": [
      {"scope": "public API ownership", "decision_id": "D1", "status": "unchanged"},
      {"scope": "input validation", "decision_id": null, "status": "assessed"}
    ],
    "assessment": "Shared ownership applies. Input limits need task-specific tests.",
    "security": {"level": "deep", "trigger": "untrusted input"},
    "gate": {
      "schema_version": 1,
      "verdict": "proceed",
      "lenses_run": [],
      "blocking_findings": [],
      "advisory_findings": [],
      "required_changes": [],
      "decision_required": null,
      "review_focus": ["Verify input limits and rejected input behavior."]
    }
  }
}
```

```bash
python3 <shared-dir>/scripts/planning_reuse.py --root <project-root> \
  --request <saved-render-request.json>
```

The result contains `gate_section`, `scope_inputs`, `checked_sources`, and
`approval_granted: false`. It preserves findings and required changes with their
stable IDs. Identical entries are copied once; conflicting IDs, severity, or
dispositions fail. Every selected decision needs an exact unchanged scope match;
new surfaces need an explicit assessment and current task gate. Open blockers or
material decisions cannot become `proceed` through reuse. Reassess conflicting
conclusions in their source record before rendering again.

Only the request and selected decision records enter `scope_inputs`. Mutable
implementation source paths in `checked_sources` are verified at render time and
stay evidence of the planning basis. The full generated gate remains in the task
contract, so implementation can use its inherited constraints without loading the
render request or replaying planning lenses. Final acceptance remains unchanged.
