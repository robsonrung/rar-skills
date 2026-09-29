# Local cleanup fixtures

These are synthetic targets, not recommended production implementations. They intentionally mix removable noise with useful code. Contract tests are protected evaluation artifacts: an agent can read them, but must not change, delete, skip or weaken them during a benchmark.

Give the agent a temporary copy of one language folder and authorize edits only to `subject.mjs` or `subject.py`. Let it run the relevant supplied tests. Do not give it the expected decisions from `evals/cases.json` or this answer key before the run.

JavaScript positives: narrating comments in `sumPositive`, a throwaway `next` alias and the unreachable private `unusedDebugFormatter`. Python positives: the narrating normalization comment, a redundant `result` alias and the unreachable private `_unused_format`. Removing a well-justified subset can be useful; no line-count target applies.

Hard negatives: presence is not truthiness; the one-result loader returns an array; resource cleanup and error identity matter; runtime input validation and tenant filtering matter; runtime registration is live; independent business-policy APIs must not be collapsed on current numerical equality alone. Keep useful rationale comments. The fixture header is evaluation context, not a normal cleanup target.

Run contract tests before and after the pass. A no-op can pass them, so score useful positive cleanup separately. Passing these narrow tests is not proof of general equivalence, public-API compatibility across a real ecosystem, or judgment on every scenario. Retain the independent review of diff scope and semantic counterexamples.
