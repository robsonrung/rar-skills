# Pipeline Server Procedure

Read this only for `mode:pipeline`.

Check driver readiness, then start the repository's documented local development server. Use the configured port when callbacks, CORS, or test configuration require it. Use another free port only when the documented startup supports that configuration. Capture stdout and stderr outside the project. Check the service readiness endpoint within 30 seconds; an open port alone is insufficient.

If the project has no documented local server command, return `SKIP` and name that missing command.

The caller may start a local server for this check. It does not authorize source, configuration, lockfile, or CI changes. Do not ask the user questions. Do not use an existing occupied port unless the caller supplied it as the target server.

If the server starts, record its port and continue with the browser workflow. If it does not start, stop browser work and return `SKIP` with the selected command, log tail, and untested route count. A pipeline run that exercises no route is never a pass.

For a flow that needs a person or external system, record `Skip` with the missing action and continue with independent routes.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._

## Owned environment and preflight

Keep one manifest with the worktree, source and dependency identities, service commands,
ports, process handles, fixture identity, driver transport, and captured readiness evidence.
Reuse a service only after its ownership and relevant identity match. Stop only owned resources.
Check browser access before expensive server preparation. No browser access means no business
interaction occurred. Record that preflight result separately; model calls still consume their budget.
For `validate-e2e`, use its `preflight` command and the same immutable input snapshot as the attempt.
Classify known baseline console and service errors before execution. A required failed gate stays
failed until its cause is fixed or the acceptance contract is explicitly changed.
