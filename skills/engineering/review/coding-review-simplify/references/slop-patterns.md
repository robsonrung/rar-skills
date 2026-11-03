# Slop patterns and counterevidence

Investigation prompts, not rewrite rules. Each row is a candidate only until its counterevidence is ruled out. A confirmed defect is a separate, behavior-changing repair.

| Candidate | Not slop when | Verify |
| --- | --- | --- |
| Narrating comment | It carries a why, invariant, unit, security rationale, workaround, license, public API doc, or compiler or linter directive | Directives, doc generation, and snapshots still match |
| Stale comment or doc | The implementation is the thing that is wrong; history explains an exception | Confirm the current contract; never make a doc endorse a bug |
| Dead function, export, or variable | Reached through dynamic import, reflection, decorators, DI tokens, routes, CLI scripts, side-effect imports, or external consumers of a published library | **Deletion gate**, then build and smoke the entry point |
| Unused dependency | Used by a framework plugin, runtime loader, workspace alias, peer or optional platform contract, build, or config | Manifest and lockfile through the package manager, as a separate approved change |
| Pass-through helper or service | It translates errors, types, lifetime, or dependency direction; it is a test seam, anticorruption layer, instrumentation or transaction boundary, or a good domain name | Caller contracts, error identity, `this` binding |
| Speculative option or variant | An active feature flag, migration, deployment, or tenant uses it | Caller and config matrix |
| Duplicate implementation | The copies sit in different bounded contexts or encode distinct policies (pricing, tax, permissions, lifecycle) with different reasons to change | Contract matrix per caller; no new dependency cycle |
| Wrong abstraction (flags interleaving unrelated policies) | It is a proven shared domain concept or a needed dependency boundary | Inline before re-extracting; test each caller |
| Repeated null check | Input is external, persisted legacy data, racy, cast, partial, or from untyped callers | null, undefined, empty, zero, false, NaN matrix |
| Catch-and-rethrow | It translates, cleans up, retries, attaches context, records telemetry, or sets an error boundary | Error type, message, cause, identity, side effects |
| Silent fallback or swallowed error | Best-effort or degradation is the published contract | Changing failure semantics is a separate repair; pin both paths first |
| Debug logging | It feeds an audit trail, security monitoring, SLOs, or support tooling | Find the log consumers before removing |
| Type escape (`any`, assertion, suppression) | It sits at a framework boundary, a validated adapter, or an upstream typing defect with a documented workaround | Typecheck every affected workspace and the public types |
| Derived React state or effect | It synchronizes an external system, subscription, persisted state, hydration, or reset semantics | Interactions, rerender, remount, cleanup |
| Memoization or callback wrapper | An effect dependency or memoized consumer relies on referential identity | Hook order; profile if performance is the claim |
| Tautological test | It guards a regression, failure path, protocol boundary, or platform case | Break the behavior on purpose; the test must fail |
| Over-mocked test | Interaction order or count is the contract, as in payment idempotency | Add the observable assertion; keep protocol checks |
| Placeholder API or fake success | It is a documented mock or demo fixture | Confirm the installed API and the real call path |

## Semantic traps

Small rewrites that look equivalent and are not:

- `value !== null && value !== undefined && value !== ""` is not `Boolean(value)`: the original accepts `0`, `false`, `NaN`, `0n`. `x || fallback` and `x ?? fallback` differ on every falsy value. `=== true` may deliberately reject truthy non-booleans.
- `Promise.all([op()])` resolves to an array, not `op()`'s value, and changes scheduling and error flow.
- A TypeScript annotation does not validate JSON, HTTP payloads, database rows, or JavaScript callers. Keep the runtime boundary.
- An early return moved above cleanup, a transaction, telemetry, `finally`/`defer`, or a React Hook changes behavior. Inlining can change `this`, stack traces, evaluation order, and module initialization; flattening can drop a short-circuit side effect.
- Batching or joining queries changes ordering, nulls, multiplicity, lock scope, tenant scope, and errors. Treat it as a separate change; no production experiments or automatic `EXPLAIN ANALYZE`.
- In asynchronous code a green happy path is weak evidence. Protect cancellation, retry counts, idempotency, ordering, and resource release, or block the change.

## Non-rules

Slop is not style. Do not demand short functions, one component per file, `function` over arrows, `Boolean(x)` over `!!x`, no `else`, no comments, no duplication, object parameters everywhere, or the removal of every one-caller interface. Apply a local rule only when the repository states it.

## Detectors

Prefer what the repository already configures. Run an optional tool only if it is installed, in check mode, after reading its config: never fetch one with `npx`, `uvx`, or a "latest" tag, and some nominally local tools download modules or send telemetry. A warning is a hypothesis, and a failed or partial scan is not "no issues". A whole-project scan for reachability widens read scope, never write scope.

| Signal | Tool | Main false positive |
| --- | --- | --- |
| JS/TS unused files, exports, dependencies | Knip | Missing entry points or framework plugins; consumers outside a published library |
| Python dead code | Vulture; Ruff for static issues | Dynamic references; Vulture's confidence is not reachability, and Ruff separates safe from unsafe fixes |
| Go static issues | `go vet`, Staticcheck | Go commands can fetch missing modules |
| Dependency direction and cycles | dependency-cruiser or existing architecture tests | A cycle shows coupling, not the right refactor |
| Copy-paste | jscpd | Similar text across bounded contexts |
| Suspicious patterns | Semgrep with reviewed local rules | Syntax matches without context |
| Tests that pass on broken behavior | Stryker or existing mutation tooling, bounded to the changed contract | Equivalent mutants |

For other languages, use the maintained compiler, linter, formatter in check mode, and tests, and state the coverage gap.
