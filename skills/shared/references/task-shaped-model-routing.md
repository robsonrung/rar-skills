# Task-shaped model routing

Select a model for its role, then select the execution path. Read
[model-roster.md](model-roster.md) for exact identifiers and availability limits,
[host-model-execution.md](host-model-execution.md) for native delegation and
session reuse, and [workflow-stage-routing.md](workflow-stage-routing.md) for
skill placement. The defaults below implement the user's 2026-09-08 quality-first
policy. They do not claim a measured ranking for this repository.

## Task defaults

| Task | Primary seat and effort | Second seat and effort | Host-only choice for the Astra family |
| --- | --- | --- | --- |
| Web research and synthesis | Fable `max` | Astra `high` or `max` when tools and structured collection matter | Astra `high` or `max` |
| Ambiguous user problem | Fable `max` | Astra `max` | Astra `max` |
| Developer's technical problem | Astra `max` | Fable `max` | Astra `max`; Sol `max` |
| Many branches or competing approaches | Astra `ultra` | Fable `max` | Astra `ultra` |
| One deep reasoning chain | Fable `max` | Astra `max` | Astra `max` |
| TDD and failure-mode tests | Astra `max` | Opus `high` or supported `xhigh` | Astra `high` or `max` |
| Routine explicit functions | Terra `medium` | Sonnet `low` or `medium` | Terra `medium`; Luna `low` for trivial pure code |
| Normal repository changes | Astra `high` | Opus `xhigh` precision review, subject to support | Astra `high`; Sol `high` |
| Hard functions | Astra `xhigh` or `max` | Opus `max` | Astra `max`; Sol `max` |
| Difficult debugging and root cause | Astra `max` | Opus `xhigh` or `max` | Astra `max` |
| Large refactor or migration | Astra `ultra` | Fable `max` for design; Opus for independent code review | Astra `ultra` |
| Broad defect discovery | Astra `high` or `max` | Sol `high` or `ultra` | Astra `high`; Sol `high` |
| Precision and subtle code issues | Opus `xhigh` | Astra `max` | Sol `high`, then Astra `high` if independent of the writer |
| Defensive security | Verified Cyber route `high`, only under the roster's access conditions | Astra `max` or `ultra` | Astra `max` or `ultra`; Sol `ultra` |
| Architecture and trade-offs | Fable `max` | Astra `max` | Astra `max` |
| Documentation and explanation | Opus `high` | Fable `high` | Sol `high` |

The second choice is an alternative or a useful independent role, not a required
extra call for every task. A high-quality routine function can use Terra without
a separate cost experiment. Hidden ambiguity, a difficult failure, or system
impact changes its classification to the matching stronger route.

Use `ultra` when multiple hypotheses, a large migration, or broad exploration
justify it, and state that reason in the plan. Plan actual branches, workers,
write ownership, and call limits separately. Do not infer parallel execution from
the effort name. Never map a UI label such as Pro to a runner effort flag.

## Interview auto roles

`interview-me --auto` uses two distinct model contexts. Default to Fable `max`
as interviewer and Astra `max` as respondent for an ambiguous user or product
problem. For a developer's technical problem, use Astra `max` as interviewer and
Fable `max` as respondent. Explain the selected classification in the preview.
The respondent answers from supplied intent and evidence; it cannot grant user
approval or invent a material preference. Each role keeps its session through
the interview. The skill owns its round bounds and human decision boundary.

If the host is restricted to its own family, propose Astra `max` interviewer and
Sol `max` respondent as an explicit alternate. Do not silently turn a missing
Fable route into two Astra contexts. An external Fable runner remains a valid
route when external models are permitted.

## Implementation and review roles

Each task track has one implementer and at least one independent reviewer whose
model differs from the writer. A fresh instance of the writer model is not model
diversity. For normal or hard work, pair the implementation route with the Opus
precision route. For a routine function, a focused independent Astra review is
sufficient unless risk calls for the precision pass.

When broad review is justified, use Astra `high` or `max`, or Sol `high` if Astra
wrote the code. Add an Opus precision pass for subtle semantics, high impact, or
an explicit two-pass review. Do not make the writer the only reviewer. Design
review by Fable does not replace a code review. Integration review inspects the
combined revision and task seams; select its roles in the original run plan.

Require captured compiler, tests, lint, type, or security checks that apply to the
change. For TDD, capture red before green and cover failure paths. Do not weaken
tests to make a patch pass. Model opinions do not replace deterministic evidence.

## Approval and exact routes

`implement-tasks` presents a model summary before any worker starts. The user
can approve it or change any route. Save the approved machine form and validate
it against `implementation-routing-plan.schema.json`. Consensus keeps its own
explicit invocation and approval. Other workflows use their stated authority;
this reference does not add a universal approval step.

Each route records task, track, role, seat, model, execution mode, transport,
effort and control, receipt policy, unavailable action, and source artifact.
Resolve native capabilities before probing external CLIs. Keep context IDs and
iteration results in mutable run state rather than changing approved rows.

Use `--disable-fallback` for every approved runner route. `unavailable` is `block`
unless the user approved one exact alternate. An unexpected runner or configured model blocks the route.
For native routes, check the approved host and native transport as well.
`model_verification: required` blocks without a verified matching receipt.
`allow_unverified` permits execution only under the workflow's recorded approval,
with that limit in the report. A verified observed-model mismatch always blocks.
Do not silently change a model, effort, mode, role, receipt policy, or transport.

The approval record binds canonical content SHA-256 values for task and PRD
inputs and a digest of normalized routes. Reject duplicate paths and route IDs.
Sort inputs by `path` and routes by `id`, then `task_id`. Serialize with sorted
object keys, UTF-8, `ensure_ascii=false`, and compact JSON separators before
hashing. Normalize text line endings to LF and omit only a line exactly equal to
`**Status:** ready-for-agent`, `**Status:** in-progress`, `**Status:** done`, or
`**Status:** blocked`. A status transition can reuse approval; scope or acceptance
edits cannot. The launcher recomputes both digests before side effects.

Reuse approval while scope and routes match. When a route fails, continue
independent authorized work and report the affected row. A new model, unsupported
effort, or changed transport needs the calling workflow's change decision.
