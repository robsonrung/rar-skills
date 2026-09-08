# Council Operations

Use this reference for state, approval, validation, artifacts, and recovery. Apply `shared/references/run-state-contract.md` and `shared/references/host-model-execution.md` as well. Mode protocols live in [poll-protocol.md](poll-protocol.md), [personas.md](personas.md), and [stance-rotation-schedule.md](stance-rotation-schedule.md).

## Approval record

Create `.ai-workflow/consensus/{session_id}.json` when the workspace is writable. Before the first model call, store:

```json
{
  "session_id": "council-42",
  "status": "awaiting_human",
  "question": "...",
  "mode": "poll",
  "preview": {
    "seats": [
      {
        "id": "seat-a",
        "requested_model": "requested-model-id",
        "provider": "provider",
        "model_receipt": {
          "status": "unverified",
          "source": "configured_model",
          "observed_model": null
        }
      }
    ],
    "roles": [
      {
        "call": "opening-seat-a",
        "role": "opening",
        "seat": "seat-a",
        "requested_model": "requested-model-id",
        "effort": "high",
        "effort_control": "configured",
        "continuity_key": "opening-seat-a"
      }
    ],
    "effort": [
      {
        "call": "opening-seat-a",
        "effort": "high",
        "effort_control": "configured"
      }
    ],
    "execution": [
      {
        "call": "opening-seat-a",
        "host": "active-host",
        "execution_path": "native_subagent",
        "transport": "native",
        "continuity_key": "opening-seat-a",
        "session_policy": "persistent_same_role",
        "resume_policy": "recorded_context_only"
      }
    ],
    "transport": "per_call",
    "serving_receipt": "explicitly_allowed_unverified",
    "tool_profile": "no_tools",
    "base_calls": 0,
    "conditional_calls": 0,
    "validation_retry_ceiling": 0,
    "maximum_calls": 0,
    "output_cap_tokens": 2000,
    "scope_fingerprint": "sha256 of the preview scope"
  },
  "approval": {"status": "pending"},
  "runtime": {
    "sessions": [
      {
        "continuity_key": "opening-seat-a",
        "context_id": null,
        "status": "not_started",
        "last_input_revision": null,
        "pending_call": null
      }
    ]
  }
}
```

Use `serving_receipt: "required"` only when every seat has `model_receipt.status: "verified"` from a native or provider event. A configured wrapper label needs `serving_receipt: "explicitly_allowed_unverified"` and `model_receipt: {status: "unverified", source: "configured_model", observed_model: null}`. An echoed label does not prove the serving model. Record `requested_model`, `configured_model`, `effective_model`, and `model_receipt` in each result envelope. Every role call and matching `effort` entry state `effort_control`; every role call also has one matching execution entry and continuity key. Use `"configured"` with a named effort. Use `"runtime"` with `"effort": null` when the transport cannot set effort.

The preview records the chosen host, execution path, and session policy, but never a returned context id. The mutable `runtime.sessions` record holds that id after a call. A generic plan uses `transport: "per_call"`; a cmux plan uses `transport: "cmux"` and `cmux_interactive` execution entries. A returned context id, runner session id, or terminal surface does not change the approved preview.

For a cmux plan, calculate `scope_fingerprint` before showing the preview:

```bash
python3 <models-consensus-dir>/scripts/cmux_council.py fingerprint --approval-state <approval-state>
```

Copy the returned digest to `preview.scope_fingerprint`. Show the preview, then wait for the user's clear approval. After that approval, record:

```json
"approval": {
  "status": "approved",
  "scope_fingerprint": "the same digest"
}
```

Only this exact approval record permits cmux adoption or sending. A changed question, model, receipt, provider, host, execution path, role, continuity key, effort, tool profile, transport, or budget changes the digest and needs a new preview and approval. Preserve the approved preview in the final report.

On resume, recheck that each planned route still resolves to the previewed model, effort, host, execution path, and transport. Reconcile each pending call before sending another prompt. If any approved route differs, set `status` to `awaiting_human` and show a revised preview. Never infer approval from a prior incomplete state.

## Questions before the preview

Ask only questions that change the neutral question, mode, or plan. Batch related questions when the host supports it. Do not ask the user to select unavailable seats. If no host question tool exists, ask one concise plain-text question and wait.

## Read-only preflight

Read the roster, task routing, and host execution contract. Check an exact native route first. Probe an external runner only when the native route cannot meet the approved model, effort, isolation, tool, or receipt policy. Record host or runner, execution path, availability, version when applicable, session-resume support, and blocker per seat. A capability check does not prove the serving model. A native or provider-observed receipt may prove it. A wrapper-echoed `effective_model` label does not.

The default tool profile is `no_tools`. `repo_read_only` and `research_read_only` require explicit appearance in the approval preview. Do not provide write, shell, or permission-bypass tools to a council seat.

The default output cap is 2,000 tokens per call. Use 1,200 for judge calls when the question is narrow. State any different cap in the preview.

## Response validation

Validate every response against its mode schema before it enters the next phase. Retry the same approved seat once with the matching key list and its recorded role context. A second malformed response remains failed; do not complete it from another seat. Include one possible retry for every planned or conditional call in `maximum_calls` before seeking approval. A session reattachment adds no model call; a retry or later substantive turn does.

| Mode | Stage | Schema |
| --- | --- | --- |
| `poll` | opening | `schemas/opening-answer.schema.json` |
| `poll` | organizer | `schemas/organizer-analysis.schema.json` |
| `poll` | gap repair | `schemas/disagreement-round.schema.json` |
| `poll` | judge | `schemas/judge.schema.json` |
| `poll` | synthesis | `schemas/synthesis.schema.json` |
| `debate` | opening | `schemas/round1-response.schema.json` |
| `debate` | later round | `schemas/later-round-response.schema.json` |

## Artifacts and state

When the workspace is writable, use:

- state: `.ai-workflow/consensus/{session_id}.json`
- report: `.ai-workflow/consensus/{session_id}.md`
- response: `.ai-workflow/consensus/{session_id}-{phase}-{seat}.json`

Write the attempt, pending call, and phase state before dispatch. The state records phase, approved plan, seat table, execution entries, role contexts, prompts, outputs, failures, and effective-model receipts. This is **the ledger, not the transcript**. A role context records its host, execution path, context id or session path, configured model and effort, tool policy, receipt reference, last input revision, completed turn, and pending call id.

When the workspace is not writable, retain the same fields in memory and return `state_path: null` and `report_path: null`.

## Recovery and failure

Resume only the next uncompleted phase. Do not repeat a completed call. Reconcile a recorded pending native call, runner job, or terminal artifact before resending it. Resume only through the matching role's recorded context id or session path; never use a global latest-session selector.

If a recorded context is unavailable, record the continuation break and the actual failure evidence. Recreate the same approved role from its checkpoint only when the preview declared that recovery policy; otherwise fail that route. If an approved seat fails, record its stderr or host-error summary and status. If the loss breaks quorum or changes the plan, end the run and present the collected evidence plus a revised-plan option. Never dispatch a replacement model, change effort, or use a different transport without new approval.

## Result contract

The report always includes the neutral question, approved plan, actual receipts, recommendation, dissent, evidence gaps, one next step, and separate answer and diversity confidence. It never starts implementation or hands work to an implementation workflow.
