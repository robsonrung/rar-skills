# Skill library review

This report records the earlier library review and its validation counts. Model
routing was revised on 2026-09-08; use the current [task routing](../skills/shared/references/task-shaped-model-routing.md)
and [host execution contract](../skills/shared/references/host-model-execution.md).
The counts below do not describe that later change.

The review covered all 59 executable skills and the shared library. 43 skills or their supporting files changed; 16 were retained after review. All entry points remain because each has a distinct purpose. Skill entry files are 27.9% shorter (7,221 to 5,206 lines). Duplicate orchestration and repeated work were removed.

## Main changes

1. One main sequence: `interview-me` → `to-prd` → `to-tasks` → `implement-tasks`. Each stage has one output and a clear next consumer.
2. Interview rounds contain five independent questions when possible, never more. Material decisions cannot be silently settled with defaults.
3. Broad architecture, domain, topology, UX, and security choices run during discovery only when they change a decision. Task planning selects focused lenses. Implementation reuses their findings and applies practices when their trigger occurs.
4. Model approval is separate from task approval. The plan binds task inputs, exact model and runner, effort, review assignment, and any approved fallback before execution.
5. Resolve implementation and independent review roles from `skills/shared/model-routing.json`. Task difficulty, uncertainty, and verification strength determine the route. No silent change of model or effort is allowed.
6. `models-consensus` is user-invoked only and shows its complete seat, role, effort, and call-budget plan before dispatch.
7. Removed the separate brainstorm, PRD, and task-planning panel configurations and the two panel-mode references. Explicit extra opinions use the council. Standalone specialist workflows remain optional.
8. Removed routine user-task creation, host goals, sidebar changes, automatic publication, and mandatory duplicate task/feature review panels. Local verified work is the default deliverable.
9. Pending side effects now require reconciliation after a restart. A report path or a pending ledger key cannot be treated as proof of completion.
10. Review filtering preserves separate defects at the same location. Agreement cannot promote severity or combine confidence into an unsupported blocker. Malformed returns remain visible as coverage limits.

The current workflow and call placement are in [workflow.md](workflow.md) and [workflow-stage-routing.md](../skills/shared/references/workflow-stage-routing.md).

## Model evidence

The model recommendations are task-fit policy, not a measured cross-provider ranking for this repository. Capability evidence comes from the [Astra model page](https://developers.openai.com/api/docs/models/gpt-6-astra), [Fable 5.1 documentation](https://platform.claude.com/docs/en/models/fable-5-1/overview), [Gemini 3.8 Flash model page](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash), [Grok 4.6 release](https://x.ai/news/grok-4-6), and [Qwen 3.8 Max documentation](https://www.alibabacloud.com/help/en/model-studio/qwen3-8-max).

Exact identifiers and transport limits belong in the [model roster](../skills/shared/references/model-roster.md). Effort and task choices belong in [task-shaped routing](../skills/shared/references/task-shaped-model-routing.md). Local tests validate dispatch and contracts; they do not benchmark model quality or prove subscription access.

## Coverage

“Updated” means the skill or one of its supporting files changed. “Retained” means its reviewed behavior remains distinct and useful.

| Skill | Decision | Role after review |
| --- | --- | --- |
| [capture-learning](../skills/engineering/deliver/capture-learning/SKILL.md) | Updated | Record a supported project lesson or settled glossary term. |
| [open-pr](../skills/engineering/deliver/open-pr/SKILL.md) | Updated | Perform requested commit, push, and PR work within explicit authority. |
| [resolve-pr-feedback](../skills/engineering/deliver/resolve-pr-feedback/SKILL.md) | Updated | Process review feedback and verify the requested corrections. |
| [session-handoff](../skills/engineering/deliver/session-handoff/SKILL.md) | Updated | Write enough current evidence to resume work in fresh context. |
| [summarize](../skills/engineering/deliver/summarize/SKILL.md) | Updated | Produce a concise record that passes the cold-start test. |
| [coding-design-plan](../skills/engineering/engine/coding-design-plan/SKILL.md) | Updated | Apply settled decisions to the local implementation plan. |
| [implement-and-review](../skills/engineering/engine/implement-and-review/SKILL.md) | Updated | Build one task with the approved implementation and review routes. |
| [worktree](../skills/engineering/engine/worktree/SKILL.md) | Updated | Provide optional isolation when the execution plan permits it. |
| [design-gate](../skills/engineering/gates/design-gate/SKILL.md) | Updated | Select at most three relevant design lenses and resolve blocking findings. |
| [security-gate](../skills/engineering/gates/security-gate/SKILL.md) | Updated | Collect security decisions early and classify later review depth. |
| [advanced-react](../skills/engineering/lenses/advanced-react/SKILL.md) | Retained | Review and implement React behavior at the affected component boundary. |
| [agent-architecture-lens](../skills/engineering/lenses/agent-architecture-lens/SKILL.md) | Retained | Choose control flow and durable execution mechanisms only when required. |
| [architecture-lens](../skills/engineering/lenses/architecture-lens/SKILL.md) | Retained | Check module boundaries, dependencies, and architectural tradeoffs. |
| [data-systems-coding-lens](../skills/engineering/lenses/data-systems-coding-lens/SKILL.md) | Retained | Check stored state, migrations, queues, retries, and concurrency. |
| [design-patterns](../skills/engineering/lenses/design-patterns/SKILL.md) | Retained | Apply a named pattern only when the implementation has matching pressure. |
| [distributed-systems-patterns](../skills/engineering/lenses/distributed-systems-patterns/SKILL.md) | Retained | Choose distributed topology and event contracts when the system needs them. |
| [domain-driven-design](../skills/engineering/lenses/domain-driven-design/SKILL.md) | Retained | Set domain boundaries early and apply domain modeling during implementation. |
| [macro-architecture](../skills/engineering/lenses/macro-architecture/SKILL.md) | Retained | Choose system structure before task design depends on it. |
| [software-design-philosophy](../skills/engineering/lenses/software-design-philosophy/SKILL.md) | Retained | Keep module and interface decisions coherent and simple. |
| [ui-ux-pro-max](../skills/engineering/lenses/ui-ux-pro-max/SKILL.md) | Updated | Own design-system and cross-screen UX choices. |
| [clean-code](../skills/engineering/practice/clean-code/SKILL.md) | Retained | Perform scoped behavior-preserving refactoring on green checks. |
| [diagnose](../skills/engineering/practice/diagnose/SKILL.md) | Retained | Reproduce a failure and prove its cause before changing code. |
| [frontend-design](../skills/engineering/practice/frontend-design/SKILL.md) | Updated | Implement a selected bespoke visual direction. |
| [safe-incremental-coding](../skills/engineering/practice/safe-incremental-coding/SKILL.md) | Retained | Build a characterization-test net before changing untested legacy behavior. |
| [tdd](../skills/engineering/practice/tdd/SKILL.md) | Retained | Use red, green, and refactor for testable behavior changes. |
| [test-lens](../skills/engineering/practice/test-lens/SKILL.md) | Retained | Resolve test value, seam, or mock-boundary decisions when they arise. |
| [coding-review-simplify](../skills/engineering/review/coding-review-simplify/SKILL.md) | Updated | Simplify a finished change within its original scope. |
| [full-review](../skills/engineering/review/full-review/SKILL.md) | Updated | Run focused independent review for final risks and task seams. |
| [claude-runner](../skills/engineering/seats/claude-runner/SKILL.md) | Updated | Execute the selected model through the Claude CLI. |
| [cline-runner](../skills/engineering/seats/cline-runner/SKILL.md) | Updated | Execute configured provider seats through Cline. |
| [codex-runner](../skills/engineering/seats/codex-runner/SKILL.md) | Updated | Execute the selected model and supported effort through the coding CLI. |
| [dcode-runner](../skills/engineering/seats/dcode-runner/SKILL.md) | Updated | Provide the documented dcode transport and its receipt limits. |
| [gemini-runner](../skills/engineering/seats/gemini-runner/SKILL.md) | Updated | Provide the Gemini transport without inventing unsupported effort control. |
| [grok-runner](../skills/engineering/seats/grok-runner/SKILL.md) | Updated | Provide the Grok transport and role/output contracts. |
| [opencode-runner](../skills/engineering/seats/opencode-runner/SKILL.md) | Updated | Provide an optional OpenCode transport. |
| [pi-runner](../skills/engineering/seats/pi-runner/SKILL.md) | Updated | Provide provider-specific seats through the shared Pi runner. |
| [brainstorm](../skills/engineering/workflow/brainstorm/SKILL.md) | Updated | Decide whether to build before a requirements interview. |
| [implement-tasks](../skills/engineering/workflow/implement-tasks/SKILL.md) | Updated | Approve exact models and effort, schedule tasks, integrate, and verify. |
| [interview-me](../skills/engineering/workflow/interview-me/SKILL.md) | Updated | Settle user decisions in independent rounds of five questions where possible. |
| [models-consensus](../skills/engineering/workflow/models-consensus/SKILL.md) | Updated | Run a council only on explicit request after approval of its seats and budget. |
| [to-prd](../skills/engineering/workflow/to-prd/SKILL.md) | Updated | Write and approve the specification from the settled decision record. |
| [to-prototype](../skills/engineering/workflow/to-prototype/SKILL.md) | Updated | Return evidence from one throwaway experiment without promoting its code. |
| [to-tasks](../skills/engineering/workflow/to-tasks/SKILL.md) | Updated | Approve executable slices with dependencies, acceptance, and selected gate findings. |
| [agents-md-craft](../skills/extras/agents-md-craft/SKILL.md) | Updated | Write compact project instructions with clear operational rules. |
| [browser-smoke](../skills/extras/browser-smoke/SKILL.md) | Updated | Verify the web flows affected by a change and capture actual observations. |
| [cmux-cli](../skills/extras/cmux-cli/SKILL.md) | Updated | Control terminal surfaces through the documented interface. |
| [collaborative-delivery](../skills/extras/collaborative-delivery/SKILL.md) | Updated | Keep an explicit specialist delivery workflow outside the default pipeline. |
| [decide-about-disagreements](../skills/extras/decide-about-disagreements/SKILL.md) | Retained | Help the user resolve material dissent from an existing report. |
| [diverse-plan](../skills/extras/diverse-plan/SKILL.md) | Updated | Compare distinct designs only when the user requests that planning exercise. |
| [dynamic-harness](../skills/extras/dynamic-harness/SKILL.md) | Updated | Coordinate a longer requested workflow with bounded state and roles. |
| [fable-mindset](../skills/extras/fable-mindset/SKILL.md) | Updated | Keep decision and evidence discipline separate from model identity. |
| [knowledge-graph](../skills/extras/knowledge-graph/SKILL.md) | Updated | Maintain sourced facts and preserve conflicting evidence. |
| [peer-sessions](../skills/extras/peer-sessions/SKILL.md) | Updated | Coordinate bounded peer work through durable handoffs. |
| [review-gate](../skills/extras/review-gate/SKILL.md) | Updated | Declare review scope and report verified findings within it. |
| [skill-expert](../skills/extras/skill-expert/SKILL.md) | Retained | Author and review focused skills with validated contracts. |
| [verify-changes](../skills/extras/verify-changes/SKILL.md) | Updated | Run actual project checks and retain captured evidence. |
| [consensus-summary-html](../skills/visualization/consensus-summary-html/SKILL.md) | Updated | Render an existing council result without starting another council. |
| [explain-architecture](../skills/visualization/explain-architecture/SKILL.md) | Updated | Explain verified architecture with the appropriate visual artifact. |
| [html-explainer](../skills/visualization/html-explainer/SKILL.md) | Updated | Create a focused, validated HTML explanation. |

The shared library was also updated for stage routing, exact model plans, path resolution, approval, evidence, and safe resumption.

## Validation

1. All 129 unit tests passed across 12 suites. These include 13 implementation-launcher tests, 22 council tests, 7 finding-integrity tests, and runner, receipt, and routing checks.
2. All 48 command-guard cases passed.
3. Frontmatter and invocation parity passed for 59 executable skills. The wording guard passed for 22 guarded skills.
4. All 60 marketplace entries resolve to the source library, including the shared marker.
5. Syntax checks passed for 48 Python files, 19 JSON files, and the remaining routing TOML. All 119 checked relative Markdown links resolve.
6. A temporary flat copy installation contains all 60 entries. Its frontmatter validator, launcher, council tool, and seven runner wrappers load successfully.
7. `git diff --check` passed. The pre-existing workflow-call-map edit still has its original SHA-256.
8. CI now runs implementation approval, council approval, model receipt, and finding-integrity checks.

## Scope limits

No provider benchmark or paid model run was performed. The changes are in this checkout; existing installed copies are not updated. The pre-existing edit to `docs/workflow-call-map.html` was left intact. Publication and installed-copy updates are separate from this review.
