# Reporting calibration

What enters the result, at what severity, with what confidence. Precision over volume: a wrong or unfalsifiable finding costs more than a missed nit.

## What to report

Report defects, in this priority order:

1. **Correctness** — logic that produces a wrong result, boundary errors, unhandled null/undefined, wrong or missing `await`, unhandled rejections, incorrect error propagation, race conditions, non-idempotent handlers.
2. **Security and data safety** — missing authorization or tenant scoping, injection, unvalidated external input crossing a trust boundary, secrets or tokens in logs or error payloads, PII leaking into telemetry, unsafe deserialization.
3. **Contract breakage** — broken public surfaces of shared libraries, violated module boundaries, imports that reach into another module's internals, non-backward-compatible changes to persisted or transported shapes and migrations.
4. **Resource and performance defects with a concrete mechanism** — an N+1 query in a request path, an unbounded fetch, a leaked handle, a synchronous call in a hot loop. Not speculative micro-optimization.
5. **Test quality** — tests asserting the mock rather than the behaviour, tests that cannot fail, deleted or weakened coverage, a behavioural change with no test.
6. **Maintainability** — only where concrete and actionable, and only at P3.

Do not report: formatting or style that the repo's linter/formatter already own, personal preferences, rewrites of code the diff did not touch, or "consider adding a comment".

Report each distinct defect once. If the same mistake repeats across many lines, file one finding on the clearest instance and list the others in the body.

## Severity

| Severity | Meaning |
|---|---|
| **P0** | Data loss, security hole, or a break that will fire in production |
| **P1** | Likely incorrect behaviour on a realistic path; must be fixed before merge |
| **P2** | Real defect with limited blast radius, or a missing test for changed behaviour; should be fixed but does not block |
| **P3** | Minor and concrete — maintainability or clarity; safe to defer |

The verdict follows severity mechanically: any surviving P0 or P1 → `request-changes`; otherwise `approve`.

## Confidence

Confidence is what it says:

- **0.9+** only when the defect is evident from the code in front of you.
- **0.5–0.7** when it depends on a caller or a runtime condition you have not read. It is easy to be wrong about who calls what — lower your confidence when you have not read the consumers.
- **Below 0.5**, prefer not to report it at all.

Do not inflate confidence to be persuasive. Findings are judged on whether they hold up, not on how firmly they were stated.

## Writing findings for a machine consumer

A `request-changes` verdict may feed an automated follow-up run that consumes findings verbatim. Each finding body must let a competent agent act without asking: what's wrong, where, why it matters, and what done looks like. Anchor precisely — a finding whose `path`/`line` is not part of the diff belongs in `comments[]`, never force-anchored to an unrelated line. Where you can state the exact replacement lines, include them.
