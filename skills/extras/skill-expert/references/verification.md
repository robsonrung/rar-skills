# Verification, Evaluation, and Packaging

## Static checks

Run the checks for the contracts the edit touches, plus the repository's required gates.

| Change | Evidence |
| --- | --- |
| Description or frontmatter | Valid YAML, name equal to directory, invocation parity, and a trigger and near-miss inspection |
| Router or moved reference | Each route reaches its method; links and script paths resolve; required rules and output fields stay reachable |
| Shared protocol, schema, or runner | The consumer, schema, parity, and runner tests it affects |
| Added or changed script | Representative success and failure inputs, plus the relevant tests |
| Leitwort or guarded phrase | `scripts/check_leitworter.py` ([leitworter.md](leitworter.md)) |
| Deleted or merged skill | No link, manifest entry, or guard still names it |

In this collection, `skills/shared/scripts/validate_skill_frontmatter.py` checks frontmatter and runner registration. Run both scripts from the source checkout root.

For a placement-only edit, compare the moved content and check its new paths. Do not add tests that only assert the new wording. If a helper is missing, look for an equivalent. A manual check of metadata or links is acceptable when reported as manual. Never report an unavailable test as passed.

## Behavioral evaluation

Run models only when the user asks for proof, or when a material execution risk cannot be checked statically. A request to edit a skill does not authorize an evaluation run.

Choose the question first: trigger accuracy, task completion, a safety boundary, output quality, or cost at equal acceptance. Use a few realistic cases that exercise the changed behavior and its nearest failure, and add cases only while the results leave real doubt. Fix the case count, models, call limit, and stop condition, and get them approved with the [routing pattern](portable-skill-authoring.md).

Pick the seats that actually run the skill. A trim can under-guide the weakest of them; an added rule can over-steer the strongest. The baseline is the prior revision, or no skill for a new one. Cases can live in `evals/evals.json` as `{id, prompt, expected_output, files, expectations}`.

Use fresh contexts when the host caches skills, and keep outputs outside the skill directory. Record the baseline and candidate revisions, the prompt, the model receipt, the host, and the result. Write expectations before seeing which candidate wins. Grade observable completion and preserved constraints; a heading or a repeated phrase is not success, and missing evidence counts as unverified.

Label each result measured or inspected. A tie shows no improvement. Fewer words, a static check, or one good run never prove better behavior.

## Packaging

Package only on request, with the repository's own tool if it has one. Otherwise assemble the skill directory at the destination with its scripts, references, assets, notices, and the shared library or a declared dependency on it. Inspect the contents and relative paths, use a scratch destination for a trial, preserve existing files, and report the path. Packaging does not authorize installation, publication, or a model run.
