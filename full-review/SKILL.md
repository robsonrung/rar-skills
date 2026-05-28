---
name: full-review
description: "Full-spectrum code review combining a swarm of parallel specialist agents, multi-model triangulation, execution-based bug verification, and ambitious structural maintainability review. Use when the user asks for PR review, commit review, deep review, ultrareview, bughunt, find bugs, find vulnerabilities, security review, thermonuclear review, code quality audit, maintainability audit, review my branch, review my changes, or any request for thorough actionable feedback on a diff."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# Full Review: Swarm-Based Code Review

## Goal

Produce the highest-signal review achievable by combining:

1. A wide-net bug-finding swarm across 6 exploit categories.
2. A judgment-intensive persona panel across 6 quality dimensions.
3. An ambitious structural quality pass that looks for simpler reframings, not just local cleanup.
4. Multi-model triangulation via external runners (Claude, Codex, Gemini).
5. Execution-based verification — every runtime candidate finding is tested by running code, not just reading it.
6. A 6-gate filtering pipeline that merges, deduplicates, and confidence-ranks survivors.
7. A clear verdict plus a bug summary line.

## Inputs

Accept one of:

1. PR number (preferred, via `gh`)
2. Commit SHA
3. Commit range
4. Local diff against base branch
5. Task-scoped file list: `Review task <TX> files: <file1>, <file2>, ...`

Accept `Quick review ...` as a prefix implying `quick_mode=true`.

## Branch Context (auto-injected)

**Current branch:** !`git branch --show-current`
**Changed files vs main:**
!`git diff --name-only main...HEAD 2>/dev/null || echo "(no changes detected vs main)"`
**Recent commits:**
!`git log --oneline -10 main..HEAD 2>/dev/null || echo "(no commits ahead of main)"`

## Configuration Knobs

| Knob | Default | Description |
|------|---------|-------------|
| `focus_paths` | — | Restrict review to these paths |
| `ignore_paths` | — | Exclude these paths |
| `max_comments` | 20 | Maximum comments to emit |
| `quiet_mode` | true | Suppress LOW-severity nitpicks |
| `quick_mode` | false | Security + runtime bugs + BC violations only, faster |
| `verify_mode` | true | Run execution-based verification (Phase 4). Disable in pure read-only environments |
| `confidence_threshold` | 0.65 | Drop comments below this score |
| `risk_tolerance` | normal | `low`, `normal`, or `high` |

## Quick Mode Behavior by Phase

| Phase | Normal Mode | Quick Mode |
|-------|-------------|------------|
| 0 — Repo calibration | Full calibration | Calibration only, skip skill loading |
| 1 — Collect context | Full context | Same |
| 2 — Gate review | Gate A + Gate B + structural quality | Gate A + security/runtime patterns only from Gate B |
| 3 — Swarm launch | All 12 agents + external models | 6 bug finders only + 1 external runner |
| 4 — Verification | Runtime findings verified; structural evidence checked | Skip verification; treat all as unverified |
| 5 — Synthesis | Full pipeline at `confidence_threshold` | Full pipeline at 0.8 |
| 6 — Final deliverables | Full report + JSON | Abbreviated report + full JSON |

## Outputs

Always produce two deliverables:

1. **Human report** — use `references/review_report_template.md`
2. **Machine JSON** — matching `references/review_output_schema.json`

At the end of the report, always include this summary line:

```
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```

## Workflow Overview

| Phase | Name | Description |
|-------|------|-------------|
| 0 | Repo calibration | Read rules, detect stack, classify areas |
| 1 | Collect context | Gather PR/commit data and diff |
| 2 | Two-gate review | Spec gate + quality gate + structural quality gate |
| 3 | Swarm launch | 12 agents + external models, all in parallel |
| 4 | Verification | Execution-based proof for runtime candidates and evidence checks for structural candidates |
| 5 | Synthesis & filtering | Merge, dedupe, confidence-filter |
| 6 | Final deliverables | Verdict, report, JSON |

