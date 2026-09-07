# Implementation Evidence

Evidence follows the changed behavior. The worker captures the red baseline before production code changes because it cannot be reconstructed later.

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

If required evidence is missing, reserve one evidence recovery in the run state
before dispatching it. If the recovery still lacks evidence, stop the task with
the missing proof recorded.

## System Boundary Check

Run this only when the changed behavior crosses a callback, middleware, event, storage, external call, or alternate entry point.

1. Trace the real execution chain far enough to find side effects.
2. Verify error handling and retry behavior at the boundary.
3. Test an interaction path that mocks alone cannot prove.
4. Check another public entry point when the behavior has one.

This is **observable behavior**, not structural test coverage. A leaf change without those boundaries does not need this extra pass.
