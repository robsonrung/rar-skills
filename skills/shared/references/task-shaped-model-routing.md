# Task shaped model routing

Use seat names in workflow prose and resolve their current models through `model-roster.md`. Model selection follows the shape of the task, not the programming language.

## Routing

1. Use the Opus seat for ambiguous architecture, product judgment, difficult root cause diagnosis, precision review, and reconciliation across competing designs.
2. Use the Codex seat for implementation from an explicit contract, terminal and verification loops, broad review recall, and execution completeness.
3. Use the Codex code seat for focused regression, concurrency, and security review when its narrower code specialization is useful.
4. Use Sonnet for maintainability and test quality, Gemini for wide cross file consistency, Grok for execution paths, GLM for failure and boundary cases, Kimi for pragmatic long horizon feasibility, Qwen for coding-first feasibility and long-horizon agentic workflow judgment, Gemma for cheap broad sweeps and multilingual or document-grounded checks, and Muse for agent orchestration, tool use, and computer-use design.
5. Keep heterogeneous opening panels heterogeneous. Task shaped routing governs organizer, synthesizer, judge, implementer, and specialist assignments; it does not replace independent opening seats with copies of one preferred model.
6. Use the Fable seat (Claude Fable 5.1, `shared/references/model-roster.md`) as an escalation, never a default: reach for it only when the Opus seat at `high` (or `xhigh` for coding/agentic work) has already run and measurably falls short — a difficult root-cause chain that stalls, or a judgment call where Opus's own confidence is low. It costs roughly twice Opus per token, so an unescalated task should never open on it. Do not confuse this seat with the `fable-mindset` skill (an epistemic posture, unrelated to and older than the Claude Fable model line) — that skill is model independent, and reporting a "Fable model seat" for it requires a real runner's effective-model receipt, not a self-claim.

The Fable posture skill is model independent. Do not report a Fable model seat unless a real runner returns an effective model receipt. Before adding such a seat, confirm its retention policy is compatible with the workload.

## Effort and prompt shape

1. Give the Codex seat a literal scope, an acceptance contract, relevant commands, and an instruction to continue until those checks pass. Prefer medium or high effort. Use extra high effort only when a measured result justifies its cost.
2. Give the Opus seat the complete specification and an explicit boundary around what must not change. Prefer medium for bounded review and high for architecture or difficult diagnosis. Do not add redundant verification narration when the acceptance contract already defines completion.
3. Give every seat a hard output budget and the three exits: success, exhausted retries, or the configured ceiling.

## Evaluation contract

Before changing another default route, compare the current route and candidate route on the same five representative tasks with equal context, time, and token budgets. Record the effective model receipt, acceptance result, repair prompts, human review minutes, elapsed time, and cost per accepted result.

Promote the candidate only when every acceptance contract passes and its cost per accepted result beats the current route. Keep the current route on a tie or any quality regression. This is the smallest reversible move for routing changes: evidence can promote a candidate, but a model name alone cannot.
