# cmux CLI Reference

Source: <https://cmux.com/pt-BR/docs/api>

## Context and Scope

| Need | Command or flag |
| --- | --- |
| Check service availability | `cmux ping` |
| Inspect focused context | `cmux identify --json` |
| Inspect socket methods and mode | `cmux capabilities --json` |
| Emit structured output | `--json` |
| Select ID form in JSON | `--id-format refs|uuids|both` |
| Target a window, workspace, or surface | `--window <id>`, `--workspace <id>`, `--surface <id>` |
| Use a custom socket | `--socket <path>` |

The cmux terminal sets `CMUX_WORKSPACE_ID` and `CMUX_SURFACE_ID`. The CLI uses
`CMUX_SOCKET_PATH` when it is set.

## Workspaces and Panels

| Intent | Command |
| --- | --- |
| List workspaces | `cmux list-workspaces --json` |
| Create a workspace | `cmux new-workspace` |
| Select a workspace | `cmux select-workspace --workspace <workspace-id>` |
| Inspect current workspace | `cmux current-workspace --json` |
| Close a workspace | `cmux close-workspace --workspace <workspace-id>` |
| Create a split | `cmux new-split <left|right|up|down>` |
| List surfaces in current workspace | `cmux list-panels --json` |
| List surfaces in focused pane | `cmux list-pane-surfaces --json` |
| Focus a surface | `cmux focus-panel --panel <surface-id>` |

## Terminal Input and Notifications

| Intent | Command |
| --- | --- |
| Send text to focused surface | `cmux send "text"` |
| Send text to a surface | `cmux send --surface <surface-id> "text"` |
| Send a key to focused surface | `cmux send-key enter` |
| Send a key to a surface | `cmux send-key --surface <surface-id> enter` |
| Create a notification | `cmux notify --title "Title" --body "Body"` |
| List notifications | `cmux list-notifications --json` |
| Clear all notifications | `cmux clear-notifications` |

Supported keys are `enter`, `tab`, `escape`, `backspace`, `delete`, `up`,
`down`, `left`, and `right`.

## Sidebar Metadata

| Intent | Command |
| --- | --- |
| Set a keyed status | `cmux set-status <key> "value" --icon <icon> --color <hex> --priority <number>` |
| Remove a keyed status | `cmux clear-status <key>` |
| List statuses | `cmux list-status` |
| Set progress from 0.0 to 1.0 | `cmux set-progress <value> --label "text"` |
| Clear progress | `cmux clear-progress` |
| Add a log entry | `cmux log --level <info|progress|success|warning|error> --source <name> "text"` |
| List log entries | `cmux list-log --limit <number>` |
| Clear all log entries | `cmux clear-log` |
| Export sidebar metadata | `cmux sidebar-state` |

## Socket Requests

The default release socket is `/tmp/cmux.sock`. Socket access is normally
limited to processes launched inside cmux. A socket request is newline-delimited
JSON such as:

```json
{"id":"workspace-list","method":"workspace.list","params":{}}
```

Legacy payloads with `command` are not supported. `CMUX_SOCKET_MODE=allowAll`
permits any local process to connect, so retain the default scope unless the
user explicitly authorizes the wider access.
