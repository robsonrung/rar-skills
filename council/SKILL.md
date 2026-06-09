---
name: council
description: Clarify ambiguous or underspecified tasks until confidence exceeds 95%, then run a four-seat planning council across Claude Opus, Claude Sonnet, Gemini, and Codex in parallel, summarize consensus and discrepancies, route a report-only decision to Codex for the final plan, and optionally start execution. If the user explicitly invokes `council`, always run the full council workflow even when the request seems trivial, obvious, or answerable without deliberation. Use when a user wants a simpler alternative to full multi-round consensus for implementation, debugging, design, architecture, planning, or even quick repo questions and wants targeted follow-up questions before action.
---

# Council

Use this skill as a lightweight council workflow:
1. Clarify the task until you are at least 95% confident you know what to do.
2. Run one parallel first-thought round with four seats.
3. Build a moderator report.
4. Give only that report to Codex for the final plan.
5. Ask whether to review or execute unless `--auto` is active.

Do not run a multi-round debate. This skill is intentionally simpler than `models-consensus`.

## Mandatory Invocation

If the user explicitly invokes `council` by name, you must run the actual council workflow.

- Do not answer directly from your own inspection just because the request looks easy.
- Do not collapse the workflow into a "lightweight" or "single-agent" interpretation.
- Do not skip the blind four-seat round because the task seems factual, local, or fast to verify.
- The only acceptable shortcuts are true tool-path fallbacks described in this skill, such as using runner fallbacks when native seats are unavailable.
- If the skill is triggered, the minimum required behavior is: clarify if needed, run the four planning seats, build the moderator report, send only that report to Codex, and present the final plan or answer.

## Operating Rules

- Treat `--auto` as enabled when the user explicitly includes `--auto` or clearly asks for fully automatic behavior. Then follow the `--auto` branches in Steps 1, 4, 5, and 6.
- Outside `--auto`, keep asking targeted questions until confidence is above 95%.
- Ask only blocking questions. Do not interview for preferences that do not change the plan.
- Ask one short question at a time unless an interactive multiple-choice UI is available and materially faster.
- Use interactive question tools when the host supports them. Otherwise ask plain-text questions.
- Keep the first council round blind, passing only the final clarified prompt as described in Step 2.
- Use the strongest planning setup available for each seat.
- Keep artifacts compact. Prefer a temporary working folder such as `.ai-workflow/council/` or `/tmp/council-<timestamp>/`.

## Host Mapping

Detect the host first, before choosing the seat implementation.

### Codex Host

Use:
- native `spawn_agent` for the Codex seat
- `claude-runner` for Opus and Sonnet
- `gemini-runner` with `--role planner` for Gemini, when the local Gemini CLI is available

Do not use `codex-runner` for the Codex seat when native Codex subagents are available.

For native Codex seats:
- set `fork_context` to `false`
- use the strongest reasoning effort available, usually `xhigh`
- tell the seat to behave like a planner and produce only an initial thought

### Claude Host

Use:
- native Claude subagents for Opus and Sonnet
- `codex-runner` with `--role planner --restrict-tools` for the Codex seat
- `gemini-runner` with `--role planner` for Gemini, when the local Gemini CLI is available

Do not use `claude-runner` for Opus or Sonnet when native Claude subagents are available.

### Other Hosts

On any other host (Gemini CLI, Qwen CLI, Kimi CLI, etc.), use the runner skills for all four seats with the same flags as above.

### Fallbacks

- If a required native path is unavailable, fall back to the corresponding runner skill.
- On any single seat failure (including Gemini), record a `seat_unavailable` reason for the moderator report, continue with lowered confidence if at least 3 seats remain, and surface the missing prerequisite (for example, a missing local Gemini CLI) to the user in the final presentation instead of silently dropping the seat.
- Stop and explain the missing prerequisites only if quorum drops below the minimum of 3 seats.

## Step 1: Clarify Until 95% Confidence

Start by checking whether the prompt is sufficiently specified.

If the prompt is already clear and confidence is immediately above 95%, build the clarified prompt directly and continue to Step 2.

You must be confident about:
- the actual objective
- the target artifact or output
- the important constraints
- the success criteria
- the autonomy level expected
- any required inputs, files, or environment assumptions

Use this rule:
- If a reasonable expert could misread the task in more than one materially different way, confidence is below 95%.

When confidence is below 95% and `--auto` is not enabled:
- ask a short blocking question
- prefer multiple choice when it reduces ambiguity quickly
- continue until confidence rises above 95%

When `--auto` is enabled:
- skip the interview
- write down the assumptions you are making
- continue without asking the user