## Host Compatibility

| Capability | Claude Code | Codex |
|------------|-------------|-------|
| Shell commands | `Bash` | `exec_command` |
| Native background subagent | `Agent` | Use runner-script path instead |
| Read persisted files | `Read` | `exec_command` (`cat`, `python3`) |
| Inline review UI | Normal review text or GitHub comments | `::code-comment` when supported |

When on Codex, do not require `Agent`, `TaskOutput`, or `Read`. Follow the runner-script path.

## Phase 0 — Repo Calibration

Read the closest relevant docs first:

- Root `AGENTS.md` and `CLAUDE.md`
- Deeper `AGENTS.md` / `CLAUDE.md` for each touched package
- `.claude/rules/multiverse-patterns.md`
- `.claude/rules/frontend.md`, `.claude/rules/backend.md`, `.claude/rules/database.md` when relevant
- `README`, `docs/`, CI configs, lint configs when they influence review expectations

Detect stack by lockfile (`bun.lock`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `poetry.lock`, `go.mod`, `Cargo.toml`, `Gemfile`).

Summarize as `rules_compact`: conventions, error handling style, testing expectations, layering boundaries, generated-file discipline, validation expectations.

Treat explicit repo rules as **hard constraints**.

### Multiverse Architecture Map

| Area | Path Hints |
|------|------------|
| Backend modules | `packages/backend-module-*/**`, `packages/backend-gateway/**`, `packages/backend-worker-*/**` |
| Backend shared libraries | `packages/backend-lib/**`, `packages/backend-lib-ts/**` |
| EntityGen surfaces | `packages/backend-module-*/schemas/entities/**`, generated GraphQL/proto/entity files, `policies/*.fga`, numbered migrations |
| Frontend web | `packages/frontend-web-console/src/**`, `packages/frontend-lib-api-client/**`, `packages/frontend-lib-ui-web/**` |
| Mobile | `packages/mobile-console/src/**` |
| Ops and infra | `packages/ops-*/**`, `packages/scripts/**` |
| Tests | `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*_test.go`, `packages/frontend-web-console/e2e/**` |

Apply area-specific checks: clean-architecture boundaries, auth-before-data, EntityGen drift as a blocker, React Query semantics, Jotai state conventions, RHF+Zod forms, Expo/React Native platform safety, infra-as-code discipline, behavior-first test assertions.

### Rule and Skill Loading

| Diff Contains | Load / Read |
|---------------|-------------|
| Backend Go, GraphQL, gRPC, persistence, events | `.claude/rules/backend.md`, `.claude/rules/database.md`, `.claude/rules/multiverse-patterns.md` |
| Frontend web React / GraphQL / routes | `packages/frontend-web-console/CLAUDE.md`, `.claude/rules/frontend.md`, `vercel-react-best-practices`, `vercel-composition-patterns` |
| Mobile React Native / Expo | `vercel-react-native-skills` |
| Entity schemas or generated surfaces | `entitygen-specialist` guidance + root `AGENTS.md` EntityGen policy |
| Backwards compatibility concerns | `check-backwards-compatibility` skill |
| New/upgraded external library | `find-docs` skill |
| Test-heavy diffs | nearby tests in the same package |

Do not reference skills that are not installed.

### Library/API Verification

When the diff introduces or modifies external library usage:

1. Prefer local evidence: typed interfaces, existing call sites, generated code, lockfile version.
2. If insufficient, use `find-docs` to retrieve current docs — especially for new deps, major version upgrades, or external API integrations.
3. If `find-docs` is unavailable, downgrade confidence and phrase as a question.

## Phase 1 — Collect Context

Prefer using `scripts/collect_context.sh`.

Determine the diff:
- PR number: `gh pr diff $target`, `gh pr view $target`, `gh pr view $target --comments` (to see existing discussion and avoid duplicating known issues)
- Branch: `git diff $target...HEAD`
- No target: `git merge-base main HEAD` (try `master` if needed), then `git diff <merge-base>...HEAD`

