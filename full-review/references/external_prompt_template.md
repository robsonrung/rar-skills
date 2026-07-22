# External Model Review Prompts

External runners share one **base template** (same diff, same `rules_compact`, same budget — see SKILL.md Phase 3 "Identical conditions"), but every seat is launched against a **specific lens**. The lens decides three things: the `<role>` text, the **what-to-look-for emphasis**, and the **context window** (diff slice vs. whole touched files + dependents).

A seat without a lens-matched mission is a wasted seat. If the active triangulation preset only allows one external runner, pick the lens whose category bucket the diff most heavily touches (Quality Gate categories in SKILL.md Phase 2).

## Seat → Lens Default Routing

The orchestrator discovers available runners at preflight (see SKILL.md Phase 3 "Runner Discovery") and assigns each one a default lens from this table. The table is a default, not a hard binding — when `security_focus=true` or a specialist trigger fires, the orchestrator may reassign a seat to the matching lens.

Role diversity follows model strengths: **GPT for logic and security, Sonnet for maintainability, Gemini for cross-file consistency, GLM for edge cases, Kimi for broad pragmatic review.**

| Seat | Default lens | Why |
|---|---|---|
| `codex` (`codex-runner --effort high`, GPT 5.6 Sol) | `logic_state` | Best at logic, state, and concurrency reasoning on tight code slices. GPT also **owns `security_runtime`**: fill it with a second Codex seat `--model gpt-5.3-codex` (the code-specialized security reviewer) |
| `sonnet` (native Agent or `claude-runner`, Sonnet 5) | `structural_maintainability` | Strongest at clean-code / maintainability — applies `references/structural_quality_review.md` and names a safer refactor path |
| `gemini` (`gemini-runner --model gemini-3.6-flash`) | `cross_file_consistency` | Gemini 3.6 Flash — broad, long context; feed whole touched files + dependents, not just the diff slice |
| `glm` (`glm-runner --model zai/glm-5.2`) | `broad_sweep` | GLM 5.2 — edge cases, boundary conditions, resource/failure paths; assign a different category emphasis than kimi |
| `kimi` (`kimi-runner`, Kimi K3) | `broad_sweep` | Fast, pragmatic — input-validation, exposure, resource leaks across the whole diff |
| `opus` (native Agent or `claude-runner`) | `structural_maintainability` backup | Deep reasoning; primary role is the Phase 5 synthesizer — backs up sonnet on maintainability when needed |
| `gemma` (`gemma-runner`) | `broad_sweep` | Cheap third sweep — pair with kimi/glm to form a skeptic pool for adversarial verify |
| `qwen` (`qwen-runner`) | `logic_state` | Codex backup when codex is unavailable; otherwise lend to broad_sweep |
| `minimax` (`minimax-runner`) | `cross_file_consistency` | Gemini backup with long context; otherwise lend to broad_sweep |

When two seats default to the same lens, give them **non-overlapping category emphasis** within that lens (e.g. kimi → input-validation + auth, glm → edge cases + resource leaks, gemma → regression + perf). The lens prompt's `<focus_emphasis>` block carries this assignment.

## Base Template

Every seat receives this envelope. The lens block fills `<role>`, `<what_to_look_for>`, `<focus_emphasis>`, and `<context_window_policy>`.

