# Model preview

How a skill picks models for its workers and gets the plan approved. Applying a method or lens in the current context, running a deterministic command, or waiting needs no model worker and no preview.

## Resolve

Run `python3 shared/scripts/model_routing.py resolve <route>` for each route the work needs (`show` lists them). Resolve only the roles the branch actually dispatches; never add a worker to fill a row.

- Precedence: the user's instructions, then [local preferences](local-config.md) (`--local-profile <name>`, plus `route_overrides` as `--role ROLE=SEAT[:EFFORT]`), then the central default. An explicit `--profile` wins over the local one. `runtime` selects null effort where a model has no effort control.
- [`model-routing.json`](../model-routing.json) is the only source of exact models and efforts. Never copy one into a skill.
- Add `--risk high` for a task that meets `policy.high_risk_triggers`. One sensitive task does not promote the rest of a feature.
- For a queue, resolve each task's route on its own risk. A preview never changes the model of the session already running.

Check each role's path before showing it: native delegation first, then `cli-runner`, `pi-runner`, or `muse-runner` ([host-model-execution.md](host-model-execution.md)). An installed CLI is not proof the route works.

## Show and approve

Show one row per worker: task and role, exact model and effort, host route (native or runner) with its tool policy, and the call limit. For an OpenRouter route, also show its `provider_routing` (`zdr: true`, `data_collection: deny`, and `require_parameters: true`) and name the gateway apart from the model author. Name anything missing.

Ask: **"Approve this plan, or specify changes."** Then:
- "Use defaults and run", or an exact model request, approves that setup as shown.
- An approval the caller already holds, such as an inherited approved plan or `interview-me --auto`, counts while its scope and controls still match.
- Silence is not approval.
- `models-consensus` keeps its own separate approval.

Save per-route changes to `.rar-skills/config.local.yaml` only when the user asks to keep them for future work.

## Mode selection

Use the mode the user named or the caller passed. Otherwise use the skill's safe default when it fits the invocation's authority. Ask only when the choice changes scope, cost, permitted effects, or an open decision, and ask once with the choices and their consequences. Keep doing independent authorized work while you wait.

## After approval

The approved plan is fixed ([work-state.md](work-state.md)). Dispatch, repair, retry, and resume use it as saved; nested skills and runners reuse it and never re-resolve, reread local preferences, or add workers. Keep **seat fidelity**: an unavailable model, unsupported effort, receipt mismatch, or failed privacy check blocks that route. Only an exact alternate named in the plan may run without a new decision. Allow one attempt and one repair with new evidence before considering more effort; recovery never resets the call ceilings. A change the user requests before dispatch replaces the plan for unfinished work only.
