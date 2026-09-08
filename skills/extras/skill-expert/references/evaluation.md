# Skill Evaluation

Use a behavioral comparison when the user requests proof or when a material execution risk cannot be checked statically. Routine prose edits do not require model runs.

## Define the comparison

Choose the question first: trigger accuracy, task completion, a safety boundary, output quality, or cost at equal acceptance. Use a few realistic cases that exercise the changed behavior and its nearest failure case. Expand only when results leave a material uncertainty.

Set the case count, models, call limit, output limit, and stop condition before running. Follow the workflow's model and spending approval rules. A request to edit a skill does not authorize an unbounded evaluation fleet. Ask about a case only when it needs domain facts or a decision the available evidence cannot supply.

For an existing skill, use its prior revision as the baseline. For a new skill, compare with no skill when useful. Keep task inputs and environment comparable.

Suggested `evals/evals.json` shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User task prompt",
      "expected_output": "Observable success",
      "files": [],
      "expectations": []
    }
  ]
}
```

## Run within the budget

Use fresh contexts when the host caches skills. Run serially unless parallel evaluation is authorized and supported. Stop at the agreed ceiling, on a decisive result, or when further calls would not resolve the uncertainty.

Keep outputs and evidence outside the skill directory. Record the baseline revision, candidate revision, prompt, model and receipt limits, host, result, and available duration or usage data. Inspect the output artifact and relevant trace.

Do not repeat successful checks without a changed candidate or an unresolved concern. Compare another revision only when a specific result justifies it and the remaining budget permits it.

## Grade

Evaluate observable task completion and preserved constraints. A heading or repeated phrase is not proof of success. Treat missing evidence as unverified; do not turn it into a pass.

A consumer may use this `grading.json` shape:

```json
{
  "expectations": [
    {
      "text": "The output preserves the required contract",
      "passed": true,
      "evidence": "The observed output and location supporting the result"
    }
  ],
  "summary": {"passed": 1, "failed": 0, "total": 1, "pass_rate": 1.0}
}
```

Choose expectations before examining which candidate wins. For subjective quality, show the material differences and request human judgment only when it is needed to decide. Empty feedback or no answer is not approval.

## Report

Show acceptance results, relevant costs, failures, and limits. State whether results were measured or inspected. A tie shows no demonstrated improvement. A smaller prompt is a size reduction until task results establish an execution benefit.
