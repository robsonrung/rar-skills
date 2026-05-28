---
name: full-review
description: "Full-spectrum code review combining parallel specialist review, multi-model triangulation, execution-based bug verification, and ambitious structural maintainability review. Use when the user asks for PR review, commit review, deep review, ultrareview, bughunt, find bugs, find vulnerabilities, security review, thermonuclear review, code quality audit, maintainability audit, review my branch, review my changes, or thorough actionable feedback on a diff."
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---

# Full Review

Run a high-signal, evidence-backed review of a pull request, commit, branch, local diff, or task-scoped file set. Favor concrete bugs, security issues, backwards-compatibility breaks, production risks, and structural maintainability regressions over cosmetic feedback.

## Inputs

Accept one of:

1. PR number, preferably through `gh`.
2. Commit SHA.
3. Commit range.
4. Local diff against a base branch.
5. Task-scoped file list, such as `Review task <TX> files: <file1>, <file2>, ...`.

Treat `Quick review ...`, `Quick review commit <hash>`, and `Quick review task <TX> files: ...` as `quick_mode=true`.

Use these knobs when requested or when context makes them obvious:

| Knob | Default | Meaning |
|---|---|---|
| `focus_paths` | none | Restrict the review to selected paths |
| `ignore_paths` | none | Exclude selected paths |
| `max_comments` | 20 | Maximum emitted comments |
| `quiet_mode` | true | Suppress low-value LOW severity comments |
| `quick_mode` | false | Review only security, runtime, and compatibility blockers |
| `verify_mode` | true | Run verification where execution is possible |
| `confidence_threshold` | 0.65 | Drop comments below this score |

## Output Contract

Always produce:

1. A human report using `references/review_report_template.md`.
2. Machine JSON matching `references/review_output_schema.json`.

End the human report with:

```text
Bugs found: N | Verified: X | Refuted: Y | Verdict: APPROVE|COMMENT|REQUEST_CHANGES
```

## Workflow

| Phase | Name | Purpose |
|---|---|---|
| 0 | Calibrate | Read repo rules, detect stack, classify touched areas |
| 1 | Collect context | Gather description, file list, diff, and existing review comments |
| 2 | Gate review | Check intent, compatibility, library/API use, and structural quality |
| 3 | Parallel review | Run bug finders, personas, specialists, and external runners |
| 4 | Verify | Reproduce runtime findings and evidence-check structural findings |
| 5 | Synthesize | Merge, dedupe, confidence-filter, and cap findings |
| 6 | Deliver | Emit verdict, report, JSON, and inline comments when supported |

In quick mode, keep Phase 0 and Phase 1, narrow Phase 2 to security/runtime/compatibility blockers, run only bug finders plus at most one external runner in Phase 3, skip Phase 4, and raise the synthesis threshold to `0.8`.

## Phase 0: Calibrate

Read only the guidance that affects reviewed files:

1. Root and nearest nested `AGENTS.md`, `CLAUDE.md`, or equivalent repo instructions.
2. Nearby package docs, README files, architectural docs, CI config, lint config, formatter config, and test config.
3. Generated-code policies, API contracts, migrations, schema docs, and ownership boundaries when the diff touches them.

Detect stack from local evidence such as lockfiles, manifests, module files, package manager files, framework config, and nearby tests.

Summarize `rules_compact` with:

1. Relevant coding conventions.
2. Error-handling style.
3. Testing expectations.
4. Layering and ownership boundaries.
5. Generated-file discipline.
6. Validation commands.

Treat explicit repo rules as hard constraints. Do not reference skills, tools, packages, or docs that are not present or available in the current environment.

## Phase 1: Collect Context

Prefer `scripts/collect_context.sh` when it covers the input.

Minimum context:

1. PR, commit, branch, or task description.
2. Changed file list.
3. Unified diff.
4. Surrounding code for touched functions, classes, routes, queries, migrations, tests, or config.

Determine the diff:

1. PR number: collect `gh pr view`, `gh pr diff`, existing comments, and review threads when `gh` is available.
2. Commit SHA: collect `git show --no-patch --pretty=fuller <sha>`, `git show --patch --unified=3 <sha>`, and `git show --name-only --pretty="" <sha>`.
3. Commit range: collect `git diff <range> --unified=3` and `git diff <range> --name-only`.
4. Branch or local changes: find the merge base against the requested base branch, falling back from `main` to `master` when needed.

If the diff is empty, say so and stop.

Treat existing PR comments as candidates, not truth. Avoid duplicating issues already raised unless adding verification or a materially better fix.

## Phase 2: Gate Review

Run a first pass before launching specialists.

### Intent Gate

Check whether the diff matches the stated goal. Look for missing requirements, scope creep, silent behavior changes, and backwards-compatibility breaks.

If intent is unclear, ask a targeted question or lower confidence. Do not invent requirements.

### Quality Gate

Check the diff for:

1. Correctness bugs.
2. Security issues.
3. Reliability and partial-failure risks.
4. Performance and scalability regressions.
5. API, data, schema, and configuration compatibility breaks.
6. Test gaps around changed behavior.
7. Library or external API misuse.
8. Structural maintainability regressions.

For new or changed external library usage, prefer local type information and existing call sites. If local evidence is insufficient and current docs are available through approved tooling, verify the API before asserting misuse. If docs are unavailable, downgrade confidence and phrase the issue as a question.

For structural quality, read `references/structural_quality_review.md`. Be ambitious. Assume there is often a "code judo" move available: a re-organization that uses the existing architecture more effectively and makes the change dramatically simpler and more elegant.

For tests, compare against nearby examples before flagging style-level issues. Prefer behavior and regression coverage findings over generic mocking or naming feedback.

