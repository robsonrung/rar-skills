---
name: bug-sweep
description: Reproduces a set of reported bugs in a browser, reports which are still real, and fixes each confirmed one through pair-programming with before-and-after videos. Use when the user invokes it with bugs from Linear, a thread, or a list; use diagnose for one unexplained failure.
argument-hint: "[Linear filter, thread, or bug list]"
disable-model-invocation: true
---

# Bug Sweep

Turn a set of reported bugs into a verdict for each and a proven fix for each real one. You conduct; the seats reproduce and fix. You own the bug list, the environment, the ledger, and the report.

The user's instructions take precedence over this skill, except the limits on commits, pushes, and outside effects. Do not comment on, move, or close tickets unless the user asks.

## Seats

| Seat | Model and effort | Context |
| --- | --- | --- |
| Reproducer | Sonnet, medium | One context for all bugs, so it keeps the environment, login, and test data it learned |
| Fix seats | As `pair-programming` sets them | Per bug, as that skill says |

Route the reproducer by host. **T3 Code:** `delegate_task`, continued with `t3_thread_send`. **Claude Code:** a native subagent, continued with `SendMessage`. An unavailable seat blocks its step. Report it; never substitute another model.

## Work folder and ledger

Keep run files in `.ai-workflow/bug-sweep/<slug>/` when the repository ignores `.ai-workflow/`, otherwise in the session scratchpad. Give each bug a folder named by its ticket ID with `repro.md`, `before.*`, and `after.*`.

`ledger.md` is the run state: one row per bug with its ID, title, verdict, fix status, and evidence paths, plus the environment URL, the commit under test, and the reproducer's thread or agent ID. Update it after every step. After compaction or a restart, resume from it with the same seats.

## 1. Collect

Read every bug in full: description, comments, attachments, and screenshots, because the steps often live in a comment. Note the version or date each was reported against; reports made on an older build may already be fixed. Write one ledger row per bug.

## 2. Environment

Run a local environment from the worktree where the fixes will land, so the after video shows the fix. If another thread or the user is using a running environment, start a separate one with its own ports and data, using the project's local-run instructions. Never stop, reuse, or reseed someone else's environment. Record its URL and the commit in the ledger.

## 3. Reproduce

The reproducer works through the bugs one at a time in the in-app browser, because they share one environment and its data. For each bug it follows the reported steps, records a video of the attempt, and writes `repro.md`: steps, expected result, actual result, evidence, and one verdict:

- `reproduced`: the bug happens on the commit under test.
- `already fixed`: the steps now give the expected result.
- `not a bug`: the app works as designed; name the design or rule.
- `cannot reproduce`: the report lacks steps or data; say what is missing.
- `blocked`: the environment or access prevents the attempt; say why.

Keep the video as `before.*` only for `reproduced`. Done when every bug has a verdict.

Report the verdict table, then ask: **"Approve fixing the reproduced bugs, or specify changes."** If the invocation already said to fix them, go on. This approval also covers the plan step of each `pair-programming` run below.

## 4. Fix

For each `reproduced` bug, one at a time, run `pair-programming`. If the host does not let you invoke it, read and follow `~/.claude/skills/pair-programming/SKILL.md`. Its brief takes `repro.md` as fact, and its acceptance contract is: the reproduction steps give the expected result, and nothing outside the bug changes behavior.

Bugs that share a cause go into one run; name the shared cause in the brief.

## 5. Prove

After each fix, the reproducer reruns the same steps in the same environment, records `after.*`, and gives a verdict of `fixed` or `still failing`. A restart the change needs (backend, migrations) comes first. A `still failing` result goes back to the same `pair-programming` author once, with the after evidence; a second failure is reported, not retried.

Use the host's browser recording (in T3 Code, `preview_recording_start` and `preview_recording_stop`).

## Report

Write `report.md` and reply with:
- the verdict table: ID, title, verdict, fix result, and before and after video paths;
- each fix in one line, with its changed files and the check commands and results from its `pair-programming` report;
- each bug that is `cannot reproduce`, `blocked`, or `still failing`, with what it needs next;
- the environment URL and the commit tested.

Never call a bug fixed unless the after recording shows it.
