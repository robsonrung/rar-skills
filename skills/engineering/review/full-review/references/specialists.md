# Specialists

Apply a specialist when the diff matches its trigger. Its rules sharpen the reviewing seat's attention; it becomes a seat of its own only when a deep plan names it.

## Database migration

**Trigger:** migration or schema files, DDL (`CREATE`, `ALTER`, `DROP`, `TRUNCATE`, indexes), data backfills.

- Migrations are repeatable or clearly one-shot, as the repo's migration system expects.
- Destructive changes carry a migration path and a rollback or recovery story.
- Large tables avoid long locks, rewrites, and unbounded backfills; backfills are batched for production volume.
- New foreign keys, filters, and joins have indexes.
- Application code, schema, generated clients, and tests stay compatible through the rollout.

**CRITICAL:** data loss, irreversible destructive migration without a rollout plan, breaking schema change with no compatibility path. **HIGH:** lock-heavy migration, missing index on a new query path, unsafe backfill, application and schema drift.

## API contract

**Trigger:** GraphQL, REST, RPC, OpenAPI, protobuf, JSON schema, public types, SDKs, generated clients.

- Removing fields, endpoints, enum values, events, exports, or response properties breaks clients.
- So does changing types, requiredness, defaults, status codes, headers, or error shapes, and adding a required input.
- Versioning, deprecation, migration notes, and generated clients move together.
- Server and client validation accept the same shapes.

**CRITICAL:** public contract break without deprecation, migration, or versioning. **HIGH:** generated clients or validators out of sync with the contract.

## Authorization

**Trigger:** authentication, roles, permissions, tenancy, sessions, tokens, policies, guards.

- Permission checks run before data access or mutation.
- New routes, commands, jobs, and mutations follow the access model of their neighbors.
- Tenant, organization, workspace, and user boundaries hold.
- Privileged paths carry justification and tests; server-side enforcement backs every client-side check.

**CRITICAL:** missing authorization on a reachable sensitive action, tenant escape, privilege escalation. **HIGH:** inconsistent permission model, missing policy test, authorization after data access.

## Performance

**Trigger:** loops over repository or service calls, bulk operations, joins, list endpoints, pagination, caching, queues, workers, hot paths.

- No N+1 access or remote calls in loops; prefer bulk fetches, batching, pagination, streaming, bounded memory.
- New query patterns have indexes or a stated reason they need none.
- Cache keys and invalidation cover the relevant state.
- Latency-sensitive paths stay free of CPU-heavy or blocking work.

**CRITICAL:** N+1 or unbounded work on a production hot path. **HIGH:** missing index, unbounded result set, cache correctness bug, avoidable blocking call.

## Integration reliability

**Trigger:** HTTP, RPC, or SDK clients, external URLs, queues, webhooks, object storage, email, payments, third-party APIs.

- External calls have timeouts, cancellation, and clear error mapping.
- Retried writes are idempotent; retries back off, stay bounded, and skip permanent failures.
- Responses are checked for both transport and application errors.
- Webhooks and async jobs handle retries, duplicates, ordering, and dead letters.

**HIGH:** missing timeout, unsafe retry, non-idempotent retried write, raw external error leakage, unhandled duplicate delivery. **MEDIUM:** missing observability, incomplete error mapping, weak degradation.

## React

**Trigger:** components, hooks, providers, `useEffect`/`useMemo`/`useCallback`/`useLayoutEffect`, `React.memo`, `forwardRef`, Context `value=`, portals, fetching in effects.

- Apply the `advanced-react` skill's `references/lenses.md`.
- Composition before memoization: move state down or pass elements as props before adding `React.memo`. Check compiler coverage before demanding manual memoization.
- `useMemo`/`useCallback` earns its place only as a hook dependency or a prop to a memoized component; one unstable non-primitive prop, `children` included, defeats `React.memo`.
- Read the repo's React version before applying version-specific rules (`forwardRef`, ref as a prop).
- State set after an `await` in an effect keyed on a changing value needs an `AbortController`, a cleanup flag, or an id comparison.

**HIGH:** fetch race overwriting fresh data, stale closure on a live path, measured provider churn on a hot path after compiler coverage is checked. **MEDIUM:** memoization that buys nothing, debounced function recreated each render, measure-then-mutate flicker in `useEffect`, hot state high enough to re-render a heavy subtree.

## UI and UX

**Trigger:** user-facing markup or styling, design tokens, themes, new screens or flows, forms, loading, empty, and error states.

- Apply the craft bar of the `frontend-design` skill and the `ui-ux-pro-max` guidelines.
- New UI uses the repo's design system (tokens, spacing and type scales, palette, components) over one-off values.
- Interactive elements have visible focus, accessible names, sufficient contrast, and consistent targets.
- Async UI has deliberate loading, empty, and error states; forms validate inline and keep input on failure.
- Generic aesthetics on a prominent surface count: default cards, uniform radius and shadow, purple-gradient defaults, placeholder copy.
- When screenshots come with the diff, review the rendered result.

**HIGH:** unusable or inaccessible primary control, destructive action without confirmation, missing error state that strands the user. **MEDIUM:** design-system violations, missing loading or empty states, broken type or spacing rhythm, generic aesthetics on a prominent surface.

## Financial and data integrity

**Trigger:** money, billing, balances, credits, inventory, quotas, counters, ledgers, pricing, tax, reconciliation, other critical mutations.

- Numeric representation and rounding are explicit.
- Mutations keep invariants under retries, concurrency, and partial failure; critical updates are atomic or compensated.
- Negative, zero, overflow, boundary, duplicate, and stale-state cases have defined behavior.
- Irreversible or externally visible state is auditable and reconcilable.

**CRITICAL:** precision loss, double charge, corruption, invariant violation, irreversible inconsistent state. **HIGH:** missing idempotency, unclear rounding, non-atomic critical update, missing concurrency guard.
