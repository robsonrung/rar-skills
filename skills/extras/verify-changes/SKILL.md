---
name: verify-changes
description: "Run a repository's deterministic checks from its own command surface. Use when the user asks to verify a branch, run repository checks, or prove that build and tests pass. It captures command evidence, does not repair code, and does not replace browser testing."
---

# Verify Changes

Produce captured evidence for the repository's required gates and the requested change: discover the commands, select the relevant checks, run their real prerequisites, and report. This skill runs commands directly and dispatches no model. It does not repair code.

## Modes

- **Manual:** honor the user's requested check set. A request for all checks runs every required gate; otherwise select the affected checks and the applicable repository gates.
- **Pipeline (`mode:pipeline`):** take the caller's scope and acceptance contract without questions. Return the structured result from [checks-schema.json](references/checks-schema.json) and one verdict. Required repository gates still apply.

## Discover and scope

Read [command-discovery.md](references/command-discovery.md). Prefer the repository's named scripts and read-only CI configuration over reconstructed commands, and record the detected build systems and command sources in `commandSurface`.

Use the caller's base when supplied; if the caller also passes an evidence snapshot, the two must resolve to the same commit, and a mismatch blocks affected checks until corrected. Otherwise resolve `origin/HEAD`, code-host metadata, then `main`. Save the selected ref, resolved commit, and where it came from in `scope.json` inside `evidenceDir`, and name that path in the report; keep it out of the schema result. For the current worktree, include committed, staged, and unstaged changes. Use native affected-package support when available; otherwise pick safe package or file checks from the repository's own commands, and fall back to whole-repository checks when no narrower valid check exists. Record `workspacesScoped.supported: false` when native scoping is absent.

## Execute

When the caller supplies an evidence snapshot, run only its declared checks through `shared/scripts/review_evidence.py` (`select-checks`, then act on each decision: run with `run-check`, reuse the captured result, or assess with `transfer-check`), as `shared/references/review-evidence.md` describes. The snapshot is the scope contract; a missing requirement means a new snapshot, never an edited one.

- Follow real command dependencies. Build first only when later checks need its output. Install only when dependencies need preparation or a clean-environment check was requested.
- Use the lockfile-respecting install command. Never modify lockfiles or install global tools to invent a check.
- Run an aggregate script once when it already covers build, type, lint, or test, and record what it covers instead of rerunning its parts.
- Absent commands are `not-applicable`. Deliberately unrun commands are `skipped` with a reason.
- Prior evidence counts only through the shared selector and transfer rules. Label its original command and path; never claim it ran in this invocation. A request for fresh runs gets fresh runs.
- Capture exit code, duration, and decisive output in a temporary evidence directory outside the project. The default per-check timeout is 15 minutes unless the caller sets another.

Capture the tracked working-tree state before and after. `treeClean` describes the final tracked state; `treeChanged` describes changes verification introduced. Preserve pre-existing changes; never stash, reset, or clean the tree.

## Evidence and result

**Only captured command results count as evidence.** Never claim a check ran that you did not run. Never modify tests, source, lockfiles, or CI configuration to obtain a pass; report failures to the caller or to `diagnose`.

Return the machine result matching `checks-schema.json`, a human table of commands and results, and a verdict:

- `PASS`: every selected required check has valid passing evidence.
- `FAIL`: an executed required check failed or timed out.
- `SKIP`: no check was verified, or a required check could not run and has no valid supplied evidence.

Name the selected base and its scope record, the skipped work, and the coverage limit. A partial check set is not proof that the whole repository passes. Keep long output in the evidence directory and only the decisive tail in the report.
