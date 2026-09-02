# EDM decision brief

Fill every section. If a fact is inferred, prefix it with `assumed:`.

## Job

- Route: `new-system` | `existing-edm` | `migrate`
- Decision in one sentence:

## Verdict

`adopt` | `hybrid` | `hold` | `review-fix` | `migrate-slice`

## Data communication layer

What is (or would be) the stream-backed **single source of truth** for shareable domain data? If there isn't one, say why — a queue that deletes after consume, a shared DB, or a dump that is not authoritative.

## Single writer

Public stream → producing service → team. Name every **single writer** violation.

## Evidence

- Files / topics / schemas / connectors:
- `assumed:` constraints:

## Rejected

| Alternative | Cost of taking it |
| ----------- | ----------------- |
|             |                   |

At least one row required.

## Next move

One action. Not a program.

## Not this skill

Work that belongs to `macro-architecture`, `domain-driven-design`, or `data-systems-coding-lens`:
