# Incremental review responses

Use after an initial structured review. Prepare a new snapshot with the latest
review bound by `--previous-review`. The reviewer reads the actual change and
assesses which earlier conclusions still hold. Do not infer semantic independence
from identical file hashes.

```json
{
  "mode": "recheck",
  "snapshot_sha256": "current snapshot file hash",
  "previous_review": {"path": "/absolute/prior/review.json", "sha256": "file hash"},
  "reuse_assessment": "State why retained coverage and observations still apply, including affected callers.",
  "affected_paths": ["src/caller.ts"],
  "coverage": [
    {"path": "src/changed.ts", "outcome": "reviewed", "reason": "Evidence for the changed behavior."},
    {"path": "src/caller.ts", "outcome": "reviewed", "reason": "Evidence for the affected interaction."}
  ],
  "findings": [],
  "checks": {},
  "observations": [],
  "summary": "Focused recheck result."
}
```

Supply fresh coverage for changed files, affected callers, new scope, and changed
exclusions. Other coverage is inherited only with the reviewer's explicit reuse
assessment. `findings` contains new findings and changed dispositions with the
normal five fields. Omitted findings retain their previous status, including open
status. IDs, paths, and severity cannot change. A new contract needs a full review.

`checks` and `observations` contain replacement or additional entries. The complete
normalized record must still satisfy the current requirements. Old check results
must match source and context or pass the explicit transfer protocol. A changed environment identity requires fresh observations. Version 2 context notes do not change identity. Declared observation input changes also require fresh evidence. Changed code also requires new browser
observations where the old behavior or runtime no longer represents the change.

For a factual correction to review prose, use `mode: addendum`. Source and
requirements must be unchanged. Coverage, affected paths, checks, and observations
must be empty. A finding's evidence or the summary can be corrected, but no finding
can be added, removed, closed, or lowered. This is a reviewer call under the existing
approved limits, not a free extra cycle or a source fix.

The helper preserves the raw execution response and stores its expanded result.
Verification re-expands the response against immutable prior records. The conductor
must never edit the reviewer's words to pass validation.

When two reviewers report one defect, group their IDs in the correction brief and
fix the common cause once. Retain both findings and each reviewer's resolution in
the evidence records. A shared correction does not let one reviewer erase the
other's finding. Reviewers may still identify new supported defects in a recheck.

Before dispatch, use `response-contract` to determine the current required observations.
Use a prepared `evidence_packet` in place of `checks` and `observations` when complete references
are available. This preserves all coverage and findings without asking the reviewer to copy hashes.

A complete evidence packet replaces prior checks and observations. Inline updates continue to merge with prior evidence. Neither form removes unresolved findings.
