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
- Server and client validation follow the same request contract. Keep closed request values and authorization states closed. When independently deployed producers can return new response labels, keep known labels typed and preserve the agreed unknown-value behavior through serialization and display. Decide this per response field; it does not make every enum open.
- Every request array has a size bound, and every limit the server enforces (page size, range length, identifier format) is one the client and other callers respect and can explain.

**CRITICAL:** public contract break without deprecation, migration, or versioning. **HIGH:** generated clients or validators out of sync with the contract.

## Authorization

**Trigger:** authentication, roles, permissions, tenancy, sessions, tokens, policies, guards, deployment accounts or submitted resource definitions.

- Permission checks run before data access or mutation.
- New routes, commands, jobs, and mutations follow the access model of their neighbors.
- Tenant, organization, workspace, and user boundaries hold.
- Privileged paths carry justification and tests; server-side enforcement backs every client-side check.
- A principal that creates resources indirectly, such as a deploy controller, a CI role, or a template submitter, is scoped by what it can create and where. A narrow name or label is not a scope. Report configuration, deployed state, and a live permission check as separate evidence.
- The query is as narrow as the check: access verified for one scope filters the data to that scope. A parameter that only picks a label or a time zone is not a filter.
- An action whose effect is wider than the scope it was checked in needs the wider permission.
- Navigation, links, and commands appear only when the target lets the user in, and an old entry stays until the new one is reachable.

**CRITICAL:** missing authorization on a reachable sensitive action, tenant escape, privilege escalation. **HIGH:** inconsistent permission model, missing policy test, authorization after data access.

## Performance

**Trigger:** loops over repository or service calls, bulk operations, joins, list endpoints, pagination, caching, queues, workers, hot paths.

- No N+1 access or remote calls in loops; prefer bulk fetches, batching, pagination, streaming, bounded memory.
- New query patterns have indexes or a stated reason they need none.
- Cache keys and invalidation cover the relevant state.
- Latency-sensitive paths stay free of CPU-heavy or blocking work.
- Filters apply before aggregation, de-duplication, or a join to a costly view; a scope several queries share is built once.
- A list that is cut says so: it returns a total or a continuation marker, so no caller reads a capped list as complete. A deep offset on a large or growing list is not pagination: cap the page depth or use a cursor.
- Client side: no request per row, no effect that walks every page, no filter or count over a loaded page beside a server total, no request loop without a cap and a cancel. Polling stops on unmount and backs off.

**CRITICAL:** N+1 or unbounded work on a production hot path. **HIGH:** missing index, unbounded result set, cache correctness bug, avoidable blocking call.

## Integration reliability

**Trigger:** HTTP, RPC, or SDK clients, external URLs, queues, webhooks, object storage, email, payments, third-party APIs, CSV or spreadsheet exports that can evaluate untrusted cells, prompts or tool results sent to a language model.

- External calls have timeouts, cancellation, and clear error mapping.
- Retried writes are idempotent; retries back off, stay bounded, and skip permanent failures.
- Responses are checked for both transport and application errors.
- An export that a spreadsheet will open encodes untrusted text so that no cell evaluates as a formula, and keeps intended numbers numeric. Quoting alone does not do this.
- Webhooks and async jobs handle retries, duplicates, ordering, and dead letters.
- A terminal failure state (retries exhausted, row marked failed) emits a log line with the record's identifiers and has an alert or a reader. Redaction keeps the error class and code.
- A catch handles the failure it expects; a catch-all that returns "no result" turns an outage into a wrong answer.
- A server-side fetch of a user- or third-party-supplied address validates the resolved address in every notation, again on each redirect and DNS answer.
- Text from users or third parties that reaches a language model is marked as data and length-capped; a lookup that is capped or filtered refuses instead of reporting "no match".

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

- Apply the craft bar of the `frontend-design` skill.
- New UI uses the repo's design system (tokens, spacing and type scales, palette, components) over one-off values.
- Interactive elements have visible focus, accessible names, sufficient contrast, and consistent targets.
- Async UI has deliberate loading, empty, and error states; forms validate inline and keep input on failure.
- A bulk action applies to exactly the set the user was shown or told: the visible items, or a stated count such as "all 240 matching". It never silently includes items that a filter, a collapsed group, or a hidden layer excludes.
- Every write guards a double submit before the call starts, reports failure in words the user can act on, and leaves no enabled control whose handler does nothing.
- When the API takes an idempotency key, the key lives with the draft until the outcome is known and a retry sends the identical body. After a version conflict the draft takes the new version, so the next save can succeed.
- State derived from an input (a confirmation, a suggestion list, a child selection) resets when the input changes; a local copy of shared state follows it; an open form survives a background reload.
- Generic aesthetics on a prominent surface count: default cards, uniform radius and shadow, purple-gradient defaults, placeholder copy.
- When screenshots come with the diff, review the rendered result.

