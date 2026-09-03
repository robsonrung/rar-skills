# Scope contract

The scope contract is the partition of every changed file into three tiers, declared in `scope{}` **before** any persona launches. It is a promise about coverage, and the `coverage[]` array is the accounting against that promise.

## The three tiers

- **Will review** — every file with a meaningful change. Group files if it helps the reader, but each one is individually owed an outcome. Full coverage is mandatory: every will-review file must be examined by a persona and appear in `coverage[]` as `clean`, `finding`, or — with a note — `skipped`.
- **Spot-check** — mechanical bulk where per-file reading adds nothing: codemod output, import rewrites, the same config churn repeated across many files, generated-but-committed code. These get sampled, and the sampling is declared honestly — name the sample size and how instances were chosen (e.g. "4 of 37 files: the two largest diffs plus two picked blind"). Sampled files appear in `coverage[]` as `spot-checked`.
- **Won't review** — lockfiles, generated artifacts, vendored code, snapshots, pure-formatting churn. Each exclusion gets a one-line reason in `filesExcluded`.

## Honesty accounting

- If anything forces you to drop declared coverage — a failed persona, a timeout, a file too large to read — `coverage[]` says so with `outcome: "skipped"` and a `note` naming the cause. Silently skipping is a broken contract.
- The contract cannot be revised downward mid-run to look complete. Moving a file from will-review to won't-review after fan-out is the same broken contract wearing a different label; record the skip instead.
- Scale enumeration to the diff: up to ~100 changed files, list every file; above that, list directories or change-groups and name individual files only where grouping would mislead. A grouped entry still owes a coverage outcome per group.

## Tier placement guidance

| Signal | Tier |
| --- | --- |
| Hand-written source, tests, migrations, config with behavioural effect | Will review |
| Same one-line change repeated across many files by a tool | Spot-check |
| `*.lock`, `*.snap`, build output, `vendor/`, generated clients | Won't review |
| A "generated" file with hand edits in the diff | Will review — the hand edit is the change |
| Formatting-only churn mixed into a substantive file | Will review — the substantive part; say the noise was ignored |

When in doubt between tiers, place the file higher. The contract's cost is honesty, not effort: a spot-check honestly declared beats a will-review silently sampled.
