# Bug Finder Agents

Six specialist agents launched in parallel during Phase 3. Each covers a distinct exploit/bug category.

---

## Mindset for All Bug Finders

Your job is not to confirm the code works — it's to try to break it. Don't just pattern-match against a checklist; actively reason about how inputs flow through the code and construct scenarios that would trigger a bug. If you can't articulate a concrete triggering scenario, it's not a real finding.

---

## False Positive Awareness (Apply Before Flagging Anything)

Before reporting a candidate, verify you haven't hit one of these common traps:

- React/Angular components are safe from XSS unless using `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, or `bypassSecurityTrustHtml`
- Environment variables and CLI flags are trusted values — attacks requiring control of env vars are invalid
- Client-side JS/TS doesn't need auth/permission checks — that's the server's job
- Shell scripts generally don't run with untrusted user input unless there's a clear path from external input
- UUIDs can be assumed unguessable
- Logging URLs is not a vulnerability (logging secrets/PII is)
- Test files and documentation files are not attack surface
- GitHub Actions workflows are generally not exploitable — only flag if untrusted input (e.g., PR title/body) flows directly into a dangerous operation
- Jupyter notebooks (`*.ipynb`) are rarely exploitable — only flag with a concrete untrusted-input attack path
- Memory safety issues (buffer overflows, use-after-free) are impossible in memory-safe languages (Go, Java, C#, Rust, etc.)
- Regex injection and regex DoS are not vulnerabilities — skip these
- Log spoofing (unsanitized user input in logs) is not a vulnerability — only flag if secrets/PII are logged
- Subtle/low-impact web vulnerabilities (tabnabbing, XS-Leaks, prototype pollution, open redirects) should not be reported unless confidence >= 0.9 with concrete impact
- Outdated third-party library vulnerabilities are managed separately — don't flag dependency versions
- A lack of hardening measures is not a bug — only flag concrete, exploitable vulnerabilities
- Including user-controlled content in LLM system prompts is not a code vulnerability
- Race conditions that are theoretical rather than practically triggerable should be skipped

**Research existing defenses before flagging.** Check whether the codebase already has security frameworks, middleware, decorators, or global guards that address the concern. Don't flag "missing auth on endpoint" if a global auth middleware already covers the route. Read the surrounding architecture, not just the diff.

---

## Agent 1: Input Validation & Injection Bugs

Search the diff for:

- SQL/NoSQL injection via unsanitized input
- Command injection in shell calls or subprocesses (string concatenation into exec/spawn/system calls)
- Path traversal in file operations (user input flowing into `fs.readFile`, `open()`, etc.)
- Template injection / eval injection
- XXE in XML parsing
- SSRF — only flag if attacker can control the host or protocol, not just the path
- XSS — reflected, stored, and DOM-based. Check `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `bypassSecurityTrustHtml`, or raw string interpolation into HTML. Skip if the framework auto-escapes (React JSX, Angular templates)
- Deserialization RCE — unsafe `pickle.loads()`, `yaml.load()` without SafeLoader, `eval(JSON.parse(...))`, `unserialize()` on untrusted input

For each candidate, trace the data flow from user input to the dangerous operation. Read the full function and its callers to confirm the input is actually user-controlled and not sanitized upstream. Skip if sanitized.

---

## Agent 2: Auth, Session & Crypto Bugs

Search the diff for:

- Authentication bypass (early returns, missing checks on new routes)
- Privilege escalation (role checks that can be circumvented)
- Missing authorization on new endpoints or actions
- Session management flaws (missing expiry, fixation, token reuse)
- JWT issues (algorithm confusion, missing signature validation, accepting expired tokens)
- CORS misconfigurations that expose sensitive endpoints
- CSRF vulnerabilities — missing anti-CSRF tokens on state-changing endpoints that use cookie-based auth
- Hardcoded API keys, passwords, tokens, or secrets in source code (not in test fixtures or env files)
- Weak cryptographic algorithms (MD5/SHA1 for security purposes, ECB mode, small key sizes)
- Improper key storage or management (keys in plaintext config, shared secrets in client bundles)
- Cryptographic randomness issues (`Math.random()` for security tokens, predictable seeds)
- Certificate validation bypasses (TLS verification disabled, `rejectUnauthorized: false`)

Read surrounding auth middleware / decorator / guard code before flagging.

---

## Agent 3: Logic & State Bugs

Search the diff for:

- Race conditions (check-then-act without locking, TOCTOU)
- Off-by-one errors in loops, slicing, pagination
- Null/undefined dereference on error or edge-case paths
- State mutations that skip validation or break invariants
- Incorrect boolean logic (inverted conditions, wrong operator precedence, short-circuit mistakes)
- Missing error handling that causes silent failures or swallowed exceptions
- Async/await mistakes (missing `await`, unhandled promise rejections, dangling promises)

---

## Agent 4: Data, Resource & Exposure Bugs

Search the diff for:

- Memory leaks (event listeners, timers, subscriptions, observers not cleaned up)
- Unbounded data structures (caches, arrays, maps that grow without eviction)
- File descriptors or DB connections not closed on error paths
- N+1 query patterns
- Missing transaction boundaries (partial writes on failure)
- Silent data loss (dropped rows, truncated fields, encoding errors)
- Integer overflow/underflow in arithmetic used for sizing or indexing
- Sensitive data logging — secrets, passwords, or PII written to logs (logging URLs or non-PII is fine)
- Debug information exposure in production (stack traces, internal paths, config dumps in error responses)
- PII handling violations (personal data stored unencrypted, retained beyond policy, sent to third-party without consent)
- API endpoint data leakage (returning more fields than the client needs, exposing internal IDs or metadata)

---

## Agent 5: Regression & Integration Bugs

Search the diff for:

- Changed function signatures that break existing callers — grep for every call site of modified functions
- Removed or renamed exports that other files import
- Changed default values that affect existing behavior
- API contract changes (response shape, status codes, headers, error format) without corresponding client updates
- Dependency version bumps with known breaking changes
- Config key renames without migration of existing configs

---

## Agent 6: Performance & Scalability Bugs

Search the diff for:

- Unnecessary work on hot paths — redundant computations, repeated file reads, duplicate API calls per request/render
- Missed concurrency — independent async operations run sequentially when they could use `Promise.all` or equivalent
- Blocking the event loop — synchronous I/O, CPU-heavy computation, or long-running loops on the main thread
- Quadratic or worse algorithms — nested loops over the same collection, repeated array scans, O(n) lookups that should be O(1) with a Set/Map
- Missing pagination — loading unbounded result sets into memory
- Cache invalidation bugs — stale data served after mutation, cache keys that don't account for all relevant state
- Connection/pool exhaustion — creating new connections per request instead of pooling, or not returning connections on error

---

## Output Format for All Bug Finders

Return a list of candidate bugs, each with:

```json
{
  "file": "path/to/file.go",
  "line": 42,
  "category": "injection",
  "summary": "one-line description",
  "triggering_scenario": "how an attacker or user would hit this",
  "confidence": 0.85,
  "source": "bug_finder_injection"
}
```

Only report candidates at confidence 0.8+. Write output to `$FINDINGS_DIR/<source-field-value>.json` (e.g., `$FINDINGS_DIR/bug_finder_injection.json`); the orchestrator passes the concrete `$FINDINGS_DIR` path in the seat prompt.

**Source field values per agent:**
- Agent 1: `bug_finder_injection`
- Agent 2: `bug_finder_auth`
- Agent 3: `bug_finder_logic`
- Agent 4: `bug_finder_data`
- Agent 5: `bug_finder_regression`
- Agent 6: `bug_finder_performance`
