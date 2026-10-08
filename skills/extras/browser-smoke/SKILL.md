---
name: browser-smoke
description: "Smoke-test the routes a branch or PR changes in a real browser. Use when the user asks to smoke-test a branch or PR, test affected pages, or run a diff-scoped browser test. It tests changed routes, not whole-product release QA."
argument-hint: "[PR number, branch name, 'current', or --port PORT]"
---

# Browser Smoke Test

Run an existing browser suite or declared browser driver directly. A direct
browser branch does not load a model preview. Before dispatching a browser worker,
use `shared/references/model-preview.md` and bind one exact approved snapshot to
the worker request, reservation, privacy controls, and report. Nested calls reuse
that snapshot and do not add workers.

Produce browser evidence for the routes a change can affect. This is a diff-scoped check. It does not repair code or replace release QA.

## Outcome

Result: a route table with captured browser evidence.

When the caller uses `shared/references/review-evidence.md`, save actual driver
output or screenshots for each required observation. Use the same observation
shape in browser smoke, validation, and review:

```json
{
  "id": "checkout",
  "result": "pass",
  "evidence": [
    {"path": "/absolute/run/checkout.png", "sha256": "<SHA256>"}
  ]
}
```

`id` must be declared by the prepared requirements. `result` is `pass`, `fail`,
or `skipped`. Every row has one or more absolute hashed artifacts. Capture a skip
reason in its driver output or other evidence file; do not add fields to the
shared row. The shared verifier checks files and the declared observed result. It
does not repeat browser actions. A skipped required observation prevents readiness.

Done: every mapped route is Pass, Fail, or Skip with a reason. A run that exercises no route is `SKIP`, never `PASS`.

## Modes

1. Pipeline is the default for an authorized implementation or validation workflow. Start owned local services through `references/pipeline-orchestration.md`. Reuse existing authority.
2. Use manual mode when the user explicitly controls the server or the request is observation only. Reuse an available server. Missing credentials or desktop access block only the affected routes.

## Workflow

### 1. Select one browser driver

Reuse the target project's working browser stack when it meets the evidence
contract. Existing browser commands run directly. A worker branch selects the
mechanism in its exact approved snapshot by required capabilities and actual worker
access:

| Mechanism | Select when |
| --- | --- |
| Playwright Test | A repeatable acceptance or regression suite already exists, including CI. Run it directly without a separate model worker. |
| Playwright CLI with its skill | First candidate for interactive exploration, locator inspection, or test creation and repair when installed and ready. This is distinct from running Playwright Test. |
| agent-browser | Supported exploration alternative after readiness succeeds in the selected worker environment. |
| Playwright MCP | Its structured tool interface or page inspection is required. Do not load it into every worker. |
| Native host browser | An authenticated session, native dialog, or host capability is required and available to the selected worker. |
| Raw Playwright library | The project already uses a small script or harness that meets the required evidence contract. |

Do not install a new browser stack. Missing commands or browser binaries are preparation gaps. Record the selected mechanism, version, and missing capability before selecting a different driver. For an external Pi browser route, bind `browser: {mechanism, preflight: {path, sha256}}` to the selection; the referenced file must contain actual readiness evidence. Use one driver per journey. Isolate sessions, browser contexts, fixtures, and accounts for parallel workers; close only resources owned by this run.

An external Pi worker does not inherit host browser tools. Preflight navigation, current state inspection, interaction, assertions, console/network capture, and artifact output from that process. Supply its driver's instructions and actual command access. Read-only analysis mode cannot run browser commands; use an explicitly selected browser tool policy within existing authority. Shell access is not a sandbox and does not authorize product repairs.

For visual work, verify model image support and the driver's screenshot path. Load a synthetic image with Pi's image reader or attachment path and capture a typed image payload through the selected adapter before sending repository material. A path or description in plain text is insufficient. Keep the route blocked when driver, tools, images, or required privacy controls fail preflight.

For external Playwright CLI or agent-browser readiness, use the shared
`browser_preflight.py` helper after observing the capability checks. Supply a JSON
object with actual booleans for `navigation`, `state_inspection`, `interaction`,
`assertions`, and `evidence_capture`, plus captured artifacts:

```bash
SHARED_DIR="<absolute shared skill directory>";
python3 "$SHARED_DIR/scripts/browser_preflight.py" record \
  --mechanism <playwright-cli-or-agent-browser> --working-dir <project-root> \
  --checks <observed-checks.json> --evidence <captured-artifact> \
  --output <preflight.json>
```

Repeat `--evidence` for multiple artifacts. The helper records prior observations
and checks driver version and identity; it does not execute a journey. Verify
the saved `{mechanism, preflight}` object with `verify --route <browser-route.json>
--working-dir <project-root>`. A version check alone cannot establish readiness.
Image payload and privacy checks remain separate requirements.

Initialize the selected driver before reserving a business test attempt. Capture its actual readiness result. A locked desktop is an environment blocker, not an executed test. Resume under the approved recovery allowance when access returns. Use a headless transport only when supported and authorized by the plan. Keep the selected driver for each journey unless an exact approved fallback applies. Driver recovery retains the original run budget.

If no available driver meets this contract, stop with `SKIP` and name the missing capability.

### 2. Identify the changed routes

Reuse the explicit caller base and the approved source snapshot's base first. When both exist, require agreement on the resolved commit and intended comparison scope; a mismatch or an unresolvable supplied base is a scope blocker, not a reason to use the default. Without either, use the PR's target base from the code host; for other requests, resolve local `origin/HEAD`, code-host metadata, then `main`. Record the selected ref, resolved commit, selection source, and supplied snapshot reference in the run report with the browser evidence. Keep base metadata outside shared observation rows; their fields remain `id`, `result`, and `evidence`. Diff the requested branch against that base. For a current-worktree request, include committed, staged, and unstaged changes, even when a PR diff is available. Prepare a new snapshot if those edits change the approved source scope.

Map each changed file to the routes that render it. Resolve the actual URL from project routing before dispatch; do not infer a route from a component name. A layout or shared style change needs at least the root page and each directly affected route. A change with no browser-facing route is `SKIP` with that reason.

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

Derive targets from current accessibility state. Prefer role, label, or stable
test ID locators with automatic waits and observable assertions. For an edit, clear
the field and read back the exact value before saving. Capture the request and
response before navigation or reload. Verify the saved value after reload. Use the
supported driver to script stable repeated actions, with assertions at each state
change. Capture screenshots for visual evidence and failures; do not return image
bytes as text.

For a shared snapshot, map every required flow to its declared observation ID and
write the exact observation row above. A route table can summarize the flow, but it
does not replace that row. Put that row in the scoped packet for the validation
unit that owns its ID. A changed observation input, runtime identity, or required
browser context needs a fresh observation. Keep the capture that explains a fail or
skip as evidence; a later passing retry does not erase it.

For OAuth, email, payment, SMS, or another external action, use existing explicit authority. If required authority or a human action is missing, ask in manual mode. In pipeline mode, mark only the affected route `Skip` and state the missing action.

### 5. Record failures

For each failure, record the route, reproduction steps, rendered error,
screenshots, relevant console output, network failures, and traces under the
project test policy. Keep the original failure and any later passing retry; a retry
does not erase flakiness. Continue with independent routes.

Do not modify code during this skill. Route a repair request to `diagnose` or the active implementation workflow after the result is delivered. Recommend stable, important discovered flows for the existing test suite; authoring those tests belongs to the authorized implementation or validation scope.

### 6. Report

Return this table and a result:

| Route | Status | Evidence | Notes |
| --- | --- | --- | --- |
| `/example` | Pass | Rendered state | Primary action completed |

Use `PASS` only when every exercised route passed. Use `FAIL` when a route failed. Use `PARTIAL` when some routes passed and others were skipped. Use `SKIP` when no route was exercised.

Name the selected base and resolved commit, tested scope, server URL, selected driver, console-error count, human
confirmations, and untested routes. Return each shared observation row and its
evidence path with the table. Never claim that a route passed without captured
browser state.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
