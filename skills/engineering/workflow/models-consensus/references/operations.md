# Council Operations

Use this reference for approval, state, artifacts, validation, and recovery. Apply `shared/references/run-state-contract.md` and `shared/references/host-model-execution.md`. Mode protocols remain in [poll-protocol.md](poll-protocol.md), [personas.md](personas.md), and [stance-rotation-schedule.md](stance-rotation-schedule.md).

## Approval and immutable state

For native and runner routes, use `scripts/council_state.py`. It records calls and validates results; it never launches models. The caller obtains approval and dispatches the exact recorded request. Keep the approval document separate from the generated runtime state.

The approval document contains `session_id`, `question`, `mode`, `preview`, and `approval`. The preview contains:

| Field | Contract |
| --- | --- |
| `seats` | Seat `id`, `provider`, `requested_model`, and `model_receipt` with status, source, and observed model |
| `roles` | Every planned step: `call`, `role`, `seat`, `requested_model`, `effort`, `effort_control`, `continuity_key`, `depends_on`, and optional `conditional` boolean |
| `effort` | Exactly one matching `call`, `effort`, and `effort_control` entry per step |
| `execution` | Exactly one matching `call`, `host`, `execution_path`, `transport`, `continuity_key`, `session_policy`, and `resume_policy` entry per step |
| `transport` | `per_call`; each execution entry selects `native` or `runner` |
| `serving_receipt` | `required` or `explicitly_allowed_unverified` |
| `tool_profile` | `no_tools`, `repo_read_only`, or `research_read_only` |
| Call budgets | `base_calls`, `conditional_calls`, `validation_retry_ceiling`, `maximum_calls` |
| Response guidance | `output_cap_tokens` |
| Optional measured budgets | `reported_limits`, keyed by shared execution metric names; `elapsed_seconds` for total elapsed time |
| `scope_fingerprint` | Digest returned by the CLI before approval |

Use `effort_control: configured` with a named effort, or `effort_control: runtime` with `effort: null`. Runner execution entries also name exact `runner` and read-only `runner_role` values. These differ from council stage identity: for example, council role `opening` can use runner role `researcher`. Non-`no_tools` runner profiles list exact `allowed_tools`; `allowed_mcp_servers` defaults to empty. An adapter effort alias can be pinned as `effort_value`; otherwise the actual forwarded effort must equal the approved effort. Each execution entry uses `session_policy: persistent_same_role` and `resume_policy: recorded_context_only`. Role names are the stage keys in the table below. The `call` identifies a planned step; each dispatch attempt gets a separate call ID at reservation.

Each independent role has its own continuity key. Only an opening seat can reuse its key for that seat's `gap_repair` or `later_round` steps. The repeated key must retain the same model, effort, host, execution path, transport, and tools. List the opening before its continuation steps. Organizer, judges, synthesizer, advisors, reviewers, and chairman use separate keys.

Opening and advisor steps have `depends_on: []`. Other stages declare their prerequisites by planned step ID. Encode the selected mode's order in these dependencies, including all blind openings before organizer analysis and independent judges before synthesis. Unknown dependencies and cycles fail initialization. The caller still supplies the correct neutral briefs, anonymized peer digests, and mode-specific quorum decision; the CLI cannot establish those from free text.

The number of roles equals `base_calls + conditional_calls`. Exactly `conditional_calls` roles have `conditional: true`. `maximum_calls` equals the role count plus `validation_retry_ceiling`. Include one possible retry for every planned or conditional call when choosing the normal `maximum_calls`; a smaller explicit retry ceiling permits fewer repairs. Each step can have at most one retry, and every retry consumes the original global and role budgets.

```bash
python3 <models-consensus-dir>/scripts/council_state.py fingerprint --approval-state <preview.json>
```

Copy the digest into `preview.scope_fingerprint`. Show only the selected council seats and planned roles, then wait for clear approval. The caller records:

