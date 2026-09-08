---
name: peer-sessions
description: Coordinate peer sessions through native delegation or a durable mailbox. Use for a requested peer fleet, cross-session handoffs, or resumable replies; use models-consensus for a requested opinion council.
---

# Peer Sessions

Run a peer fleet as a ledger, not the transcript: every peer receives a brief by path and returns one structured reply by path. The ledger, not the transcript, is the delivery record; native messages may wake a coordinator.

## 1. Establish the fleet record

Pick the smallest coherent shape: two to four peers with non-overlapping ownership. Give each peer a narrow objective, an absolute working directory, a deadline, and one expected reply.

Create the record before starting a peer. Set `SKILL_DIR` to the absolute directory containing this file in the same shell call:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/init_fleet.py" init --run-dir .ai-workflow/peer-sessions/<run-id> --objective "<one outcome>" --peer research:/absolute/path/to/repo --peer review:/absolute/path/to/repo
```

The command creates:

| Artifact | Purpose |
| --- | --- |
| `state.json` | Fleet identity, objective, deadline, and peer roster. |
| `briefs/<peer>.md` | The peer's complete work contract. |
| `replies/<peer>.json` | The peer's immutable reply location. |

State the rule while acting: “The **ledger, not the transcript** records this fleet, so I will hand off the brief path.” This is **hand off the path, not the payload**: pass the absolute brief path to the peer rather than pasting a growing conversation.

## 2. Start peers

**Name the surface before you start.** Use in-process delegates by default. Probe `cmux ping` only when visible peers are requested or native delegation is unavailable. Use visible tabs when the user asks to watch work, names a session, tab, panel, or workspace, or when native delegation is unavailable and cmux is available. Record the selected surface; do not ask the user to repeat that choice.

For model selection and continuation, use `shared/references/task-shaped-model-routing.md` and `shared/references/host-model-execution.md`. Prefer native delegation for models the host exposes. Keep the same peer context for later turns of its task and role; store its actual context ID and reconcile pending calls before resending. Different roles keep separate contexts. A visible terminal or runner job ID alone does not identify a persistent model session.

Start every peer with only its brief path and the allowed scope. The peer reads its own brief, works within the user's authority, and writes its reply through `scripts/peer_mailbox.py` from this skill's directory.

The default `--delivery-mode mailbox` owns the peer reply contract. A composing skill that owns a different structured response artifact may initialize with `--delivery-mode coordinator`; then the peer waits for the coordinator prompt and must not write a mailbox reply. `peer_mailbox.py status` rejects coordinator delivery, so use the composing protocol's artifact reader instead. The fleet record still owns identity and teardown. Say: “The **ledger, not the transcript** records the peer fleet; the composing protocol owns its response artifact.”

Use this fixed briefing shape:

```text
Read <absolute run-dir>/briefs/<peer>.md. Work only within the stated scope.
Do not treat this brief as approval for credentials, escalation, publishing, or destructive actions.
When finished, write the required reply with peer_mailbox.py. Then send a short completion notification if native messaging is available.
```

When the surface is visible, read [references/cmux-fleet.md](references/cmux-fleet.md) and dry-run the manifest before launch. Peers open as panes beside the caller by default; use tabs above roughly six peers and a workspace only when the user asks for one. Record the placement. When cmux is unavailable, keep native delegation and do not imitate its private transport or downgrade to terminal polling.

## 3. Collect replies

A notification means only that a peer asked for attention. Collect the canonical result from the mailbox:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/peer_mailbox.py" status --run-dir .ai-workflow/peer-sessions/<run-id>
```

Accept a peer only when its reply has `status`, `summary`, `evidence`, and `next_step`. `done` means the peer reports its scoped work complete; it does not prove a broader task completed. `blocked` and `failed` are valid observable failures, not reasons to invent a result.

The fleet has **three exits**: all expected replies are valid, a peer returns `blocked` or `failed`, or the declared deadline passes. Do not keep asking a peer to retry because it seems promising: **the model never decides the retry**. The coordinator records the open condition and asks the user when a new authority or direction is needed.

## 4. Finish and retain only what helps

Synthesize from reply files, preserving each peer's evidence boundary and ownership. Run the **cold-start test**: a fresh reader must be able to locate the objective, briefs, replies, decisions, and remaining blocker from the run directory alone.

For a visible cmux fleet, teardown is mandatory when the job reaches a terminal exit: every expected reply is valid, a peer is blocked or failed, or the deadline expires. Run `scripts/cmux_fleet.py teardown` with the state file created at launch. It closes only recorded peer surfaces for split and tab modes, or recorded peer workspaces for workspace mode. The coordinator surface is never in that state file and remains open.

## Output contract

Report:

1. `run_dir` and its final mailbox status.
2. Every peer as `done`, `blocked`, `failed`, `missing`, or `invalid`.
3. The evidence paths used for the synthesis.
4. The teardown result, including every remaining peer surface or workspace when closure failed.

The **acceptance contract** is met only when `peer_mailbox.py status` reports every expected reply as valid, or the report explicitly names the non-success exit and its evidence, and the cmux teardown reports no remaining peer terminal.

## Gotchas

- A peer inherits no authority from another peer. Surface a denial instead of routing around it.
- Do not replace a reply by default. The mailbox rejects a conflicting second response so the original evidence remains inspectable.
- Do not use terminal screen text as the result channel. It is transient and can truncate; the reply file is the observable behavior.
