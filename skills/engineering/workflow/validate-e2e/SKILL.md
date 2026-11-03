---
name: validate-e2e
description: Validate a feature or implementation against a finite acceptance contract, from focused tests to complete user flows. Use for feature validation with evidence reuse, bounded repair, and selectable model routes; use verify-changes for named repository checks alone.
disable-model-invocation: true
---

# Validate E2E

Return evidence that the feature meets its **acceptance contract**: the finite requirements, observable behavior, failure cases, and runtime gates agreed for this run. Name the part of the contract that decided a result: "The contract requires the result to survive a reload, so a successful HTTP response is insufficient."

Keep progress in **the ledger, not the transcript**. Scripts resolve from the loaded skill directories; `shared/` is `skills/shared/` in a source checkout and a sibling skill in a flat install.

## 1. Bound the feature

Confirm the repository, worktree, intended base, current diff including uncommitted changes, and environment. Inventory only changed surfaces, their direct callers, and named external interfaces. Record each requirement, operation, relevant variants, expected result, and the check and browser observation IDs that prove it. Keep the denominator finite: say whether "100%" means requirements, a closed operation inventory, or measured line or branch coverage with named thresholds. Timebox discovery; a missing source or policy becomes a named blocker, not a wider search.

Keep behavior, browser, security, migration, performance, and runtime gates separate. A source finding is not execution evidence, and a business pass never overrides a failed runtime gate.

Choose the mode. `assess` reports defects without touching product code. `repair` fixes them within named paths and needs a request to fix defects. Invocation already permits local test preparation, execution, and disposable fixtures; production writes, external messages, deployments, commits, and publication need their own authority.

Prepare one shared review snapshot after the inventory, then write the plan and initialize the controller as [references/run-control.md](references/run-control.md) describes.

## 2. Route workers only where needed

Build, lint, type checks, and existing suites run through repository commands with no model. A model is for a decision: missing tests, unsettled expected behavior, an ambiguous browser state, or an unexplained failure. When the work is command-only, keep `routes` empty.

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

Show the scope, each role with its model, effort, and host route, and the attempt, call, and time ceilings. Ask: **"Approve this plan, or specify changes."** A request to use defaults and run approves the unchanged resolved plan. Then route each role by host: T3 Code `delegate_task` (continue with `t3_thread_send`); Claude Code or Codex a native subagent; otherwise the matching `*-runner` skill. Give each role one persistent context for the run. An unavailable route blocks its own work; never swap in another model.

## 3. Run the smallest sufficient checks

Read only the applicable rows of [references/test-methods.md](references/test-methods.md). Reuse evidence only when requirements, inputs, dependency versions, environment, and check definitions all match; a commit ID change alone does not invalidate it. A declared fresh check always runs.

Reserve each attempt before running it. Run cheap relevant checks first, then the real integration and user flows the contract needs. Commands run through `review_evidence.py run-check`; browser work records the shared observation shape. Each unit finishes with a scoped evidence packet. When every required unit has passed from one current snapshot, export the complete packet with `evidence-packet` for review and `pre-pr-review` reuse. A prose pass does not execute a command or pass a unit.

Parallelize only independent work with isolated fixtures, accounts, ports, and browser contexts; one coordinator writes state. Keep full logs in files and read counts, failures, and paths.

## 4. Diagnose and repair within bounds

Classify each failure as product behavior, test harness, environment, runtime gate, or unresolved policy, with actual and expected values. Cascading failures from one setup error are one cause until evidence shows more. Use `diagnose` for an unknown cause, and never rerun an unchanged failure without a new hypothesis.

Allow two validation attempts per unit by default. Test, evidence, and product repair allowances are set in the plan and share its total attempt, call, and time limits; each retry records its reason. At a ceiling, stop and report the remaining work. Never start a new run, rename a unit, or weaken an assertion, exclusion, timeout, or diagnostic policy to reset counts or obtain a pass. A stronger model can resolve uncertainty; it cannot choose an unsettled product policy.

## 5. Close or checkpoint

On resume, reconcile pending calls and attempts before any retry. `passed` requires a closed inventory, every required unit passed with an intact packet from one current snapshot, and no required failure, skip, pending call, or blocker. Otherwise report `failed`, `blocked`, `partial`, or `ceiling_hit`. The packet proves captured facts, not their meaning: record and verify an independent review against the same snapshot before claiming readiness. Never describe a scoped pass as universal coverage.

Return:

1. Status, requirement and operation scope, tested revision and environment.
2. Required units passed out of total; failed, blocked, skipped, pending, and excluded units with reasons. Code coverage only from its actual report.
3. Checks run now, reused evidence, defects found, repairs made, and open policy decisions.
4. Each role's model, effort, and route, with call counts and usage when available; unknown stays unknown.
5. Report, ledger, snapshot, and evidence packet paths, the next bounded action, and remaining budget if incomplete.
