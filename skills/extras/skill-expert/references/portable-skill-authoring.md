# Portable Skill Authoring

Use this reference when a change touches model routing, host capabilities, authority, or a protocol several skills share.

## Model routing

`shared/model-routing.json` owns every model and effort mapping. Skill prose names a route or role, never a model ID; concrete IDs belong in that file, run plans, receipts, and test fixtures.

A skill that dispatches models uses this pattern and nothing longer:

1. Use the models the user names, or the routes in a plan the skill inherited. Otherwise run `python3 shared/scripts/model_routing.py resolve <route>` with the route that fits the work (`show` lists them).
2. Show the plan: each role with its model, effort, and host route, plus any ceiling. Ask: **"Approve this plan, or specify changes."** An inherited approved plan is already the approval.
3. Route each role by host. T3 Code: `delegate_task`, continued with `t3_thread_send`. Claude Code or Codex: a native subagent, continued by messaging the same subagent. A model the host lacks: the matching `*-runner` skill.
4. One persistent context per role for the whole task. Later turns of a role go to its context; different roles never share one.
5. **Seat fidelity**: an unavailable model blocks its role, and the skill reports it. It never swaps in another model or the host's own.

A skill that does not dispatch models says nothing about routing, and no skill opens with routing ceremony. `skills/engineering/engine/implement-and-review/SKILL.md` is the reference implementation.

## Protocol and judgment

Keep a rule whose omission could change authority, state, coverage, counts, output fields, or a downstream handoff.

| Keep explicit | Leave to judgment |
| --- | --- |
| Output paths, fields, enums, schemas | Order of independent investigations |
| Dependencies and required state transitions | Number of alternatives to sketch |
| Approval, mutation, and isolation boundaries | Generic self-checks and reread loops |
| Evidence and coverage a consumer needs | Repeated rationale and quality reminders |
| Bounded retries and terminal outcomes | Choice among several valid techniques |

Put each rule beside the action it governs, and state it once, in its owner. Another skill points to the owner rather than restating it.

## Authority

An explicit change request authorizes its necessary reversible work; an audit request authorizes none. Reuse approval already given for the same scope; silence is not new approval. Ask only when a choice changes scope, cost, permitted effects, or an unresolved decision, and keep working on whatever that choice does not block.

A multi-agent tool being present is no reason to use it. Delegation needs a reason (independent, sizeable, parallel work), and each worker needs a scope, an output contract, and an owner who integrates its result.

## Portability

Inspect the real adapter or consumer when a change depends on its behavior. A prompt-only restriction is not a sandbox, and one missing binary does not prove the host lacks every equivalent capability. Use deterministic checks for metadata, paths, schemas, and scripts; claim a behavioral improvement only from a bounded comparison, never from fewer words or one good run.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
