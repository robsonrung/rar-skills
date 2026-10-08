# Implementation Evidence

Evidence follows the changed behavior. Reuse a captured red baseline when it proves the same defect on the same source and relevant environment. Otherwise capture it before a behavior repair. Do not recreate correct work to change the order of its history.

## Choose One Evidence Route

| Situation | Required evidence |
| --- | --- |
| An existing test exposes the intended behavior | Capture its failing result before the change. |
| A nearby test asserts the old behavior | Change its expectation and capture the failure before implementation. |
| Existing coverage misses the real path | Add the smallest focused failing test or **characterization test**. |
| Automated testing is not meaningful | Record the reason and a direct replacement check before marking the task complete. |

For every behavior change, report:

1. `existing_tests_inspected`
2. `tests_added_or_changed`
3. `red_baseline`
4. `verification_commands`
5. `verification_result`

For a no-test route, report `no_test_reason` and the replacement verification. Do not add a hollow test only to satisfy a process step.

## Capture the final implementation checks

Before dispatch, the coordinator discovers the repository's required commands
and acceptance checks. Give the worker stable check IDs, command argument lists,
working directories, timeouts, required fresh flags, observation requirements,
intended base, contract path, and an artifact directory. Declare check inputs only
when their complete dependencies are known. Use the requirements format and
capture API in `shared/references/review-evidence.md`.

The implementer retains the required failing regression evidence. After all
implementation and simplification edits, it records actual runtime, dependency,
and relevant external state, then uses the shared helper:

```bash
python3 <shared-dir>/scripts/review_evidence.py prepare \
  --root <worktree> --base <intended-base> --contract <accepted-task> \
  --requirements <requirements.json> --output <new-evidence-directory>
python3 <shared-dir>/scripts/review_evidence.py run-check \
  --snapshot <new-evidence-directory>/snapshot.json --id <required-check-id>
```

Resolve `<shared-dir>` from the loaded shared skill. Keep artifacts outside source
or declare the launcher's generated directory with `--artifact-dir`. Run source
changing prerequisites before preparation. Stop other writers while preparing and
capturing. Capture each required command once on the final unchanged source. A
repair needs a new snapshot directory and retains failed captures. Return the
snapshot and original result paths with raw logs, failing regression evidence,
and any missing or failed check. Do not replace captures with a prose summary.
For a repair after review, bind the latest review with `--previous-review` during
preparation so earlier findings remain part of the next review contract.

The coordinator confirms the final source and environment, then calls:

```bash
python3 <shared-dir>/scripts/review_evidence.py select-checks \
  --snapshot <current-snapshot> --from-snapshot <worker-snapshot> \
  --checks <original-check-paths.json>
```

Always supply the original worker snapshot when selecting its captures. When
source and context are unchanged, use that same snapshot for both snapshot
arguments. For changed source or context, prepare a new target snapshot.

If any selected `run` already has a capture in the target directory, prepare a
new target snapshot before execution. Run the selector again with that target,
the original worker snapshot, and its capture map. This also applies when source
is unchanged and one check can be reused while another requires a fresh run.
Keep the validated original result for the reusable check; capture the fresh
check in the new target directory. Build the packet for that new target using
both result paths. Preserve the first results and every fresh requirement.

Execute all selected `run` entries, keep validated `reuse` paths, and use
`transfer-check` only after the required environment and base assessment.
Prepare the complete packet and send it to the independent final reviewer with
`shared/references/reviewer-response.md`. Worker checks do not supply reviewer
judgment. These captures use the existing implementation turn; they require no
extra model call. **Only captured command results count as evidence.**

If required evidence is missing, reserve recovery within the approved route allowance
before dispatch. Keep prior consumption. Stop with the missing proof recorded when that allowance
or another shared limit is exhausted.

## System Boundary Check

Run this only when the changed behavior crosses a callback, middleware, event, storage, external call, or alternate entry point.

1. Trace the real execution chain far enough to find side effects.
2. Verify error handling and retry behavior at the boundary.
3. Test an interaction path that mocks alone cannot prove.
4. Check another public entry point when the behavior has one.

This is **observable behavior**, not structural test coverage. A leaf change without those boundaries does not need this extra pass.
