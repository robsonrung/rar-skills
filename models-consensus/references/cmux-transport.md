# cmux Interactive Transport

Use this reference only for `transport: cmux`. This transport opens one cmux workspace per seat and keeps the agent process interactive. The **terminal relay** is the load-bearing rule: the moderator sends every turn to a recorded surface, reads the seat's JSON artifact, then relays only the permitted digest to another surface. Do not treat terminal screen text as an answer channel.

## Preconditions

1. Set `CMUX_BIN` to `cmux` when it is on `PATH`. On macOS app installs, use `/Applications/cmux.app/Contents/Resources/bin/cmux` when needed. Run `"$CMUX_BIN" ping` and `"$CMUX_BIN" identify --json` from a process permitted to use the cmux socket. If either fails, mark the transport unavailable and use `transport: headless`; do not change `CMUX_SOCKET_MODE`.
2. Create `.ai-workflow/consensus/<session-id>-cmux.json` and an output path for every seat before starting a terminal.
3. Use `models-consensus/scripts/cmux_council.py start` with a JSON manifest. The script creates a workspace, records the focused workspace and surface, starts an interactive CLI, and refuses known headless forms.

```json
{
  "session_id": "<session-id>",
  "workspace": "<absolute project path>",
  "seats": [
    {"id": "opus", "command": ["claude", "--permission-mode", "plan", "--model", "opus"]},
    {"id": "codex", "command": ["codex", "--sandbox", "read-only", "--no-alt-screen"]}
  ]
}
```

Read the active roster before building commands. Do not add a model ID to this reference. The manifest is per run and holds the current aliases or model IDs.

## Seat Launches

| Seat CLI | Interactive command shape | Use of its communication feature |
| --- | --- | --- |
| Claude Code | `claude --permission-mode plan --model <alias>` | Remote Control is a human remote-control interface. Enable it only when the user requests remote access; it is not the council relay. |
| Codex | `codex --sandbox read-only --no-alt-screen` | App Server supports stdio, Unix, and WebSocket transports. Keep it separate from cmux unless a local socket bridge is explicitly requested and authenticated. |
| Grok | `grok --permission-mode plan --minimal --no-alt-screen --leader-socket <per-run-path>` | Use a unique leader socket for the run. Its documented management interface lists, inspects, and stops leaders; it is not a peer-message API. |
| Cline | `cline --tui --plan --auto-approve false --model <roster-model>` | ACP is a stdio editor protocol and Hub/Connect are external control surfaces. Neither replaces the artifact relay. |
| Antigravity | `agy --prompt-interactive --mode plan --sandbox --model <roster-model>` | The documented CLI exposes interactive and print modes but no socket relay. Use the cmux surface and artifacts. |

Never use `claude --print`, `codex exec`, `grok --single`, Cline JSON/ACP/Zen, or Antigravity print mode in this transport. They belong to `transport: headless` or to their own integration, not an interactive terminal.

Start with the explicit binary path when the app bundle is not on `PATH`:

```bash
SKILL_DIR="<absolute path of the models-consensus directory containing SKILL.md>"; CMUX_BIN="<cmux executable path>"; python3 "$SKILL_DIR/scripts/cmux_council.py" --cmux-bin "$CMUX_BIN" start --manifest <manifest-path> --state-file <state-path>
```

## Relay Protocol

For every turn, write a prompt file containing the task, the response schema, the exact output artifact path, and this instruction:

```text
Return only the requested JSON. Write it atomically to <output-path>.
You may read the declared sources and write only this output artifact.
Do not send a message to another terminal. Wait for the moderator's next turn.
```

Send that file's content with:

```bash
SKILL_DIR="<absolute path of the models-consensus directory containing SKILL.md>"; python3 "$SKILL_DIR/scripts/cmux_council.py" send --surface <surface-id> --message-file <prompt-file>
```

Then read the artifact with `collect`. It validates JSON and emits a normal seat envelope with `execution_path: cmux_interactive` and `receipt_status: unverified_terminal`. For poll openings, send the raw brief to each seat. For later turns, write an anonymized digest from collected artifacts and send it only to the selected responding seats.

The **terminal relay** keeps poll openings blind and makes the moderator the only path by which a seat learns another seat's view. State the rule while acting: “The **terminal relay** will forward the anonymized digest, not a terminal transcript.”

## Evidence and Cleanup

The output artifact is the **observable behavior**. Validate it with the existing schema flow before it enters the organizer or synthesis step. Capture the surface ID, artifact path, round, and `receipt_status` in the council state.

Interactive CLIs do not all provide an authenticated serving-model receipt. Set `effective_model` to `null` unless a documented, observed receipt proves it. Such a response can inform the conclusion but cannot increase independent diversity confidence; the council cannot report high diversity confidence from unverified terminal seats.

Record every workspace ID in the state file. Do not close cmux workspaces or clear shared sidebar logs automatically. Closing a workspace needs an explicit user request.

## Sources

cmux CLI API: <https://cmux.com/pt-BR/docs/api>

Claude Code Remote Control: <https://code.claude.com/docs/en/remote-control>

Codex App Server: <https://developers.openai.com/codex/app-server/>

Cline CLI reference: <https://docs.cline.bot/cli/cli-reference>

Grok Build: <https://docs.x.ai/build/overview>

Antigravity CLI: <https://www.antigravity.google/docs/home>
