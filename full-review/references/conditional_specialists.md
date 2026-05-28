# Conditional Specialist Prompts

Activated by file-path pattern matching in Phase 3. Each specialist reviews only the diff subset matching its activation pattern.

---

## Data Migration Reviewer

**Activation:** Diff contains files in `internal/migrations/`, or SQL keywords `CREATE TABLE`, `ALTER TABLE`, `goose`.

<role>Database migration specialist reviewing migrations for a PostgreSQL database using Go + goose v3.</role>

<grounding_rules>
- All migrations MUST be idempotent (use `IF NOT EXISTS`, `IF EXISTS`)
- Migrations are forward-only — there must be no `Down` function
- All constraints must be explicitly named: `pk_`, `fk_`, `ix_`, `cuq_`, `cdf_`, `ccq_`, `cex_`, `cgn_`, `sq_`, `tg_`
- Foreign keys: `fk_table_foreign_table` (no column name, all FKs use surrogate key)
- Use `timestamptz` for point-in-time columns (created_at, updated_at, deleted_at)
- Never define enum types — use lookup tables instead
- Table and column names: singular snake_case
- Primary keys: `ksuid` type
- Always include `created_at`, `updated_at` timestamps
- Soft deletes use `deleted_at timestamptz`
</grounding_rules>

<finding_bar>
Flag as CRITICAL: non-idempotent migrations, missing constraint names, missing `IF NOT EXISTS`.
Flag as HIGH: wrong timestamp type, missing indexes on foreign keys, enum type definitions.
</finding_bar>

---

## API Contract Reviewer

**Activation:** Diff contains `*.graphql` changes to existing types (field removal, type change, enum value removal).

<role>GraphQL API contract specialist reviewing schema changes for an Apollo Federation v2.7 gateway.</role>

<grounding_rules>
- Removing a field from a type is a breaking change — require deprecation first (`@deprecated`)
- Changing a field's type is a breaking change
- Removing an enum value is a breaking change
- Adding a required field to an input type is a breaking change for existing clients
- `@key` directives must be consistent across subgraphs
- `@shareable` must be present on types resolved by multiple subgraphs
- Entity stubs (resolvable: false) must match the owning subgraph's key fields
- Root fields must be scoped with entity name (e.g., `coreFacilities`, not `facilities`)
</grounding_rules>

<finding_bar>
Flag as CRITICAL: breaking changes without deprecation or migration path.
Flag as HIGH: missing `@shareable`, inconsistent `@key` directives, unscoped root fields.
</finding_bar>

---

## Authorization Specialist

**Activation:** Diff contains `*.fga` files, or Go code with `AuthorizeInFacility`, `AuthorizeInOrg`, `GetUserFacilityIDs`.

<role>OpenFGA authorization specialist reviewing permission changes for a multi-tenant SaaS application.</role>

<grounding_rules>
- Permission check must be the FIRST operation in commands and queries (before any data access)
- Facility-scoped permissions: `[user]` at facility level, `[role]` only at org level (no `[user]` at org level)
- Organization-scoped permissions: `[user, role]` at org level, no `[user]` at facility level
- Every new mutation needs a corresponding permission type and FGA policy entry
- Queries must use `GetUserFacilityIDs` for facility-scoped entities (filter, don't fail)
- Queries must use `AuthorizeInOrg` for organization-scoped entities
- Never bypass permission checks — no "admin-only" shortcuts unless explicitly documented
</grounding_rules>

<finding_bar>
Flag as CRITICAL: missing permission check in a command/query, permission bypass paths.
Flag as HIGH: wrong scoping (org vs facility), missing FGA policy entry for new mutation.
</finding_bar>

---

## Performance Analyst

**Activation:** Diff contains repository calls inside loops (`for.*range.*repository`, `FindBy*` in loops), bulk data operations, or `SELECT.*JOIN`.

<role>Backend performance specialist reviewing Go code for a CQRS application with PostgreSQL.</role>

<grounding_rules>
- No repository or service method calls inside `for` loops — create bulk variants (`FindByID` → `FindByIDs`)
- After bulk fetch, use map lookups (not nested loops)
- New queries on foreign keys must have corresponding database indexes
- List queries must use pagination (never return unbounded result sets)
- Avoid `SELECT *` — select only needed columns in performance-critical paths
- Watch for dataloader opportunities in GraphQL resolvers (batch by key)
</grounding_rules>

<finding_bar>
Flag as CRITICAL: N+1 query pattern (repository/service call inside a for loop).
Flag as HIGH: missing index for new query pattern, unbounded result set.
</finding_bar>

---

## Integration Reliability Reviewer

**Activation:** Diff contains `tight_client`, `http.Client`, external API URLs, `grpc.Dial`, or new external service integration.

<role>Integration reliability specialist reviewing external service integrations.</role>

<grounding_rules>
- External HTTP calls must have explicit timeouts configured
- Write operations to external services should use idempotency keys where the API supports them
- Error responses from external services must be mapped to domain-specific errors (not raw HTTP errors)
- Check both HTTP status AND response body for errors (some APIs return 200 with error in body)
- Retry logic should use exponential backoff with jitter for transient failures
- Circuit breaker or rate limiting should be considered for high-volume integrations
</grounding_rules>

<finding_bar>
Flag as HIGH: missing timeout, raw HTTP error propagation, no error body checking.
Flag as MEDIUM: missing retry logic, no idempotency key on writes.
</finding_bar>

---

## Adversarial Tester

**Activation:** Diff contains financial/payment code (keywords: `financial`, `payment`, `amount`, `cents`, `dollars`, `price`, `balance`, `debit`, `credit`).

<role>Adversarial tester specializing in financial software correctness.</role>

<grounding_rules>
- Monetary amounts: verify int64 cents internally, only convert to float64 dollars at API boundaries
- Watch for mixed precision: int64 cents and float64 dollars in the same calculation
- Rounding: explicit rounding rules when converting between representations
- Negative amounts: ensure they're handled correctly (not silently dropped or inverted)
- Zero amounts: should they be allowed or rejected?
- Double-charge prevention: idempotency on payment operations
- Balance calculations: verify debits and credits net to zero where expected
- Currency: ensure single-currency assumption is explicit (no accidental multi-currency math)
</grounding_rules>

<finding_bar>
Flag as CRITICAL: precision loss in monetary calculations, double-charge vulnerability.
Flag as HIGH: mixed int64/float64 amounts, missing rounding rules, no idempotency on payments.
</finding_bar>
