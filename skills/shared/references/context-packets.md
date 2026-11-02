# Bounded context packets

Use **selection over compression**: send the task's acceptance contract, settled decisions,
open questions, allowed paths, relevant source locators, and remaining limits. Keep complete
reports and logs in files. Do not summarize an entire parent conversation into a worker prompt.

Prepare a worker packet only for actual dispatch. Methods and routine read-only
lenses applied in the assigned role use its current inputs and record findings
in the caller's existing artifact. They do not create another role or packet.

## Bind the derived notes

Prepare a source list with absolute paths, authority (`decision`, `evidence`, or
`superseded`), and a section or line locator. At least one current decision source
is required. A superseded document is history, not an instruction.

```json
[
  {"path": "/project/prd.md", "authority": "decision", "locator": "Access and acceptance"},
  {"path": "/project/research.md", "authority": "evidence", "locator": "Current authorization path"}
]
```

```bash
python3 <shared-dir>/scripts/context_packet.py prepare \
  --brief <brief.md> --sources <sources.json> --output <brief.md.packet.json>
python3 <shared-dir>/scripts/context_packet.py verify --packet <brief.md.packet.json>
```

The derived-note limit remains 24,000 UTF-8 bytes. `prepare --max-bytes` controls only
those notes.
The packet hashes the brief and source revisions. Only an exact task status line can change
without changing a decision hash. If decisions change, revise the affected brief and create a
new packet path. Never replace old evidence to conceal drift.

Callers verify `<brief-file>.packet.json` before their own worker dispatch. Reuse source
locators and revisions from the decision record; recheck changed or disputed facts. Resolve conflicting notes against current
user decisions before sending the packet; a checksum cannot resolve their meaning.

## Check the complete rendered input

Keep each complete worker input within **24,000 UTF-8 bytes** by default: the task contract,
derived notes, source locators, execution boundaries, and evidence references. Never truncate
required instructions or acceptance rules. When input is oversized, shorten derived notes, link
supporting evidence, or split genuinely independent work; do not remove acceptance cases. A route
can raise the limit with `context_budget: {"max_bytes": 32000, "reason": "..."}`.

For a direct caller, check its final rendered file without writing or dispatching:

```bash
python3 <shared-dir>/scripts/context_packet.py measure --input <complete-worker-input.md>
```

The command returns 0 within the limit and 2 when blocked. A direct caller can supply
`--max-bytes` and, above the default, `--reason`; these flags do not grant authority.
The caller must use its approved allowance.

This measures worker input text, not the full provider context. Host instructions, tool schemas,
retained role history, and later file reads are unmeasured. Adapter text has its own
`adapter_input_measurement` in the result envelope. `token_count` stays null. Use actual execution receipts for input and cached token totals per accepted task.
Do not convert bytes to a claimed token saving or count a high cache hit rate as free input.

## Isolate tasks and retain repairs

Start each independent task and role with no parent conversation history. Send the bound task
packet as its initial input; keep source files available on demand. For native dispatch, honor
`parent_history: none` with the host's supported empty-history option. A host with `fork_turns`
uses `fork_turns: none` for creation. Do not fork the coordinator's full conversation.

Reuse the recorded context for that task's repairs and rechecks. Send changed facts
and relevant evidence in the derived followup; a live context already holds the
acceptance text. Keep the context IDs in **the ledger, not the transcript**:
"The ledger proves this continuation; the role receives only the repair context."

A fresh or reconstructed context receives the full contract. Reviewer input still
includes the current snapshot, all required coverage, prior findings, and capture locators.

Missing proof restores the full acceptance contract under the original route and
remaining counters. Proof loss starts a fresh full reconstruction. An altered receipt, session, route,
policy, contract, or prior input blocks for reconciliation. Confirmed context
loss uses an explicit recovery reason. Reconcile uncertain outcomes before resend.
Native and runner contexts cannot be exchanged. Unsupported shared-latest sessions
never qualify as exact continuation. A new task starts a new context. Context
replacement cannot reset call or retry counters. These rules do not authorize
additional workers or user-owned tasks.
