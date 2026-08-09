# Optional cmux fleet

Use this reference only when the user wants visible interactive terminal peers and `cmux ping` succeeds. The terminal is a launch surface. The mailbox remains the **ledger, not the transcript**.

## Preconditions

1. Create the fleet record with `scripts/init_fleet.py`. When a composing skill owns the response artifacts, pass `--delivery-mode coordinator`; its peers wait for the first terminal prompt and do not write mailbox replies.
2. Use one interactive command per peer. Do not use a one-shot or print-only command because it cannot receive the brief.
3. Build a manifest outside the skill directory. It must use absolute paths and an argv array for every command.

Example manifest:

```json
{
  "run_dir": "/absolute/project/.ai-workflow/peer-sessions/example",
  "peers": [
    {
      "id": "research",
      "cwd": "/absolute/project",
      "command": ["<interactive-cli>", "<interactive-arguments>"]
    },
    {
      "id": "review",
      "cwd": "/absolute/project",
      "command": ["<interactive-cli>", "<interactive-arguments>"]
    }
  ]
}
```

Validate the plan without changing the terminal layout:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/cmux_fleet.py" start --manifest /absolute/path/to/fleet.json --dry-run
```

Start it only after confirming the plan and the user's terminal-placement intent:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/cmux_fleet.py" start --manifest /absolute/path/to/fleet.json --state-file /absolute/path/to/fleet-terminals.json
```

## Choose the placement

`--surface-mode` decides where the peers appear, and the two shapes are not interchangeable:

| Mode | Effect | Use when |
| --- | --- | --- |
| `split` (default) | One pane per peer, tiled beside the caller in the current workspace. | The user wants the whole fleet visible on one screen at once. |
| `tab` | One tab per peer in one existing workspace. Only one is on screen at a time. | Peers are long-running and the user will switch between them. |
| `workspace` | One new workspace per peer. | The user explicitly wants peers isolated in separate workspaces. |

Split mode anchors the first split on the caller's own surface (`--anchor-surface`, defaulting to `CMUX_SURFACE_ID`) and every later split on the pane it just created, so panes tile instead of repeatedly halving the coordinator's pane. `--split-direction auto` alternates right/down toward a grid; pass a fixed direction for a single row or column.

All in-workspace modes target `--workspace`, defaulting to the caller's own `CMUX_WORKSPACE_ID`, and create surfaces with `--focus false` so the fleet never steals focus mid-launch. Every `send` carries an explicit `--surface`. **Address the surface, never the focus**: an unaddressed `send` lands in whatever pane happens to be selected, which can be the coordinator's own session.

Screen space is the real limit on split mode, not the fleet cap. Four panes plus the coordinator is comfortable; beyond roughly six, panes get too short to read and `tab` is the better placement. Say which one you chose and why.

The state file contains only workspace and surface IDs created by this run. It is the teardown allowlist. Do not close a workspace or tab not present in that file. In tab mode the enclosing workspace pre-existed the run and is never yours to close — close only the recorded surfaces.

## Relay rule

After launch, send each peer only its generated brief path. The **terminal relay** must never copy one peer's terminal transcript into another peer's prompt. With the default mailbox delivery, read replies from `replies/<peer>.json`; with coordinator delivery, the composing skill reads its declared artifact instead. Then pass a compact, authorized decision or digest through a new brief if another peer needs it.

If `cmux` is absent, inaccessible, or returns malformed JSON, report the terminal transport unavailable and use native delegation. Do not change system socket settings, parse undocumented socket protocols, or turn a failed terminal layout into a reason to keep polling.
