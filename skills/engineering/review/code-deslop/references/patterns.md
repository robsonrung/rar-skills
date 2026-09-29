# Candidate patterns and counterevidence

These are investigation prompts, not rewrite rules. Assess purpose and behavior, not authorship. A confirmed defect may require a separately authorized behavior-changing repair.

| Candidate | Evidence needed for cleanup | Reasons to keep or block | Targeted verification |
| --- | --- | --- | --- |
| Narrating comments | Comment repeats the adjacent operation and carries no contract or tool meaning | Why, invariant, units, security rationale, compatibility workaround, license, public API documentation, compiler/linter directive | Review comment syntax, directives, snapshots and generated documentation |
| Stale comments or documentation | Conflict with implementation and an independently confirmed current contract | Implementation may be wrong; history may explain an exception | Confirm requirements; do not silently make documentation endorse a bug |
| Dead variables, functions or exports | No reachable use across configured entry points and supported consumers | Dynamic imports, reflection, decorators, DI tokens, routes, CLI scripts, external library consumers, side-effect imports | Correct import graph, compile/build, entry-point smoke test |
| Unused dependency | No runtime, type, build, test, config, script, optional-platform or peer use | Framework plugins, runtime loaders, workspace aliases, transitive/peer contracts | Authorized manifest and lockfile update, clean local validation; no hand-edited lockfile |
| Pass-through helper or service | Only forwards without translating policy, types, lifetime, errors or dependency direction | Stable public API, test seam, Anticorruption Layer, instrumentation, transaction boundary, one good domain name | Caller contracts, error identity, method binding, runtime call count |
| Speculative generality | Unused options or variants with no supported caller, compatibility promise or requirement | Active feature flags, migrations, multiple deployments, tenant-specific configuration | Caller/config matrix; explicit scope for removing supported configuration |
| Duplicate implementation | Same business knowledge, same contract, same reasons to change, verified canonical implementation | Similar code in distinct bounded contexts; distinct pricing, tax, permission or lifecycle policies | Contract matrix for all callers; ensure extraction does not create dependency cycles |
| Wrong abstraction | Flags and conditionals interleave unrelated policies; abstraction increases change coupling | A proven shared domain concept or necessary dependency boundary | Consider inlining before re-extracting; test each caller independently |
| Excess nesting | Equivalent simpler branches can be demonstrated | Resource lifetime, finally/defer blocks, hook ordering, variable initialization, short-circuit side effects | Branch table plus ordering and exception tests |
| Repeated null checks | An earlier runtime guarantee dominates every path and applies to actual inputs | External data, persisted legacy data, races, unsafe casts, partial objects, JavaScript callers | Null/undefined/empty/zero/false/NaN matrix; validate trust boundary |
| Catch-and-rethrow | No translation, cleanup, telemetry, retry, context attachment or error-boundary behavior | Stack/cause differences, error classes, recovery, resource release, operational logging | Failure-path type/message/cause/identity and effects |
| Silent fallback or swallowed error | Hides a real failure or contradicts contract | Explicit best-effort behavior, graceful degradation, optional resources, published return contract | Treat changed failure semantics as a separate repair; characterize both paths |
| Debug logging | Confirmed temporary output with no contractual or operational consumer | Audit trail, security monitoring, SLOs, support tooling, structured events | Inspect consumers and log metadata; do not suppress operational signals for a cleaner diff |
| Type escape | `any`, assertion or suppression conceals a mismatch or repeats existing narrowing | Framework boundary, validated adapter, upstream typing defect with documented workaround | Typecheck relevant workspaces and public type contract; runtime validation where needed |
| Derived React state/effect | Value can be calculated during render without losing temporal semantics | Synchronization with external systems, subscriptions, persisted state, SSR/hydration, transition/reset semantics | Interaction, rerender, remount, cleanup and browser checks as applicable |
| Memoization or callback wrapper | No semantic reliance and measurable or clear cognitive cost | Referential identity relied on by effect dependencies or memoized consumers; expensive calculation | Profile when performance matters; preserve hook order and behavior |
| Kitchen-sink utility/config | Unrelated responsibilities make callers depend on irrelevant policy | A genuinely cohesive module; extraction could only scatter understanding | Compare coupling and call-site clarity, not file length |
| Weak or tautological tests | Test passes when the behavior it claims to protect is deliberately broken | Regression rationale, failure path, protocol boundary, integration seam, platform-specific case | Targeted mutation/fault injection or assertion review; preserve coverage of contracts |
| Over-mocked tests | Only assert interaction details, missing observable outcomes | Interaction order/count may itself be the contract, e.g. payment idempotency | Add observable assertions; retain required protocol and failure checks |
| Placeholder APIs and fake success | Referenced API does not exist, TODO returns success, placeholder data escapes | Explicit mock/demo fixture within its documented use | Verify installed APIs and real call path; behavioral fixes need separate authorization |
| Inconsistent convention | Violates explicit repository rule or introduces a second implementation of the same policy | Existing inconsistency means no clear standard; newer code may intentionally fix old practice | Use maintained exemplars, agreed contracts and local lint/type rules |
| Architecture erosion | Wrong dependency direction, duplicated domain rule, business logic leaked into transport/UI | Intended adapter translation or presentation-specific policy | Existing Dependency Rule, Context Map, architecture tests; broad repair is a separate task |

## Deletion gate

Before deleting executable code or a dependency, establish all of the following:

1. Search coverage includes supported entry points, tests, scripts, generated consumers, manifests, runtime loading and external APIs. Report gaps.
2. No required runtime side effect, resource lifetime, error behavior, compatibility behavior or operational signal disappears.
3. The alleged replacement has the same relevant contract, including empty/failure/cancellation paths.
4. Verification is available and authorized. An analyzer warning alone is not enough.

If any item is unknown, block deletion and state what evidence is missing. Do not treat absent documentation as proof that a requirement never existed.

## Small rewrites with large semantic risks

### Truthiness is not presence

```typescript
const hasValue = value !== null && value !== undefined && value !== "";
```

Replacing this with `Boolean(value)` rejects `0`, `false`, `NaN`, and `0n`, which the original accepts. Replacing `x || fallback` with `x ?? fallback` changes treatment of falsy values. An explicit `=== true` check may intentionally reject truthy non-booleans.

### One-promise combinators are not necessarily redundant

`Promise.all([operation()])` resolves to an array, not the scalar value from `operation()`. Destructuring, error flow, and scheduling matter. Do not delete a combinator from syntax alone.

### TypeScript is not runtime input validation

A static annotation does not validate JSON, an HTTP payload, a database row, or a JavaScript caller. Replace unsupported assertions with evidence-backed narrowing; do not remove the boundary that provides the runtime guarantee.

### Early returns can bypass required work

Moving a return above a cleanup, transaction, telemetry, `finally` region, or React Hook can change semantics. Inlining methods can also change `this`, exception stacks, evaluation order, and module initialization.

### Fewer queries is not automatically equivalent

Batching or joining can change ordering, null behavior, multiplicity, consistency, lock scope, tenant boundaries, and error handling. Treat query optimization as separate unless equivalence and scope are established. No production experiments or automatic `EXPLAIN ANALYZE`.

## Explicit non-rules

Do not require 20-line functions, one component per file, `function` instead of arrows, `Boolean(x)` instead of `!!x`, removal of all `else`, zero comments, or zero duplication. Do not convert all positional arguments to objects, extract every expression, or remove every one-caller interface. Apply an explicit local rule only when it is compatible with the task and behavior.