Build a final clarified prompt that contains only the task to perform. This prompt becomes the sole input to the first council round.

## Step 2: Run The Blind Four-Seat Round

Launch four seats in parallel:
- Claude Opus
- Claude Sonnet
- Gemini
- Codex

Give every seat the same job and the same clarified prompt.

Do not pass:
- your own notes or analysis
- the clarification interview transcript
- repo summaries
- preferred solutions or prior conclusions
- the expected answer

The only seat-specific differences should be the model identity, the host mechanism, and the planning role wrapper.

### Seat Instructions

Tell every seat to produce an initial planning thought, not final execution. Use the strongest planning mode available:
- planner role where supported
- highest planning reasoning or thinking budget available
- no write access during the council round

Use the council-seat prompt in the Prompting Pattern section as the output contract.

Run all four seats concurrently.

## Step 3: Build The Moderator Report

After the first round, write a compact report with these sections:
- original clarified prompt
- Opus conclusion
- Sonnet conclusion
- Gemini conclusion
- Codex conclusion
- consensus
- discrepancies
- unresolved questions
- `seat_unavailable` reasons for any seat that failed to run
- moderator notes limited to factual synthesis

Keep this report faithful. Do not smuggle in extra context or repo-specific explanations that were not present in the first round.

## Step 4: Send Only The Report To Codex

Pass the moderator report, with no other context, to Codex for the final planning decision.

On Codex host:
- use a fresh native Codex subagent
- set `fork_context=false`
- pass only the report

On non-Codex host:
- use `codex-runner`
- pass only the report file or report text

Ask Codex for the final decision using the Codex final-decision prompt in the Prompting Pattern section.

If Codex confidence is above 95%:
- adopt the plan without asking the user for more detail

If Codex confidence is below 95% and `--auto` is not enabled:
- ask the user targeted follow-up questions
- if the answers materially change the task, rebuild the clarified prompt and rerun the four-seat round
- if the answers only resolve a minor choice, update the plan directly

If Codex confidence is below 95% and `--auto` is enabled:
- make the best supported decision
- record the assumption
- continue

## Step 5: Present The Plan

Show the user:
- a concise statement of the clarified task
- the final plan
- any key assumptions
- the main consensus and main discrepancy from the council

Then:
- if `--auto` is enabled, start execution immediately
- otherwise ask whether the user wants to review the plan or start execution

If the user chooses review:
- stop after presenting the plan
- answer plan questions
- do not start implementation

## Step 6: Start Execution

If execution begins, use the finalized plan as the implementation brief.

### In `--auto`

Always execute with Codex in automatic mode.

On Codex host:
- use a native Codex subagent for execution
- do not use `codex-runner`

On non-Codex host:
- use `codex-runner` in its automatic execution mode

Do not ask the user which model to use in `--auto`.

### Outside `--auto`

Ask which execution engine to use:
- Opus
- Sonnet
- Codex

Use:
- native Claude subagents for Opus and Sonnet on Claude host
- `claude-runner --model opus` or `claude-runner --model sonnet` when Claude native agents are unavailable
- native Codex subagent on Codex host
- `codex-runner` only when native Codex subagents are unavailable

Gemini participates in planning only for this skill. Do not offer Gemini as the execution engine unless the user explicitly asks to change the workflow.

## Prompting Pattern

Use this compact council-seat prompt shape:

```text
You are one planning seat in a blind four-model council.
Produce an initial thought only. Do not assume access to moderator context.

Task:
<clarified prompt>

Return:
1. Task understanding
2. Proposed approach
3. Key assumptions
4. Risks or unknowns
5. Confidence from 0-100
```

Use this compact Codex final-decision prompt shape:

```text
You are the final decision-maker.
Use only the report below.
Choose the best plan, note rejected alternatives, state explicit assumptions, list unresolved questions if confidence is below 95, and give confidence from 0-100.

Report:
<moderator report>
```

## Decision Thresholds

- `>= 95`: proceed without more user input
- `90-94`: ask only if the missing information could change the plan in a meaningful way
- `< 90`: ask targeted questions unless `--auto` is enabled

Be conservative about false confidence. Reaching 95% means the task is clear enough that you would be comfortable acting without reinterpretation.

## Example Triggers

This skill should activate for requests like:
- "Use council to clarify this feature request and propose a plan."
- "Run a quick council on this bug, then let Codex choose the plan."
- "I want a simpler alternative to models-consensus with a short interview first."
- "council where is the login screen"
- "use council to find the file that handles sign-in"
- "council what's the fix for this failing test"