Run `git diff --name-only` to get the changed file list. If the diff is empty, tell the user and stop.

If reviewing a PR and `gh` is available, also gather existing inline review comments, issue comments, and bot comments — treat them as **candidates, not truth**. Skip issues already flagged by reviewers.

## Phase 2 — Two-Gate Review

### Gate A — Spec and Intent

- Confirm the diff matches the stated goal
- Look for missing requirements, risky scope creep, backwards-compatibility changes
- Flag unclear behavior; ask targeted questions and lower confidence rather than guessing

### Gate B — Code Quality (delegates to `quality-gate`)

Run the `quality-gate` skill against the diff. It checks 43 concrete error patterns across 10 categories. After the checklist pass, apply:

- Backwards-compatibility: `check-backwards-compatibility` seven rules — violations are blocking
- Library/API correctness: use `find-docs` for new external usage
- Architectural coherence: coupling, module boundaries, design intent
- Structural quality: read `references/structural_quality_review.md` and apply its stricter bar for maintainability regressions, file growth, branch explosion, wrong-layer ownership, unnecessary wrappers, cast-heavy contracts, and missed simpler reframings

Structural quality is not a style pass. Report only changed code that creates future change risk and has a concrete simpler path. Be ambitious: assume there is often a "code judo" move available, a re-organization that uses the existing architecture more effectively and makes the change dramatically simpler and more elegant.

In `quick_mode`, limit to security vulnerabilities, obvious runtime bugs, and BC violations only unless the user explicitly asked for a thermonuclear review, code quality audit, or maintainability audit.

## Phase 3 — Swarm Launch

This is the heart of full-review. All agents launch simultaneously in a **single parallel batch**. Do not wait for one group to finish before starting another.

### Shared Communication: Findings Collection

Each agent writes its findings to its own file under a shared directory:

```bash
FINDINGS_DIR="/tmp/full-review-findings-$(date +%s)"
mkdir -p "$FINDINGS_DIR"
echo "$FINDINGS_DIR"
```

Pass `$FINDINGS_DIR` to every agent. Each agent writes its candidate findings to `$FINDINGS_DIR/<agent-name>.json`. The verification phase (Phase 4) reads all files from this directory and merges them.

### Bug-Finding Agents (6) — launch all in parallel

See `references/bug_finders.md` for the full agent prompts, false positive awareness rules, and output format.

Each bug-finding agent covers one exploit category:

1. **Input Validation & Injection** — SQL/NoSQL injection, command injection, path traversal, template injection, XXE, SSRF, XSS, deserialization RCE
2. **Auth, Session & Crypto** — auth bypass, privilege escalation, missing authorization, session flaws, JWT issues, CORS, CSRF, hardcoded secrets, weak crypto, certificate bypass
3. **Logic & State** — race conditions, off-by-one errors, null dereference, state mutations, boolean logic errors, missing error handling, async/await mistakes
4. **Data, Resource & Exposure** — memory leaks, unbounded data structures, unclosed connections, N+1 queries, missing transactions, data loss, integer overflow, sensitive data logging, PII violations, API leakage
5. **Regression & Integration** — broken function signatures, removed exports, changed defaults, API contract changes, dependency breaking changes, config key renames
6. **Performance & Scalability** — unnecessary work on hot paths, missed concurrency, event loop blocking, quadratic algorithms, missing pagination, cache invalidation, connection exhaustion

Each bug finder reads the full diff and changed source files. Confidence threshold: report only at 0.8+.

### Review Persona Agents (6) — launch all in parallel alongside bug finders

See `references/panel_roles.md` for the full persona prompts.

Personas handle **judgment-intensive reasoning**, not pattern matching (that's the quality gate's job). Each persona focuses on its unique contribution:

1. **Spec Guardian** — intent mismatch, missing acceptance criteria, backwards compat
2. **Security Sentinel** — multi-step attack chains, injection, auth bypass, secret leakage
3. **Reliability Skeptic** — production failure scenarios, concurrency, timeouts, partial failures
4. **Performance Tuner** — N+1, caching, memory spikes, hot paths, algorithmic complexity
5. **Maintainer Gardener** — ambitious structural simplification, cohesion, abstraction boundaries, layer violations
6. **Test Cartographer** — test gaps, brittle tests, missing edge cases, coverage of risks

Tag each comment with the appropriate `source` field (`persona_spec`, `persona_security`, etc.).

The Maintainer Gardener must apply `references/structural_quality_review.md`. It should look for "code judo" moves that delete branches, modes, wrappers, casts, or helper layers while preserving behavior. Do not downgrade clear structural regressions into optional cleanup.

### Conditional Specialist Agents (0–6) — activate by file-path pattern

See `references/conditional_specialists.md` for full prompts.

| Diff Pattern | Specialist |
|---|---|
| `internal/migrations/`, `CREATE TABLE`, `ALTER TABLE`, `goose` | **Data Migration Reviewer** |
| `*.graphql` changes to existing types | **API Contract Reviewer** |
| `*.fga`, `AuthorizeInFacility`, `AuthorizeInOrg`, `GetUserFacilityIDs` | **Authorization Specialist** |
| `FindBy*` in loops, `for.*range.*repository`, bulk data operations | **Performance Analyst** |
| `tight_client`, `http.Client`, external API URLs, `grpc.Dial` | **Integration Reliability Reviewer** |
| `financial`, `payment`, `amount`, `cents`, `price`, `balance`, `debit`, `credit` | **Adversarial Tester** |

Multiple specialists can activate on the same diff. Each receives only the relevant diff subset plus `rules_compact`.

### Cross-Model Runners — launch simultaneously with the agent swarm

Do not wait for Phase 3 agents to finish before starting external models. All run in parallel.

Use `references/external_prompt_template.md` as the prompt template. Prepare a fully-substituted prompt file for each runner:

```bash
artifacts/full-review/external-prompt-codex.md
artifacts/full-review/external-prompt-gemini.md
artifacts/full-review/external-prompt-claude.md
```

Run runners in parallel with background processes. Redirect output to persistent files — never pipe runner output (`| head`, `| tee`) as it masks exit codes.

```bash
python3 .agents/skills/codex-runner/scripts/run_codex.py \
  --prompt-file artifacts/full-review/external-prompt-codex.md \
  --json --timeout 3600 \
  > artifacts/full-review/codex-output.json 2>&1 &
CODEX_PID=$!

python3 .agents/skills/gemini-runner/scripts/run_gemini.py \
  --prompt-file artifacts/full-review/external-prompt-gemini.md \
  --json --timeout 3600 \
  > artifacts/full-review/gemini-output.json 2>&1 &
GEMINI_PID=$!

wait $CODEX_PID; echo "codex exit: $?"
wait $GEMINI_PID; echo "gemini exit: $?"
```

When running inside Claude Code, prefer a native `Agent` subagent for the Claude seat instead of the CLI runner (runs in parallel with the bash runners).

| Running Inside | Call These Runners |
|----------------|-------------------|
| Claude Code | Codex + Gemini; use native `Agent` for Claude seat |
| Codex | Claude + Gemini |
| Gemini | Claude + Codex |
| Unknown | Any available (prefer 2+) |

If zero runners are available, lower all confidence scores by 0.1 in Phase 5 and note the limitation in the report.

Tag each comment with `source`: `external_codex`, `external_gemini`, `external_claude`.

In `quick_mode`: invoke at most 1 external runner.

## Phase 4 — Verification

This phase turns candidates into confirmed findings. Read all files from `$FINDINGS_DIR` and merge them — every candidate from every source in Phase 3 goes through verification, not just the bug finders.

Runtime, security, correctness, regression, performance, and reliability findings require execution-based proof. Structural maintainability findings are verified differently: measure file-size movement, inspect surrounding ownership boundaries, grep call sites, compare duplicate branches, and identify the smaller refactor path. Do not mark a structural finding `verified: true` unless a concrete run proves an associated behavior; otherwise keep the evidence in `problem`, `evidence`, `suggested_fix`, and `tests_to_run`.

