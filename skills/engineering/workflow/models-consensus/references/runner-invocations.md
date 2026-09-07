# Runner Invocation Rules

Read this only after the user approves the council preview. Resolve the selected seat through `shared/references/model-roster.md` and use that seat's runner documentation for its current command shape. Do not copy a command from an old report.

## One approved call

Every headless call must:

1. Use the approved seat, model, transport, role, effort, tool profile, and output cap.
2. Use a fresh context and the phase schema where the runner supports one.
3. Use `--disable-fallback`, structured output, and an output file when artifacts are writable.
4. Use an analysis role only: `planner`, `codereviewer`, `synthesizer`, `adversarial`, `challenger`, or `researcher`.
5. Stay read-only. Do not pass a write permission, full-auto flag, or `implementer` role.

The approved preflight chooses native or runner transport. A native transport that fails after approval does not authorize a runner transport. Stop and show a revised preview.

## Tool profiles

| Profile | Allowed use |
| --- | --- |
| `no_tools` | Answer only from the approved brief and supplied context |
| `repo_read_only` | Read the approved repository paths |
| `research_read_only` | Use approved read-only research tools and list sources |

All opening seats use the same profile. Any route that cannot enforce it is unavailable for this run.

## Receipt and validation

Read the runner envelope's `agent_message`, not a command transcript. Record:

- `success` and `status`
- requested seat and model
- `requested_model`, `configured_model`, `effective_model`, and `model_receipt`
- `effective_provider`
- `effective_runner`, transport, and effort
- `auth_ok`, `fallback_reason`, and output path

`fallback_reason` must be empty. A nonempty value is a failed approved seat, even if it produced text. Set `model_receipt.status: verified` only for a native or provider event. A wrapper-echoed `effective_model` label uses `status: unverified`, `source: configured_model`, and `observed_model: null`. A verified observed model that differs from `requested_model` blocks the route, even when unverified receipts were approved. An absent, mismatched, or unverified receipt cannot support diversity confidence.

Validate the final message with the schema for its phase. On failure, retry that same approved route once with the key list. The second failure ends that seat's participation.

## Interactive transport

Use [cmux-transport.md](cmux-transport.md) only when `cmux` appears in the approved preview. Its terminal artifact is not a serving-model receipt, so it cannot raise diversity confidence.
