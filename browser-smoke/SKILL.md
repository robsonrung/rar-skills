---
name: browser-smoke
description: "Diff-scoped browser smoke test: map the files changed by a branch or PR to the routes that render them, then drive a real browser through each affected page to verify it loads and works. Use when the user asks to smoke test this branch/PR in the browser, test the affected pages, or run a diff-scoped browser test. Not qa-execution — that is whole-product persona/journey release QA; browser-smoke only smoke-tests the pages a diff touches."
argument-hint: "[PR number, branch name, 'current', or --port PORT]"
---

# Browser Smoke Test

Run end-to-end browser checks on the pages affected by a PR or branch, using the best browser driver available in the active harness.

## Modes

- **Manual (default):** the user controls the dev server.
- **Pipeline (`mode:pipeline`):** invoked by an automated pipeline (e.g. implement-and-review or ship). The run is unattended — never block on a question. Read `references/pipeline-orchestration.md` from this skill's directory and follow it; it overrides the dev-server verification (step 5) and any interactive prompts. It still uses the preferred port that step 4 computes.

## Browser Driver Policy

Select the driver before the first browser action:

1. **Prefer the in-app Browser tools** — the harness-native browser pane driven by `mcp__Claude_Browser__navigate`, `mcp__Claude_Browser__read_page`, `mcp__Claude_Browser__computer`, plus `read_console_messages`, `read_network_requests`, and `find`. It can navigate local URLs, inspect rendered and interactive state, click/fill/press, capture screenshots, and read console errors — everything this skill needs — and the user can watch progress in the pane.
2. **Otherwise fall back to the playwright MCP** (`mcp__playwright__browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_take_screenshot`, `browser_console_messages`, ...). If these tools are deferred, load them with a single `ToolSearch` call before starting.
3. **Do not introduce a third browser stack.** Never install standalone Playwright/Puppeteer, or substitute other ad hoc browser automation. (A standalone `agent-browser` CLI, if the user has one installed and asks for it, is an optional last resort — not a default.)

Use one driver for the entire run. Switching drivers is allowed only if initialization fails before the first route is tested. After testing begins, do not mix driver sessions, element references, screenshots, or authentication state.

## Workflow

### 1. Select the Browser Driver

Apply the Browser Driver Policy above and record the selected driver. This skill also requires a git repository with changes to test.

### 2. Determine Test Scope

**If PR number provided:**
```bash
gh pr view [number] --json files -q '.files[].path'
```

**If 'current' or empty:**
```bash
git diff --name-only main...HEAD
```

**If branch name provided:**
```bash
git diff --name-only main...[branch]
```

### 3. Map Changed Files to Routes

Map each changed file to the route(s) that render it, then build the list of URLs to test. The table below is a starting point of common patterns, not an exhaustive rule set — apply judgment for the project's actual layout:

| File Pattern | Route(s) |
|-------------|----------|
| `app/views/users/*` | `/users`, `/users/:id`, `/users/new` |
| `app/controllers/settings_controller.rb` | `/settings` |
| `app/javascript/controllers/*_controller.js` | Pages using that Stimulus controller |
| `app/components/*_component.rb` | Pages rendering that component |
| `app/views/layouts/*` | All pages (test homepage at minimum) |
| `app/assets/stylesheets/*` | Visual regression on key pages |
| `app/helpers/*_helper.rb` | Pages using that helper |
| `src/app/*` (Next.js) | Corresponding routes |
| `src/components/*` | Pages using those components |

### 4. Determine the Dev Server Port

Determine the preferred port using this priority:

1. **Explicit argument** — if the user passed `--port 5000`, use that directly.
2. **In-context project instructions** — if your active project instructions already in context explicitly state the dev-server port, use it. Don't grep instruction files for a port: prose mentions (docs, examples, troubleshooting) are unreliable and false-positive-prone — config files and `.env` are the trustworthy sources.
3. **package.json** — check dev/start scripts for `--port` flags.
4. **Environment files** — check `.env`, `.env.local`, `.env.development` for `PORT=`.
5. **Default** — fall back to `3000`.

```bash
# If your in-context project instructions state the dev-server port, set EXPLICIT_PORT first.
PORT="${EXPLICIT_PORT:-}"
if [ -z "$PORT" ]; then
  PORT=$(grep -Eo '\-\-port[= ]+[0-9]{4,5}' package.json 2>/dev/null | grep -Eo '[0-9]{4,5}' | head -1)
fi
if [ -z "$PORT" ]; then
  PORT=$(grep -h '^PORT=' .env .env.local .env.development 2>/dev/null | tail -1 | cut -d= -f2)
fi
PORT="${PORT:-3000}"
echo "Preferred dev server port: $PORT"
```

