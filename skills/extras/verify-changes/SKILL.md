---
name: verify-changes
description: "Run a repository's deterministic checks from its own command surface. Use when the user asks to verify a branch, run repository checks, or prove that build and tests pass. It captures command evidence, does not repair code, and does not replace browser testing."
---

# Verify Changes

Run declared commands directly. This skill does not load a model preview for a
command only branch. If another branch dispatches a worker, that branch must bind
one exact approved snapshot to its request, reservation, and report. Nested calls
reuse that snapshot and do not add workers.

Produce captured evidence for the repository's required gates and the requested change. Discover commands, select the relevant checks, run their actual prerequisites, and report results. This skill does not repair code.

## Modes

- **Manual:** honor the user's requested check set. An explicit request for all checks runs every required gate; otherwise select the affected checks and applicable repository gates.
- **Pipeline (`mode:pipeline`):** use the caller's scope and acceptance contract without questions. Return the structured result from `references/checks-schema.json` and one verdict. Required repository gates still apply.

## Discover and scope

Read [references/command-discovery.md](references/command-discovery.md). Prefer the repository's named scripts and read-only CI configuration over reconstructed commands. Record detected build systems and command sources in `commandSurface`.

Resolve the base from `origin/HEAD`, code-host metadata, then `main`. Include staged and unstaged changes for the current worktree. Use native affected-package support when available. Without it, identify safe package or file checks from the repository's commands; use whole-repository checks when required or when a narrower valid check is unavailable. Record `workspacesScoped.supported: false` when native scoping is absent.

## Execute the selected checks

When the caller supplies a snapshot from
`shared/references/review-evidence.md`, execute only its declared checks through
`shared/scripts/review_evidence.py`. The snapshot is the scope contract for check
IDs, commands, inputs, source, dependencies, environment, and requirements. A
prose pass is insufficient. If discovery reveals a missing requirement, update the
requirements and prepare a new snapshot before execution. Never edit a frozen
record.

Select affected execution and reuse from declared inputs and changed paths. Supply
the target snapshot, an optional prior snapshot, prior original captured check
results in a JSON map, and any caller required fresh IDs:

```bash
python3 "$SHARED_DIR/scripts/review_evidence.py" select-checks \
  --snapshot "$TARGET_SNAPSHOT" --from-snapshot "$PRIOR_SNAPSHOT" \
  --checks "$RUN_DIR/prior-checks.json" --fresh tests
```

`prior-checks.json` maps a check ID to its original captured result path. Act on
each returned decision. `run` executes the declared command with `run-check`.
`reuse` keeps the matching captured result. `transfer` requires the explicit
`transfer-check` assessment with current runtime, dependency, external state, and
base interaction evidence before it can be used. The selector only identifies a
candidate transfer; it does not assess those current facts.

A declared `fresh: true` check always executes and cannot transfer. `--fresh` also
forces a named fresh execution. A check without declared `inputs` has whole source
scope. Unknown dependencies therefore require whole source equality or a fresh
command. A check with declared inputs can reuse only when each declared input,
command definition, contract, and environment identity still match. Keep the
original raw logs and provenance through the shared result path.

- Follow real command dependencies. Build first only when later checks require its output. Install only when dependencies need preparation or the requested clean-environment check requires it.
- Use the repository's lockfile-respecting install command. Do not modify lockfiles or install global tools to invent a check.
- Run an aggregate script once when it already includes the required build, type, lint, or test checks. Record which checks it covers instead of running its parts again.
- Show absent commands as `not-applicable`. Show deliberately unrun commands as `skipped` with a reason, including an unnecessary install or a check covered by an aggregate command.
- Reuse supplied prior evidence only through the shared selector and transfer protocol. Label its original command and evidence path; do not claim it ran in this invocation. A request for fresh runs requires fresh execution.
- Capture exit code, duration, and decisive output in a temporary evidence directory outside the project. Default per-check timeout is 15 minutes unless the caller supplies another ceiling.
- After success, repeat or expand only for changed content, failures, or unresolved concerns.

Capture the tracked working-tree baseline before execution and compare it afterward. `treeClean` describes the final tracked state; `treeChanged` describes changes introduced by verification. Preserve pre-existing changes. Never stash, reset, or clean the tree.

## Evidence and result

**Only captured command results count as evidence.** Never claim a check ran that
you did not run. A shared `run-check` result preserves actual stdout, stderr, exit
status, timeout, command definition, and source identity. Never modify tests,
source, lockfiles, or CI configuration to obtain a pass. Report failures for the
caller or `diagnose`.

Return shared result paths to the caller. Validation can place each result in a
scoped packet for the unit that owns its ID. After all required units pass, it
exports one complete packet for review. A human table and a generic pass status
remain context only; they cannot establish shared readiness.

Return the machine result matching `references/checks-schema.json`, a human table of commands and results, and a verdict:

- `PASS`: every selected required check has valid passing evidence.
- `FAIL`: an executed required check failed or timed out.
- `SKIP`: no check was verified, or a required check could not run and has no valid supplied evidence.

Name skipped work and the coverage limit. A partial check set is not proof that the whole repository passes. Keep long output in the evidence directory and only its decisive tail in the report.
