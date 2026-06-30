---
name: full-review
description: "Full-spectrum code review combining parallel specialist review, multi-model triangulation, execution-based bug verification, and ambitious structural maintainability review. Use when the user asks to review a PR, commit, branch, or diff; to find bugs (bughunt); for a security review (find vulnerabilities); for a maintainability or code-quality audit; or for a deep/thorough review (ultrareview, thermonuclear review)."
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
| `confidence_threshold` | per mode | Override the active threshold from `references/filtering_pipeline.md` section 4 |
| `security_focus` | false | Prioritize the security dimension; optionally takes recorded security decisions to verify against |
| `triangulation` | per mode | External-runner posture: `off`, `light`, or `quality`. Defaults: `quick_mode` → `light`; ultra/thorough → `quality`; otherwise `quality` when ≥3 runner CLIs are present, else `light` |

When `security_focus=true` (set by the caller — e.g. a pipeline's `security-gate` for a `security: deep` change): treat any provided security decisions (recorded auth, validation, logging, and tenancy choices) as hard constraints and explicitly check the implementation against each; activate the `specialist_authorization`, `specialist_database`, and `specialist_data_integrity` specialists in Phase 3 regardless of trigger patterns; and never drop security-category findings to satisfy `max_comments`.

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

In quick mode, keep Phase 0 and Phase 1, narrow Phase 2 to security/runtime/compatibility blockers, run only bug finders plus the `triangulation: light` external panel in Phase 3, skip Phase 4 (both execution-based verify and the adversarial-verify sub-pass), and apply the quick-mode synthesis threshold from `references/filtering_pipeline.md` section 4. The fresh-model synthesizer in Phase 5 still runs.

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

Determine the diff with the matching `scripts/collect_context.sh` mode (`pr`, `commit`, `range`, `local`). If the script does not cover the input, replicate the equivalent commands for the matching mode in `scripts/collect_context.sh`. For branch or local review, find the merge base against the requested base branch, falling back from `main` to `master` when needed (the script defaults to `main` without fallback).

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

For structural quality, read `references/structural_quality_review.md` and apply its review stance and blocking bar.

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

Pass the concrete `$FINDINGS_DIR` path in every seat prompt. Each review seat writes candidate findings to `$FINDINGS_DIR/<seat-name>.json` (bug finders use their `source` field value as the seat name).

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

External runners are a panel of distinct-model reviewers, each assigned a **specific lens** rather than a generic role. The roster is data-driven from the runners present on the host — not a fixed three.

#### Runner Discovery

At preflight, run the shared probe and record the resulting seat table:

```bash
python3 .agents/skills/_shared/scripts/discover_runners.py probe \
  --native-agent yes \
  --format json
```

Pass `--native-agent yes` only when the host exposes the native `Agent` tool (Claude Code); otherwise pass `no` or omit. The script returns the JSON envelope documented in `_shared/scripts/discover_runners.py`: `seats[]` (each with `seat`, `execution_path`, `available`, `version`, `cli_path`, `blocked_reason`, `depends_on`, `notes`) plus `summary.light_quorum_met` and `summary.quality_quorum_met`. Use those fields directly — do not re-probe `PATH` inline.

The probe covers this default candidate set, in priority order:

| Seat | Execution path | Default lens |
|------|----------------|--------------|
| `opus` | native `Agent` subagent (`model: "opus"`) or `claude-runner --model claude-opus-4-8` | `structural_maintainability` |
| `sonnet` | native `Agent` subagent (`model: "sonnet"`) or `claude-runner --model claude-sonnet-5-0` | `security_runtime` |
| `codex` | `codex-runner --effort high` | `logic_state` |
| `gemini` | `gemini-runner` (Antigravity `agy`) | `cross_file_consistency` |
| `kimi` | `kimi-runner --model kimi-code/kimi-for-coding` | `broad_sweep` (input/auth) |
| `glm` | `glm-runner --model z-ai/glm-5.2` | `broad_sweep` (resources/exposure) |
| `gemma` | `gemma-runner` | `broad_sweep` (regression/perf) |
| `qwen` | `qwen-runner` | `logic_state` backup |
| `minimax` | `minimax-runner` | `cross_file_consistency` backup |

Mark seats with `available: false` as `unavailable` in your run config and continue. Never fail the review because a runner is missing.

#### Triangulation Preset

The `triangulation` knob selects how many seats run and which lenses are mandatory:

| Preset | Seats engaged | Lens coverage |
|---|---|---|
| `off` | none | Skip external runners entirely. Use only when the host has zero runners or the caller explicitly disables. |
| `light` | 2 cheap seats (kimi + glm, falling back to gemma/qwen) | `broad_sweep` only, with two non-overlapping `category_emphasis` assignments. Default for `quick_mode`. |
| `quality` | All available distinct seats, up to 6 | One seat per lens (`logic_state`, `cross_file_consistency`, `broad_sweep` ×1–3, `security_runtime`, `structural_maintainability`). Default otherwise. |

When `security_focus=true`, force the `security_runtime` lens to be filled even if it costs the `structural_maintainability` seat.

#### Quorum

Require **at least 3 distinct external seats** in `quality` mode (`light` requires 2). If quorum is not met:

1. Try to fill open lenses from the backup column of the discovery table.
2. If still under quorum, run with what is available, mark the review's confidence cap at `0.85` (no finding can exceed this), and record `triangulation: degraded` in the report.
3. In `quick_mode`, the quorum is **bypassed** — proceed with as few as one runner, and note the degraded posture.

The prior "lower the confidence cap by 0.1 when zero runners execute" rule is **removed**; the cap above is the single posture.

#### Seat → Lens Routing

For each engaged seat, the orchestrator picks a lens from `references/external_prompt_template.md` (seat → lens default table), then composes the base template with that lens's `<role>`, `<what_to_look_for>`, `<focus_emphasis>`, `<context_window_policy>`, and `{category_emphasis}` slot.

Two seats may share a lens (e.g. three `broad_sweep` seats) only when they receive non-overlapping `{category_emphasis}` values.

#### Identical Conditions

Every engaged seat receives **the same**:

1. Diff (and the same `{extended_context}` payload when the lens calls for it).
2. `rules_compact`.
3. Tool profile and budget.
4. `--disable-fallback` (or runner-equivalent) so a missing CLI does not silently borrow another provider.

Uneven access biases the panel and breaks the multi-model corroboration boost in synthesis.

#### Invocation

Use `references/external_prompt_template.md`, write composed prompts to files under `artifacts/full-review/`, redirect runner output to persistent files, and check exit codes explicitly. Launch all engaged seats **concurrently**.

For each successful runner:

1. Parse JSON against `references/review_output_schema.json`.
2. Tag comments with `external_<seat>` — the seat id from runner discovery (e.g. `external_opus`, `external_codex`, `external_gemini`, `external_kimi`, `external_glm`, `external_gemma`, `external_qwen`, `external_minimax`, `external_sonnet`).
3. Discard invalid JSON or nonzero exits and note the failure in the report.

## Phase 4: Verify

Apply verification before synthesis.

Start with a **pre-verify dedupe pass**: walk every candidate finding, group near-duplicates by `(path, line_range, category)` per `references/filtering_pipeline.md` section 3, and compute the `corroborated_models` count on each surviving candidate. This pass exists only to inform Phase 4 trigger decisions (the canonical dedupe + confidence boost run in Phase 5 — do not apply the confidence bumps here).

Runtime, security, correctness, regression, performance, and reliability findings require execution-based proof when `verify_mode=true`.

For each runtime candidate:

1. Read full local context around the reported location.
2. Check for upstream validation, downstream recovery, middleware, guards, feature flags, or documented intentional behavior.
3. Write minimal reproduction scripts only to `/tmp` or `$TMPDIR`.
4. Run the nearest existing tests or a targeted probe.
5. Mark as verified when reproduced, refuted when disproven, or unverified when execution is not possible.

Structural maintainability findings are evidence-checked rather than runtime-verified. Measure or inspect the concrete indicator per the evidence requirements in `references/structural_quality_review.md`. Keep only findings with a concrete safer refactor path.

Do not modify project files during verification.

### Adversarial-Verify Sub-Pass

After execution-based verification, hot single-model findings get a refute-by-default skeptic vote from the cheap pool (Kimi/GLM/Gemma) following `references/adversarial_verify.md`. Trigger conditions, skeptic selection, voting math, and the surviving-finding confidence delta live in that reference.

Run conditions in brief:

- Skip when `triangulation: off`.
- Trigger on `security|correctness|reliability|performance` findings at CRITICAL or HIGH severity with `corroborated_models == 1` and no Phase 4 verdict.
- Up to 10 findings per review enter this sub-pass; prioritize by severity, then confidence.

Refuted findings are dropped before Phase 5. Surviving findings carry `adversarial_verify` metadata into synthesis.

## Phase 5: Synthesize

Synthesis is delegated to a **fresh-model synthesizer**, not run inline by the orchestrator. The orchestrator assembles the inputs, the synthesizer applies the filtering pipeline and writes the final candidate list, and the orchestrator validates the output against the record.

### Synthesizer

A fresh read-only subagent context — default Opus 4.8 (`Agent` with `subagent_type=general-purpose`, `model: "opus"`) — receives:

1. All candidate comments from gates, bug finders, personas, specialists, external runners, and existing PR comments.
2. A per-finding **corroboration map** keyed by `(path, line_range, category)` showing every originating source and the `corroborated_models` count.
3. The `adversarial_verify` metadata block on findings that went through Phase 4's sub-pass.
4. `rules_compact` and `triangulation` posture (`off | light | quality | degraded`).
5. The current values of `max_comments`, `quiet_mode`, `quick_mode`, and `confidence_threshold`.

The synthesizer:

1. Applies `references/filtering_pipeline.md` end to end (normalize → evidence → dedupe + multi-model corroboration boost → confidence filter → risk-based cap → tone).
2. Suppresses cosmetic style, broad refactor wishes, generic hardening requests, pre-existing issues outside the diff, and already-raised issues.
3. Returns the final list of comments tagged with `source: synthesizer` only on net-new findings (rare — only when synthesis surfaces a missed cross-link); preserves the originating `source` and `corroborated_by` on every other comment.
4. Returns a short "synthesis log" describing which corroboration bumps and adversarial-verify drops were applied — this becomes the report's "Synthesis activity" section.

### Orchestrator Validation

The orchestrator does **not** rewrite the synthesizer's output prose. It validates:

1. Every emitted comment has `path`, `line_range`, and concrete evidence.
2. No comment was added with a stronger severity than its originating source justified (the corroboration-boost upgrade in `references/filtering_pipeline.md` section 3 is the only allowed bump path).
3. Refuted adversarial-verify findings are absent.
4. Counts in the human report match the JSON.

If validation fails, send the synthesizer one bounded repair round with the specific issue. Do not loop.

Structural findings are allowed when changed code meets the blocking bar and "What To Flag" criteria in `references/structural_quality_review.md`.

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

On hosts that support inline review output, mirror retained findings there. When mirroring findings as GitHub inline comments, follow `references/github_comment_format.md`. On Codex desktop, use `::code-comment{...}` directives. Keep the machine JSON as the source of truth.

## Confidence Rubric

| Score | Meaning |
|---|---|
| `0.9+` | Deterministic bug, security flaw, or rule violation with direct evidence |
| `0.7` to `0.9` | Likely issue with strong indicators |
| `0.5` to `0.7` | Plausible risk, question, or targeted defensive test |
| Below `0.5` | Weak signal — suppress unless explicitly requested. Scoring band only, not a second filter; the active filter threshold lives in `references/filtering_pipeline.md` section 4 |

Verification and corroboration boosts are applied per `references/filtering_pipeline.md`. For structural maintainability, use `0.85+` only when the evidence and simpler refactor path are concrete.

## Helper Scripts

| Script | Purpose |
|---|---|
| `scripts/collect_context.sh` | Gather PR, commit, range, or local diff context |
| `scripts/diff_line_map.py` | Parse diffs into structured file and line ranges |
| `_shared/scripts/discover_runners.py` | Standardized preflight probe used by Phase 3 to enumerate available runner seats |