```json
{"approval": {"status": "approved", "scope_fingerprint": "the exact preview digest"}}
```

The CLI never infers or writes approval. A changed question, mode, model, provider, receipt requirement, effort, role, dependency, tool profile, execution path, transport, or budget requires a new preview. Initialize only after approval:

```bash
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> init --approval-state <preview.json>
```

Initialization stores an immutable plan, stage schemas, and digest beside the runtime state. Repeating initialization verifies the approval and preserves existing attempts, contexts, failures, artifacts, and budgets. Resume uses these snapshots; it does not resolve new defaults or substitute current schemas after a CLI upgrade. An unknown state version blocks changes and preserves the file.

For a cmux plan, continue to use [cmux-transport.md](cmux-transport.md) and its `cmux_council.py fingerprint --approval-state <preview.json>` command. The generic state CLI does not adopt or launch terminal seats.

## Reserve before dispatch

```bash
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> reserve --step <planned-step> --call <unique-attempt-id> --brief <prompt.txt>
```

Dispatch only when the successful command returns `reservation: new` and `dispatch_allowed: true`. The state lock reserves the attempt before returning. Concurrent repeats have one winner. A replay returns `dispatch_allowed: false`, including a replay of a pending call. A lost command response requires reconciliation; it is not permission to send again.

The returned dispatch artifact binds call ID, input digest, approved scope digest, model, effort, host, transport, role, tools, and current context. Use the saved prompt artifact under the call's `intent.input` for dispatch. The CLI retains exact prompt bytes, so a later source edit does not erase the original input.

After context creation, bind the actual context through a saved adapter event:

```bash
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> bind --call <attempt-id> --event <context-event.json>
```

The event contains `setup_reference: council:<attempt-id>`, `call_id`, `input_revision`, `context_id`, `host`, `transport`, and `evidence: {path, sha256}` for the raw creation result. A queued setup token is not a context ID. Runner events may also contain exact `job_id` and `working_dir` values. A context cannot belong to two roles, and a bound job cannot change.

## Budgets

`output_cap_tokens` is response guidance, default 2,000 tokens. Narrow judge calls may use 1,200 through an approved role-level `output_cap_tokens` override. The generic CLI always reports this cap as advisory. It makes no hard token cap claim for a transport. Native output length depends on the host.

Call ceilings count reservations, including failures and malformed answers. `reported_limits` can bound measured `input_tokens`, `output_tokens`, `reported_cost_usd`, `duration_ms`, or other shared metric fields before the next dispatch. These are dispatch stop conditions, not provider spending guarantees. One in-flight call can exceed a measured limit.

Missing usage remains unknown. When a reported limit is selected, any pending or completed call with unknown usage for that metric blocks another reservation. This serializes measured-budget runs until each result supplies the required usage. Without reported limits, independent ready seats can run concurrently within call ceilings. `elapsed_seconds` blocks new calls after the wall-clock limit; it does not cancel running work.

## Receipt and response validation

```bash
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> reconcile --call <attempt-id> --receipt <saved-receipt.json>
```

Reconcile the actual runner envelope or the record produced by `shared/scripts/native_completion.py`. The CLI checks exact call, prompt revision, model, effort, host, transport, role, tools, and context. Native success also reuses `native_completion.capture` to verify the final message against intact raw host evidence and the reserved dispatch artifact. The supported wait response does not attest the serving model; it stays unverified. A consumed native turn ID cannot satisfy a new call, and its completed-turn counter must advance.

The raw receipt is saved byte for byte with its digest. A separate normalized artifact contains the parsed response, stage schema digest, response status, error, model receipt, and raw receipt reference. Completed receipt replay verifies these artifacts and performs no new model call. A failed receipt retains its context and measured usage. For runners, actual `session_id` or top-level `context_id` supplies continuity evidence; metadata context is dispatch intent only. Successful runner receipts must report the expected actual configured model, effort, runner, runner role, and tool profile. Tool startup evidence must be verified and its profile, observed tools, and observed servers must match the approved inventory. Text-only or unsupported adapters without this evidence cannot complete a council step. Fallback, tool policy violation, missing required serving proof, or an observed model mismatch blocks acceptance.