## Phase 3: Parallel Review

Run all relevant review seats in one parallel batch when the host supports it.

### Findings Directory

Use a shared findings directory:

```bash
FINDINGS_DIR="/tmp/full-review-findings-$(date +%s)"
mkdir -p "$FINDINGS_DIR"
echo "$FINDINGS_DIR"
```

Each review seat writes candidate findings to `$FINDINGS_DIR/<seat-name>.json`.

### Bug Finders

Run the six bug finders from `references/bug_finders.md`:

1. Input validation and injection.
2. Auth, session, and crypto.
3. Logic and state.
4. Data, resource, and exposure.
5. Regression and integration.
6. Performance and scalability.

Only report candidates with confidence `0.8` or higher.

### Personas

Run the six personas from `references/panel_roles.md`:

1. Spec Guardian.
2. Security Sentinel.
3. Reliability Skeptic.
4. Performance Tuner.
5. Maintainer Gardener.
6. Test Cartographer.

The Maintainer Gardener must apply `references/structural_quality_review.md` and must not downgrade clear structural regressions into optional cleanup.

### Conditional Specialists

Activate specialists from `references/conditional_specialists.md` only when the diff matches their trigger patterns. Give each specialist only the relevant diff subset plus `rules_compact`.

Tag specialist findings with `specialist_database`, `specialist_api_contract`, `specialist_authorization`, `specialist_performance`, `specialist_integration`, or `specialist_data_integrity`.

### External Runners

Invoke at least two external runners when available. Use `references/external_prompt_template.md`, write prompts to files under `artifacts/full-review/`, redirect runner output to persistent files, and check exit codes explicitly.

Never fail the review because an external runner is unavailable. If zero external runners execute, note that triangulation was unavailable and lower the confidence cap by `0.1` in synthesis. If exactly one external runner executes, note partial triangulation without changing confidence handling.

For each successful runner:

1. Parse JSON against `references/review_output_schema.json`.
2. Tag comments with `external_claude`, `external_codex`, or `external_gemini`.
3. Discard invalid JSON or nonzero exits and note the failure in the report.

## Phase 4: Verify

Apply verification before synthesis.

Runtime, security, correctness, regression, performance, and reliability findings require execution-based proof when `verify_mode=true`.

For each runtime candidate:

1. Read full local context around the reported location.
2. Check for upstream validation, downstream recovery, middleware, guards, feature flags, or documented intentional behavior.
3. Write minimal reproduction scripts only to `/tmp` or `$TMPDIR`.
4. Run the nearest existing tests or a targeted probe.
5. Mark as verified when reproduced, refuted when disproven, or unverified when execution is not possible.

Structural maintainability findings are evidence-checked rather than runtime-verified. Measure or inspect the concrete indicator: file size movement, new branch clusters, duplicated blocks, wrappers, casts, ownership leaks, or partial-update flows. Keep only findings with a concrete safer refactor path.

Do not modify project files during verification.

## Phase 5: Synthesize

Combine candidate comments from all gates, bug finders, personas, specialists, external runners, existing PR comments, and orchestrator analysis.

Apply `references/filtering_pipeline.md`:

1. Normalize fields.
2. Require path, line range, and concrete evidence.
3. Dedupe by path, overlapping line range, and category.
4. Merge corroborated sources.
5. Drop comments below the active confidence threshold.
6. Keep all CRITICAL and HIGH findings even when over `max_comments`.
7. Suppress cosmetic style, broad refactor wishes, generic hardening requests, pre-existing issues outside the diff, and already-raised issues.

Structural findings are allowed when changed code creates a concrete architecture regression, crosses a healthy file-size threshold, adds tangled branching, leaks feature logic into shared paths, or misses an obvious simplification that would delete meaningful complexity.

Never emit a comment without path and line range.

## Phase 6: Deliver

Verdict rules:

| Condition | Verdict |
|---|---|
| Any CRITICAL or HIGH finding remains | `REQUEST_CHANGES` |
| No blockers but meaningful MEDIUM findings remain | `COMMENT` |
| Only LOW findings or no findings remain | `APPROVE` |

Severity guidance:

| Severity | Meaning |
|---|---|
| CRITICAL | Security vulnerability, data-loss risk, or compatibility break |
| HIGH | Runtime bug on a likely path, or structural regression that blocks safe future changes |
| MEDIUM | Missing safeguard, meaningful pattern deviation, or localized maintainability regression |
| LOW | Minor clarity or optimization improvement |

Each comment must include `severity`, `confidence`, `category`, `path`, `line_start`, `line_end`, `title`, `problem`, `evidence`, `suggested_fix`, and `tests_to_run`. Include `verified` when Phase 4 ran.

Keep evidence snippets short. Prefer exact identifiers. Scope findings to the reviewed change. Name the violated local rule when a finding depends on repo-specific convention.

On hosts that support inline review output, mirror retained findings there. On Codex desktop, use `::code-comment{...}` directives. Keep the machine JSON as the source of truth.

## Confidence Rubric

| Score | Meaning |
|---|---|
| `0.9+` | Deterministic bug, security flaw, or rule violation with direct evidence |
| `0.7` to `0.9` | Likely issue with strong indicators |
| `0.5` to `0.7` | Plausible risk, question, or targeted defensive test |
| Below `0.5` | Suppress unless explicitly requested |

Verified findings receive `+0.10`. Corroborated findings receive `+0.05` per additional independent source. For structural maintainability, use `0.85+` only when the evidence and simpler refactor path are concrete.

## Helper Scripts

| Script | Purpose |
|---|---|
| `scripts/collect_context.sh` | Gather PR, commit, range, or local diff context |
| `scripts/diff_line_map.py` | Parse diffs into structured file and line ranges |
