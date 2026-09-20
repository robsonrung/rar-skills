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

Each check runs once per evidence directory. A retry uses a new directory and preserves the failed result. Reference a prior captured check when its source hash, context hash, and complete command definition match. For identical content after a commit or worktree transfer, use the explicit `transfer-check` protocol below. The validator checks these bindings. A prose claim of a pass is insufficient.

For browser observations, save actual driver output or screenshots and their SHA-256 hashes. The helper checks file integrity and the declared result; it does not execute or interpret browser actions. Missing or skipped required observations prevent readiness.

## Reviewer response

Give the independent reviewer the snapshot path, its file SHA-256, requirements, prior findings, and check result paths. For an initial review, its complete final response is one JSON object with these exact fields. For a recheck or a prose-only correction, use [incremental-review.md](incremental-review.md) to retain prior coverage without repeating it:

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

The normalized record needs exactly one coverage row for every changed path. An incremental response supplies only changed or affected coverage; the helper expands the bound prior record. `outcome` is `reviewed` or `excluded`. Excluded paths and reasons must exactly match requirements. Missing, duplicate, or extra rows are invalid.

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

A changed source, index, intended base, contract, requirement, or evidence file blocks implicit reuse. An explicit transfer can reuse a captured check on identical content; it never silently transfers review acceptance. The error lists changed source paths where available. Review affected paths and interactions, then create a new snapshot and result. Preserve old records. A reviewer can retain earlier coverage after assessing the effects of later changes; matching individual file hashes cannot prove semantic independence.

Legacy Markdown reports remain context. They cannot establish deterministic readiness without a current structured record. Human reports link to snapshots, review records, captured checks, and verifier output.

## Transfer checks after a commit or worktree change

The snapshot keeps its original source identity, including root, base, and index.
`content_id` separately hashes present file contents, executable modes, and symlink
targets. Deletions are represented by absence, so committing a deletion does not
change that content identity. Older snapshots remain readable.

Prepare a target snapshot. Capture fresh evidence of runtime, installed dependency
state, external state, and changed-base interactions. Save an assessment JSON with
`from_snapshot_sha256`, `to_source_id`, and four objects named `runtime`,
`dependencies`, `external_state`, and `base_interactions`. Each object needs a
nonempty `reason` and `evidence` list of absolute `path` and file `sha256` pairs.
A not-applicable external state still needs a recorded explanation. The reviewer
assesses these facts; a checksum does not prove that an environment is equivalent.

```bash
python3 <shared-dir>/scripts/review_evidence.py transfer-check \
  --from-snapshot <original-snapshot.json> --to-snapshot <target-snapshot.json> \
  --check <original-check/result.json> --assessment <transfer-assessment.json>
```

The helper rejects changed required inputs, contract, environment identity, command definitions,
failed checks, altered logs, and nested transfers. It writes a target check with
links to the original snapshot, result, and assessment. Use that path in the new
review. Transfer directly from the original check, not from a prior transfer.
Keep final combined acceptance and review of changed interactions. Check-specific input subsets require an unchanged explicit `inputs` declaration
from the original check. Otherwise use a fresh check when whole-content equality cannot be established.

## Evidence packet before dispatch

Run `response-contract --snapshot <snapshot.json>` before building the reviewer brief. It
returns the required checks, observations, fresh observation IDs, prior findings, and coverage paths.
Prepare a JSON observation list from actual driver captures. Each entry contains `id`, an observed
`result`, and absolute evidence paths. Existing `{path, sha256}` links are accepted only when correct.
Use `prepare-packet --snapshot <snapshot.json> --observations <observations.json> --output <packet.json>`.
An optional `--checks <checks.json>` maps check IDs to captured result files. Otherwise the helper
uses the snapshot's check directory. Preparation rejects missing entries and invalid hashes.
For the task launcher, pass `review --evidence-packet <packet.json>` to validate the packet before
reserving a review cycle. The launcher adds required response coverage to the bound review brief.

The reviewer can replace its `checks` and `observations` fields with the returned
`evidence_packet: {path, sha256}` reference. All judgment fields remain required. The helper
expands the exact packet, preserves the original response, and checks every referenced file again.
A packet does not prove that an observation passed. Preserve the observed result and require the
reviewer to assess it. Never edit a reviewer response to repair a hash or close a finding.

## Structured context and scoped inputs

New requirements can use `context: {"version": 2, "identity": {"runtime": "...", "dependencies": "...",
"fixtures": "...", "services": "..."}, "notes": "Review explanation"}`. Identity values must represent
observed relevant state. Notes remain bound to their snapshot but do not change environment identity.
Legacy contexts keep their full comparison. An identity change requires fresh observations.

A check definition can include `inputs`, a nonempty list of relative captured file paths.
Declare the complete dependency set, including tests, scripts, lockfiles, configuration, and schema,
before the original check. Directories, symbolic links, and existing ignored files are rejected.
Use explicit captured files; deleted files can be tracked as absent. A transfer requires the same declaration and unchanged file identities,
command, contract, and environment identity, plus the existing transfer assessment. Without inputs,
whole-content equality remains required. A declaration is a scope decision, not an inferred proof
that omitted callers are independent. Unknown dependencies require the full scope.

Optional `observation_inputs` maps observation IDs to relative captured file paths. A change to a
listed file or the declaration requires a fresh observation. The reviewer still assesses semantic
effects on unlisted callers. This does not authorize reuse after a behavior change.
