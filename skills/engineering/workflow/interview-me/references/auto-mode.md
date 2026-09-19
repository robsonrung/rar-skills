# Auto interview mode

Read this only when the invocation includes `--auto`. This mode uses two fixed
roles to progress the **design tree** from supplied scope and repository facts.
It is not a council and does not invoke `models-consensus`.

## Route and authority

Read `shared/references/model-roster.md`,
`shared/references/task-shaped-model-routing.md`, and
`shared/references/host-model-execution.md`. Resolve `interview-product` or `interview-technical` from
`shared/model-routing.json`. That file owns all role, model, and effort defaults.

Classify the request before the first call:

| Request shape | Route |
| --- | --- |
| Ambiguous user or product problem | `interview-product` route |
| Explicit developer technical problem | `interview-technical` route |
| Unclear | `interview-product` route; record the classification assumption |

Record a compact auto route preview with the classification, roles, host
execution paths, effort, receipt status, and ceilings. Continue without a
separate model approval: `--auto` is **the mandate** for the selected default
pair and for automated answers inside the supplied scope. A missing capability
or a change to model, effort, role, transport, or receipt policy pauses the
affected route for a user decision. Never silently use the coordinator model, a
different host model, or two contexts for one role.

Record the route's `model_verification` policy. `--auto` authorizes an
`allow_unverified` route when the host cannot expose the serving identity, but
the route preview and run state must label that limit. A `required` route stays
blocked without a matching verified receipt.

Use native isolated subagents or persistent task threads when the selected model
is native to the active host. For a foreign model or an unsupported native path,
use the checked external runner selected by the shared reference. Reuse the
same role context throughout the run. A lost context may be recreated only as
the same recorded role and route from its checkpoint, as the host execution
contract permits.

Every external runner call names the recorded model and effort and passes
`--disable-fallback`. Accept a result only when `effective_runner` and
`configured_model` match the recorded route, `fallback_reason` is empty, and a
verified `effective_model` does not differ from the requested model. Apply the
recorded receipt policy before the result enters the decision record.

## Role protocol

Create two isolated role contexts. They exchange only the persisted decision
record, question packets, answer packets, and cited repository evidence. Do not
merge their conversations or call a later response an independent opinion.

| Role | Job | Inputs | Required output |
| --- | --- | --- | --- |
| Interviewer | Build and recompute the frontier | Request, decision record, prior answer packet, relevant repository facts | Up to five independent questions, each with repository basis, materiality, and dependencies |
| Respondent | Answer the packet from evidence and supplied authority | Question packet, decision record, cited evidence, explicit user scope | Per-question answer or `awaiting-human`, evidence, source category, assumptions, and reason |

For an external runner, keep the semantic role in state and use this supported
analysis adapter role:

| Semantic role | Runner role |
| --- | --- |
| Interviewer | `planner` |
| Respondent | `researcher` |

The interviewer asks exactly five questions when five independent frontier
decisions exist. It asks fewer only when fewer independent decisions exist or
the host cannot present five. It never asks more than five.

The respondent may settle a technical fact, constraint, or reversible choice
when the supplied scope and evidence determine it. It must use one source
category for each result:

1. `user-supplied`: an explicit statement in the request or a later user reply.
2. `repository-evidence`: an observed project fact with a path, locator, or
   command result.
3. `automated-inference`: a stated inference from the supplied scope and cited
   evidence. Explain why it does not require a preference or approval.
4. `nonmaterial-default`: a documented default for a nonmaterial uncertainty.
5. `out-of-scope`: an explicit boundary.
6. `awaiting-human`: a material decision that remains unresolved.

The respondent must not claim a user preference, approval, acceptance, or
external authority that was not supplied. It must mark a question
`awaiting-human` when it needs product preference, policy or risk acceptance,
external authority, data ownership, a security commitment, or another material
choice that evidence and scope do not decide. Model output is not runtime
evidence. Use `to-prototype` only when the **smallest reversible move** can
settle the decision under the supplied scope.

Continue automatic rounds without pausing for ordinary answers. Complete every
independent grounded or reversible question that does not depend on a material
unknown. Then collect only the remaining material unknowns into one user request
of at most five questions. Do not ask for approval between automatic rounds.

## State, artifacts, and bounds

Use `shared/references/run-state-contract.md`. Keep **the ledger, not the
transcript** at:

```text
.ai-workflow/work/<feature-slug>/interview-auto/<run-id>/run-state.json
```

Use the same directory for `round-<n>-questions.json` and
`round-<n>-answers.json`. The decision record remains at
`.ai-workflow/work/<feature-slug>/decision-record.md`. Store artifacts by path;
do not put full conversation transcripts in state.

Under `## Auto interview run` in the decision record, store `Run ID`, `State`,
and `Status`. Update the pointer at each checkpoint. It is the first resume
lookup; it is not a substitute for the state validation below.

