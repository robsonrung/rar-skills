# Filtering Pipeline

Every candidate comment passes through these six stages in order. A comment that fails a stage is either dropped, downgraded, or converted to a question.

Verification results from Phase 4 are applied **before** this pipeline:
- Refuted findings are dropped immediately and never enter the pipeline.
- Verified findings have their confidence boosted by +0.10 (already applied during Phase 4).
- Unverified findings (when `verify_mode=false`) proceed with their original confidence.

---

## 1. Normalize

Standardize all fields before any comparison or filtering.

**Rules:**

| Field | Rule |
|---|---|
| `path` | Relative from repo root. Strip leading `./` or `/`. Use forward slashes. Example: `packages/backend-module-core/internal/domain/user.go` |
| `severity` | Uppercase enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`. Any other value is invalid — reject the comment. |
| `confidence` | Float clamped to `[0.0, 1.0]`. Round to two decimal places. Values outside the range are clamped. |
| `category` | Lowercase kebab-case. Example: `correctness`, `security`, `performance`, `style`, `test-quality`. |
| `line_start`, `line_end` | Positive integers. If `line_end < line_start`, swap them. If only `line_start` is set, `line_end` defaults to `line_start`. |

---

## 2. Evidence check

Each comment must cite:

- A `path` and a `line_start`..`line_end` range.
- A concrete indicator in the code — a variable name, function call, pattern, or literal snippet that proves the issue exists at that location.

For structural maintainability findings, the concrete indicator can be a file crossing the 1000-line threshold, new branch cluster, duplicated block, misplaced ownership boundary, unnecessary wrapper, cast-heavy contract, or partial-update sequence. The comment must also name the simpler framing; vague "this could be cleaner" comments fail this stage.

**Actions:**

- Comment has path + line range + concrete indicator: **keep**.
- Comment has path + line range but vague reasoning ("this looks wrong"): **convert to a question** (prefix with "Question:" and set severity to `LOW`).
- Comment lacks path or line range: **drop**.

---

## 3. Dedupe and merge

### Near-duplicate definition

Two comments are near-duplicates when **all three** conditions hold:

1. Same `path`.
2. Overlapping `line_start`..`line_end` ranges (any intersection counts).
3. Same `category`.

If two comments target the same lines but **different categories** (e.g., one `security`, one `correctness`), they are distinct findings — keep both.

### Merge rules

When merging near-duplicates:

1. **Keep** the comment with the highest `confidence`.
2. **Combine** `evidence` arrays from both comments (deduplicate identical strings).
3. **Use** the more specific `suggested_fix`. If one fix includes exact code and the other is prose, prefer the code.
4. **Expand** the line range to the union of both ranges.

### Source corroboration

When near-duplicates originate from **different sources** (bug finders, personas, external models):

1. Record all originating sources in the `corroborated_by` array on the surviving comment.
2. Boost `confidence` by `+0.05` for each additional corroborating source beyond the first.
3. Cap `confidence` at `1.0`.

Example: a comment found by the Architect (confidence 0.80) and the Security persona (confidence 0.75) merges to confidence `min(0.80 + 0.05, 1.0) = 0.85` with `corroborated_by: ["architect", "security"]`.

### Dedupe example

**Before (two candidate comments):**

```json
[
  {
    "path": "packages/backend-module-trade/internal/application/commands/create_order.go",
    "line_start": 42,
    "line_end": 48,
    "category": "correctness",
    "severity": "HIGH",
    "confidence": 0.82,
    "source": "persona_reliability",
    "evidence": ["uow.Commit is called but error return is ignored on line 47"],
    "suggested_fix": "Wrap the Commit call: `if err := uow.Commit(ctx); err != nil { return nil, err }`"
  },
  {
    "path": "packages/backend-module-trade/internal/application/commands/create_order.go",
    "line_start": 45,
    "line_end": 50,
    "category": "correctness",
    "severity": "HIGH",
    "confidence": 0.75,
    "source": "bug_finder_logic",
    "evidence": ["error from Commit on line 47 is discarded, transaction may silently fail"],
    "suggested_fix": "Check the error from Commit."
  }
]
```

**After merge (one surviving comment):**

```json
{
  "path": "packages/backend-module-trade/internal/application/commands/create_order.go",
  "line_start": 42,
  "line_end": 50,
  "category": "correctness",
  "severity": "HIGH",
  "confidence": 0.87,
  "corroborated_by": ["persona_reliability", "bug_finder_logic"],
  "evidence": [
    "uow.Commit is called but error return is ignored on line 47",
    "error from Commit on line 47 is discarded, transaction may silently fail"
  ],
  "suggested_fix": "Wrap the Commit call: `if err := uow.Commit(ctx); err != nil { return nil, err }`"
}
```

Confidence: `0.82 + 0.05 = 0.87` (one additional corroborating source). The more specific `suggested_fix` (with code) is kept. Line range is the union `[42, 50]`.

---

## 4. Confidence filter

Drop any comment whose `confidence` falls below the active threshold.

| Mode | Threshold | Exception |
|---|---|---|
| Default | `0.60` | None |
| Quiet | `0.70` | Keep `LOW` severity if `quick_win: true` |

Comments that survive this step proceed regardless of severity.

---

## 5. Risk-based cap

Enforce `max_comments` to keep reviews actionable, but never hide dangerous findings.

**Procedure:**

1. Partition surviving comments into two buckets: **blockers** (`CRITICAL` and `HIGH`) and **non-blockers** (`MEDIUM` and `LOW`).
2. All blockers are kept unconditionally, even if their count exceeds `max_comments`.
3. Fill remaining slots (`max_comments - blocker_count`) with non-blockers, sorted by `confidence` descending.
4. If `blocker_count >= max_comments`, emit all blockers and zero non-blockers. Add a summary note: _"N additional non-blocking findings were suppressed. Re-run with a higher max_comments to see them."_

---

## 6. Tone and clarity

Final pass over every surviving comment to ensure it is actionable and respectful.

**Each comment must include:**

- **Why it matters** — one sentence explaining the real-world consequence (data loss, crash, security exposure, maintenance burden).
- **Concrete fix steps** — exact code change, not just "fix this". Use fenced code blocks with the target language.
- **`tests_to_run`** — at minimum one command or test file path the author can run to verify the fix. Example: `nx run backend-module-trade:test -- --grep "CreateOrder"`.

Structural maintainability comments must include the current complexity, the future change risk, the proposed simpler structure, and the smallest safe refactor path. Suppress ordinary style feedback even when it passes the confidence threshold.

**Tone rules:**

- No accusatory language ("you forgot", "you should have"). Use neutral phrasing ("this path does not handle X", "consider adding Y").
- No hedging filler ("I think maybe", "it seems like perhaps"). State the finding directly.
- If confidence is below `0.75`, frame as a question: _"Is the intent here to skip validation when X is nil?"_
