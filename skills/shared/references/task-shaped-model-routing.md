# Task-shaped model routing

Choose the model by the work it must do. Use the seat names and model mapping
in `model-roster.md`. Use the stage placement rules in
`workflow-stage-routing.md` to decide which engineering skill shapes the work.

## Approval route

`implement-tasks` presents a model summary before any worker starts. The user
can approve it or change any route. After approval, store the machine form at
the path selected by the implementation run and validate it against
`implementation-routing-plan.schema.json`.

Each active task track has one approved implementer and one approved reviewer.
Each route records its task, track, role, seat, runner, model, effort, effort
control, model-verification policy, mode, unavailable action, and source task
artifact. The plan records the canonical content SHA-256 of every task or PRD
artifact and the digest of the normalized route list. A route is invalid when
it has no user approval, its reviewer is the same model as its implementer,
its input digest changed, or it relies on an automatic fallback.

Use `--disable-fallback` for every approved runner route. `unavailable` is
`block` unless the user approved one exact alternate route. A receipt with an
unexpected runner or configured model blocks the route. A route with
`model_verification: required` also blocks unless `model_receipt.status` is
`verified` and its observed model matches the approved model. A route with
`allow_unverified` may continue only because the user approved that limit; its
report must say that the serving model was not verified. A verified receipt
with a different observed model always blocks. Do not replace a model with a
nearby model.

For the approval digests, reject duplicate input paths and route ids. Sort
inputs by `path` and routes by `id`, then `task_id`. Serialize with sorted
object keys, UTF-8, `ensure_ascii=false`, and compact JSON separators before
calculating SHA-256. For each text task artifact, normalize line endings to LF
and omit only a line exactly equal to `**Status:** ready-for-agent`,
`**Status:** in-progress`, `**Status:** done`, or `**Status:** blocked` before
calculating `content_sha256`. This permits a task-status transition without
reusing approval after a scope or acceptance edit. The launcher recomputes both
digests before side effects.

The approval preview names the model-verification policy for every route. With
the current wrappers, Astra and Fable may need `allow_unverified` because their
headless output does not expose a serving-model identifier. The user approves
that condition explicitly. A future native or provider receipt can use
`required` instead. Dcode cannot appear in an approved implementation or review
route because its wrapper does not forward the selected model.

## Default recommendations

| Work shape | Implementer | Reviewer |
| --- | --- | --- |
| Bounded change with explicit acceptance checks | Astra, `medium` | Fable, `medium` |
| System boundary, security, data integrity, difficult diagnosis, or multistep integration | Astra, `high` | Fable, `high` |
| Repository-scale feature, large refactor, performance work, long-running coding, or high-fidelity interface | Fable, `high` | Astra, `high` |
| Narrow visual interface work with a settled contract | Fable, `medium` | Astra, `medium` |
| Final reconciliation across task seams | Astra, `high` | Fable, `high` when an independent second review is needed |

`low` is allowed only after local evidence shows it passes the same acceptance
contract. `xhigh` is for unresolved high-risk work. `ultra` needs a recorded
reason. Do not select Sol or Terra by default because they are less capable
than the frontier routes. Use either only when the user selects it or local
evidence shows equal acceptance at a better elapsed cost.

## Evidence boundary

Provider capability statements guide the initial task fit. They do not prove
that a local account can invoke a model or that one route is better for this
repository. A transport probe confirms only the CLI. A completed envelope with
the approved runner and `model_receipt.status: verified` confirms model access.
An `allow_unverified` route proves only that the configured transport ran.

When considering Sol, Terra, or any future candidate, compare it with the
approved frontier route on the same acceptance contract. Record acceptance,
elapsed time, repair rounds, and model-receipt status. Keep the frontier route
when the comparison is tied, incomplete, unverified, or lower quality.
