# Council Execution Rules

Read this only after the user approves the council preview. Resolve the selected
seat through `shared/references/model-roster.md` and follow
`shared/references/host-model-execution.md` before opening an external runner.
Use the selected adapter documentation for its current command shape. Do not
copy a command from an old report.

## One approved call

Initialize the approved plan and reserve the attempt with `council_state.py` as [operations.md](operations.md) defines. Only a new reservation permits dispatch. Copy the returned dispatch artifact into the adapter metadata; send the saved prompt bytes from `intent.input.path`. Every approved call must:

1. Use the approved seat, model, host, execution path, role, effort, tool profile, continuity key, and advisory response cap.
2. Create the declared isolated role context, or resume only that role's recorded context for a later turn.
3. Use structured output and an output artifact when the selected path supports it.
4. Use an analysis role only: `planner`, `codereviewer`, `synthesizer`, `adversarial`, `challenger`, or `researcher`.
5. Stay read-only. Do not pass a write permission, full-auto flag, or `implementer` role.

For a runner call, also use `--disable-fallback`, the previewed `runner_role`, and the exact tool profile. Keep the council stage in dispatch metadata; it is separate from the adapter role. Use structured output that includes startup tool evidence. A successful envelope without verified tool inventory cannot complete a council step. For a native call, record the
host's worker or task context id and configured model and effort. A native
parent session is not a separate worker. The approved preflight chooses native
or runner transport. A native transport that fails after approval does not
authorize a runner transport. Stop and show a revised preview.

## Tool profiles

| Profile | Allowed use |
| --- | --- |
| `no_tools` | Answer only from the approved brief and supplied context |
| `repo_read_only` | Read the approved repository paths |
| `research_read_only` | Use approved read-only research tools and list sources |

All opening seats use the same profile. Any route that cannot enforce it is unavailable for this run.

## Receipt and validation

After dispatch, bind the actual role context using the saved creation event.
Runner envelopes must retain the reserved dispatch metadata, including `call_id`
and `input_revision`. Save the exact response before reconciliation.

For a completed native turn, capture the saved wait result with the shared helper:

```bash
python3 <shared-dir>/scripts/native_completion.py --raw <wait-result.json> --dispatch <reserved-dispatch.json> --context-id <actual-context> --host-id <approved-host> --turn-id <actual-turn> --completed-turn <turn-number> --output <receipt-record.json>
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> reconcile --call <attempt-id> --receipt <receipt-record.json>
```

The capture record retains raw evidence and reports serving proof as unverified.
For runner calls, use the same reconcile command with the saved runner envelope.
Do not assemble response artifacts with hand-written parsing or state updates.


Read the selected path's clean response, not a command transcript. Record:

- `success` and `status`
- requested seat and model
- `requested_model`, `configured_model`, `effective_model`, and `model_receipt`
- `effective_provider`
- host, `effective_runner` when present, execution path, transport, and effort
- continuity key, returned context id or session path, resume status, and input revision
- `auth_ok`, `fallback_reason`, and output path

`fallback_reason` must be empty. A nonempty value is a failed approved seat,
even if it produced text. Set `model_receipt.status: verified` only for a
native or provider event. Native dispatch alone is not a serving-model receipt.
A wrapper-echoed `effective_model` label uses `status: unverified`,
`source: configured_model`, and `observed_model: null`. A verified observed
model that differs from `requested_model` blocks the route, even when
unverified receipts were approved. An absent, mismatched, or unverified receipt
cannot support diversity confidence.

Validate the final message with the schema for its phase. On failure, retry the
same approved route once through the same role context with the key list. The
second failure ends that seat's participation. A lost context is an observable
failure; reconstruct only the same approved role from its persisted checkpoint
when that recovery policy was in the preview.

## Interactive transport

Use [cmux-transport.md](cmux-transport.md) only when `cmux` appears in the approved preview. Its terminal artifact is not a serving-model receipt, so it cannot raise diversity confidence.
