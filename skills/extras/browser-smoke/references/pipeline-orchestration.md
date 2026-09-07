# Pipeline Server Procedure

Read this only for `mode:pipeline`.

Start the repository's documented local development server on the first free port at or above the preferred port. Capture stdout and stderr in a temporary directory outside the project. Wait no more than 30 seconds for the port to listen.

If the project has no documented local server command, return `SKIP` and name that missing command.

The caller may start a local server for this check. It does not authorize source, configuration, lockfile, or CI changes. Do not ask the user questions. Do not use an existing occupied port unless the caller supplied it as the target server.

If the server starts, record its port and continue with the browser workflow. If it does not start, stop browser work and return `SKIP` with the selected command, log tail, and untested route count. A pipeline run that exercises no route is never a pass.

For a flow that needs a person or external system, record `Skip` with the missing action and continue with independent routes.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