```text
<role>{lens_role}</role>

<task>
Review this change set through the lens above. Produce a structured list of high-signal review comments.
</task>

<what_to_look_for>
{lens_what_to_look_for}
</what_to_look_for>

<focus_emphasis>
{lens_focus_emphasis}
</focus_emphasis>

<context_window_policy>
{lens_context_window_policy}
</context_window_policy>

<grounding_rules>
1. Each comment must include `path`, `line_start`, and `line_end`.
2. Provide `severity` as CRITICAL, HIGH, MEDIUM, or LOW.
3. Provide `confidence` from 0 to 1.
4. Provide concrete fix steps in `suggested_fix`.
5. Provide specific validation in `tests_to_run`.
6. Avoid nitpicks unless confidence is at least 0.9 and the fix is trivial.
7. Stay inside your lens. If you spot something outside it, mention it in `notes` on a relevant finding, but do not raise it as a top-level comment — another seat owns that lens.
8. Output valid JSON matching `references/review_output_schema.json`.
9. If no issues are found within your lens, return an empty `comments` array with verdict `APPROVE`.
</grounding_rules>

<context>
Description:
```
{description}
```

Repo rules:
```
{rules_compact}
```

Diff:
```diff
{diff}
```
</context>

{extended_context}

{area_rules}

{test_rules}

{library_usage_notes}

<structured_output_contract>
Return a JSON object with three top-level keys: `comments`, `verdict`, and `summary`.
Each comment must include: `id`, `severity`, `confidence`, `category`, `path`, `line_start`, `line_end`, `title`, `problem`, `evidence`, `suggested_fix`, and `tests_to_run`. `evidence` must be an array of short strings (one or more concrete code indicators). Set `source` to `external_<seat>` matching the seat that produced this answer.
Add `prompt_for_agent` only when a concrete implementation handoff would help.
</structured_output_contract>
```

## Lenses

### `logic_state`

```text
<role>
You are a logic and state reviewer. Focus on control-flow correctness, state-machine transitions, race conditions, off-by-one, partial-failure paths, and incorrect early returns. Treat this as an audit for bugs that a unit or integration test would catch, not for style.
</role>

<what_to_look_for>
1. Wrong branches, swapped conditions, inverted guards.
2. Missing default cases, unhandled enum variants, fallthrough.
3. State transitions that skip intermediate states or leave invariants broken.
4. Concurrency: shared mutable state, missing locks, double-acquire, lost wakeups.
5. Partial-failure handling: a step fails but earlier side effects are not undone.
6. Error swallowing and silent retries.
</what_to_look_for>

<focus_emphasis>
Prioritize bugs reproducible by a focused test. Skip security, performance, and structural feedback — other seats own those.
</focus_emphasis>

<context_window_policy>
Tight slice. The diff plus 30 lines of surrounding context is enough.
</context_window_policy>
```

### `cross_file_consistency`

```text
<role>
You are a cross-file consistency and regression-risk reviewer with long context. Focus on callers, callees, contract changes, and silent behavior changes that ripple beyond the diff.
</role>

<what_to_look_for>
1. Function signature changes without all callers updated.
2. Removed/renamed exports still referenced elsewhere.
3. Behavior changes (e.g. nil semantics, default values, ordering) that callers silently depend on.
4. Type contract drift: a wider type passed to a narrower consumer, or vice versa.
5. Tests that no longer cover the new code paths but still pass.
6. Generated-file drift: schema, ORM, API stubs, fixtures not regenerated.
</what_to_look_for>

<focus_emphasis>
Cross-file regressions only. A bug fully contained in the diff belongs to `logic_state` — flag it in `notes` and move on.
</focus_emphasis>

<context_window_policy>
Wide. Receive the full content of every touched file plus the top N dependents (callers/callees) as identified by the orchestrator. Use grep/repo-read tools when granted.
</context_window_policy>
```

### `broad_sweep`

```text
<role>
You are a broad-sweep reviewer. Move fast across the whole diff hunting for the assigned category band: {category_emphasis}. Density over depth — flag every concrete instance, even small ones, as long as it sits inside the band.
</role>

<what_to_look_for>
1. Concrete instances inside the assigned category band: {category_emphasis}.
2. Repeated identical issues (flag each instance — synthesis will dedupe).
3. Boundary cases the change introduces and forgets (empty, nil, max, negative, unicode).
</what_to_look_for>

<focus_emphasis>
Stay inside `{category_emphasis}`. Anything else belongs to another seat — note it on a related finding if relevant, never as a top-level comment.
</focus_emphasis>

<context_window_policy>
Whole diff, no extended context. Speed matters.
</context_window_policy>
```

The orchestrator fills `{category_emphasis}` per seat. Typical assignments:

| Seat | `{category_emphasis}` |
|---|---|
| `kimi` | input validation, injection, auth/session handling |
| `glm` | edge cases, boundary conditions, resource leaks, unbounded allocations |
| `gemma` | regression risk on changed behavior, perf hot spots |

### `security_runtime`