Before the first dispatch, append this required entry to the shared `gates`
array. It records the explicit `--auto` authorization; it does not ask for a
second approval:

```json
{
  "gate": "auto_route_authorization",
  "decision": "approved",
  "source": "--auto",
  "scope_fingerprint": "sha256 of supplied request and constraints",
  "original_input_revision": "initial source revision or digest",
  "route_fingerprint": "sha256 of the selected role routes"
}
```

Calculate `scope_fingerprint` from the stable supplied request and constraints
plus the original input revision. Exclude the evolving decision record and
round packets so ordinary answers do not invalidate the mandate. A later
material scope change appends a new gate with its user-message reference and
updated fingerprint before affected calls. A route change still follows the
route-change boundary.

Keep the required shared state fields and one `auto.roles.<semantic-role>` entry
for each role:

```json
{
  "auto": {
    "request_shape": "ambiguous_user_or_product",
    "scope_reference": "user request reference",
    "scope_fingerprint": "stable supplied-scope digest",
    "route_fingerprint": "selected-route digest",
    "decision_record_path": ".ai-workflow/work/<feature-slug>/decision-record.md",
    "roles": {
      "<semantic-role>": {
        "route_id": "recorded route id",
        "semantic_role": "interviewer or respondent",
        "runner_role": "planner or researcher or null for native",
        "task": "feature slug",
        "host": "active host",
        "transport": "native_subagent_or_runner",
        "context_id": "returned context id or session path",
        "requested_model": "selected model",
        "configured_model": "configured model or null",
        "effective_model": null,
        "effort": "selected effort or null",
        "effort_control": "configured or runtime",
        "tool_policy": "selected tool policy",
        "capability_source": "native or runner capability evidence",
        "supported_efforts": ["observed supported effort values"],
        "model_verification": "allow_unverified or required",
        "receipt_reference": "host or provider receipt path or null",
        "model_receipt": {"status": "unverified", "source": "configured_model", "observed_model": null},
        "last_input_revision": "input digest or revision",
        "pending_call_id": null,
        "completed_round": 0,
        "status": "ready"
      }
    },
    "open_frontier": [],
    "round_artifacts": []
  }
}
```

Replace placeholder receipt values only with actual host or provider evidence.
A configured model label, a transcript, or a self-description is not a verified
receipt. Persist a pending call and its attempt before dispatch; reconcile it
before sending another prompt after a restart.

Use these ceilings from the first checkpoint:

| Ceiling | Value |
| --- | --- |
| Automatic rounds | 5 |
| Questions in one round | 5 |
| Normal role calls | 10 |
| Repair calls | 10 |
| Total dispatches | 20 |

One normal interviewer call and one normal respondent call make an automatic
round. Validate each packet for its required fields and question count. Reconcile
the recorded pending call before a repair. Send one repair prompt to the same
recorded role context only for malformed output or a transient same-route
failure with intact model, effort, transport, and receipt policy. The
orchestrator increments the matching `attempts` entry before each call: **the
model never decides the retry**. A second eligible failure records `failed`; do
not replace the role.

An unavailable seat, fallback, unexpected runner or configured model, verified
model mismatch, unsupported effort, changed transport, or missing required
receipt pauses the affected route as `awaiting_human`. Do not send a repair
prompt or select an alternate route.

The run has **three exits**: `complete` when the ready-for-PRD gate passes,
`failed` when an allowed repair is exhausted, and `ceiling_hit` when a listed
ceiling is reached. `awaiting_human` is a durable pause for a material unknown.
Do not extend a ceiling, reset attempts, or start a new run without a user
instruction.

## Resume and ready-for-PRD gate

Before creating roles, read the decision-record pointer. If it names an
unfinished state whose gate, scope fingerprint, and route fingerprint match,
resume that run by its `run_id`. If the pointer is absent or stale, inspect
`.ai-workflow/work/<feature-slug>/interview-auto/*/run-state.json`. Resume when
exactly one unfinished state matches. When multiple candidates or a mismatch
remain, record `awaiting_human` and present their paths; do not launch new roles.

On resume, reuse each recorded context ID and pass only the next prompt, changed
input, and artifact paths. Reconcile a pending call before retrying it. Keep all
attempt counters, round artifacts, route values, and material-unknown items. A
completed, failed, or ceiling-hit run does not restart itself.

Set `decision-record.md` to `ready-for-prd` only when all of these are true:

1. Every frontier branch has a `user-supplied`, `repository-evidence`,
   `automated-inference`, `nonmaterial-default`, or `out-of-scope` result.
2. No `awaiting-human` material decision remains.
3. Each automatic result records its source category, evidence paths or
   locators, assumptions, and the role execution reference.
4. Every `automated-inference` states why the supplied scope permits it and why
   it is not an invented user preference or approval.
5. Role route and receipt limits are recorded accurately in the run state.

Otherwise retain `draft`, record the open frontier, and present only the next
material questions or the terminal limit. The next workflow step after a passed
gate is `to-prd`.
