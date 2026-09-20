# Select tests by exposed behavior

Use existing project commands, tools, and fixtures. Load `verify-changes` for command discovery, `test-lens` for a disputed test choice, `browser-smoke` for browser mechanics, and `diagnose` for unexplained failures. Their whole workflows are not mandatory extra phases.

| Surface | Required evidence when in scope | Efficiency control |
| --- | --- | --- |
| Pure logic and components | Inputs, outputs, boundary values, invalid inputs, empty/null values, relevant state transitions; property tests when a general invariant earns them | Test observable behavior. Do not mirror implementation or assert incidental calls. Reuse existing cases. |
| API and service contracts | Real request/response status and body, validation, authentication/authorization at the claimed boundary, persistence and error behavior | Request injection proves the injected boundary only. A mocked identity does not prove the gateway. |
| Database and migration | Required real engine/version, before/after rows, tenant and owner scope, constraints, rollback, migration compatibility and cleanup | Disposable data; batch compatible cases in one fixture. Preserve business isolation between cases. |
| Events and async work | Commit ordering, payload, correct recipients, retries, duplicate delivery/idempotency, failure and recovery where exposed | Capture events once. Separate propagation effects from unique entrypoint counts. |
| Complete browser journey | Exact URL and environment, real interaction, visible result, persisted result after reload, validation/error path, console/network failures | Reuse a prepared local stack. Script stable repeated flows; a model handles changed state or ambiguity. A screenshot alone is not proof of a save. |
| Visual and accessibility | Required viewport/theme/state, keyboard/focus behavior, labels/roles, automated scan plus manual interpretation of exposed risks | Capture changed states and failures. Do not run every viewport or screenshot unrelated pages. |
| Security and isolation | Allowed/denied actors, foreign tenant and object references, privilege boundaries, private fields, failure state | Use controlled fixtures. Strong review covers the expected oracle independently. Keep every required denial. |
| Concurrency and resilience | Controlled conflicting operations, invariants after commit, rollback, retry and fault recovery | Deterministic barriers and bounded faults; distinguish one root failure from cascading case errors. |
| Performance | Fixed workload/data/hardware, baseline and changed revision, repetitions, latency percentiles, throughput and resources, explicit threshold | Timing from one run is not a regression proof. A model selects/interprets experiments; load tools generate load. |
| Build and runtime | Repository gates, diagnostics, natural exit when required, remaining sessions/handles, network and cleanup audit | Run affected checks and required aggregate gates once. Force exit is not proof of natural cleanup. |

For each check, record command or browser action, tested revision, dependency and fixture fingerprint, expected result, actual result, exit code, duration, and raw evidence path. A skipped required check is not passed. A high test count does not close a missing operation or requirement.

Store reports and generated output outside fingerprint inputs. Bind relevant source, lockfiles, configuration, schema, test code, fixtures, and runtime facts; list per file hashes and explicit exclusions. Do not hash an entire workspace by habit. If a prior contract requires broad hashing, preserve it until a change is approved. An input change creates a new evidence revision and invalidates only dependent checks.

Resolve the actual browser URL, then check driver access before reserving a business attempt.
Clear and read back the exact input before save. Capture the request and response before reload,
then verify the saved result. Keep service, port, fixture, and process ownership in the environment manifest.

Preflight required services and credentials once per changed environment. Keep secrets out of evidence. Before a sealed run, ensure no relevant source, build, or report writer is active. On drift, compare saved per file hashes and rerun the affected preparation, not all prior phases. Preserve failed results and old seals.
