# Description Optimization

Use this reference when a skill under-triggers, over-triggers, competes with nearby skills, or needs a measurable frontmatter `description` improvement.

## Build Trigger Evals

Create about 20 queries:

- 8-10 should-trigger queries.
- 8-10 should-not-trigger queries.
- Mix terse, detailed, formal, casual, typo-prone, and context-heavy prompts.
- Include file paths, URLs, column names, project names, backstory, and adjacent tasks where realistic.
- Include cases where the user does not name the skill or file type but clearly needs it.
- Make should-not-trigger queries near misses that share keywords but need another skill, not obviously irrelevant prompts.

Poor trigger evals are too abstract:

```text
Format this data.
Extract text from a PDF.
Create a chart.
```

Better trigger evals are concrete and a little messy:

```text
my manager sent ~/Downloads/Q4 sales final FINAL v2.xlsx and wants margin % added from revenue col C and cost col D. can you fix the sheet and send it back?
```

Avoid simple one-step tasks when measuring automatic triggering. Some agents skip skills for tasks they can solve directly, even when the description matches.

## Measure

Run each query against the same client/model that will use the skill. If possible, run each query 3 times and compute trigger rate.

Passing criteria:

- Should-trigger query: skill triggers above the chosen threshold.
- Should-not-trigger query: skill stays below the threshold.

If no trigger-observability tooling exists, still build the query set and review the description manually, but do not claim measured accuracy.

## Improve

When rewriting the description:

- Generalize from failures instead of listing every missed query.
- Stay comfortably below 1024 characters; 100-200 words is usually enough.
- Front-load the distinctive user intent and key trigger words.
- Mention adjacent exclusions only when they reduce real conflicts.
- Change wording structure when repeated attempts fail; do not just append more phrases.
- Prefer "Use when..." language that names outcomes and user intent.
- Avoid implementation details unless they are important triggers.

Keep a held-out portion of the eval set. Choose the description that performs best on held-out prompts, not only the prompts used to improve it.

## Report

When applying a new description, show:

- Previous description.
- New description.
- Trigger-eval score or qualitative rationale.
- Remaining known false negatives or false positives.
