---
name: cmux-cli
description: "Control cmux workspaces, panels, terminal input, notifications, and sidebar state through its CLI. Use when the user asks to inspect or manage cmux, create or target a workspace or panel, send text or keys, or report task status in cmux."
---

# cmux CLI

Use the cmux CLI as the default interface. Treat every command as acting on a
specific workspace, panel, or surface. **Observable behavior** is the anchor:
state the intended target, run the command, then query the cmux state that can
prove the result.

## Establish Context

1. Run `cmux ping`. If it fails, report that cmux is unavailable or not
   responding. Do not install it, change socket settings, or use another
   terminal manager unless the user asks.
2. Run `cmux identify --json` to capture the focused window, workspace, panel,
   and surface. Use `cmux current-workspace --json` or
   `cmux list-workspaces --json` when the request names a workspace rather than
   the focused one.
3. For a non-focused target, resolve its identifier from JSON output and pass
   the documented scope flag: `--window`, `--workspace`, or `--surface`.
   Request `--id-format both` if a reference ID and UUID must be distinguished.

Say: “The **observable behavior** I will verify is that surface `<id>` receives
the requested input.” Never infer the target from a previous command when a
fresh query can establish it.

## Execute the Requested Operation

Use one `cmux` command per shell call. Prefer JSON output when parsing IDs or
reporting state. Read `references/cli-reference.md` from this skill's directory
when an operation is uncommon or its exact flags are not below.

### Workspace and Panels

```bash
cmux new-workspace
cmux select-workspace --workspace <workspace-id>
cmux new-split right
cmux list-panels --json
cmux focus-panel --panel <surface-id>
```

`new-split` accepts `left`, `right`, `up`, or `down`. Create a workspace or
split only when the user requested that state change. Before
`close-workspace --workspace <workspace-id>`, identify the workspace and obtain
explicit user intent to close it.

### Terminal Input

Send text to the explicit surface when a target is known. Send Enter separately
when the text is meant to execute.

```bash
cmux send --surface <surface-id> "npm test"
cmux send-key --surface <surface-id> enter
```

`send` changes terminal input and `send-key enter` executes it. Do not send a
command to a terminal merely to inspect state. Inspect with the cmux query
commands first. `send-key` supports `enter`, `tab`, `escape`, `backspace`,
`delete`, and the arrow keys.

### Status, Progress, Logs, and Notifications

Use a unique, task-scoped key for status. Clear only state owned by that key.

```bash
cmux set-status task-build "running" --icon hammer --color "#ff9500" --priority 80
cmux set-progress 0.5 --label "Tests running"
cmux log --level progress --source task-build "Tests started"
cmux notify --title "Task complete" --body "Tests passed"
```

`clear-notifications` and `clear-log` remove shared state. Run either only on
an explicit request. Use `cmux sidebar-state` to report the resulting status,
progress, and recent operational context.

## Verify and Report

The **acceptance contract** is a successful command followed by an independent
cmux query that shows the requested result:

| Requested result | Verification |
| --- | --- |
| Workspace selected | `cmux current-workspace --json` |
| Split or focused surface changed | `cmux list-panels --json` and `cmux identify --json` |
| Status or progress updated | `cmux sidebar-state` |
| Notification created | `cmux list-notifications --json` |

For terminal input, report the target and exact text or key sent. Do not claim
the terminal command itself succeeded unless its own output can be observed.
Report the cmux command, resolved target, and verification result. If cmux
returns an error, stop the requested operation and include its error text.

## Socket Boundary

Use the CLI unless the user explicitly asks for socket automation. For a socket
request, read `references/cli-reference.md`; use only JSON requests with
`id`, `method`, and `params`. Do not enable `CMUX_SOCKET_MODE=allowAll` or
change `CMUX_SOCKET_PATH` without explicit user approval.
