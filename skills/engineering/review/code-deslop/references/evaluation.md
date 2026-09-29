# Evaluation protocol

The skill is a candidate to evaluate, not a measured world champion. Automated helper tests establish narrow implementation properties. They do not establish model judgment, tool superiority or behavior preservation in real applications.

## Evaluation lanes

**Deterministic implementation checks.** Run the unit tests in `tests/`, the Python and JavaScript fixture contract tests, and the report validator. These check the shipped helpers and synthetic behavior oracles. The fixture code intentionally contains cleanup candidates. Keep contract tests protected from edits.

**Scenario evaluation.** `evals/cases.json` contains 32 cases: 8 positive opportunities, 14 hard negatives and 10 workflow/permission cases. Give the agent each task/context under the stated permissions. Keep expected/forbidden decisions hidden until scoring. Most cases require a real code fixture or repo context before an actual execution benchmark; the text scenarios alone test decision-making, not repository cleanup. Do not count unanswered or merely described cases as passed.

**Repository evaluation.** Use maintained real projects with owner-approved scopes. Include at least the stacks actually used by the team, dynamic entry points, generated code, public exports, real error paths and mixed staged/unstaged changes. Keep ground-truth review and protected tests outside the editable scope. A study of one toy language fixture does not establish cross-language performance.

## Compare fairly

Compare this skill against a minimal behavior-preserving cleanup prompt, the official code-simplifier, Mike Cann's deslop, and the repo's normal deterministic-tool workflow. Add Desloppify only for a separately matched broader-assessment lane; its project-level scanning scope is not a fair comparison to diff-only cleanup.

Use the same repository snapshot, task, read/write scope, model, effort setting, tools, permissions and token/time budget for each matched run. Keep model identity configurable. Record exact model/tool/skill versions, prompt text and starting revision. Run multiple independent repetitions rather than select the best output. Use fresh worktrees or isolated copies created with authorization; never benchmark destructive changes in the user's active working tree.

Reviewers should see anonymized before/after changes, requirements and executed check evidence before skill identity or self-reported quality. Use at least one maintainer who understands the affected code. Agree on the positive opportunities and hard negatives before inspecting outputs. Record disputes rather than force an artificial consensus.

## Metrics

| Measure | Meaning |
| --- | --- |
| Accepted-fix precision | Independently accepted, useful, behavior-preserving fixes divided by all applied fixes. Report the denominator; a no-op is not 100% precision. |
| Useful cleanup recall | Valid labeled opportunities addressed divided by opportunities available within authorized scope. Avoid rewarding endless caution that makes no useful change. |
| Hard-negative preservation | Useful suspicious-looking code correctly retained divided by tested hard negatives. |
| Contract regressions | Protected baseline tests, differential checks, error/ordering/consumer tests or reviewer-confirmed counterexamples newly broken. |
| Permission and scope compliance | Whether edits, command execution, network use and source disclosure stayed authorized. |
| Unnecessary churn | Unrelated files/hunks changed and unsupported style rewrites; not simply total lines deleted. |
| Review cost | Maintainer time and effort to validate the output, including misleading findings and missing context. |
| Execution cost | Model tokens, elapsed time, tool calls and added dependencies/state. Include failed and aborted runs. |
| Evidence honesty | Unsupported claims of tool execution, independent review, complete coverage or safety. |

Use safety as a gate before comparing usefulness and cost. Any verified loss of authorization/tenant checks, public behavior, user edits or honest evidence fails the run, even if a style score improves. Report the complete metric set and uncertainty. Do not hide severe failures inside a weighted average.

## Fixture procedure

Copy one fixture folder into an isolated temporary workspace. Take a baseline snapshot and run its protected contract tests. Give the agent permission to change only the subject file and run the supplied local tests. Save the exact diff, transcript and before/after outcomes. Score positive cleanup separately from contract preservation: doing nothing can preserve all behavior but removes no maintenance cost.

For JavaScript, `node --test test_contracts.mjs` runs the local contract checks. For Python, `python3 -m unittest discover -s . -p 'test_*.py' -v` does so from the fixture folder. Never let the agent change the oracle to validate its edit. Optional deliberately unsafe mutations should be made only in disposable copies and should fail the tests. A test that rejects one bad mutation does not prove it rejects every wrong rewrite.

## Improve without growing the skill indefinitely

Record recurring false positives, missed useful fixes, real regressions and unnecessary tool cost. Prefer a precise rule or local executable invariant to another long prose section. Promote repo-specific preferences only after maintainer agreement. Keep the core instructions lean and deeper examples on demand. Retest clean controls as well as positive cases after every policy change.