For each runtime candidate finding:

1. **Read the relevant source code** to understand full context around the reported location.
2. **Write a minimal reproduction script** to `/tmp/full-review-verify-<id>.sh` or `.py`:
   - Injection: craft malicious input and pass through the vulnerable function
   - Auth: simulate a request without credentials, check if it succeeds
   - Logic: write a test with the boundary input that triggers wrong behavior
   - Resource: create/destroy in a loop, check for leaks
   - Regression: import the changed module, call with arguments existing callers use
   - Performance: benchmark or demonstrate the quadratic behavior
   - Reliability: simulate a timeout or partial failure, check recovery
3. **Run adversarial probes** appropriate to the finding type:
   - Concurrency: parallel requests to check for duplicate writes or lost updates
   - Boundary values: 0, -1, empty string, very long strings, unicode, MAX_INT
   - Idempotency: same mutating request twice — duplicates, errors, or correct no-op?
   - Orphan operations: reference IDs that don't exist — crash or graceful?
4. **Run existing tests** related to changed files.
5. **Mark each finding**:
   - **Verified** ✓ — reproduction succeeded, bug is real and triggerable. Boost confidence by +0.10.
   - **Refuted** ✗ — reproduction failed or defenses prevent it. Drop from report regardless of original confidence.

For each structural maintainability candidate:

1. Measure or inspect the concrete indicator: file length before/after, new branch count, duplicated block, wrapper layer, cast boundary, ownership leak, or partial update sequence.
2. Read enough surrounding code to confirm whether an existing helper, module, service, component, transaction boundary, or state model already owns the concept.
3. Keep the finding only when the simpler framing is concrete and behavior preserving.
4. Drop or downgrade the finding when it is mostly taste, broad architectural preference, or a refactor with no clear small path.

Apply the false positive awareness rules from `references/bug_finders.md` before marking any runtime, security, correctness, regression, performance, or reliability finding verified.

Before marking a runtime finding verified, check for defensive code elsewhere: upstream validation, downstream error recovery, global middleware, documented intentional behavior.

Spawn verification agents in parallel — batch related runtime candidates from the same file together to reduce context overhead.

**Rules**:
- Do NOT modify project files. Write scripts only to `/tmp` or `$TMPDIR`. Clean up when done.
- If you catch yourself writing "this looks like it could be a bug" for a runtime finding without running anything — stop. Run the code.
- If you can't reproduce a runtime finding after a genuine attempt, mark it refuted. Don't rationalize.
- If `verify_mode=false` or `quick_mode=true`, skip this phase. All candidates remain as unverified with their original confidence.

## Phase 5 — Synthesis & Filtering

Combine all candidate comments from:
- Quality gate findings (Phase 2 Gate B)
- Structural quality findings (Phase 2 Gate B)
- Bug-finding agents (Phase 3)
- Review personas (Phase 3)
- Conditional specialists (Phase 3)
- External model outputs (Phase 3)
- Your own orchestrator analysis

Verification results from Phase 4 are applied first:
- Refuted findings are **dropped**
- Verified findings get confidence boosted by +0.10 (already applied in Phase 4)
- Unverified findings (when `verify_mode=false`) proceed with original confidence

Apply the filtering pipeline from `references/filtering_pipeline.md`:

1. Normalize paths, severities, confidence
2. Evidence check — require path + line range + concrete indicator
3. Dedupe and merge — `corroborated_by` populated when sources agree on same location + category
4. Confidence filter — drop below threshold (default 0.65; quiet mode 0.70)
5. Risk-based cap — keep all CRITICAL/HIGH unconditionally; fill remaining slots with top-confidence non-blockers
6. Tone and clarity — explain why it matters, concrete fix steps, `tests_to_run`

If Phase 3 external triangulation was skipped, lower confidence cap by 0.1 for all remaining findings.

Never emit a comment without path and line range.

