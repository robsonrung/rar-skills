---
name: browser-smoke
description: "Smoke-test the routes a branch or PR changes in a real browser. Use when the user asks to smoke-test a branch or PR, test affected pages, or run a diff-scoped browser test. It tests changed routes, not whole-product release QA."
argument-hint: "[PR number, branch name, 'current', or --port PORT]"
---

# Browser Smoke Test

Produce browser evidence for the routes a change can affect. This is a diff-scoped check: it does not repair code or replace release QA. Run the project's browser suite or a browser driver directly; no model is dispatched.

Done means every mapped route is Pass, Fail, or Skip with a reason. A run that exercises no route is `SKIP`, never `PASS`.

## Modes

- **Pipeline** (default inside an authorized implementation or validation workflow): start owned local services through [pipeline-orchestration.md](references/pipeline-orchestration.md), within the authority the caller already has.
- **Manual**, when the user controls the server or asked only for observation: reuse a running server. Missing credentials or desktop access block only the affected routes.

## 1. Select one driver

Reuse the project's browser stack; never install one. A missing command or browser binary is a preparation gap.

| Driver | Select when |
| --- | --- |
| Playwright Test | A repeatable suite already exists. Run it directly. |
| Playwright CLI | Interactive exploration, locator inspection, or test repair, when installed. |
| agent-browser | An exploration alternative, once ready. |
| Playwright MCP | Its structured page inspection is required. |
| Native host browser | An authenticated session, native dialog, or host capability is required. |
| Raw Playwright library | The project already has a small harness. |

Use one driver per journey and capture its readiness before the first route; a locked desktop is an environment blocker, not a test result. Parallel journeys get isolated sessions, fixtures, and accounts; close only what this run opened. If no driver works, stop with `SKIP` and name the missing capability.

## 2. Map the changed routes

Use the caller's base, else the PR's target base, else `origin/HEAD`, code-host metadata, then `main`; a supplied base that does not resolve is a scope blocker. Record the ref and commit. A current-worktree request includes staged and unstaged changes.

Map each changed file to the routes that render it, resolving actual URLs from the project's routing; never infer a route from a component name. A layout or shared style change needs the root page and each directly affected route. A change with no browser-facing route is `SKIP` with that reason. An empty diff is `SKIP`.

## 3. Reach the server

Select the port in this order: explicit `--port`, project instructions, project server configuration, environment configuration, then `3000`.

In manual mode, check that the port is listening. If not, stop with `SKIP`, name the port and the untested route count, and tell the user the documented start command. In pipeline mode, follow pipeline-orchestration.md and record the port it starts.

## 4. Exercise the routes

Open the root page first and confirm it returns rendered content. Then, for each route, capture fresh state and check:

1. The page heading or title is present.
2. The primary content renders.
3. The flow causes no visible application error and no new console error.
4. A changed form or interaction works, when the diff affects one.

Prefer role, label, or test-ID locators with automatic waits. For an edit, capture the request and response and verify the saved value after reload. Save screenshots as files.

For OAuth, email, payment, SMS, or another external action, use only authority that already exists. When authority or a human step is missing, ask in manual mode; in pipeline mode mark that route `Skip` with the missing action.

When the caller names observation IDs, record each required flow under its ID with its result and its screenshot and trace paths, in the caller's `evidence/` folder (`shared/references/work-state.md`). A route table summarizes; it does not replace the row.

## 5. Record failures

For each failure, record the route, reproduction steps, rendered error, screenshots, console output, network failures, and traces. Keep the original failure next to any later passing retry; a retry does not erase flakiness. Continue with independent routes.

Do not modify code here; route a repair to `diagnose` or the active implementation workflow, and recommend stable, important flows for the test suite.

## 6. Report

| Route | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `/example` | Pass | Rendered state | Primary action completed |

The result is `PASS` only when every exercised route passed, `FAIL` when any route failed, `PARTIAL` when some routes passed and others were skipped, and `SKIP` when no route was exercised.

Name the base and commit, server URL, driver, console-error count, human confirmations, untested routes, and any observation rows. Never claim a route passed without captured browser state.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
