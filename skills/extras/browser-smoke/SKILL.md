---
name: browser-smoke
description: "Smoke-test the routes a branch or PR changes in a real browser. Use when the user asks to smoke-test a branch or PR, test affected pages, or run a diff-scoped browser test. It tests changed routes, not whole-product release QA."
argument-hint: "[PR number, branch name, 'current', or --port PORT]"
---

# Browser Smoke Test

Produce browser evidence for the routes a change can affect. This is a diff-scoped check. It does not repair code or replace release QA.

## Outcome

Result: a route table with captured browser evidence.

Done: every mapped route is Pass, Fail, or Skip with a reason. A run that exercises no route is `SKIP`, never `PASS`.

## Modes

1. Manual is the default. The user starts and controls the local server.
2. Pipeline is a non-interactive caller. Read `references/pipeline-orchestration.md` from this skill's directory. Do not ask questions in this mode.

## Workflow

### 1. Select one browser driver

Use the first available driver that can navigate, inspect rendered state, interact, and read console errors. Prefer the host browser surface, then the established browser automation available in the harness. Do not install a new browser stack.

Use one driver for the whole run. Switch only if initialization fails before the first route is tested. Record the driver in the result.

If no available driver meets this contract, stop with `SKIP` and name the missing capability.

### 2. Identify the changed routes

For a PR, get its changed files from the code host. Otherwise resolve the default branch in this order: local `origin/HEAD`, code-host metadata, then `main`. Diff the requested branch against that branch. When the request targets the current worktree, include staged and unstaged changes too.

Map each changed file to the routes that render it. Read the project's routing and component usage when the path alone is not enough. A layout or shared style change needs at least the root page and each directly affected route. A change with no browser-facing route is `SKIP` with that reason.

If the diff is empty, stop with `SKIP`. Do not report a pass for an empty scope.

### 3. Reach the local server

Select the port in this order: explicit `--port`, active project instructions, project server configuration, environment configuration, then `3000`.

In manual mode, check that the selected port is listening. If it is not, stop with `SKIP`, name the port and untested route count, and tell the user to start the documented local server command.

In pipeline mode, use the local procedure in `references/pipeline-orchestration.md`. Record the actual port it starts.

### 4. Exercise the routes

Open the root page first. Confirm that the server returns rendered content before testing mapped routes.

For each route, capture fresh state and check:

1. The page heading or title is present.
2. The primary content renders.
3. No visible application error or new console error is caused by the flow.
4. A changed form or interaction works when the diff affects it.

Derive targets from the current inspected state. Do not reuse stale element references or guess selectors. Capture a screenshot when a failure, changed visual surface, or later reviewer needs it.

For OAuth, email, payment, SMS, or another external action, ask the user for the required confirmation in manual mode. In pipeline mode, mark that route `Skip` and state the missing external action.

### 5. Record failures

For each failure, record the route, reproduction steps, rendered error, and relevant console output. Continue with independent routes.

Do not modify code during this skill. Route a repair request to `diagnose` or the active implementation workflow after the result is delivered.

### 6. Report

Return this table and a result:

| Route | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `/example` | Pass | Rendered state | Primary action completed |

Use `PASS` only when every exercised route passed. Use `FAIL` when a route failed. Use `PARTIAL` when some routes passed and others were skipped. Use `SKIP` when no route was exercised.

Name the tested scope, server URL, selected driver, console-error count, human confirmations, and untested routes. Never claim that a route passed without captured browser state.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
