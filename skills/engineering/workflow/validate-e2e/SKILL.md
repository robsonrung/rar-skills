---
name: validate-e2e
description: Validate a feature or implementation against a finite acceptance contract, from focused tests to complete user flows. Use for feature validation with evidence reuse, bounded repair, and selectable model routes; use verify-changes for named repository checks alone.
disable-model-invocation: true
---

# Validate E2E

Return evidence that the feature meets its **acceptance contract**: the finite requirements, observable behavior, failure cases, and runtime gates agreed for this run. Name the part of the contract that decided a result: "The contract requires the result to survive a reload, so a successful HTTP response is insufficient."

Keep progress in **the ledger, not the transcript**: the run's `validation/` folder beside the feature's tasks (`shared/references/work-state.md`) holds `plan.md`, `report.md`, and `evidence/`. Resume from it. `shared/` is `skills/shared/` in a source checkout and a sibling skill in a flat install.

## 1. Bound the feature

Confirm the repository, worktree, intended base, current diff including uncommitted changes, and environment. Inventory only changed surfaces, their direct callers, and named external interfaces. Record each requirement, operation, relevant variants, expected result, and the check and browser observation IDs that prove it. Keep the denominator finite: say whether "100%" means requirements, a closed operation inventory, or measured line or branch coverage with named thresholds. Timebox discovery; a missing source or policy becomes a named blocker, not a wider search.

Keep behavior, browser, security, migration, performance, and runtime gates separate. A source finding is not execution evidence, and a business pass never overrides a failed runtime gate.

Choose the mode. `assess` reports defects without touching product code. `repair` fixes them within named paths and needs a request to fix defects. Invocation already permits local test preparation, execution, and disposable fixtures; production writes, external messages, deployments, commits, and publication need their own authority.

Write `plan.md` after the inventory:

- the mode, scope, base, requirement IDs, and whether discovery is closed (an open inventory blocks an overall pass);
- the units: each with its requirements, whether it is required, its check and browser observation IDs, and its attempt limit;
- the roles, if any, and the ceilings: total attempts, role calls per route and in total, parallel workers, and a deadline. Propose 12 attempts, 12 role calls, 3 per role, 2 per unit, 2 workers, and 90 minutes as editable starting values. Repair allowances sit inside those totals.

Every requirement maps to a required unit. The ceilings bound what you start; they do not stop a running call, so they are not a spend cap.

## 2. Route workers only where needed

Build, lint, type checks, and existing suites run through repository commands with no model. A model is for a decision: missing tests, unsettled expected behavior, an ambiguous browser state, or an unexplained failure. When the work is command-only, the plan names no roles.

For a worker, resolve the route that fits with `python3 shared/scripts/model_routing.py resolve <route> [--risk high]`:

| Work | Route |
| --- | --- |
| Scope, requirement mapping, final evidence assessment | `validation-scope` |
| Missing unit, component, or property tests from agreed cases | `validation-unit` |
| API, database, queue, migration, integration, performance diagnosis | `validation-integration` |
| Interactive browser journeys, visual state, accessibility | `validation-browser` |
| Authorization, money, concurrency, data loss, complex root cause | `validation-risk` |
| Diagnosis and correction from a proven cause | `validation-diagnosis` |
| Independent assessment of evidence and missing cases | `validation-review` |

A strong role settles expected behavior before a cheaper role writes the tests. A browser worker needs real browser tools in its own process. The reviewer's model differs from any model that wrote the assertions.

Show the scope, each role with its model, effort, and host route, and the attempt, call, and time ceilings. Ask: **"Approve this plan, or specify changes."** A request to use defaults and run approves the unchanged resolved plan. Then route each role by host: T3 Code `delegate_task` (continue with `t3_thread_send`); Claude Code or Codex a native subagent; otherwise `cli-runner`, `pi-runner`, or `muse-runner`. Give each role one persistent context for the run. An unavailable route blocks its own work; never swap in another model.

## 3. Run the smallest sufficient checks

Read only the applicable rows of [references/test-methods.md](references/test-methods.md). Reuse evidence only when requirements, inputs, dependency versions, environment, and check definitions all match; a commit ID change alone does not invalidate it. A declared fresh check always runs.

Write each attempt into `report.md` before running it; a failed or interrupted attempt still counts. Run cheap relevant checks first, then the real integration and user flows the contract needs. Capture every command with `shared/scripts/capture_check.py run` into `evidence/`. A browser observation records its ID, result, and screenshot and trace paths; check browser access first and record it with `shared/scripts/browser_preflight.py record`; a blocked preflight consumes no attempt. A unit passes only when each of its checks has a current capture with the expected result. A prose pass does not execute a command or pass a unit.

Parallelize only independent work with isolated fixtures, accounts, ports, and browser contexts; one coordinator writes state. Keep full logs in files and read counts, failures, and paths.

## 4. Diagnose and repair within bounds

Classify each failure as product behavior, test harness, environment, runtime gate, or unresolved policy, with actual and expected values. Cascading failures from one setup error are one cause until evidence shows more. Use `diagnose` for an unknown cause, and never rerun an unchanged failure without a new hypothesis.

Allow two validation attempts per unit by default. Test, evidence, and product repair allowances are set in the plan and share its total attempt, call, and time limits; each retry records its reason. At a ceiling, stop and report the remaining work. Never start a new run, rename a unit, or weaken an assertion, exclusion, timeout, or diagnostic policy to reset counts or obtain a pass. A stronger model can resolve uncertainty; it cannot choose an unsettled product policy.

## 5. Close or checkpoint

On resume, find out what pending calls and attempts did before any retry. `passed` requires a closed inventory, every required unit passed with current captures of one tree, and no required failure, skip, pending call, or blocker. Otherwise report `failed`, `blocked`, `partial`, or `ceiling_hit`. Captures prove facts, not their meaning: get an independent review of the same tree before claiming readiness. Never describe a scoped pass as universal coverage.

Return:

1. Status, requirement and operation scope, tested revision and environment.
2. Required units passed out of total; failed, blocked, skipped, pending, and excluded units with reasons. Code coverage only from its actual report.
3. Checks run now, reused evidence, defects found, repairs made, and open policy decisions.
4. Each role's model, effort, and route, with call counts and usage when available; unknown stays unknown.
5. Plan, report, and evidence paths, the next bounded action, and remaining budget if incomplete.