### Exclusion Rules

Do NOT report:
- Cosmetic style issues, TODO comments, broad refactor wishes, theoretical DoS, generic hardening requests, or ordinary suggestions for improvement
- Issues in code that was not changed by this branch (pre-existing bugs)
- Issues in test files or documentation files
- Issues already flagged by existing PR reviewers (gathered in Phase 1)

This exclusion does not suppress structural maintainability findings. If changed code creates a concrete architecture regression, crosses the 1000-line file threshold, adds spaghetti branching, leaks feature logic into shared paths, or misses an obvious simplification that would delete meaningful complexity, keep it in the review.

## Phase 6 — Final Deliverables

### Verdict Rules

| Condition | Verdict |
|-----------|---------|
| Any CRITICAL or HIGH remains | `REQUEST_CHANGES` |
| No blockers but meaningful MEDIUM exists | `COMMENT` |
| Only LOW or none | `APPROVE` |

Severity guidance:

| Severity | Meaning | Blocking |
|----------|---------|----------|
| CRITICAL | Security vulnerability, data-loss risk, or backwards-compatibility violation | Yes |
| HIGH | Runtime bug likely on a production path, or structural regression likely to block safe future changes | Yes |
| MEDIUM | Missing safeguard, significant pattern deviation, or localized maintainability regression | No |
| LOW | Minor clarity or optimization improvement | No |

### Human Report

Use `references/review_report_template.md`:

- Summary, walkthrough, key risks
- Test plan, top issues, questions

End with the summary line:

```
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```

If no bugs were verified, say the diff looks clean — do not manufacture findings. Optionally mention refuted candidates briefly so the user knows what was checked.

### JSON Output

Each comment includes `suggested_fix`, `prompt_for_agent` when a follow-up would help, `tests_to_run`, and `verified` (boolean) when Phase 4 ran. Match `references/review_output_schema.json`.

### Host-Specific Output

On Codex desktop, emit `::code-comment{...}` directives per retained finding. Keep machine JSON as the source of truth.

## Comment Writing Rules

| Field | Required | Description |
|-------|----------|-------------|
| `severity` | Yes | CRITICAL, HIGH, MEDIUM, LOW |
| `confidence` | Yes | 0.0 to 1.0 |
| `category` | Yes | spec, correctness, security, reliability, performance, maintainability, tests, docs, style, tooling |
| `path` | Yes | File path relative to repo root |
| `line_start` | Yes | First line of the issue |
| `line_end` | Yes | Last line of the issue |
| `title` | Yes | Short description |
| `problem` | Yes | What is wrong and why |
| `evidence` | Yes | Concrete code snippet or indicator |
| `suggested_fix` | Yes | How to fix it |
| `tests_to_run` | Yes | Commands or test names to validate |
| `verified` | When Phase 4 ran | Whether execution confirmed the bug |

Keep evidence snippets short. Prefer pointing to exact identifiers. Scope findings to the reviewed change. Name the violated rule when a finding depends on a repo-specific convention.

## Confidence Rubric

| Score | Meaning |
|-------|---------|
| 0.9+ | Deterministic bug, security flaw, or rule violation with direct evidence |
| 0.7–0.9 | Likely issue with strong indicators |
| 0.5–0.7 | Plausible risk — ask a question or suggest a defensive test |
| Below 0.5 | Do not comment unless explicitly requested |

For structural maintainability, use 0.85+ only when the changed line range, file-size movement, layer boundary, duplicate branch, wrapper, cast, or partial-update path is directly visible and the simpler refactor path is concrete. Otherwise downgrade to a question or suppress it.

Verified findings (Phase 4 reproduced) receive +0.10 boost. Corroborated findings (multiple sources) receive +0.05 per additional source.

## Helper Scripts

| Script | Purpose |
|--------|---------|
| `scripts/collect_context.sh` | Gather PR/commit/range context and diff |
| `scripts/diff_line_map.py` | Parse diff into structured JSON with file paths and line ranges |
