# Skill Evaluation

Use this reference when a skill needs proof that it works, especially for file transforms, data extraction, code generation, fixed workflow steps, or other objectively verifiable outputs. For subjective work, use the same loop but rely more on human review than numeric assertions.

## Eval Set

Start small:

- Create 2-3 realistic prompts that resemble what a user would actually type.
- Include expected outputs and input files when relevant.
- Do not write detailed assertions until the task shape is clear.
- Ask the user to review the prompts when interactive; in headless mode, continue with explicit assumptions.

Suggested `evals/evals.json` shape:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User task prompt",
      "expected_output": "Human-readable success description",
      "files": [],
      "expectations": []
    }
  ]
}
```

## Workspace

Write results outside the skill directory so the skill stays clean:

```text
<skill-name>-workspace/
  skill-snapshot/                # optional old copy for update baselines
  iteration-1/
    eval-<descriptive-name>/
      eval_metadata.json
      with_skill/
        outputs/
      without_skill/             # for brand-new skills
        outputs/
      old_skill/                 # for improving an existing skill
        outputs/
```

Use descriptive eval directory names instead of only numeric names.

For existing skills, snapshot the original before editing and use that snapshot as the baseline. For new skills, compare against no skill when possible.

## Run Loop

1. Run the candidate and baseline on the same prompts.
2. If parallel workers are available, launch candidate and baseline runs together so they finish under comparable conditions. If not, run sequentially and record that limitation.
3. Save outputs, transcripts, and any available timing or token data immediately.
4. While runs execute, draft objective expectations. Do not force numeric assertions onto subjective outputs.
5. Inspect actual output files, not just the transcript summary.
6. Grade each expectation with `text`, `passed`, and `evidence`.
7. Aggregate pass rate, time, token/tool cost, errors, and notes.
8. Show outputs and benchmark data to the user before revising when human judgment matters.
9. Iterate until the user is satisfied, feedback is empty, or changes stop improving results.

## Grading

Use this structure for each run's `grading.json`:

```json
{
  "expectations": [
    {
      "text": "The output contains the required section",
      "passed": true,
      "evidence": "Found heading 'Risk Summary' in report.md"
    }
  ],
  "summary": {
    "passed": 1,
    "failed": 0,
    "total": 1,
    "pass_rate": 1.0
  }
}
```

Grade conservatively:

- Pass only when the evidence shows real task completion, not surface compliance.
- Fail when the evidence is missing, contradictory, unverifiable, or coincidental.
- Quote or describe the evidence tightly.
- Critique weak expectations that would pass for bad outputs.
- Extract important output claims and verify them when feasible.

## Benchmark Analysis

Look past aggregate pass rates:

- Expectations that pass in both candidate and baseline may not measure skill value.
- Expectations that fail everywhere may be broken, too hard, or checking the wrong thing.
- High variance suggests flaky prompts, ambiguous instructions, or nondeterministic execution.
- Large time, token, or tool-call increases must buy meaningful quality improvements.
- Repeated helper-code invention across runs is a signal to bundle a script.

## Human Review

Prefer a reviewer UI or static HTML when available. If no browser/display is available, present each prompt, output path, grade summary, and key diff inline.

Empty feedback usually means the user accepted that case. Focus revisions on specific complaints and clear benchmark failures.
