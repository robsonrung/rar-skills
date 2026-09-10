---
name: verify-changes
description: "Run a repository's deterministic checks from its own command surface. Use when the user asks to verify a branch, run repository checks, or prove that build and tests pass. It captures command evidence, does not repair code, and does not replace browser testing."
---

# Verify Changes

Produce captured evidence for the repository's required gates and the requested change. Discover commands, select the relevant checks, run their actual prerequisites, and report results. This skill does not repair code.

## Modes

- **Manual:** honor the user's requested check set. An explicit request for all checks runs every required gate; otherwise select the affected checks and applicable repository gates.
- **Pipeline (`mode:pipeline`):** use the caller's scope and acceptance contract without questions. Return the structured result from `references/checks-schema.json` and one verdict. Required repository gates still apply.

## Discover and scope

Read [references/command-discovery.md](references/command-discovery.md). Prefer the repository's named scripts and read-only CI configuration over reconstructed commands. Record detected build systems and command sources in `commandSurface`.

Resolve the base from `origin/HEAD`, code-host metadata, then `main`. Include staged and unstaged changes for the current worktree. Use native affected-package support when available. Without it, identify safe package or file checks from the repository's commands; use whole-repository checks when required or when a narrower valid check is unavailable. Record `workspacesScoped.supported: false` when native scoping is absent.

## Execute the selected checks

When the caller supplies a snapshot from `shared/references/review-evidence.md`,
execute its checks through `shared/scripts/review_evidence.py run-check`. Return
captured result paths with the normal check report. Reuse an older captured check
only when the shared validator accepts its source, context, and command definition.
A prose pass is insufficient. If discovery reveals a missing requirement, update
the plan and prepare a new snapshot before execution. Never edit a frozen record.

- Follow real command dependencies. Build first only when later checks require its output. Install only when dependencies need preparation or the requested clean-environment check requires it.
- Use the repository's lockfile-respecting install command. Do not modify lockfiles or install global tools to invent a check.
- Run an aggregate script once when it already includes the required build, type, lint, or test checks. Record which checks it covers instead of running its parts again.
- Show absent commands as `not-applicable`. Show deliberately unrun commands as `skipped` with a reason, including an unnecessary install or a check covered by an aggregate command.
- Reuse supplied prior evidence only when the relevant revision, files, dependencies, environment, and assumptions still match and the caller permits reuse. Label its original command and evidence path; do not claim it ran in this invocation. A request for fresh runs requires fresh execution.
- Capture exit code, duration, and decisive output in a temporary evidence directory outside the project. Default per-check timeout is 15 minutes unless the caller supplies another ceiling.
- After success, repeat or expand only for changed content, failures, or unresolved concerns.

Capture the tracked working-tree baseline before execution and compare it afterward. `treeClean` describes the final tracked state; `treeChanged` describes changes introduced by verification. Preserve pre-existing changes. Never stash, reset, or clean the tree.

## Evidence and result

**Only captured command results count as evidence.** Never claim a check ran that you did not run. Never modify tests, source, lockfiles, or CI configuration to obtain a pass. Report failures for the caller or `diagnose`.

Return the machine result matching `references/checks-schema.json`, a human table of commands and results, and a verdict:

- `PASS`: every selected required check has valid passing evidence.
- `FAIL`: an executed required check failed or timed out.
- `SKIP`: no check was verified, or a required check could not run and has no valid supplied evidence.

Name skipped work and the coverage limit. A partial check set is not proof that the whole repository passes. Keep long output in the evidence directory and only its decisive tail in the report.
