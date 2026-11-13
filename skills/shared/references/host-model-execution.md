# Host model execution

How to run an approved worker route on the current host. [model-preview.md](model-preview.md) owns selection and approval; this reference starts from an approved route. Keep **seat fidelity**: the route keeps its model and reuses its own role context.

## Choose the execution path

1. Inspect what the host actually exposes: tools, model catalog, effort control, role isolation, result collection, and follow-up support. Don't infer capabilities from the app name or the coordinator's model.
2. **T3 Code:** run every model call as an internal subagent, including organizers, moderators, judges, reviewers, and synthesizers. Use the native subagent tool only when it supports the approved provider, model, and settings; otherwise use `delegate_task`. Before the first `delegate_task`, call `orchestrator_capabilities`. Pass settings in `target.options`. Follow the tool result for continuation and waiting. Each independent review or recheck requires a new `delegate_task`. If the route is unavailable, report the blocked role. **Exception: run every Muse route through `muse-runner`.** T3's Muse provider has no `auto` runtime mode, so its children ask for approval on every command; the runner runs Muse without approval prompts and read-only by default. Never use other external CLIs, runner scripts, or shell model calls in this host. This rule also applies to retries and explicit transport requests.
3. **Claude Code or Codex:** use a native subagent when the host has the exact model. Don't start a runner to call a model the host already runs natively. The parent session is not a separate worker.
4. **Outside T3 Code, model the host lacks,** or a native path that cannot meet the route: use `cli-runner`, `pi-runner`, or `muse-runner` ([runner-common.md](runner-common.md)). An explicit user request for a CLI or transport wins.
5. If no path meets the model, effort, isolation, tools, or receipt policy, report it. Run only an exact alternate the plan names; never substitute the coordinator's model.

| Host | Native | Runner when needed |
| --- | --- | --- |
| Claude Code | Claude subagents with exact model selection | Other families, or a control the native tool lacks |
| Codex | Astra, Sol, or Terra subagents; task threads where authorized | Other families |
| T3 Code | Internal subagents with the approved provider, model, and settings | `muse-runner` for Muse routes; otherwise never, report unavailable routes |
| Pi or another host | Its actual exposed delegation | A checked runner for what it lacks |

These are hints, not guarantees. An installed CLI or `agents/openai.yaml` metadata does not create a native seat. A native tool may inherit a model only when its exact identity matches the route. Creating, renaming, or deleting user-owned tasks needs the user's request.

## Keep role contexts through iterations

Start one isolated context per task and role, with no parent conversation history (`fork_turns: none` where the host offers it), and give it the bounded brief from [handoff-contract.md](handoff-contract.md). Reuse that context for the same role's later turns: interview rounds, fixes, rechecks, debate rounds. Start a new one for a different task, an independent role, a blind opening, or an approved model change.

An implementer and its reviewer never share a context. Consensus seats don't see each other's answers before the protocol allows it. Judges start without seat history. Repeated turns from one context are one opinion, not several.

Keep each role's actual context ID or session path with the run's work state ([work-state.md](work-state.md)). A background job ID, a requested model, or a setup token is not a context ID; wait for the real handle before sending work. Continue with that ID, never a "most recent session" selector while several roles run; each runner documents its own session handling. A lost session is rebuilt from that role's artifacts under the same route, and the report says it was a reconstruction. Keep a reviewer open while fix cycles remain.

## Browser and provider capabilities

A runner does not inherit the host's browser tools or logged-in session. Check the selected browser mechanism inside the worker's environment. For visual work, prove the model receives the screenshot as image content; a file path in a prompt is not an image.

For Pi gateway routes, carry the route's `provider_routing` into every request, including repairs and resumes. The wrapper proves the serialized privacy fields locally before sending repository material and keeps a policy receipt. Keep the model author, gateway, and observed inference provider apart; a model prefix doesn't name the inference host. A missing required control blocks the route.

## Evidence and authority

The configured model, the observed serving model, and completion are separate facts. Record a serving model only from a native event or the model the CLI or provider reports, such as Claude's or Grok's `modelUsage`. Native transport does not make a receipt verified or enforce read-only tools; when tools can't enforce the scope, use a no-tools brief or a restricted route, and don't call a prompt instruction a sandbox. The calling workflow owns approval, budgets, writes, and the terminal status.

Save raw completion output as soon as a call returns. A missing session ID or malformed result is a receipt failure to reconcile, not permission to restart. A native completion that reports no model stays unverified; never copy the configured model into an observed field.

## Environment

Before dispatch, bind the worktree, allowed write paths, service ports, and artifact root into the brief, and check the host's permission surface for that worktree. Operating-system write access is not sandbox authority. Resolve the shared library and selected skills once with `skill_paths.py --start <loaded-skill> --names <skill> ...` and reuse the paths.
