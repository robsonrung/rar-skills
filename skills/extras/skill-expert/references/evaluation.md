# Skill Evaluation

Run a behavioral comparison when the user asks for proof or when a material execution risk cannot be checked statically. Routine prose edits need no model runs.

## Define the comparison

Choose the question first: trigger accuracy, task completion, a safety boundary, output quality, or cost at equal acceptance. Use a few realistic cases that exercise the changed behavior and its nearest failure case, and expand only when the results leave a material uncertainty.

Fix the case count, models, call limit, and stop condition before running, and get them approved with the routing pattern in [portable-skill-authoring.md](portable-skill-authoring.md). A request to edit a skill does not authorize an evaluation fleet.

Pick models from the seats that actually run the skill: its routes in `shared/model-routing.json` or its documented callers. When a change removes guidance, include the weakest of them, since a trim can under-guide a smaller model. When a change adds guidance, include the strongest, since an added rule can over-steer it.

The baseline is the prior revision, or no skill for a new one. Keep inputs and environment comparable. Cases can live in `evals/evals.json` as a list of `{id, prompt, expected_output, files, expectations}`.

## Run

Use fresh contexts when the host caches skills. Stop at the ceiling, on a decisive result, or when more calls would not settle the question. Keep outputs outside the skill directory, and record the baseline and candidate revisions, prompt, model receipt, host, result, and any duration or usage data.

## Grade

Write expectations before looking at which candidate wins. Grade observable task completion and preserved constraints; a heading or a repeated phrase is not success, and missing evidence is unverified, not a pass. For subjective quality, show the material differences and ask the user only when the decision needs it.

## Report

Give acceptance results, costs, failures, and limits, and say whether each result was measured or inspected. A tie shows no improvement. A smaller prompt is a size reduction until task results show an execution benefit.
