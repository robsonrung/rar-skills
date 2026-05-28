# External Model Review Prompt Template

<role>{role}</role>

<task>
Review this change set and produce a structured list of review comments.
</task>

<grounding_rules>
1. Each comment must include `path`, `line_start`, `line_end` — comments without line anchors will be discarded.
2. Provide `severity` (CRITICAL, HIGH, MEDIUM, LOW) and `confidence` (0 to 1).
3. Provide concrete fix steps in `suggested_fix` and specific test commands in `tests_to_run`.
4. Prefer high-signal issues — avoid nitpicks unless confidence >= 0.9 and the fix is trivial.
5. Be ambitious on structural quality. If changed code creates branch explosion, wrong-layer ownership, unnecessary wrappers, cast-heavy contracts, file growth past 1000 lines, or misses a clear code judo simplification, report it as maintainability with a concrete safer refactor path.
6. Output must be valid JSON matching `references/review_output_schema.json`.
7. If you cannot identify any issues, return: `{"comments": [], "verdict": "APPROVE", "summary": {"files_reviewed": 0, "issues_total": 0, "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}}`.
</grounding_rules>

<context>
PR or commit description:
```
{description}
```

Repo rules (compact):
```
{rules_compact}
```

Diff:
```diff
{diff}
```
</context>

{frontend_rules}

{test_quality_rules}

{library_usage_notes}

<structured_output_contract>
Return a JSON object with three top-level keys: `comments` (array), `verdict` (string), `summary` (object). Each comment must have: `id`, `severity`, `confidence`, `category`, `path`, `line_start`, `line_end`, `title`, `problem`, `evidence`, `suggested_fix`, `tests_to_run`. Add `prompt_for_agent` when a concrete follow-up implementation prompt would help.
</structured_output_contract>

---

## Template Variable Reference

### {frontend_rules}

Include this section **only when the diff touches frontend web or mobile files**. Otherwise, omit it entirely.

```
Frontend quality rules (apply to Multiverse frontend code in this diff):

Frontend web (`packages/frontend-web-console`, `packages/frontend-lib-*`):
- HIGH: Preserve TanStack Router route patterns and typed params
- HIGH: Keep API usage aligned with generated GraphQL operations/hooks and query invalidation patterns
- HIGH: Preserve loading, empty, and error states for user-visible data flows
- MEDIUM: Follow React Hook Form + Zod validation patterns where forms are touched
- MEDIUM: Keep Jotai and local module state scoped to the feature; avoid leaking feature logic into shared UI without a clear boundary
- MEDIUM: Preserve accessibility semantics from existing React Aria / UI component usage

Mobile (`packages/mobile-console`):
- HIGH: Preserve navigation and app lifecycle behavior
- HIGH: Guard async state updates and platform-specific flows
- MEDIUM: Avoid regressions in list rendering, offline/slow-network handling, and device permission flows
```

### {test_quality_rules}

Include this section **only when the diff touches test files** (`*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*_test.go`, `*.unit.test.ts`, `*.int.test.ts`). Otherwise, omit it entirely.

```
Test quality rules (apply to all test files in this diff):

Strong signals:
- as jest.Mock casts
- as never or as any casts in new test code
- mock-only assertions as the primary proof of behavior
- brittle time/order dependent setup without deterministic control

Review against nearby package patterns:
- Prefer behavior-first assertions over plumbing assertions
- Prefer the touched package's existing builders, factories, and helpers over ad hoc fixtures
- Match unit vs integration style to the code under test
- Add regression coverage for observed risk, not just happy paths

Go tests:
- Prefer targeted table-driven coverage when the package already uses it
- Check for deterministic clocks, stable fixtures, and explicit error assertions
```

### {library_usage_notes}

Include this section **only when the diff introduces new library imports or modifies library API usage**. Populate it from local type information, package source, or official docs. Otherwise, omit it entirely.

```
Library usage notes:
- [library name]: [specific finding about correct/incorrect API usage]
```
