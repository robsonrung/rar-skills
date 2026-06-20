# Script and Degrees-of-Freedom Standards

Read this when a skill bundles `scripts/`, or when deciding how much to constrain the host agent (text vs. pseudocode vs. script). The rest of authoring lives in `SKILL.md`.

## Degrees of Freedom

- Use text instructions when multiple approaches are valid and context should guide execution.
- Use pseudocode, examples, or parameterized commands when there is a preferred pattern with valid variation.
- Use scripts with narrow inputs when the workflow is fragile, error-prone, security-sensitive, or likely to be repeated.

## Script Standards

- Prefer a one-off pinned command when an existing tool with a few flags is enough.
- Move complex or repeatedly generated commands into `scripts/`.
- Reference bundled files with paths relative to the skill root.
- Make scripts non-interactive. Accept inputs through flags, environment variables, files, or stdin.
- Provide `--help` output with usage, flags, and examples.
- Send machine-readable results to stdout and diagnostics to stderr.
- Use clear error messages that say what failed, what was expected, and what to try next.
- Prefer structured output such as JSON, CSV, or TSV for data the agent will consume.
- Add idempotency and `--dry-run` support for stateful or destructive operations.
