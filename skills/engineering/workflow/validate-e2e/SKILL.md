---
name: validate-e2e
description: Validate a feature or implementation against a finite acceptance contract, from focused tests to complete user flows. Use for feature validation with evidence reuse, bounded repair, and selectable model routes; use verify-changes for named repository checks alone.
disable-model-invocation: true
---

# Validate E2E

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Return evidence that the requested feature meets its **acceptance contract**: the finite requirements, observable behavior, failure cases, and required runtime gates agreed for this run. Say which contract changed a decision, for example: “The acceptance contract requires a saved result after reload, so a successful HTTP response is insufficient.”

Keep progress in **the ledger, not the transcript**. Use the collection's `shared/` library: in a source checkout it is `skills/shared/`; in a flat installation it is a sibling skill. Resolve all script paths from the loaded skill directories. A missing shared library blocks dependent work.

## 1. Bound the feature

Reuse current requirements, project rules, implementation reports, and valid evidence. Confirm the repository, worktree, intended base, current diff including uncommitted changes, and environment. Resolve discoverable facts directly.

Create `validation-plan.json` in a unique run directory outside source, build, and dependency scan roots. Read [references/run-control.md](references/run-control.md) for its contract and commands. Inventory only changed surfaces, their direct callers, and named external interfaces. Record each requirement, unique operation, relevant variants, expected result, and required check IDs. Tables and shared effects are links to operations, not additional operation counts.

A source finding is not execution evidence. Keep source discovery, behavior, browser, security, migration, performance, and runtime gates separate. State whether requested “100%” means requirement coverage, a closed operation inventory, or measured line/branch coverage with explicit files and thresholds. An unknown denominator stays unknown. Timebox unresolved discovery; turn a specific missing source or policy into a blocker. Never widen the search to unspecified external systems.

Invocation permits local test preparation, execution, and disposable fixtures within the user's existing authority. Product repair requires a request to fix defects or prior repair authority. Record `assess` or `repair` and allowed paths. Production writes, external messages, deployments, commits, and publication need their own authority. Reuse authorization; do not add phase approvals for ordinary local checks.

## 2. Let the user select the routes

Read [references/model-selection.md](references/model-selection.md). Resolve only applicable `validation-*` routes from `shared/model-routing.json` with `--profile default` and any validated `--local-profile`, unless the user selects an explicit profile or legacy family. It is the only maintained source of model and effort defaults. Deterministic tests run through repository tools without a separate model worker. Distinguish test design and diagnosis from test execution.

Before proposing worker models for a new run, execute the `preview-models` command in [references/model-selection.md](references/model-selection.md) for the applicable routes. Show the resolved profile and each route's model and effort from that output. Keep the configuration path and digest in the plan so the loaded installation can be identified. Do not infer worker choices from the coordinator model, session effort, available native model list, or previous conversation. A missing external runner is an availability blocker for the recommended route, not a reason to omit that route or silently replace it. If preview resolution fails, report the failure instead of inventing defaults. A saved approved plan still controls a resume.

Use the shared preview for scope, test classes, actual coordinator, exact worker models, efforts, native or runner paths, browser driver access, privacy controls, receipt limits, and ceilings. A request to “use defaults and run” permits the unchanged resolved setup within existing source sharing authority and accepted receipt limits; show it and proceed. Otherwise obtain the existing plan decision after the plan is reviewable. Nested skills reuse the selected snapshot. Keep useful read-only planning moving. Silence is not approval.

Save the exact selected routes, provider controls, capabilities, tool policy, fallback triggers, limits, and user decision reference. Reuse this snapshot on resume; do not reread local preferences. An explicit override before dispatch creates a replacement snapshot for unresolved work only. An unavailable route blocks only its work; never silently substitute a model, effort, transport, or verification policy. Model changes or increases beyond the approved total budget need a new decision. Use approved recovery categories within their existing allowance without another question. No model research or availability probe loop is required during normal validation; use the dated research only when selecting or updating routes.

## 3. Run the smallest sufficient checks

