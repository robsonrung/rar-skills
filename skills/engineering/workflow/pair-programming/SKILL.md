---
name: pair-programming
description: Builds a code change after a two-model design debate and an independent review. Use when the user invokes it for a fix or feature whose design is still open; use implement-and-review when the design is settled.
argument-hint: "[task, ticket, or thread]"
disable-model-invocation: true
---

# Pair Programming

Turn one request into a reviewed change that meets the **design bar**. You conduct; the seats below think, build, and review. You own the brief, the round count, the run state, and the final report.

The user's instructions take precedence over this skill, except the limits on commits, pushes, and outside effects. When a seat stops or diverges because of a skill or a repository rule, it names the file and quotes the rule.

## Design bar

Every seat judges the design and the diff against these, in this order when they conflict:

1. **KISS and YAGNI:** the simplest solution that does the requested work. No speculative abstractions, options, or extension points.
2. **No regressions:** behavior outside the scope stays the same, with no side effects.
3. **Smallest blast radius:** a minimal diff, touching the fewest files, callers, contracts, and data.
4. **Low coupling, high cohesion:** make the change at an existing seam (a module, port, or extension point where it fits without editing callers), stay out of unrelated modules, and keep code that changes together in one place.
5. **Follow existing conventions:** reuse the codebase's patterns, abstractions, and idioms, found in the code and in its agent rules, instead of adding new ones (DRY against existing code). Extract a new shared abstraction only for duplication that exists now (rule of three), never for one use.
6. **Test behavior, not implementation:** black-box tests through the public interface that check outputs and observable effects. Mock only at system boundaries. No change-detector tests that check private calls, internal mocks, or call order. A reversible, low-impact change whose only possible test would mirror the code gets no new test.

A finding or objection names the criterion it serves. Taste without a criterion is not a finding.

## Seats

| Seat | Model and effort | Context |
| --- | --- | --- |
| Author: proposes, implements, fixes | Opus, high | One context for the whole run, so it keeps the reasons behind each design choice |
| Challenger | Astra, high | One context across all rounds |
| Arbiter (only on deadlock) | Fable, high | Fresh |
| Reviewer | Sol, xhigh | Fresh; never sees the debate, so its conclusions cannot anchor the review |

Route by host. **T3 Code:** start each seat with `delegate_task` and continue it with `t3_thread_send`. **Claude Code:** native subagents for Opus and Fable, continued with `SendMessage`; `cli-runner` for Astra and Sol. An unavailable seat blocks its step. Report it; never substitute another model.

Brief every seat with the same five parts:
- **Goal:** its job in this step.
- **Context:** the work-folder paths to read.
- **Constraints:** the design bar; only the author edits files; no commits, pushes, package installs, deploys, or messages to outside services; the repository's agent rules; do the work directly without starting further subagents; resolve discoverable facts yourself and return a question only for a decision `brief.md` marks open.
- **Done when:** the completion condition the step below gives.
- **Return:** the output the step below names.

## Work folder and state

Keep run files in `.ai-workflow/pair-programming/<slug>/` when the repository ignores `.ai-workflow/`, otherwise in the session scratchpad. Seats read files from it by path, so nothing is lost between seats: `brief.md`, `design.md`, `review.md`, `report.md`.

Keep `state.md` current: the step, the round, each seat's thread or agent ID, and open questions. After compaction or a restart, read it and continue the same seats rather than starting new ones.

## 1. Brief

Read the request, then collect what the seats need and cannot find alone: the code paths and their callers, the agent rules that apply, linked tickets, threads, screenshots, and earlier decisions in this conversation. Write `brief.md`: the goal, scope and non-goals, invariants, acceptance criteria, known facts with file references, and open questions.

Resolve a discoverable fact yourself. A product or scope decision only the user can make is a stop: ask it, together with the plan. Show the brief summary and the seats, then ask: **"Approve this plan, or specify changes."** If the invocation already said to proceed and no question is open, go on.

## 2. Design debate

1. The author reads `brief.md` and the code, then writes `design.md`. It says what changes and where, the existing patterns it reuses, the non-goals, the tests to add and the behavior each one proves, and the alternatives considered with the bar criterion each fails.
2. The challenger acts as devil's advocate: it looks for a simpler or less coupled design, then checks `design.md` against the code and the bar. It returns `AGREE`, or `OBJECT` with numbered objections, each tied to a criterion and to evidence.
3. The author accepts each objection by revising `design.md`, or rebuts it with evidence. Each rebuttal goes back to the challenger.

One round is one challenger verdict. **Consensus** means the challenger returns `AGREE` with no objection open. Stop at consensus or after round 3. If consensus is reached, skip step 3.

If a debate exposes a product or scope decision only the user can make, stop and ask it. Do not let the seats decide it.

## 3. Arbitration (deadlock only)

Give the arbiter `brief.md`, the final `design.md`, and each open objection with both final positions. It decides each one against the bar, giving a one-line reason. Its decision is final. The author updates `design.md` to match.

## 4. Implement

The author builds `design.md` in the same context. No scope creep: it edits only what `design.md` lists. A change outside the design comes back to you first, not into the diff.

Done when everything in `design.md` is built and the checks the author judges relevant pass. It fixes failures caused by the change and reruns the affected checks without asking at each step. Return the changed files and each check command with its result.

## 5. Review

The reviewer gets `brief.md`, `design.md`, the diff, and the check results. It leaves every file unchanged. It checks correctness, conformance to the design, and every bar criterion. Return `review.md`: each finding with an ID, severity, file and line, criterion, and evidence, plus a verdict of `ready` or `changes required`.

## 6. Fix

The author reads `review.md` and fixes the findings it judges valid and in scope, then reruns the affected checks. Return each finding marked fixed, or declined with a one-line reason. There is no second review unless the user asks for one.

## Report

Write `report.md` and reply with:
- the agreed design in two or three lines, and whether it came from consensus or arbitration;
- the changed files;
- each check command and its result;
- each review finding, marked fixed or declined with the reason;
- open questions, a blocked seat, or a check that could not run.

Never call a check passed unless its command ran.
