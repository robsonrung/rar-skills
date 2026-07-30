# Verification Menu

Concrete checks per quality attribute. Read this when a lens finding needs to become an
executable check instead of an opinion. Choose checks matching the two or three quality
attributes the change most affects — do not run every row.

1. **Modularity**: dependency cycle checks, forbidden import checks, architecture tests, public API tests.
2. **Maintainability**: complexity budgets, cohesive file and module boundaries, duplication checks, clear naming.
3. **Performance**: benchmarks, query plans, p95 checks, load focused smoke tests.
4. **Scalability and elasticity**: queue depth checks, concurrency tests, capacity assumptions, back pressure tests.
5. **Availability and resilience**: retry behavior, timeout checks, fallback tests, chaos or failure mode tests when appropriate.
6. **Security and privacy**: auth path tests, least privilege checks, dependency scans, sensitive data checks.
7. **Data integrity**: migration tests, contract tests, idempotency tests, transaction and consistency tests.
8. **Deployability**: build checks, migration dry runs, rollback notes, release checklist.
9. **Observability**: logs, metrics, traces, alert coverage, local log review.

A check that only a human can judge is not a verification step — it is a review note. When
the concern will recur, promote the check to a fitness function (`fitness-functions.md`) so
future changes cannot quietly break it.
