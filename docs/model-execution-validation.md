# Model execution validation

Checked 20 September 2026. The repository implements the approved
[model execution design](model-execution-update-proposal.md). Installed skill
copies outside this repository were not changed.

## Delivered behavior

Economy is the workflow default. The central catalogue selects GLM High for
bounded implementation, test authorship and browser exploration, with independent
Luna review. Strong planning and risk routes remain. Balanced and explicit role
changes remain available. Existing approved snapshots retain their exact routes.

All 61 executable skill entries use one shared model preview. Child skills reuse
the selected snapshot. Existing tests run directly without another model worker.

The Pi adapter binds the trusted gateway destination, verifies its request hook
before releasing task content, and sends the selected privacy policy on every
request. It rejects policy weakening in a Pi fallback. It supports typed images,
browser command access and cumulative usage. Strict runs stop before automatic
compaction because the supported runtime bypasses its request hook for summaries.
Completion waits for the settled event. The verified runtime is Pi 0.85.1.

Browser guidance selects Playwright Test for stable regression suites and CI.
Interactive work selects an available driver with captured capability evidence.
Driver identity, workspace and artifact hashes are checked before dispatch.
Browser tool access is not a filesystem sandbox.

## Repository checks

Run these from the repository root:

```sh
python3 -m unittest discover -s skills/shared/tests -q
python3 -m unittest discover -s skills/engineering/engine/implement-and-review/tests -q
python3 -m unittest discover -s skills/engineering/workflow/validate-e2e/tests -q
python3 -m unittest discover -s skills/engineering/seats/pi-runner/tests -q
python3 skills/shared/scripts/validate_skill_frontmatter.py
python3 scripts/check_leitworter.py --json
git diff --check
```

All 230 tests passed: 149 shared tests, 41 launcher tests, 17 validation
controller tests and 23 Pi tests. All 61 skill frontmatter checks passed.
Vocabulary and whitespace checks passed. The compaction regression failed when
the guard was removed and passed when restored; the guarded resume emitted no
new provider request.

The Pi integration tests need permission to bind a loopback server. They use
synthetic credentials and a local endpoint, with no paid provider calls. They
check serialized privacy fields, reasoning, tool turns, image content, resume,
usage, missing hooks, changed configuration and gateway redirection. The fixture
overrides the trusted destination only within the test process.

## Live checks

The live probes used synthetic content, GLM High, the strict provider policy,
and no repository source. No repair call was needed for the implementation cases.

| Check | Observed result |
| --- | --- |
| Minimal provider request | Returned the expected text with an enforcement receipt |
| Three implementation cases | Stable deduplication, count parsing and interval merging passed 29 assertions |
| Local browser readiness | agent-browser 0.36.0 passed navigation, state inspection, interaction, assertions and screenshot capture |
| GLM with the real browser driver | Save and reload, access denial and asynchronous failure paths passed on a local fixture |
| Browser evidence | Screenshot inspected by the coordinator; local server recorded the expected 403 and 500 responses |

The browser worker reported one locator correction. It used 12 provider requests
and 23,280 tokens. Its client reported cost was about USD 0.00229. The code probe
used one request and 2,518 tokens, with a client reported cost of about USD
0.00062. These values cover only those worker probes. They exclude coordinator
and review work and are not a billing reconciliation or a spending cap.

Temporary evidence is in `/private/tmp/rar-skills-browser-check/`,
`/private/tmp/rar-skills-code-check/`, and
`/private/tmp/rar-skills-live-glm-check.json`. The local checks and live probes are
separate: synthetic HTTP adapter tests prove request shape; browser observations
prove fixture behavior. Neither establishes application readiness.

## Limits

The inference host was not independently observed. Request enforcement does not
prove upstream retention practices. Account guardrails were not changed.

No comparison against the previous model setup was completed. The six small
cases show working implementation and browser paths, not equivalent quality or
measured savings per accepted project task. There was no comparison between
browser drivers. Playwright CLI was absent from PATH; its route remains subject
to readiness checks. A maintained application suite should use its existing
Playwright Test setup where suitable.
