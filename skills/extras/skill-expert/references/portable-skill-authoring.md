# Portable Skill Authoring

Use this when a skill dispatches models or relies on a host capability. A skill that dispatches nothing says nothing about routing.

## The routing pattern

`shared/model-routing.json` owns every model and effort setting. Skill prose names a route or role, never a model ID. A skill that dispatches models uses this pattern and nothing longer:

1. Use the routes in a plan the skill inherited, or else the models the user names. Otherwise run `python3 shared/scripts/model_routing.py resolve <route> --provider <host> [--risk high]` with the route that fits the work (`routes` lists every route and when to use it). `<host>` is the provider the session runs on: `claude`, `openai`, `grok`, `gemini`, or `muse`.
2. Show each role with its model, effort, and host route, plus any ceiling. Ask: **"Approve this plan, or specify changes."** An inherited approved plan is already the approval.
3. Route each role by host:
   - **T3 Code:** start it with `delegate_task` and continue it with `t3_thread_send`. A Muse route uses `muse-runner`.
   - **Claude Code or Codex:** use a native subagent when the host has the model, and continue it by messaging the same subagent.
   - **A model the host lacks:** use `cli-runner`, `pi-runner`, or `muse-runner`.
4. Give each role one persistent context for the whole task. Different roles never share a context.
5. **Seat fidelity**: an unavailable model blocks its role, and the skill reports it. Never swap in another model or the host's own.

`skills/engineering/engine/implement-and-review/SKILL.md` is the reference implementation. Copy its shape, not its roles.

## Delegation

Having a multi-agent tool is not a reason to delegate. Delegate independent, sizeable work that can run in parallel. Do not delegate a handful of tool calls or the check of your own work. Each worker gets a scope, an output contract, and an owner who integrates its result. The lead keeps working while workers run.

## Host behavior

Inspect the real adapter or consumer before relying on its behavior. A restriction stated only in the prompt is not a sandbox. One missing binary does not prove the host lacks every equivalent.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
