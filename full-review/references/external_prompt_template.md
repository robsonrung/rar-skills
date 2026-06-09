# External Model Review Prompt Template

<role>{role}</role>

<task>
Review this change set and produce a structured list of high-signal review comments.
</task>

<grounding_rules>
1. Each comment must include `path`, `line_start`, and `line_end`.
2. Provide `severity` as CRITICAL, HIGH, MEDIUM, or LOW.
3. Provide `confidence` from 0 to 1.
4. Provide concrete fix steps in `suggested_fix`.
5. Provide specific validation in `tests_to_run`.
6. Avoid nitpicks unless confidence is at least 0.9 and the fix is trivial.
7. Be ambitious on structural quality. If changed code creates branch explosion, wrong-layer ownership, unnecessary wrappers, cast-heavy contracts, unhealthy file growth, or misses a clear code judo simplification, report it as maintainability with a concrete safer refactor path.
8. Output valid JSON matching `references/review_output_schema.json`.
9. If no issues are found, return an empty `comments` array with verdict `APPROVE`.
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

{area_rules}

{test_rules}

{library_usage_notes}

<structured_output_contract>
Return a JSON object with three top-level keys: `comments`, `verdict`, and `summary`.
Each comment must include: `id`, `severity`, `confidence`, `category`, `path`, `line_start`, `line_end`, `title`, `problem`, `evidence`, `suggested_fix`, and `tests_to_run`. `evidence` must be an array of short strings (one or more concrete code indicators).
Add `prompt_for_agent` only when a concrete implementation handoff would help.
</structured_output_contract>

## Template Variables

### {area_rules}

Include only when the diff touches a recognizable area such as frontend, backend, database, API contract, mobile, infrastructure, or tests. Populate from local repo rules and nearby code patterns.

```text
Area rules:
1. [area]: [specific local rule or pattern to apply]
2. [area]: [specific local validation expectation]
```

### {test_rules}

Include only when the diff touches test files or test helpers.

```text
Test rules:
1. Prefer behavior-first assertions over implementation plumbing.
2. Match nearby test style and fixtures.
3. Cover success, failure, boundary, and regression paths tied to the change.
4. Keep setup deterministic for time, randomness, order, and async work.
```

### {library_usage_notes}

Include only when the diff introduces or changes external library/API usage. Populate from local type information, existing call sites, package source, or current official docs when available.

```text
Library usage notes:
1. [library or API]: [specific evidence about correct or incorrect usage]
```
