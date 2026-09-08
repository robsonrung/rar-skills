# cmux Interactive Transport

Use this reference only after the approval preview selects `transport: cmux`. Select a native host route first when it can meet the approved model and isolation contract; cmux is an approved interactive route, not an automatic fallback. `peer-sessions` owns the terminal fleet. `models-consensus` adopts that fleet, sends each turn to its recorded surface, and collects the declared JSON artifacts. The **terminal relay** is load-bearing: no terminal transcript is an answer channel.

## Preconditions

1. Set `CMUX_BIN` to `cmux` when it is on `PATH`. On macOS app installs, use `/Applications/cmux.app/Contents/Resources/bin/cmux` when needed. Run `"$CMUX_BIN" ping` and `"$CMUX_BIN" identify --json` from a process permitted to use the cmux socket. If either fails, mark this route unavailable; do not change `CMUX_SOCKET_MODE` or switch transport without a revised user-approved preview.
2. Create `.ai-workflow/consensus/<session-id>.json` with the complete preview described in [operations.md](operations.md). Calculate its scope fingerprint, show the preview, and wait for user approval. Copy the approved fingerprint into `approval.scope_fingerprint`.
3. Create one output artifact path per seat before opening a terminal.
4. Invoke `peer-sessions` with the selected seat IDs, their absolute working directory, `--delivery-mode coordinator`, and run directory `.ai-workflow/peer-sessions/<session-id>`. Use its cmux launch path and persist its terminal state as `<absolute peer fleet run directory>/terminals.json`. Each recorded surface is the persistent context for its own seat through all approved later turns.

The coordinator-delivery brief tells every peer to wait for the council's first terminal prompt. It does not write a peer mailbox reply, because the council's JSON artifact is the only response channel.

## Fleet adoption

After `peer-sessions` reports a terminal state, adopt that exact fleet. The approval state must already contain a matching approved fingerprint. Set `SKILL_DIR` to the absolute directory containing this skill's `SKILL.md` in the same shell call:

```bash
SKILL_DIR="<absolute path of the models-consensus directory>"; python3 "$SKILL_DIR/scripts/cmux_council.py" adopt --approval-state <absolute approved council state path> --peer-run <absolute peer fleet run directory> --terminal-state <absolute peer terminal state path> --state-file <absolute adopted cmux state path>
```

`adopt` verifies all of these before a council turn starts:

1. The peer fleet uses `delivery_mode: coordinator`.
2. The recorded terminal state belongs to that fleet.
3. The peer roster exactly matches the selected council seats, and every selected peer appears once with a workspace ID and surface ID.
4. The approved state has an exact scope fingerprint for the question, seats, models, providers, roles, efforts, tool profile, transport, and budget.

The council script adopts a peer fleet only. It does not create a second fleet. Record each workspace and surface in the role context state. On resume, reuse only that recorded surface; a missing surface is an observable failed route, not a reason to launch another one.

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

Send that file's content to an adopted surface. Reuse the same surface for that
seat's schema retry, gap repair, or later debate round:

```bash
SKILL_DIR="<absolute path of the models-consensus directory>"; python3 "$SKILL_DIR/scripts/cmux_council.py" send --approval-state <absolute approved council state path> --adopted-state <absolute adopted cmux state path> --seat <approved-seat-id> --message-file <prompt-file>
```

`send` resolves the surface only from the adopted state. It rejects a pending plan, a changed scope fingerprint, a changed roster, an unapproved seat, or a missing recorded surface. Then read the artifact with `collect`. It validates JSON and emits a normal seat envelope with `execution_path: cmux_interactive` and `receipt_status: unverified_terminal`. For poll openings, send the raw brief to each seat. For later turns, write an anonymized digest from collected artifacts and send it only to the selected responding seats.

The **terminal relay** keeps poll openings blind and makes the moderator the only path by which a seat learns another seat's view. State the rule while acting: “The **terminal relay** will forward the anonymized digest, not a terminal transcript.”

## Evidence and cleanup

The output artifact is the **observable behavior**. Validate it with the existing schema flow before it enters the organizer or synthesis step. Capture the peer fleet run directory, workspace ID, surface ID, artifact path, round, and `receipt_status` in the council state.

Interactive CLIs do not all provide a native or provider-observed serving-model receipt. Set `effective_model` to `null` and `model_receipt` to `{status: unverified, source: not_observed, observed_model: null}` unless such a receipt exists. A terminal artifact can inform the conclusion but cannot increase independent diversity confidence while unverified. Do not replace an unverified approved terminal route with another model.

`peer-sessions` owns teardown. When the council reaches its final report, run the peer fleet teardown immediately. It closes only the recorded peer surfaces or workspaces and verifies that none remain. A failed teardown is an observable failure: report its remaining targets and keep the coordinator surface open.

## Sources

cmux CLI API: <https://cmux.com/pt-BR/docs/api>