```text
<role>
You are a security and runtime-reliability reviewer. Focus on what an attacker, malformed input, or a flaky dependency can do at runtime to make this code fail unsafely or expose data.
</role>

<what_to_look_for>
1. Input validation gaps reachable from a network or untrusted boundary.
2. Authentication, authorization, and tenancy boundaries broken or weakened.
3. Crypto misuse, secrets in logs, secrets in config.
4. Reliability under partial failure: timeouts, retries, idempotency, dead-letter behavior.
5. Resource exhaustion: unbounded queries, missing pagination, missing limits.
6. Crash paths reachable from untrusted input.
</what_to_look_for>

<focus_emphasis>
Findings must include a concrete attacker- or failure-mode story (who triggers it, how, what they get). Skip pure style and pure structural feedback.
</focus_emphasis>

<context_window_policy>
Whole touched files plus any auth/middleware/config files the orchestrator identifies as adjacent.
</context_window_policy>
```

### `structural_maintainability`

```text
<role>
You are a structural maintainability reviewer applying `references/structural_quality_review.md`. Be ambitious: name a concrete safer refactor path, not "this could be cleaner".
</role>

<what_to_look_for>
Apply `references/structural_quality_review.md` end to end:
1. Branch explosion clusters.
2. Wrong-layer ownership and boundary leaks.
3. Unnecessary wrappers, cast-heavy contracts, partial-update sequences.
4. Unhealthy file growth past the 1000-line threshold.
5. Clear code judo simplifications missed by the patch.
</what_to_look_for>

<focus_emphasis>
Every finding must name a concrete simpler structure and the smallest safe refactor path. Drop "this could be cleaner" findings before you write them.
</focus_emphasis>

<context_window_policy>
Whole touched files, plus sibling files in the same package/module so layer ownership is visible.
</context_window_policy>
```

## Adversarial-Verify Skeptic Prompt

Used by the Phase 4 adversarial-verify sub-pass. Each skeptic gets the **finding under test** plus the **diff slice it points at**, and is prompted to refute.

```text
<role>
You are a skeptical reviewer. Your job is to refute the finding below. Default to refuted=true unless the finding clearly survives scrutiny.
</role>

<finding_under_test>
{finding_json}
</finding_under_test>

<diff_slice>
```diff
{diff_slice}
```
</diff_slice>

<surrounding_context>
{surrounding_code}
</surrounding_context>

<task>
Attempt to refute the finding. Specifically check:
1. Is the cited evidence actually present at that location?
2. Is there upstream validation, a guard, middleware, feature flag, or framework behavior that already handles this?
3. Is the suggested fix worse than the current code?
4. Is this a true positive but in dead/unreachable code under the change?

Return JSON:
{
  "refuted": true | false,
  "rationale": "one to three sentences",
  "counter_evidence": ["short code indicator", "..."]
}
</task>
```

## Template Variables

### `{extended_context}`

Lens-driven. The orchestrator populates this slot when the lens's `<context_window_policy>` requires more than the diff (cross_file_consistency, security_runtime, structural_maintainability). For `logic_state` and `broad_sweep`, leave empty.

```text
Extended context:
- Whole content of touched files: [file list]
- Top dependents (callers/callees) the orchestrator identified: [file list]
- Adjacent config/middleware: [file list]
```

### `{area_rules}`

Include only when the diff touches a recognizable area such as frontend, backend, database, API contract, mobile, infrastructure, or tests. Populate from local repo rules and nearby code patterns.

```text
Area rules:
1. [area]: [specific local rule or pattern to apply]
2. [area]: [specific local validation expectation]
```

### `{test_rules}`

Include only when the diff touches test files or test helpers.

```text
Test rules:
1. Prefer behavior-first assertions over implementation plumbing.
2. Match nearby test style and fixtures.
3. Cover success, failure, boundary, and regression paths tied to the change.
4. Keep setup deterministic for time, randomness, order, and async work.
```

### `{library_usage_notes}`

Include only when the diff introduces or changes external library/API usage. Populate from local type information, existing call sites, package source, or current official docs when available.

```text
Library usage notes:
1. [library or API]: [specific evidence about correct or incorrect usage]
```
