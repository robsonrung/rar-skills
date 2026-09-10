# Review Evidence Contract

Use this contract for reusable task, integration, and PR review evidence. Resolve `shared/scripts/review_evidence.py` from the loaded collection.

The helper checks source identity, record integrity, declared coverage, command results, and readiness. Selecting a complete requirements plan, assessing review quality, resolving findings, and interpreting browser observations still require judgment. Local checksums detect changed records; they are not signatures against a writer who can replace all files.

## Prepare before review

Complete planned simplification first. Write a task contract and a requirements JSON file. Declare every required check and browser flow. Select exclusions before review. Empty lists are valid only when the task and repository require none.

```json
{
  "context": {
    "runtime": "Actual runtime version",
    "dependencies": "Actual installed dependency state",
    "external_state": "Relevant service or browser state, or none"
  },
  "checks": [
    {
      "id": "tests",
      "command": ["npm", "test"],
      "cwd": ".",
      "timeout_seconds": 900
    }
  ],
  "observations": [],
  "exclusions": {}
}
```

Replace these placeholders with actual facts and repository commands. Context is caller supplied. Refresh it before reuse. If runtime, installed dependencies, or external state cannot be confirmed, run fresh verification. A matching context file alone does not prove that a service is unchanged.

```bash
python3 <shared-dir>/scripts/review_evidence.py prepare \
  --root <git-worktree-root> --base <intended-base> \
  --contract <task-or-feature-contract> \
  --requirements <requirements.json> --output <new-evidence-directory>
```

For a recheck, add `--previous-review <prior-review.json>`. The task launcher
requires the latest recorded review for that track. For integration, pass the
latest record from each task; use task-specific finding IDs to avoid collisions.
Prior records are bound by checksum. The new response must retain their finding
IDs, paths, and severity, then state each resolution. Findings cannot disappear
or become less severe without an explicit rejected or fixed result.

Use absolute paths. The helper resolves the base to a commit. It hashes tracked and nonignored untracked files, executable modes, symbolic link targets, and the index. Coverage includes committed, staged, unstaged, deleted, renamed, and new paths. Renames use old and new paths.

Keep evidence outside the source tree. For launcher artifacts inside the worktree, pass `--artifact-dir <launcher-artifact-directory>` to exclude only that generated directory. It cannot contain tracked source. Never put task source files there. Non-Git directories, submodules, unresolved index conflicts, and symbolic links outside the source root return `blocked`.

The task contract is hashed separately. Its standalone status line can change; acceptance cannot. Requirements, context, and exclusions are frozen by hash. Ignored files and remote state are outside the source hash.

Keep other source writers stopped during preparation, checks, and review, or use
an isolated worktree. This is a source hash record, not a copied filesystem.
The helper compares captured and current state; it cannot detect an intermediate
edit that another process made and then reverted during review.

## Capture checks

```bash
python3 <shared-dir>/scripts/review_evidence.py run-check \
  --snapshot <evidence-directory>/snapshot.json --id tests
```

The helper executes the declared argument list without an implicit shell. It records exit code, duration, timeout, source changes, and hashes of stdout and stderr. A command that changes captured source cannot supply passing evidence for that snapshot. Run prerequisites that change source before preparation.

Each check runs once per evidence directory. A retry uses a new directory and preserves the failed result. Reference a prior captured check only when its source hash, context hash, and complete command definition match. The validator checks these fields. A prose claim of a pass is insufficient.

For browser observations, save actual driver output or screenshots and their SHA-256 hashes. The helper checks file integrity and the declared result; it does not execute or interpret browser actions. Missing or skipped required observations prevent readiness.

## Reviewer response

Give the independent reviewer the snapshot path, its file SHA-256, requirements, prior findings, and check result paths. Its complete final response must be one JSON object with these exact fields:

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

Every changed path needs exactly one coverage row. `outcome` is `reviewed` or `excluded`. Excluded paths and reasons must exactly match requirements. Missing, duplicate, or extra rows are invalid.

Each finding has exactly `id`, `path`, `severity`, `status`, and `evidence`. IDs are unique within a review. Severity is P0, P1, P2, or P3. Status is `open`, `fixed`, `rejected`, `deferred`, or `disputed`. Evidence explains the defect or supports its resolution. Carry prior finding IDs into rechecks and record their resolution. The reviewer must assess that resolution; the validator cannot infer it from code. Map full-review severity CRITICAL to P0, HIGH to P1, MEDIUM to P2, and LOW to P3.

Each observation has exactly `id`, `result`, and `evidence`. Result is `pass`, `fail`, or `skipped`. Evidence is a nonempty list of objects with absolute `path` and file `sha256`. Observation IDs must match requirements.

## Record and verify

For `implement-and-review`, use the launcher's `record-review`. It reads the completed native receipt or runner response, checks the approved route, validates the result, and records its path and checksum in the task manifest. Do not rewrite the reviewer's result before recording it.

For a standalone or integration review, save the actual execution envelope with `success: true` and the reviewer's complete JSON response in `agent_message`. Preserve host or runner metadata. Then run:

```bash
python3 <shared-dir>/scripts/review_evidence.py record \
  --snapshot <evidence-directory>/snapshot.json --execution <execution.json>
python3 <shared-dir>/scripts/review_evidence.py verify \
  --snapshot <evidence-directory>/snapshot.json --base <current-intended-base>
```

The generic recorder checks response identity and integrity. Model identity and context independence remain the caller's execution protocol; the task launcher checks its own route plan. Never construct a successful envelope from a failed or missing execution.

The verifier returns JSON and an exit code: 0 for `ready`, 1 for `needs-work`, and 2 for `blocked`. Preparation and recording can succeed before readiness is checked. Always verify before a completion decision.

Readiness requires complete coverage, passing required checks and observations, no open or disputed finding, and no deferred P0, P1, or P2. Deferred P3 findings need a reason in their evidence. There is no approval field to override these rules.

A changed source, index, intended base, contract, requirement, or evidence file blocks reuse. The error lists changed source paths where available. Review affected paths and interactions, then create a new snapshot and result. Preserve old records. A reviewer can retain earlier coverage after assessing the effects of later changes; matching individual file hashes cannot prove semantic independence.

Legacy Markdown reports remain context. They cannot establish deterministic readiness without a current structured record. Human reports link to snapshots, review records, captured checks, and verifier output.