Manual mode uses this preferred port as-is — the user controls their own server, so do not scan for alternatives. In pipeline mode, `references/pipeline-orchestration.md` takes the preferred port value printed here and scans upward to a genuinely free port.

### 5. Verify the Dev Server Is Running

```bash
if lsof -i ":${PORT}" -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Server running on port ${PORT}";
else
  echo "Server not running on port ${PORT}";
  echo "Start your dev server, then re-run:";
  echo "  Rails: bin/dev  or  rails server -p ${PORT}";
  echo "  Node/Next.js: npm run dev";
  echo "  Custom port: run this skill again with --port <your-port>";
  exit 0;
fi
```

In pipeline mode, do not stop here — `references/pipeline-orchestration.md` auto-starts the server in the background instead.

### 6. Verify the Root

No visibility question is needed: the in-app Browser pane is always visible to the user (keep it non-blocking and do not repeatedly steal focus as routes change), and the playwright MCP fallback runs its own managed browser.

Use the selected driver to navigate to `http://localhost:<port>`, capture its rendered or interactive state (`read_page` / `browser_snapshot`), and confirm the root is served before iterating.

### 7. Test Each Affected Page

For each affected route, use the selected driver to navigate and capture fresh rendered or interactive state.

**Verify key elements:**
- Page title/heading present
- Primary content rendered
- No error messages visible
- Forms have expected fields
- No new console errors attributable to the tested flow

**Test critical interactions:** derive locators or element references from the selected driver's latest inspected state (`ref_N` from `read_page`/`find`, or snapshot refs in playwright), perform the click/fill/press action, then inspect the resulting state. Do not guess selectors or reuse stale references.

**Take screenshots:** capture viewport and full-page evidence when the selected driver supports it. Materialize screenshots as local artifacts when a later workflow or report needs file paths; otherwise in-app evidence is sufficient.

### 8. Human Verification (When Required)

Pause for human input when testing touches flows that require external interaction. **Pipeline mode:** do not pause — log each such flow as Skip with the reason and continue.

| Flow Type | What to Ask |
|-----------|-------------|
| OAuth | "Please sign in with [provider] and confirm it works" |
| Email | "Check your inbox for the test email and confirm receipt" |
| Payments | "Complete a test purchase in sandbox mode" |
| SMS | "Verify you received the SMS code" |
| External APIs | "Confirm the [service] integration is working" |

Ask the user with the harness's blocking question tool (in Claude Code, `AskUserQuestion` — load via `ToolSearch` with `select:AskUserQuestion` if its schema isn't loaded; otherwise present numbered options in chat and wait):

```
Human Verification Needed

This test touches [flow type]. Please:
1. [Action to take]
2. [What to verify]

Did it work correctly?
1. Yes - continue testing
2. No - describe the issue
```

### 9. Handle Failures

When a test fails (**pipeline mode:** do not ask how to proceed — capture the error screenshot and repro steps, log the failure, and continue):

1. **Document the failure:**
   - Capture a screenshot of the error state with the selected driver
   - Note the exact reproduction steps

2. **Ask the user how to proceed:**

   ```
   Test Failed: [route]

   Issue: [description]
   Console errors: [if any]

   How to proceed?
   1. Fix now - debug and fix the failing test
   2. Skip - continue testing other pages
   ```

3. **If "Fix now":** investigate, propose a fix, apply, re-run the failing test
4. **If "Skip":** log as skipped, continue

### 10. Test Summary

After all tests complete, present a summary:

```markdown
## Browser Test Results

**Test Scope:** PR #[number] / [branch name]
**Server:** http://localhost:${PORT}

### Pages Tested: [count]

| Route | Status | Notes |
|-------|--------|-------|
| `/users` | Pass | |
| `/settings` | Pass | |
| `/dashboard` | Fail | Console error: [msg] |
| `/checkout` | Skip | Requires payment credentials |

### Console Errors: [count]
- [List any errors found]

### Human Verifications: [count]
- OAuth flow: Confirmed
- Email delivery: Confirmed

### Failures: [count]
- `/dashboard` - [issue description]

### Result: [PASS / FAIL / PARTIAL]
```

## Quick Usage Examples

```bash
# Test current branch changes (auto-detects port)
/browser-smoke

# Test specific PR
/browser-smoke 847

# Test specific branch
/browser-smoke feature/new-dashboard

# Test on a specific port
/browser-smoke --port 5000
```

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
