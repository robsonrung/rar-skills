---
name: environment-check
description: "Check local prerequisites and present the result. Use when the user asks to check the environment, verify machine setup, diagnose a missing tool, or confirm this machine can run the skills. Read-only: it installs nothing, calls no provider, and never auto-fixes."
---

# Environment Check

Run the repository's environment checker and present its report. No model
worker: the coordinator runs one direct command, so the model preview resolves
to **No additional model worker** and adds no approval gate.

## Run

From the rar-skills checkout (resolve the actual path; in a target project
using installed skills, use the checkout recorded at install time):

```bash
bash scripts/check-environment.sh --json
```

Add flags only when the user's context calls for them:

- `--project /absolute/path/to/repo` when the user asks about a specific project.
- `--browser auto|playwright-cli|agent-browser|none` when browser work matters;
  the mode-selection rule applies — ask which browser mechanism to check unless
  the user already named one.
- `--native-models` when the user relies on host model access instead of
  external CLIs.

If the script reports that Python is missing, present its printed
instructions verbatim and stop; the remaining checks did not run.

## Present

Parse the JSON and show:

1. **Verdict line** from `summary.status`:
   - `local_checks_passed` — every required check is OK.
   - `needs_verification` — nothing missing, but named warnings need the
     user's action or a live test.
   - `missing_requirements` — required tools are absent; setup is incomplete.
2. **Check table**: one row per entry in `checks` — status (OK / WARN /
   MISSING), name, whether it is required, and its `detail`. Group MISSING
   first, then WARN, then OK. Do not drop optional checks; label them.
3. **Actions**: for every WARN or MISSING row with a non-empty `action`,
   list the action verbatim, numbered, in check order. These are instructions
   for the user — do not execute installs, logins, or browser launches on
   their behalf.
4. **Limits**: show the `limits` list so the user knows what was not tested
   (no provider request, no installation, no login; a present credential is
   not a valid one).

Keep the report to the verdict, the table, the actions, and the limits. Point
to `docs/machine-setup.md` for setup detail.

The load-bearing rule is **green only from a fresh run**: a check is OK only
because this invocation's output says so. Never carry a green forward from
memory, an earlier session, or the user's claim; suggest re-running after the
user completes an action and report only what the new output shows.
