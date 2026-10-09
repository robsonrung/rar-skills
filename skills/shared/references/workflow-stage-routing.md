# Engineering Workflow Stage Routing

Use this reference to place engineering skills in the four-stage workflow. It is a routing contract, not a checklist. A skill runs only when its trigger changes a decision, a task contract, or the implementation.

Apply methods and read-only lenses in the assigned coordinator or implementer by
default. Loading a skill is not worker dispatch. Select an independent specialist
only for a material risk or unresolved question and include its exact route in the
approved snapshot. Independent final code review remains required.

## 1. Interview Me: discover decisions that change the next question

The interview produces a decision record with stable decision IDs and one compact source index containing path, locator, authority, and content revision. It may use a broad lens when that lens changes the next question or prevents a false assumption. Use another only when the first decision makes it necessary. It does not run `design-gate`, implementation practices, a review panel, or every matching lens.

| Decision needed now | Procedure to apply | What the interview records |
| --- | --- | --- |
| System style, service decomposition, data ownership, or durable architecture trade-off | `macro-architecture` | Chosen shape, trade-off, and rejected alternative |
| Domain boundary, business vocabulary, or external-context relationship | `domain-driven-design` strategic route | Bounded context, ubiquitous language, and integration choice |
| Container topology, event-stream adoption, or distributed ownership | `distributed-systems-patterns` | Named pattern or event-driven verdict and its operating cost |
| Agent loop versus graph, durable state, or human gate | `agent-architecture-lens` | Signals that fire, needed mechanism, and ceiling |
| Enduring module, API, or interface boundary | `software-design-philosophy` or `architecture-lens` | Boundary, characteristics in tension, and accepted cost |
| User-facing flow or durable design-system direction | `ui-ux-pro-max` | User flow, accessibility constraint, and design direction |
| Exposed auth, data, input, tenancy, secrets, or abuse surface | `security-gate` threat-model-lite | Security decisions for the PRD |

Interview lenses contribute decision fields to that existing record. Their standalone brief, code, test, and comment mechanics do not apply at this stage. The user may decide no broad design work is needed. Record that fact and continue. A question whose answer can be learned from the repository is not an interview question.

## 2. To PRD: preserve settled choices

The PRD turns the decision record into one specification. Reuse its source locators
and revisions by decision ID; recheck missing, changed, or disputed sources. It does not open fresh
architecture choices, invoke a council, or repeat an interview. When a decision
needed for implementation is missing, settle that decision with the user.

The PRD carries outcomes, constraints, security decisions, and observable success conditions. It does not prescribe test mechanics, design patterns, or files to edit.

## 3. To Tasks: turn one PRD into executable slices

For each slice, apply `design-gate` once. It selects at most three relevant inline lenses
and records the canonical gate result from [gate-result.md](gate-result.md) in the Slice Contract. Preserve blocking and advisory finding IDs and review focus. Reuse settled shared decisions when their scope and evidence match; classify each slice's design and security risks separately.
Recheck only a blocking lens after the design changes. Apply `security-gate` to
record `security: deep` or `security: standard`. Reuse these findings in implementation.

Apply `test-lens` only for a real test-design decision, such as an integration
boundary, mock boundary, concurrency case, or brittle test. Otherwise express
acceptance as observable behavior. Settle material unanswered decisions before
approval. Task-only planning presents canonical task drafts without worker route
resolution. When execution is requested, the caller can offer combined approval
of those drafts and the required concrete worker routes.

## 4. Implement Tasks: apply the selected constraints

The implementation engine starts from the approved Slice Contract. It uses the inherited `design-gate` constraints as its last focused design check and re-routes only when implementation changes the slice's design surface. It does not replay every lens.

| Trigger during implementation or review | Procedure to apply | Moment |
| --- | --- | --- |
| Any new behavior or bug fix with a usable test seam | `tdd` | Default execution loop |
| Untested legacy code must change | `safe-incremental-coding` then `tdd` | Build the characterization test net first |
| Failure is surprising or cause is unknown | `diagnose` | Prove the cause from existing evidence or a bounded probe before fixing |
| Green refactor, local smell, naming, or comment decision | `clean-code` | Refactor step only |
| A behavior-preserving simplification would help the next reader | `coding-review-simplify` in the implementer context | After green, before final snapshot and check capture, including candidates found after implementation |
| Test value, mock boundary, or brittle test needs a decision | `test-lens` | Before writing or keeping that test |
| Stored state, migration, queue, cache, retry, concurrency, or external API | `data-systems-coding-lens` | Before the affected implementation step and in verification |
| Domain logic, aggregate, value object, domain event, or context integration | `domain-driven-design` tactical or strategic route | Before the affected implementation step |
| Module boundary, dependency direction, deep interface, or scope pressure | Inherited `architecture-lens` or `software-design-philosophy` | Only when selected by the gate or the design changes |
| Emerged structural pressure such as a repeated variation or tangled notification | `design-patterns` | Only after the pressure is concrete |
| React component, hook, context, fetch, overlay, or render behavior | `advanced-react` | Plan and implementation of that surface |
| Design system, cross-screen UX, or UI quality review | `ui-ux-pro-max` | Selected UI work and delivery review |
| Bespoke visual direction or high-craft frontend implementation | `frontend-design` | When the user asks for creative visual direction |
| Distributed topology or event-stream contract changes | Inherited `distributed-systems-patterns` | Only when selected by the gate or topology changes |
| Agent control flow changes | Inherited `agent-architecture-lens` | Only when selected by the gate or control flow changes |
| Deep security slice | `security-gate` with `full-review` | Verify recorded decisions against the implementation |

`models-consensus` is never a workflow escalation. Run it only when the user explicitly asks for more opinions. Its own skill presents the proposed seats before work begins.

## Small accepted task

Select this entry first when the user supplies one accepted task. Use standalone `implement-and-review` for one accepted task with a complete
acceptance contract and no unresolved product, data, security, public contract,
or dependency decision. This is an entry to the existing engine, not another
stage. Keep scoped implementation, required checks, and independent final review.
Bind the accepted task and its source evidence, then reuse a matching approved execution route or obtain the required route approval. For a PRD queue requested with execution, offer the existing combined task and model preview before approval. A task-only response grants no model authority. If a material decision remains open, settle it through the applicable stage first.

## Completion rule

The next stage receives a small, durable handoff: a decision record, one PRD, an approved Slice Contract, or captured acceptance evidence. Do not replace a handoff with a transcript or a broad list of skills that did not run.
