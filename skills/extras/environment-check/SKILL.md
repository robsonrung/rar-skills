---
name: environment-check
description: "Check local prerequisites and present the result. Use when the user asks to check the environment, verify machine setup, diagnose a missing tool, or confirm this machine can run the skills. Read-only: it installs nothing, calls no provider, and never auto-fixes."
---

# Environment Check

Run the shared checker and present what it reports:

```bash
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/scripts/check_environment.py" --json [--project <repo>] [--browser auto|playwright-cli|agent-browser|none] [--native-models]
```

Add a flag only when the user's context calls for it. If `python3` is missing or older than 3.11, nothing ran: point to section 1 of `docs/machine-setup.md` and stop.

Lead with `summary.status`, then a table of `checks` (MISSING, then WARN, then OK, optional checks labelled), then each non-empty `action` verbatim, then `limits`. Actions are for the user; run no install, login, or browser launch for them.

**Green only from a fresh run**: a check is OK only because this run's output says so, never from memory, an earlier session, or the user's word. After the user acts, run it again.