Accept either a raw JSON object or exactly one JSON fence with optional prose around it. Extra JSON values, multiple fences, duplicate keys, invalid constants, malformed JSON, and schema violations fail validation. Ambiguous structural or scalar JSON outside a fence is rejected. A configured label cannot establish model diversity.

The CLI reuses `shared/scripts/output_contract.py`. It checks every branch of the schema, including absent properties and empty arrays, before validating the whole response. All bundled schemas use its supported Draft 7 vocabulary. Unsupported keywords, malformed schema rules, and other dialects fail closed; this is not a general Draft 7 implementation. No extra package is required.

| Mode | Stage key | Schema |
| --- | --- | --- |
| `poll` | `opening` | `opening-answer.schema.json` |
| `poll` | `organizer` | `organizer-analysis.schema.json` |
| `poll` | `gap_repair` | `disagreement-round.schema.json` |
| `poll` | `judge` | `judge.schema.json` |
| `poll`, `debate` | `synthesis` | `synthesis.schema.json` |
| `debate` | `opening` | `round1-response.schema.json` |
| `debate` | `later_round` | `later-round-response.schema.json` |
| `personas` | `advisor` | `opening-answer.schema.json` |
| `personas` | `reviewer` | `persona-review.schema.json` |
| `personas` | `chairman` | `persona-chairman.schema.json` |

A malformed response or failed execution can use one new attempt through the same recorded context if the original budget allows it. A completed valid step cannot run again. Missing context blocks retry except for a proven failure before the first model invocation. This exception requires every prior attempt for that role to have an intact failed receipt with `terminal_status: preflight_blocked`, `print_invocation_started: false`, blocked preflight evidence with `provider_calls: 0`, matching actual runner, model, effort, role, and tools, and no session, response, startup, serving, or nonzero model-usage evidence. The `provider_calls` preflight field alone proves nothing about a later invocation.

After correcting the CLI prerequisite, this proven case may spend the original retry allowance to create its first context. Keep the same approved plan and all failed receipts, reservation counts, and measured budgets. Do not refund an attempt or raise a ceiling. A required serving receipt is not expected for a proven prelaunch failure; that failure supplies no accepted vote. The successful retry must still meet the original serving-proof requirement. Existing, lost, and uncertain contexts retain the strict same-context rule; no global latest-session lookup or replacement context is allowed.

## Progress and recovery

```bash
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> status
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> observe
python3 <models-consensus-dir>/scripts/council_state.py --state <run.json> skip --step <conditional-step> --reason <reason>
```

`observe` uses `runner_jobs.observe_many` for explicitly bound pending jobs. It reads status without dispatch or automatic retry. A dead or missing job is unresolved until exact failure evidence is reconciled. Native pending calls use the host's recorded context and turn, then the shared completion capture.

A planned conditional step can be skipped before any attempt, with a stored reason. An attempted or required step cannot be skipped. Dependent steps require valid or explicitly skipped prerequisites. State becomes completed when all approved steps are valid or skipped. `status` reports the stored attempts, step outcomes, measured usage, unknown counts, and advisory response cap.

Keep state at `.ai-workflow/consensus/{session_id}.json` and the report at `.ai-workflow/consensus/{session_id}.md`. The CLI stores immutable artifacts in `{state-path}.artifacts/`. If this location is not writable, report the blocker; durable reservation is required before dispatch.

The final report names the approved plan, actual receipts, failures, recommendation, dissent, evidence gaps, one next step, and separate answer and diversity confidence. A loss of quorum ends deliberation with the available evidence. The council never starts implementation.
