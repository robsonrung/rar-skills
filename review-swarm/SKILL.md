---
name: review-swarm
description: Cheap-first swarm review of a PR or diff — one inexpensive router seat reads the whole change, rates each region's blast radius, and delegates only the risky regions to stronger specialist seats, then posts findings as inline PR comments plus one upserted summary comment. Use when the user asks for a swarm review or qa swarm, a routed or cost-aware review, to review a PR and post the findings as comments, or as pr-shepherd's review step. Do not use for a maximal review of everything regardless of cost — that is full-review.
---

# Review Swarm

One cheap seat reads everything; strong seats read only what the router proves is risky. **Cheap-first** is the posture: for most diffs the router's own findings are the whole product, and delegating nothing is the cheap-first result, not a shortcut. **Blast radius** is the routing signal: every delegation names the region's blast radius and the trigger that set it.

Narrate the routing as you decide it: *"auth middleware changed — blast radius HIGH, delegating that hunk to the security seat"*, or *"rename-only diff — blast radius LOW, no delegation, cheap-first holds."*

## Inputs

Accept a PR number or URL (through `gh`), a commit range, or a local diff against a base branch.

| Knob | Default | Meaning |
|---|---|---|
| `post` | auto | Post to the PR when one exists and `gh` is authenticated; otherwise terminal report only |
| `max_comments` | 20 | Cap on posted inline comments, filled in severity order |
| `no_delegate` | false | Router pass only, regardless of blast radius (report what would have been delegated) |
| `public_repo` | auto-detect | When true, apply the metric-hygiene rule in `references/pr-posting.md` |

## Seats

Probe once at preflight with the shared discovery script:

```bash
python3 .agents/skills/_shared/scripts/discover_runners.py probe --native-agent yes --format json
```

| Role | Seat order (first available wins) | Why |
|---|---|---|
| Router | `glm` → `kimi` → `gemma` → native `sonnet` | Cheapest competent full-diff reader |
| Security delegate | `codex` (`--model gpt-5.3-codex`) → native `opus` | Code-specialized security review |
| Logic/state delegate | `codex` → `qwen` → native `opus` | Deep logic tracing |
| Structural delegate | native `sonnet` → native `opus` | Maintainability lens |
| Cross-file delegate | `gemini` → `minimax` → native `sonnet` | Long-context consistency |

A missing seat is reported absent and its role falls through the chain — never silently substituted (**seat fidelity**). With zero runner CLIs, the swarm still runs: router on native `sonnet`, delegates on native `opus`.

## Workflow

### 1. Collect

Gather the diff, changed-file list, commit messages, and PR description (`gh pr diff` / `gh pr view`, or `git diff <base>...HEAD`). Fetch existing review threads so the swarm does not re-raise a topic already under discussion. If the diff is empty, say so and stop.

### 2. Router pass

Run the router seat once over the full diff with the composed prompt from `references/router-prompt.md`. The router returns, as JSON:

1. Its own findings (it is a real reviewer, not just a dispatcher).
2. A region map — each region a file/hunk group with a blast radius and the trigger that set it.
3. Delegation requests — only for regions it cannot clear on its own.

### 3. Route by blast radius

| Blast radius | Trigger examples | Action |
|---|---|---|
| LOW | Renames, comments, small localized logic, config the router fully understands | No delegation — router findings stand |
| MEDIUM | Unfamiliar patterns, ~200–400 changed lines, one router finding needing a second opinion | Delegate the flagged regions to at most 2 lens-matched seats |
| HIGH | Auth, billing, schema, or concurrency touched; >400 lines; multiple unconfirmed findings | Delegate flagged regions; security and logic seats are mandatory |
| CRITICAL | Destructive migrations, secrets in the diff, data-loss paths | Stop swarm-side delegation and escalate the whole change to `full-review` (quality triangulation); fold its output into the summary |

The full rubric lives in `references/router-prompt.md`. The common case is LOW with zero delegations — treat that as success, not as skipped work.

### 4. Delegate

Launch all delegations concurrently. Each delegate receives only its region's diff slice plus the router's stated concern and any repo rules — not the whole diff. Delegates return findings in the same JSON shape as the router.

### 5. Synthesize

Merge all findings. Two findings at the same file within 5 lines describing the same concern collapse into one tagged `convergent: <seat1> + <seat2>` — convergence raises confidence and never lowers severity. Drop findings on lines the diff did not touch. Apply `max_comments` in severity order.

Verdict from the surviving set:

| Surviving findings | Verdict |
|---|---|
| Any CRITICAL | `BLOCKED` |
| ≥2 HIGH, or any convergent HIGH | `REQUEST CHANGES` |
| One uncorroborated HIGH, or ≥3 MEDIUM | `APPROVE WITH NITS` (name the HIGH prominently) |
| Only LOW/NIT or nothing | `APPROVE` |

### 6. Deliver

With a PR and `post` enabled, follow `references/pr-posting.md`: one COMMENT-event review carrying the inline findings, plus one summary comment upserted via the `<!-- review-swarm-summary -->` marker. Every posted body starts with the bot header from that reference. Without a PR, emit the same content as a terminal report.

The swarm never submits an approving or blocking GitHub review state — the verdict is text in the summary. Approval authority belongs to `approval-gate`.

## Finding format

Every finding: `path`, `line_start`, `line_end`, `severity`, `reviewer` (seat tag, e.g. `router/glm`, `security/codex`), `confidence` (0–1), `problem`, `evidence`, `suggested_fix`.

| Severity | Meaning |
|---|---|
| CRITICAL 🔴 | Security vulnerability, data loss, destructive operation |
| HIGH 🟠 | Runtime bug on a likely path, compatibility break |
| MEDIUM 🟡 | Missing safeguard, meaningful pattern deviation |
| LOW 🟢 | Minor clarity or robustness improvement |
| NIT ⚪ | Style-level; posted only when comment budget remains |

## Gotchas

1. Do not run every seat on every diff to be safe — that is `full-review`'s job; the swarm's value is what it does **not** spend. Delegating nothing is the cheap-first result.
2. The router must justify every delegation with a named blast radius trigger; "just in case" is not a trigger.
3. Delegates get region slices, not the whole diff — a delegate reading everything is the cost model failing silently.
4. Do not re-post a concern that an existing unresolved thread already covers; add to the summary's "already under discussion" list instead.
5. Re-runs upsert the summary comment; never create a second summary.
6. On public repos, never post absolute production metrics (event counts, revenue, user counts) — percentages and ratios only.
