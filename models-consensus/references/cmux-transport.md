# cmux Interactive Transport

Use this reference only for `transport: cmux`. `peer-sessions` owns the terminal fleet. `models-consensus` adopts that fleet, sends each turn to its recorded surface, and collects the declared JSON artifacts. The **terminal relay** is load-bearing: no terminal transcript is an answer channel.

## Preconditions

1. Set `CMUX_BIN` to `cmux` when it is on `PATH`. On macOS app installs, use `/Applications/cmux.app/Contents/Resources/bin/cmux` when needed. Run `"$CMUX_BIN" ping` and `"$CMUX_BIN" identify --json` from a process permitted to use the cmux socket. If either fails, mark the transport unavailable and use `transport: headless`; do not change `CMUX_SOCKET_MODE`.
2. Create `.ai-workflow/consensus/<session-id>-cmux.json` and one output artifact path per seat before opening a terminal.
3. Invoke `peer-sessions` with the selected seat IDs, their absolute working directory, `--delivery-mode coordinator`, and run directory `.ai-workflow/peer-sessions/<session-id>`. Use its cmux launch path and persist its terminal state as `<absolute peer fleet run directory>/terminals.json`.

The coordinator-delivery brief tells every peer to wait for the council's first terminal prompt. It does not write a peer mailbox reply, because the council's JSON artifact is the only response channel.

## Fleet adoption

After `peer-sessions` reports a terminal state, adopt that exact fleet. Set `SKILL_DIR` to the absolute directory containing this skill's `SKILL.md` in the same shell call:

```bash
SKILL_DIR="<absolute path of the models-consensus directory>"; python3 "$SKILL_DIR/scripts/cmux_council.py" adopt --session-id <session-id> --peer-run <absolute peer fleet run directory> --terminal-state <absolute peer terminal state path> --seat <selected-seat-id> --seat <selected-seat-id> --state-file <absolute consensus cmux state path>
```

`adopt` verifies all of these before a council turn starts:

1. The peer fleet uses `delivery_mode: coordinator`.
2. The recorded terminal state belongs to that fleet.
3. The peer roster exactly matches the selected council seats, and every selected peer appears once with a workspace ID and surface ID.

Do not call `cmux_council.py start` for a council cmux run. It would create a second fleet and break the one-to-one relationship between the peer record and council state.

## Seat launches

Build the peer-fleet manifest from the active roster. Each command must be interactive, read-only, and use the same tool profile and budget. The command list belongs to the run manifest, not to this reference, so model aliases do not become stale skill text.

Never use a print, one-shot, JSON, ACP, or similar non-interactive command. Such commands cannot receive the coordinator's later turns. If a seat cannot start in interactive read-only form, mark the seat unavailable and retain its blocker in the council state.

## Relay protocol

For every turn, write a prompt file containing the task, response schema, exact output artifact path, and this instruction:

```text
Return only the requested JSON. Write it atomically to <output-path>.
You may read the declared sources and write only this output artifact.
Do not send a message to another terminal. Wait for the moderator's next turn.
```

Send that file's content to an adopted surface:

```bash
SKILL_DIR="<absolute path of the models-consensus directory>"; python3 "$SKILL_DIR/scripts/cmux_council.py" send --surface <surface-id> --message-file <prompt-file>
```

Then read the artifact with `collect`. It validates JSON and emits a normal seat envelope with `execution_path: cmux_interactive` and `receipt_status: unverified_terminal`. For poll openings, send the raw brief to each seat. For later turns, write an anonymized digest from collected artifacts and send it only to the selected responding seats.

The **terminal relay** keeps poll openings blind and makes the moderator the only path by which a seat learns another seat's view. State the rule while acting: “The **terminal relay** will forward the anonymized digest, not a terminal transcript.”

## Evidence and cleanup

The output artifact is the **observable behavior**. Validate it with the existing schema flow before it enters the organizer or synthesis step. Capture the peer fleet run directory, workspace ID, surface ID, artifact path, round, and `receipt_status` in the council state.

Interactive CLIs do not all provide an authenticated serving-model receipt. Set `effective_model` to `null` unless a documented, observed receipt proves it. Such a response can inform the conclusion but cannot increase independent diversity confidence; the council cannot report high diversity confidence from unverified terminal seats.

`peer-sessions` owns teardown. Do not close cmux workspaces or clear shared sidebar logs automatically. Closing a user-visible workspace needs an explicit user request.

## Sources

cmux CLI API: <https://cmux.com/pt-BR/docs/api>
