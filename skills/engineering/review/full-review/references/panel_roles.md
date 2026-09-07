# Review concern prompts

Use only concerns selected by the approved review plan. The table does not create a panel.

| Concern | Review question |
| --- | --- |
| Specification | Does the changed behavior meet the stated acceptance contract without unrelated scope? |
| Security | Can untrusted input, identity, privilege, data, or secrets cross a boundary unsafely? |
| Reliability | Does failure, retry, timeout, ordering, or partial completion leave an unsafe state? |
| Performance | Does the change add unbounded work, repeated access, a slow path, or an invalid cache path? |
| Structure | Does the change add unnecessary complexity, unclear ownership, or a fragile boundary? |
| Tests | Do the tests prove the changed behavior and its important failure or boundary case? |

Each selected route receives its question, the same scoped context, and the output contract. Synthesis merges exact duplicates, applies the filtering pipeline, and preserves the plan's route receipts. Do not add a route because a concern appears in this table.
