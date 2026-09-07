# Pull request description

The diff already shows implementation. The description explains the outcome, the decision a reviewer must make, and evidence the diff cannot show.

## Compose

1. Read the project's pull request template and contribution conventions. They define required headings and fields.
2. Resolve the complete change range. For an existing pull request, use its base and head. For the current branch, use the remote default branch when available. If local references cannot establish the range, use the forge diff. Do not describe only the latest commit.
3. Build a small scope map: material outcomes, meaningful design decisions, validation evidence, and residual uncertainty. Ignore fix-up commits and file names unless they help explain one of those items.
4. Write a title that states the umbrella outcome. Match repository convention, keep it short, and avoid release-breaking syntax unless the user explicitly requests it.
5. Write the body in the project's required structure. Without a template, use a short outcome-first summary, a decision note only when needed, related work when known, and validation evidence.
6. Audit the result. Remove any sentence a reviewer can reconstruct from the diff. Retain every material outcome, uncertainty, and required template field.

## Size

Size content by decision cost, not changed lines:

| Change | Description |
| --- | --- |
| Mechanical or tiny | One or two outcome sentences. |
| Small behavior change | Outcome, before and after behavior when user-visible, and validation. |
| Feature or refactor | Outcome, key decision, validation, and remaining risk. |
| Large change | A compact summary with only the decisions and evidence needed to review it. |

For a performance claim, include the measured before and after result. For a user-visible bug, name what users experienced before the fix and what they experience now before explaining implementation detail.

## Evidence and references

Use only evidence that changes reviewer confidence: captured test output, a manual check, a benchmark, an API result, a rollout observation, or an honest statement that a check could not run. Do not invent screenshots, links, or results.

Preserve an existing related-work reference when rewriting. Use a closing reference only when the pull request fully resolves the item and the project's tracker syntax is known. Otherwise use a neutral related reference or omit it.

Never add generated-by lines, badges, authorship claims, or co-author trailers. Never claim a test passed without captured evidence.
