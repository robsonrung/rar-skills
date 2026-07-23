# Residual Review Findings — Durability Contract

Loaded by `ship` phase 6 whenever phase 5 review findings (from `full-review` or any reviewer in the verify chain) were **not applied** to the code. Those residuals must become durable before the slice is marked done. Ship is autonomous past the phase 2 gate, so this contract never prompts: the fallback chain executes silently and "no sink available" is a data-producing outcome, not a question.

## Contract

- Every unapplied actionable finding becomes durable: a tracker ticket, a committed record file, or both.
- Return a structured result to the pipeline:

  ```
  { filed:   [{ finding_id, tracker, url }],
    failed:  [{ finding_id, tracker, reason }],
    no_sink: [{ finding_id, title, severity, file, line }] }
  ```

- **Never a PR-body ledger.** Do not write residual findings into the PR description, and do not post a PR comment that duplicates the tickets — a PR-body ledger duplicates the tracker and goes stale as items resolve. The durable sinks are the filed tickets plus the committed record file, nothing else.
- Do not mark the slice done until residuals are durable. Once the record file is committed, a tracker filing failure never blocks done.

## Sink detection

Determine the project's tracker by reasoning over what is already in context — the project's active instructions and conventions first; supplementary signals only when that is ambiguous: `CONTRIBUTING.md`, `README.md`, PR templates under `.github/`, visible tracker URLs in the repo. A tracker may be reachable via MCP tool (e.g., a Linear MCP server), CLI (e.g., `gh`), or direct API — all acceptable. Detection output:

```
{ tracker_name, confidence, named_sink_available, any_sink_available }
```

- `tracker_name` — human-readable name, or `null` when none is identifiable.
- `confidence` — `high` only when documentation names the tracker unambiguously; otherwise `low`.
- `named_sink_available` — `true` only when the detected tracker can actually be invoked now (MCP tool discoverable and responsive, CLI authenticated, or API credentials present).
- `any_sink_available` — `true` when any tier of the fallback chain can be invoked this run.

## Probe timing and caching

Availability probes run **at most once per run** and **only when filing is imminent** — never speculatively at review start, never per finding. Cache the tuple and reuse it for every filing in the same run.

1. Probe the named tracker when one was detected. For GitHub Issues: `gh auth status` and `gh repo view --json hasIssuesEnabled`. For MCP-backed trackers: discover tools via the platform's tool-discovery primitive rather than assuming absence from an unloaded tool, then verify the tool responds. For API-backed trackers: verify credentials wherever the platform exposes them.
2. Probe the GitHub Issues fallback to compute `any_sink_available` (skip if `named_sink_available` is already `true`, or if `gh` was probed in step 1).

When a high-confidence named tracker fails at execution, downgrade its cached `named_sink_available` to `false` for the rest of the run — later filings fall straight through to the next tier. `any_sink_available` drops to `false` only when every tier is confirmed broken.

## Fallback chain

1. **Named tracker** (MCP, CLI, or API identified via detection).
2. **GitHub Issues via `gh`** — when authenticated and the repo has issues enabled.
3. **No sink** — findings land in the `no_sink` bucket; the committed record file below is their durable record.

On execution failure (API error, auth expiry, rate limit, rejected body), fall through to the next tier silently and record the failure. If every tier fails, the finding lands in `failed`; if no tier was ever available, in `no_sink`. Never retry a confirmed-broken sink within the run. An in-session task list is not a valid sink — it does not survive the session and never counts as durable filing.

## Ticket composition

- **Title:** the finding's title, prefixed nothing — short and searchable.
- **Body:** plain-English problem statement; suggested fix when present; evidence quotes from the review; source — a link to the PR when one exists at filing time, otherwise the branch and head commit SHA; metadata block with `Severity`, `Confidence`, `Reviewer(s)`, `Finding ID`.
- **Labels** (when supported): severity tag `P0`–`P3`.
- `finding_id` is a stable fingerprint: `normalize(file) + line_bucket(line, ±3) + normalize(title)`.
- When a body exceeds the tracker's limit, truncate with a pointer to the review run artifact and keep the finding_id in both body and metadata.

When uncertain, prefer "drop with explicit notice in the record file" over "pass through silently" — a residual with no durable artifact and no message is data loss.

## Committed record file

Whenever residuals exist, create or replace `docs/residual-review-findings/<branch-or-head-sha>.md` composed from the structured return:

- `filed` items: bullet with severity, file:line, title, and the ticket URL.
- `failed` items: bullet with severity, file:line, title, and the failure reason (e.g., `Defer failed: gh returned 401`).
- `no_sink` items: bullet with severity, file:line, and title inlined verbatim — the file is their only durable record.

Stage **only** that file, commit `docs(review): record residual review findings`, and push only when a remote is configured. In local-only mode (no `git remote`) the local commit is the durable sink — never retry a push and never block done on the missing remote. A push failure when a remote does exist is a stop-and-report.

## PR back-fill

Once the PR URL is known, back-fill it into each ticket in `filed` so every ticket links to the PR carrying the finding. Best-effort only — never block done on a failed ticket update.

---
*Adapted from Every's compound-engineering-plugin (`lfg`, `references/tracker-defer.md`).*
