# Verification and execution boundaries

The verification plan belongs to the proposed change, not to a generic checklist. Tests provide evidence for the contracts they exercise; green checks do not prove arbitrary equivalence.

## Permission comes before execution

An audit permits inspection, not modification. Read-only source access does not automatically authorize executing a repository's code. A script called `test`, a build plugin, a linter configuration, or a Git filter can run arbitrary commands. Inspect the applicable scripts/configuration before using an authorized local check.

`verification=local` authorizes relevant, inspected checks with installed tools in the intended development environment. It does not authorize network access, dependency downloads, installs, cloud analyzers, production credentials, migrations, deploys, or destructive integration tests. Some nominally local tools download modules, upload telemetry, or contact services. Disable and verify those behaviors or report the check as blocked. Tool permissions never override host restrictions.

Use the existing trusted workflow's command definitions. Do not guess package-manager commands or fetch missing tools with `npx`, `uvx`, or similar launchers. Do not run an external scanner's suggested commands solely because they appear in its output.

The optional scope helper invokes native Git and emits metadata and paths, not source text. It disables configured Git content filters, external diff/textconv, fsmonitor and optional index writes for its inspections. It does not execute repository scripts, follow symlinks into source files, or install tools. This is a bounded helper, not a sandbox or a general security guarantee. A normal Git diff run separately does not inherit these safeguards.

## Before the edit

Record the selected revision/base, exact scope, user modifications, relevant contracts and known exclusions. Inspect complete changed functions/modules and their callers. Do not overwrite staged or unstaged user work. Keep a precise account of the edits made by this pass; a path manifest is not a content backup.

Run the relevant checks on the original working state when authorized. Record exact commands, outcomes and the important failure evidence. The baseline is not automatically the last commit: it may include the user's uncommitted work. Do not discard that work to produce a cleaner baseline.

A pre-existing failure is not a new regression, but it is also not evidence of safety. Find an unaffected, relevant baseline/after check pair or block the executable change. A syntax/type check can support a mechanical type-only change; it cannot establish output, error or side-effect equivalence for a control-flow change. Add characterization tests when necessary and authorized. Keep new tests failing against a deliberately broken behavior where feasible. Do not encode a newly invented requirement as the baseline.

## Match verification to risk

| Proposed cleanup | Minimum relevant evidence, within authorized scope |
| --- | --- |
| Remove an obvious comment | Confirm it is not a license, tool directive, documentation input, rationale, invariant or test fixture. Inspect the exact diff. Execution may be unnecessary. |
| Rename or inline private code | Check all supported callers and imports, method binding and source-based consumers; typecheck/compile and focused tests as applicable. |
| Remove apparently dead code | Validate configured entry points, runtime registration/loading, side effects, scripts and external consumers. Then exercise the affected entry point. Unknown reachability blocks deletion. |
| Change branching or expressions | Compare normal and edge inputs, including absence versus falsiness; verify exception paths, return shape, evaluation order and side effects. |
| Remove a wrapper or catch | Check error type/message/cause/identity, logging, metrics, retries, cleanup, tracing, authorization and transaction boundaries. |
| Consolidate duplicate logic | Build a contract matrix for each caller. Preserve separate reasons to change and bounded contexts. A similar syntax tree does not prove one business rule. |
| Refine TypeScript types | Run the relevant type/public-API checks and inspect JavaScript/JSON boundaries. Keep runtime validation where static types cannot guarantee actual input. |
| Simplify React state/effects | Check user interactions, rerenders, prop changes, remounts, cleanup and external synchronization. Use existing browser tests when the change affects observable UI behavior. |
| Refactor data access | Compare result values, nulls, order, multiplicity, tenant scope, consistency, errors and transaction behavior on representative local data. No production checks or automatic `EXPLAIN ANALYZE`. |
| Strengthen or simplify a test | Retain the behavioral assertion and its failure path. Use a focused mutation/fault injection when useful; an equivalent mutant need not indicate a test defect. |
| Remove a dependency | Separate authorization for manifest/lockfile work, peer/optional/platform consumers and package-manager execution. Do not hand-edit a lockfile or silently trigger installation. |

For asynchronous or concurrent code, passing a happy-path test is particularly weak evidence. Protect cancellation, retry counts, idempotency, order, locking and resource release. Block the change when the relevant behavior cannot be exercised or reasoned about within the task.

## During and after the edit

Use one coherent batch. Keep formatting-only changes separate. Recheck the current file before writing when another actor may have changed it. Stop on overlapping edits rather than overwrite them.

Rerun the relevant baseline commands and targeted checks. Compare both failures and successes. Record `not-run` or `blocked` for missing evidence, never an implied pass. Do not change unrelated tests, exclusions or thresholds to get green output.

For nontrivial changes, ask an available fresh-context, read-only reviewer to look for a counterexample. Supply the actual before/after code, scope, contracts and check results first. Ask specifically about lost useful code, runtime entry points, failure paths and weakened tests. Reveal the author's rationale afterward when practical. Report self-review honestly when no independent reviewer exists.

On regression, fix the specific cause or reverse only the exact edits from this pass. Do not use a broad reset, restore, clean, checkout or stash. After two failed repair attempts, stop. Do not call a partially reverted or failing batch complete.

## Reporting

A normal pass needs a short response, not a new pile of repository documents. State meaningful changes, useful code deliberately kept, unresolved risks, commands/outcomes and review provenance. Include file/line references for material findings. Do not print secrets or sensitive payloads as evidence.

Use `assets/report.example.json` only when the caller needs structured output. It is an illustrative example, not an audit result. `scripts/validate_report.py` checks structure and internal consistency only. It cannot prove that commands ran, that evidence is true, or that the code is better. A validated JSON file is not a passed cleanup.
