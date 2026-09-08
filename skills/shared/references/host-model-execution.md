# Host model execution

Use this contract whenever a skill delegates to more than one model or resumes
a role. Select the model from `model-roster.md` and `task-shaped-model-routing.md`;
then select the native host tool or external runner. Preserve **seat fidelity**:
"This route keeps the selected model and reuses its own role context."

## Choose the execution path

1. Inspect the current host's exposed tools, model catalog, and restrictions.
   Confirm exact model selection, supported effort, role isolation, tool policy,
   result collection, and follow-up or resume support. Do not infer capabilities
   from the app name or the model running the coordinator.
2. For a selected model available through native delegation, use that native
   subagent or task context. Do not start a runner just to call the same native
   model. A native parent session alone is not a separate worker.
3. Use a persistent native task thread when the host exposes it for delegation
   and the action is authorized. If creating a user-owned task requires an
   explicit request, prefer internal subagents. A skill cannot grant permission
   to create, rename, pin, archive, or delete user-owned tasks.
4. For a foreign model, or a native path that cannot meet the exact route, use
   an available external runner. State why it is needed before dispatch. An
   explicit user request for a particular CLI or transport takes precedence.
5. If neither path can meet model, effort, isolation, tools, or receipt policy,
   report the missing capability. Use only an authorized exact alternate route.
   Do not substitute the coordinator model or pretend a session is persistent.

| Active host | Native preference | External route when needed |
| --- | --- | --- |
| Claude Code app or CLI | Exposed Claude subagents with exact Fable, Opus, Sonnet, or Haiku selection | Other model families, or a required control absent from native tools |
| ChatGPT app or Codex app/CLI | Exposed Astra, Sol, Terra, or Luna subagents; persistent task threads where supported and authorized | Foreign families, or an exact route unsupported by the native tools |
| Pi | Exposed delegation with the selected provider model; Pi is a multi-provider host | A configured model alone does not prove a subagent extension exists; use a checked runner if needed |
| Grok or another host | Its actual exposed model selection, isolated worker, and follow-up tools | A checked external route for capabilities the host does not expose |

These are discovery hints, not universal capability claims. An installed CLI,
model family name, or `agents/openai.yaml` metadata does not create a native seat.
Native tools may inherit a model only when its exact configured identity matches
the route and the host permits inheritance. Otherwise select it explicitly.

For an implementation plan, use `mode: native` and `effort_control: native`.
The schema keeps `runner` as the model-family adapter key for compatibility;
it does not require a CLI call. The `native` object records `host`,
`transport` (`subagent` or `thread`), `capability_source`, and `supported_efforts`.
The selected effort must appear in that observed capability list. Record the
returned context ID later in run state. Older native rows with runner effort
control remain legacy records; they are not proof of native capability checks.

## Keep role contexts through iterations

Start one isolated context per task and role. Keep that context for later turns
of the same role: interview rounds, debate rounds, gap repair, implementation
fixes, reviewer rechecks, or integration reconciliation. Create a new context for
a different task, independent role, blind opening, or approved model change.

An implementer and reviewer never share a session. Consensus opening seats do
not see each other's answers before the protocol allows it. Judges start without
opening-seat or organizer history. Persistence preserves a role's evidence; it
does not merge roles or turn repeated turns into extra independent opinions.

Persist each role's route ID, host, transport, returned context ID or session
path, task and role, configured model and effort, tool policy, receipt reference,
last input revision, completed turn, status, and pending call ID in the workflow's
existing state file. A background job ID, UI metadata file, requested model, or
local transcript path is not a native conversation ID.
If native setup is pending, wait for the usable context handle before sending
work. A temporary setup identifier is not a ready model session.

Before each call, record its attempt and pending state. After it returns, capture
the result and receipt. On resume, reconcile the pending call with its actual
status before resending. Use the recorded ID to send only the next prompt,
changed inputs, and relevant artifact paths. Never use a global "last session"
selector when concurrent roles can select the wrong context.

Keep contexts available until their role is complete and evidence is captured.
Do not close a reviewer after its first pass when fix cycles remain. Do not reuse
a task worker for an unrelated task. Release only resources owned by this run
and only within the host's authority.

## External session adapters

Use the selected runner's actual command reference. The current adapters expose:

| Runner | Persistent route |
| --- | --- |
| Claude | Capture `session_id` from structured output; use `--resume <id>`. Omit `--no-session-persistence` for an iterative role. |
| Codex | Capture `session_id`; use `--resume <id>`. Avoid ephemeral mode for iterative work. |
| Grok | Capture `session_id`; use `--resume <id>`. Stored sessions persist under the CLI's own controls. |
| Pi | Allocate a unique session file per role and pass it through `--session <path>` on the first and later turns. The stream does not supply a new session ID. Omit `--no-session-persistence` and `--ephemeral`. |
| Gemini through agy | No exact native session ID is exposed. Its shared latest-conversation continuation is unsuitable for concurrent independent roles. Use proven isolated runtime state or a disclosed reconstruction from artifacts. |
| Other runners | Inspect their continuation support. Do not assume another CLI's flags work. |

A text handoff can restore facts after a lost or unsupported session, but it is
not native resumption. Record the break and recreate only the same authorized
role from its checkpoint. Preserve call counts, write ownership, input revision,
and approval. A changed model or transport follows the workflow's route-change
rule. If the last call's outcome is uncertain, reconcile it before retrying.

## Evidence and authority

Configured identity, serving-model evidence, and completion are separate facts.
Keep native model and effort selection evidence with the route. Store observed
serving identity only from a native or provider event. Native transport does not
automatically make a receipt verified or enforce a read-only tool profile.

When tools cannot enforce the required scope, use an authorized no-tools brief
or a route with the required restrictions. Do not describe a prompt-only request
as a sandbox. The workflow owns approval, budgets, allowed writes, and terminal
status. This contract adds no hidden calls, review panel, or publication action.
