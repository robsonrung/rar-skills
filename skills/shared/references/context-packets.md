# Bounded context packets

Use **selection over compression**: send the task's acceptance contract, settled decisions,
open questions, allowed paths, relevant source locators, and remaining limits. Keep complete
reports and logs in files. Do not summarize an entire parent conversation into a worker prompt.

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
those notes. It cannot increase the launcher's complete input limit.
The packet hashes the brief and source revisions. Only an exact task status line can change
without changing a decision hash. If decisions change, revise the affected brief and create a
new packet path. Never replace old evidence to conceal drift.

The launcher verifies `<brief-file>.packet.json` before dispatch. New workflow runs use this
binding. Legacy briefs remain readable and receive the complete input check too. Direct interview,
design, and handoff callers run `verify` themselves. Resolve conflicting notes against current
user decisions before sending the packet; a checksum cannot resolve their meaning.

## Check the complete rendered input

The task launcher applies a separate default ceiling of **24,000 UTF-8 bytes** to the exact
final text for implementation, review, and native followups. This includes the full task
contract, derived notes, source locators, execution boundaries, appended review requirements,
and evidence packet references. It never truncates required instructions or acceptance rules.

The check runs before worktree creation or worker dispatch and before a review cycle or native
followup is reserved. Oversized input returns the actual size and limit. Shorten derived notes,
link supporting evidence, or split genuinely independent work within the existing mandate.
Do not remove acceptance cases or restart a role merely to evade the limit.

A route can set `context_budget: {"max_bytes": 32000, "reason": "Required acceptance cases need this space"}`.
A positive integer is required; a limit above the default needs a nonempty reason. This field
is bound by the existing route approval digest. There is no launch flag that overrides it.
Preserve exact approved routes; use the normal plan change procedure when a larger limit is needed.

For a direct caller, check its final rendered file without writing or dispatching:

```bash
python3 <shared-dir>/scripts/context_packet.py measure --input <complete-worker-input.md>
```

The command returns 0 within the limit and 2 when blocked. A direct caller can supply
`--max-bytes` and, above the default, `--reason`; these flags do not grant authority.
The caller must use its approved allowance.

The manifest stores `brief_binding.input_measurement`; the native handoff and runner metadata
carry the same measurement. It includes the exact UTF-8 byte count, limit, and SHA-256 of the
final text. The transport rechecks the file before live dispatch. Dry runs measure proposed text
without creating files or starting workers.

This measures launcher text, not the full provider context. Host instructions, tool schemas,
adapter-added text, retained role history, and later file reads are unmeasured. `token_count`
stays null. Use actual execution receipts for input and cached token totals per accepted task.
Do not convert bytes to a claimed token saving or count a high cache hit rate as free input.

## Isolate tasks and retain repairs

Start each independent task and role with no parent conversation history. Send the bound task
packet as its initial input; keep source files available on demand. For native dispatch, honor
`parent_history: none` with the host's supported empty-history option. A host with `fork_turns`
uses `fork_turns: none` for creation. Do not fork the coordinator's full conversation.

Reuse the recorded context for that task's repairs and rechecks. Send only changed facts and
relevant evidence in the derived followup. Reconstruct a lost context from that role's artifacts
under the existing recovery protocol. A new task starts a new context; changing the context must
never reset call or retry counters. These rules do not authorize additional workers or user-owned tasks.
