# docs/solutions/ — the knowledge store

Durable, searchable documentation of solved problems and hard-won practices, written by the `capture-learning` skill (and editable by hand). Each doc lives in a category subdirectory (e.g. `runtime-errors/`, `tooling-decisions/`) and records one problem: what broke, what didn't work, the verified fix, and how to prevent recurrence — so the next occurrence takes minutes instead of research.

## Frontmatter contract

Every doc carries YAML frontmatter so agents can grep by field before reading bodies. The canonical contract — required fields, enum values, track rules (bug vs knowledge), and the problem_type → directory mapping — is `capture-learning/references/schema.yaml`, with a quick reference in `capture-learning/references/yaml-schema.md`. Hand-written docs must follow the same contract.

## One learning per run

Each `capture-learning` run documents exactly one solved problem. Multiple learnings from one session mean multiple sequential runs — never one batched doc or stitched cross-references between drafts.

## Pilot status and graduation signal

This store is a deliberate pilot: capture only. The refresh sibling — refresh-learnings, which would consolidate overlapping docs, fix drift, and bootstrap repo-wide vocabulary — gets built only after captured learnings are demonstrably retrieved and grounding later work (roughly within 30 days). Until then, capture-learning records refresh recommendations in its run reports and nothing acts on them automatically.

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
