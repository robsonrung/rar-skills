# Engineering Workflow Stage Routing

Where each engineering skill fits in the four stages. A skill runs only when its trigger changes a decision, a task contract, or the code. Apply methods and lenses in the current role; loading a skill is not dispatching a worker. Independent final code review is always required.

## 1. Interview Me: decisions that change the next question

Use a lens only when it changes the next question or prevents a false assumption. The interview records decisions with stable IDs and one source index; it runs no `design-gate`, review panel, or implementation practice. A question the repository can answer is not an interview question.

| Decision needed now | Skill | Recorded |
| --- | --- | --- |
| System style, service decomposition, data ownership, module or API boundary | `architecture-lens` or `software-design-philosophy` | Chosen shape, trade-off, rejected alternative |
| Domain boundary or business vocabulary | `domain-driven-design` (strategic) | Bounded context, language, integration choice |
| Container topology or event streams | `distributed-systems-patterns` | Pattern or event-driven verdict and its cost |
| Agent loop, durable state, or human gate | `agent-architecture-lens` | Mechanism and ceiling |
| User-facing flow or design direction | `frontend-design` | Flow, accessibility constraint, direction |
| Auth, data, input, tenancy, secrets, or abuse surface | `security-gate` threat-model-lite | Security decisions for the PRD |

## 2. To PRD: keep settled choices

The PRD reuses decisions by ID and rechecks only missing, changed, or disputed sources. It opens no fresh architecture choices and prescribes no test mechanics, patterns, or files. A missing decision goes to the user.

## 3. To Tasks: one PRD into executable slices

| Need | Skill |
| --- | --- |
| Repeated settled choices across tasks | [planning-reuse.md](planning-reuse.md) |
| Unresolved or changed boundary | `design-gate`; recheck only the blocking lens after a fix |
| Security level per task (`deep` or `standard`) | `security-gate` |
| Real test-design decision (integration or mock boundary, concurrency, brittle test) | `test-lens` |

Otherwise express acceptance as observable behavior.

## 4. Implement Tasks: apply the selected constraints

`implement-and-review` builds each task from its approved contract and the inherited `design-gate` constraints, rerouting only when implementation changes the design surface. A bound `review_policy` follows [feature-review.md](feature-review.md) and the engine's `Feature policy` section.

| Trigger | Skill | When |
| --- | --- | --- |
| New behavior or bug fix with a test seam | `tdd` | Default loop |
| Untested legacy code must change | `safe-incremental-coding`, then `tdd` | Characterization test first |
| Cause unknown | `diagnose` | Before any fix |
| Local smell, naming, or comment | `clean-code` | Refactor step |
| Behavior-preserving simplification | `coding-review-simplify` | After green; under a feature policy, in the combined pass |
| Test value or mock boundary | `test-lens` | Before writing or keeping the test |
| Stored state, migration, queue, cache, retry, concurrency, external API | `data-systems-coding-lens` | Before the step and in verification |
| Domain logic or context integration | `domain-driven-design` | Before the step |
| Module boundary, dependency direction, or concrete pattern pressure | `software-design-philosophy` or `architecture-lens` | When the gate selected it or the design changes |
| React component, hook, fetch, or render behavior | `advanced-react` | That surface |
| UI composition, design system, or visual quality | `frontend-design` | Selected UI work |
| Topology or agent control flow changes | `distributed-systems-patterns`, `agent-architecture-lens` | When selected or changed |
| Deep security slice | `security-gate` with `full-review` | Verify recorded decisions |

`models-consensus` is never an escalation; run it only when the user asks for more opinions.

## Small accepted task

One accepted task with a complete acceptance contract and no open product, data, security, public-contract, or dependency decision goes straight to `implement-and-review`. Otherwise settle the open decision in the applicable stage first.

## Handoff

Each stage passes one durable artifact: a decision record, a PRD, an approved task contract, or captured acceptance evidence. Never a transcript.
