# Fitness functions — make architectural rules enforce themselves

A *fitness function* is any automated, objective check that a candidate design still satisfies an architectural characteristic. The idea: instead of relying on people remembering a rule, encode it so the build fails when the rule is broken. This turns "we agreed not to do X" into "the CI gate won't let you do X."

Reach for one whenever a decision establishes a rule that future code could silently violate.

## Map the characteristic → a check

| Characteristic / rule | Concrete fitness function |
|---|---|
| Layering / dependency direction (e.g. domain must not import infra) | Architecture test (ArchUnit, ts-arch, dependency-cruiser, import-linter, eslint `no-restricted-imports`). |
| No cycles between modules | Cycle detection in dependency-cruiser / madge in CI. |
| Performance budget (latency, response time) | Automated perf/load test asserting a p95 threshold; Lighthouse/bundle-size budget for frontend. |
| Bundle / artifact size | size-limit or bundlesize check failing the build past a cap. |
| Security posture | Dependency audit, SAST, secret scanning as required CI steps. |
| API contract stability | Schema/contract tests; OpenAPI diff that flags breaking changes. |
| Test coverage of a critical path | Coverage threshold gate (scoped to the path, not a blunt global %). |
| Code-level invariant (naming, no `any`, no direct DB access in controllers) | Custom lint rule / type check. |

## Properties of a good fitness function
- **Objective** — pass/fail, not a judgment call.
- **Automated & wired into CI** — runs without anyone remembering to.
- **Cheap to run** — or it gets disabled.
- **Tied to a real characteristic** — don't gate on something nobody decided mattered.

## How to use in a coding session
1. When a decision creates a rule ("X must never depend on Y", "this stays under N ms"), ask: *can a test enforce this?*
2. If yes, propose the smallest check that does, and where it goes (lint config, an arch test file, a CI step).
3. Note it in the ADR's Consequences ("enforced by `<check>`") so the link between decision and guard is explicit.
4. Don't over-gate. Each fitness function is itself maintenance; add them for rules that are important *and* genuinely at risk of being broken.
