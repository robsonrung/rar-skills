# Failure modes → structural remedies

Read this when a symptom is known and the question is which mechanism cures it. Each row names the smallest structural change that removes the failure, not the largest.

## Symptom table

| Symptom | Root cause | Smallest remedy |
| --- | --- | --- |
| The agent called a broken tool dozens of times | The retry decision lives in the model's reasoning | Attempt counter written to state before each call; fallback route at the bound |
| The agent gave up after one failure and invented a result | Same cause, opposite expression | Same remedy, plus a named failure exit so "give up" has somewhere to go |
| A restart lost 40 minutes of work | State lives only in the message list | Externalize state (ladder rung 1), then checkpoint after each step (rung 2) |
| The approval request vanished when the process died | The gate is a conversational turn | Record the gate decision in durable state; resume reads it instead of re-asking |
| Step 12 spends thousands of tokens re-reading its own reasoning to do arithmetic | Context growth with no compaction | A summarization step at a token threshold; move computed values into typed fields |
| Two parallel branches produced conflicting values in one field | No write rule for a shared field | Declare a reducer per field, or partition the field by branch |
| The same email/commit/ticket was created twice | A crash between the side effect and the checkpoint replayed the step | Stable key written to state _before_ the effect, checked at the top on re-execution |
| Nobody can explain what happened in a run | Flat message history, unnamed steps | Named steps with logged inputs, outputs, and durations |
| A run that should cost cents cost hundreds | No hard ceiling | A spend or step ceiling counted outside the model, plus a visible signal when it fires |
| Recovery worked in theory and failed in practice | Resume path never exercised | The crash-resume test as a required integration test |
| Checkpoint storage grew without bound | No TTL, no purge | Expiry on checkpoint keys; purge completed runs past the audit window |
| A read-only step modified files | Tools scoped per run, not per step | Per-step tool permissions |

## Calibration

Two datapoints for how far an unbounded run actually goes. Both are the same failure — nothing outside the model enforcing a limit — at different scales.

- A documented 2026 case: an agent called a broken tool **400 times in five minutes**. Not a reasoning failure; the model was never given a bound it could not talk itself out of. (Data Science Dojo, "Agentic Loops" guide, June 2026.)
- Peter Steinberger's **$1.3 million monthly token bill** — roughly **603 billion tokens** across 100 Codex instances on the OpenClaw project. The extreme version of long-running agents operating without a hard budget cap. (Tom's Hardware, 17 May 2026; The Decoder, 16 May 2026.)

Use these when a reviewer argues a ceiling is premature. The cost of the ceiling is a counter and a comparison. The cost of omitting it has no upper bound by construction.

## What is not a failure mode

Do not raise these as findings:

- A loop that stays a loop because no signal fires. That is the correct outcome, not an oversight.
- A single-step agent without checkpointing. There is nothing to resume to.
- Sequential execution of steps that are genuinely dependent. Parallelism is not owed here.
- Missing observability on a run nobody audits and that costs nothing to repeat.
