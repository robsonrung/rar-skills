# Council Operations

Use this reference for state, approval, validation, artifacts, and recovery. Mode protocols live in [poll-protocol.md](poll-protocol.md), [personas.md](personas.md), and [stance-rotation-schedule.md](stance-rotation-schedule.md).

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
        "effort_control": "configured"
      }
    ],
    "effort": [
      {
        "call": "opening-seat-a",
        "effort": "high",
        "effort_control": "configured"
      }
    ],
    "transport": "cmux",
    "serving_receipt": "explicitly_allowed_unverified",
    "tool_profile": "no_tools",
    "base_calls": 0,
    "conditional_calls": 0,
    "validation_retry_ceiling": 0,
    "maximum_calls": 0,
    "output_cap_tokens": 2000,
    "scope_fingerprint": "sha256 of the preview scope"
  },
  "approval": {"status": "pending"}
}
```

Use `serving_receipt: "required"` only when every seat has `model_receipt.status: "verified"` from a native or provider event. A configured wrapper label needs `serving_receipt: "explicitly_allowed_unverified"` and `model_receipt: {status: "unverified", source: "configured_model", observed_model: null}`. An echoed label does not prove the serving model. Record `requested_model`, `configured_model`, `effective_model`, and `model_receipt` in each result envelope. Every role call and matching `effort` entry state `effort_control`. Use `"configured"` with a named effort. Use `"runtime"` with `"effort": null` when the transport cannot set effort.

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

Only this exact approval record permits cmux adoption or sending. A changed question, model, receipt, provider, role, effort, tool profile, transport, or budget changes the digest and needs a new preview and approval. Preserve the approved preview in the final report.

On resume, recheck that each planned route still resolves to the previewed model, effort, and transport. If any differs, set `status` to `awaiting_human` and show a revised preview. Never infer approval from a prior incomplete state.

## Questions before the preview

Ask only questions that change the neutral question, mode, or plan. Batch related questions when the host supports it. Do not ask the user to select unavailable seats. If no host question tool exists, ask one concise plain-text question and wait.

## Read-only preflight

Read the roster and task routing, then probe the planned transport. Record `available`, CLI path, version, and blocker per seat. A probe does not prove the serving model. A native or provider-observed receipt may prove it. A wrapper-echoed `effective_model` label does not.

The default tool profile is `no_tools`. `repo_read_only` and `research_read_only` require explicit appearance in the approval preview. Do not provide write, shell, or permission-bypass tools to a council seat.

The default output cap is 2,000 tokens per call. Use 1,200 for judge calls when the question is narrow. State any different cap in the preview.

## Response validation

Validate every response against its mode schema before it enters the next phase. Retry the same approved seat once with the matching key list. A second malformed response remains failed; do not complete it from another seat. Include one possible retry for every planned or conditional call in `maximum_calls` before seeking approval.

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

Write phase state before dispatch. The state records phase, approved plan, seat table, prompts, outputs, failures, and effective-model receipts. This is **the ledger, not the transcript**.

When the workspace is not writable, retain the same fields in memory and return `state_path: null` and `report_path: null`.

## Recovery and failure

Resume only the next uncompleted phase. Do not repeat a completed call. Cancel recorded unfinished runner jobs before resuming their phase.

If an approved seat fails, record its stderr summary and status. If the loss breaks quorum or changes the plan, end the run and present the collected evidence plus a revised-plan option. Never dispatch a replacement model, change effort, or use a different transport without new approval.

## Result contract

The report always includes the neutral question, approved plan, actual receipts, recommendation, dissent, evidence gaps, one next step, and separate answer and diversity confidence. It never starts implementation or hands work to an implementation workflow.
