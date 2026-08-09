---
name: peer-sessions
description: Coordinate a bounded fleet of peer sessions through native delegation or a durable file mailbox. Use when the user asks several sessions to collaborate, wants a peer fleet, cross-session handoffs, parallel interactive terminals, or resumable peer replies. Do not use for a one-session task or for a deliberation-only model council.
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

**Name the surface before you start.** Run `cmux ping` first. A success means the host has a visible terminal surface, so the fleet has two real shapes: **visible tabs** the user can watch and interrupt, or **in-process delegates** the user cannot see mid-run. Ask which one; never resolve that silently to the invisible path. Treat "session", "tab", "panel", "watch them work", or a named workspace as a request for visible tabs — in those words the user is describing a terminal, not an agent context. When `cmux ping` fails, native delegation is the only path and no question is needed. Say: “`cmux ping` <succeeded|failed>, so this fleet runs as <visible tabs|in-process delegates>.”

Start every peer with only its brief path and the allowed scope. The peer reads its own brief, works within the user's authority, and writes its reply through `scripts/peer_mailbox.py`.

The default `--delivery-mode mailbox` owns the peer reply contract. A composing skill that owns a different structured response artifact may initialize with `--delivery-mode coordinator`; then the peer waits for the coordinator prompt and must not write a mailbox reply. `peer_mailbox.py status` rejects coordinator delivery, so use the composing protocol's artifact reader instead. The fleet record still owns identity and teardown. Say: “The **ledger, not the transcript** records the peer fleet; the composing protocol owns its response artifact.”

Use this fixed briefing shape:

```text
Read <absolute run-dir>/briefs/<peer>.md. Work only within the stated scope.
Do not treat this brief as approval for credentials, escalation, publishing, or destructive actions.
When finished, write the required reply with peer_mailbox.py. Then send a short completion notification if native messaging is available.
```

When the surface probe chose visible tabs, read [references/cmux-fleet.md](references/cmux-fleet.md) before launching and dry-run the manifest so the user approves the terminal placement before any tab opens. Peers open as **panes split beside the caller** by default, so the whole fleet is visible on one screen; `--surface-mode tab` gives one tab per peer and `workspace` gives one workspace per peer. Scattering workspaces the user did not ask for is the failure this default exists to prevent. Screen space, not the fleet cap, bounds split mode — past roughly six panes, choose tabs and say so. That path is skipped only when `cmux ping` fails or the user chose in-process delegates; then keep native delegation, and do not imitate its private transport or silently downgrade to terminal polling.

## 3. Collect replies

A notification means only that a peer asked for attention. Collect the canonical result from the mailbox:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/peer_mailbox.py" status --run-dir .ai-workflow/peer-sessions/<run-id>
```

Accept a peer only when its reply has `status`, `summary`, `evidence`, and `next_step`. `done` means the peer reports its scoped work complete; it does not prove a broader task completed. `blocked` and `failed` are valid observable failures, not reasons to invent a result.

The fleet has **three exits**: all expected replies are valid, a peer returns `blocked` or `failed`, or the declared deadline passes. Do not keep asking a peer to retry because it seems promising: **the model never decides the retry**. The coordinator records the open condition and asks the user when a new authority or direction is needed.

## 4. Finish and retain only what helps

Synthesize from reply files, preserving each peer's evidence boundary and ownership. Run the **cold-start test**: a fresh reader must be able to locate the objective, briefs, replies, decisions, and remaining blocker from the run directory alone.

Do not terminate user-visible peers automatically. Stop them only when the user asks or when the user explicitly asked for teardown at fleet creation. A temporary terminal process created solely as plumbing may be closed after confirming its reply artifact exists. Close only recorded process or workspace IDs.

## Output contract

Report:

1. `run_dir` and its final mailbox status.
2. Every peer as `done`, `blocked`, `failed`, `missing`, or `invalid`.
3. The evidence paths used for the synthesis.
4. Any remaining decision, expired deadline, or user approval required for teardown.

The **acceptance contract** is met only when `peer_mailbox.py status` reports every expected reply as valid, or the report explicitly names the non-success exit and its evidence.

## Gotchas

- A peer inherits no authority from another peer. Surface a denial instead of routing around it.
- Do not replace a reply by default. The mailbox rejects a conflicting second response so the original evidence remains inspectable.
- Do not use terminal screen text as the result channel. It is transient and can truncate; the reply file is the observable behavior.