Read only the applicable rows in [references/test-methods.md](references/test-methods.md). Reuse evidence when its requirement, inputs, dependency versions, environment, and checks still match. Record reuse explicitly. A commit ID change alone is not invalidation. Required fresh checks still run.

Use [references/run-control.md](references/run-control.md) to initialize limits and reserve each test attempt before execution. A repeated reservation is for reconciliation, not another execution. For model work, also reserve each role turn through the shared call ledger. Apply command timeouts and a host deadline. Stop new work at a ceiling; record remaining work instead of starting a new run to reset counts.

Run cheap relevant checks first, then the real integration and user flows needed by the contract. Combine independent reads and commands. Parallelize only authorized independent work with isolated fixtures, accounts, ports, browser contexts, and write ownership. One coordinator writes shared state. A new worker needs a concrete gap that offsets its context and coordination cost; use at most two concurrent workers by default. Do not create user owned tasks without the host's required authorization.

Give workers the requirement, relevant source locators, expected evidence, allowed actions, route, and remaining budget. Keep implementer and reviewer contexts separate. Reuse each role for its own followups. Review changed assertions and semantic deltas once; deterministic comparisons establish unchanged control bytes. Keep full logs in files and return counts, failures, changed facts, and paths. Use wait cursors and bounded waits; inspect unchanged output only when needed for a decision.

## 4. Diagnose and repair within bounds

Classify a failure as product behavior, test harness, environment, runtime gate, or unresolved policy. Capture actual versus expected values and the relevant revision. Cascading failures from one setup or observer error are one cause until evidence proves more.

Use `diagnose` only for an unknown cause. Use the cheapest discriminating probe; retain a sufficient reproduction. Do not rerun an unchanged failure without a new hypothesis or changed input. Before a repair, preserve the failing case. In repair mode, fix within scope, then rerun affected cases and required gates. In assess mode, report the defect without changing product code.

Allow two validation attempts per unit by default. Include any test repair, evidence repair, and authorized product repair allowances in the initial plan. They share the total attempt, call, and time limits. Record a reason and changed input or new evidence for each retry. Record driver and service preflight separately before a business attempt. A separate diagnostic unit needs a bounded question and consumes the same total budget. At exhaustion report the unresolved defect or blocker. A stronger model can resolve uncertainty; it cannot select an unsettled product policy.

Preserve tenant isolation, transaction rollback, event checks, native diagnostics, process exit, and cleanup gates when required. Business passes do not override a failed runtime gate. Do not weaken assertions, exclusions, timeouts, or diagnostic policy to obtain a pass. Finish source, build, and report writers before capturing a runtime seal. Keep per file hashes so drift can be located without reconstructing old outputs.

## 5. Close or checkpoint

Reconcile pending calls and test attempts before any retry after interruption. Resume from current unit, counters, route snapshot, and evidence references. Reload instructions only when missing from context or changed. Read the compact ledger and changed evidence, not complete transcripts or all historical preparations.

Use the controller summary. `passed` requires a closed inventory, every required unit passed with intact evidence, and no required failure, skip, pending call, or unresolved blocker. Report `failed`, `blocked`, `partial`, or `ceiling_hit` otherwise. Never describe a scoped pass as universal coverage.

Return:

1. Status, requirement and operation scope, tested revision and environment.
2. Required units passed/total; failed, blocked, skipped, pending, and excluded units with reasons. Give code coverage only from its actual report.
3. Checks run now, reused evidence, defects found, repairs made, and remaining policy decisions.
4. Actual model/effort/transport and receipt limits; total parent and worker calls, input, cached input, output, elapsed time, and cost when available. Keep unknown fields unknown and goal counters separate from billed use.
5. Report and ledger paths, the next bounded action, and remaining budget if incomplete.

Use [references/model-research.md](references/model-research.md) only when explaining or refreshing the selection. Offline contract checks do not prove model quality or token savings. Evaluate savings per accepted feature, including failed attempts and review, before making a performance claim.