**HIGH:** unusable or inaccessible primary control, destructive action without confirmation, missing error state that strands the user. **MEDIUM:** design-system violations, missing loading or empty states, broken type or spacing rhythm, generic aesthetics on a prominent surface.

## Figures, dates, and units

**Trigger:** counts, totals, rates, badges, report cards, drill-down links, exports, date presets or "today" logic, quantities with units.

- A count and the list it counts apply the same filters; a figure and its drill-down share one scope builder, or the link says it is not scoped.
- A rule such as "archived items are hidden" lives in one place that the figure, the list, and the export all call, with a test on the record at the edge of the rule.
- A breakdown adds up to its total. An export carries what the screen shows and records its period and filters.
- A result that is loading, failed, or capped is labelled partial before it is counted, exported, or answered from.
- "Today", "this week", and period bounds use the time zone the business rule names, never the browser's or UTC by accident; a period has both bounds; items in different zones compare as instants.
- Where a tenant or a site chooses its unit, a displayed quantity converts through one shared conversion with that unit. A contract that names a unit (a stored column, a report format, a partner API) converts to the named unit. Conversion factors live in that one shared place.
- A rate that is not exactly 0% or 100% does not display as one.

**HIGH:** a figure that disagrees with its own list or export, a date boundary in the wrong time zone that moves records between periods, a unit assumed where configuration chooses it, or a conversion factor outside the shared conversion. **MEDIUM:** unlabelled partial data, an unscoped drill-down, misleading rounding.

## Stacked change

**Trigger:** a pull request whose base is another open pull request, or a diff described as one slice of a larger feature.

- Each slice builds, type-checks, lints, and passes its tests at its own head; a test imports nothing a later slice adds. Recheck every slice after a restack.
- Code lands with its first caller by default: a table, route, repository, or helper nothing in the slice uses cannot be reviewed there. A foundation slice says so and names where the caller arrives.
- Nothing visible points at something missing: no link, menu entry, or action for a route or dialog a later slice adds, unless the description says the stack merges together.
- The slice carries no unrelated change to shared layout, configuration, or an older feature; one that must ride along is called out with its reason.
- When the last caller goes, the callee goes in the same slice.

**HIGH:** a slice that fails its own build or tests, a user-reachable dead link or broken action if the slice ships alone. **MEDIUM:** code with no caller, an unannounced shared change.

## Financial and data integrity

**Trigger:** money, billing, balances, credits, inventory, quotas, counters, ledgers, pricing, tax, reconciliation, other critical mutations.

- Numeric representation and rounding are explicit.
- Mutations keep invariants under retries, concurrency, and partial failure; critical updates are atomic or compensated.
- Negative, zero, overflow, boundary, duplicate, and stale-state cases have defined behavior.
- Irreversible or externally visible state is auditable and reconcilable.

**CRITICAL:** precision loss, double charge, corruption, invariant violation, irreversible inconsistent state. **HIGH:** missing idempotency, unclear rounding, non-atomic critical update, missing concurrency guard.

## Stored state and async paths

**Trigger:** schemas, migrations, queues, caches, retries, idempotency keys, locks, leases, background jobs, concurrent writes.

- Apply the `Checks` section of the `data-systems-coding-lens` skill. That skill owns the rules for replay, lock order, claims, partial results, and time limits. This file adds only severity.

**CRITICAL:** a retry or replay that duplicates or destroys stored data. **HIGH:** a replay that skips the current access check, an inconsistent lock order on paths that contend, a failed or partial run that clears stored data, a write path that skips a rule the create path enforces.

## Tests

**Trigger:** added or changed tests, fixtures, mocks, test helpers, or test configuration.

- Apply the `test-lens` skill: the four pillars, the doubles boundary, and its checks for a test that cannot fail.

**HIGH:** a test that cannot fail for the behavior it names, a local suite that can write to a shared environment. **MEDIUM:** a brittle assertion on private structure.
