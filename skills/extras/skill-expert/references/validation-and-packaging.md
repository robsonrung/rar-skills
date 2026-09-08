# Validation and Packaging

Use the repository's own checks for the contracts an edit affects. Required repository gates still apply.

## Choose checks by change

| Change | Relevant evidence |
| --- | --- |
| Description or frontmatter | Valid YAML, name and directory match, invocation parity, and a short trigger/near-miss inspection. |
| Router or moved reference | Every selected route reaches its method; links and script paths resolve; required rules and output fields remain reachable. |
| Shared protocol, schema, or runner | Existing consumer, schema, parity, and affected runner tests. |
| Added or changed script | Representative success and failure inputs, plus the narrow relevant tests. |
| Named project convention | The repository's convention guard and any affected registry entries. |
| Behavioral claim | A bounded baseline comparison from `references/evaluation.md`, with actual outputs and limitations. |

In this collection, frontmatter and runner registration are checked by `skills/shared/scripts/validate_skill_frontmatter.py`; named vocabulary is checked by `scripts/check_leitworter.py`. Resolve these from the confirmed source checkout root. Other repositories may provide different commands.

For a placement-only edit, compare moved content and check its new paths. Do not add tests that merely assert the new wording. After checks pass, repeat or broaden only for a subsequent edit, failure, or unresolved risk. Reuse evidence only when the relevant content, dependencies, and assumptions still match.

If a helper is missing, inspect whether the repository supplies an equivalent. For metadata and links, a manual check is acceptable when reported as such. Do not claim that an unavailable executable test passed.

## Package only when requested

Use the repository's actual package tool if one exists. Do not assume an initializer or packager from another installed skill is available. Otherwise assemble the skill directory in the requested destination, preserving the supported layout.

Include the required scripts, references, assets, notices, and dependencies. This collection permits a shared library; a standalone package must include or explicitly require it. Do not silently omit shared contracts.

Inspect the package contents and its relative paths. Use a scratch destination for a trial package, preserve existing user files, and report the resulting path. Packaging does not authorize installation, publication, or a new model run.
