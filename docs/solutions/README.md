# Solution documents

Use `capture-learning` to record one verified, non-obvious solution. Each document lives in a category directory such as `runtime-errors/` or `tooling-decisions/`. It explains the problem, cause, verified fix, and conditions where the fix applies.

## Frontmatter contract

Every document carries YAML frontmatter for searching by field. The [schema](../../skills/engineering/deliver/capture-learning/references/schema.yaml) defines required fields, values, track rules, and destination directories. The [quick reference](../../skills/engineering/deliver/capture-learning/references/yaml-schema.md) explains the same contract. Manually written documents follow these rules too.

## One learning per run

Each run creates or updates one solution document. Update an existing document when the problem, cause, and solution match. Separate problems need separate documents. A run without enough verified evidence reports that documentation was skipped.

## Related project knowledge

The same run may add a missing term to an existing `CONCEPTS.md` when that term belongs to the learning. It does not create a glossary, change project instructions, or start a documentation audit. Follow the current [capture-learning workflow](../../skills/engineering/deliver/capture-learning/SKILL.md) for validation.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
