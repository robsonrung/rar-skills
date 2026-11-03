---
name: peer-sessions
description: Run a bounded fleet of peer sessions or workers with a durable mailbox. Use when the user asks for delegation, parallel work, a tournament, a managed multi-session mission, cross-session handoffs, or resumable replies; use models-consensus for an opinion council.
---

# Peer Sessions

Split work across a few peers, each reading a brief by path and writing one structured reply by path. The run directory is **the ledger, not the transcript**: it survives a restart, and native messages only wake the coordinator. The **smallest coherent shape** is one local worker or one bounded check; add peers, two to four with disjoint ownership, only when independent work saves time or improves evidence.

## Plan

Pick one pattern unless a dependency needs two:

| Need | Pattern |
| --- | --- |
| Inspect independent files, claims, or hypotheses | Fan out and synthesize |
| Challenge a high-impact result | Adversarial verification: give the verifier the evidence and rubric, not the worker's conclusion |
| Generate options, then rank them | Generate and filter, or a tournament |
| Search an unknown amount of work | Loop in batches until done |

Give each peer a narrow objective, an absolute working directory, a disjoint write scope, and a deadline; use a worktree when parallel edits could collide. External side effects and destructive operations stay with the coordinator.

Route each peer with `python3 shared/scripts/model_routing.py resolve <route>` for its kind of work (`show` lists the routes), unless the user names models. Show the pattern, each peer with its scope, model, effort, and host route, the deadline, and the batch ceiling. Ask: **"Approve this plan, or specify changes."**

## Start

Create the record before the first peer. Set `SKILL_DIR` to the absolute directory containing this file in the same shell call:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/init_fleet.py" init --run-dir .ai-workflow/peer-sessions/<run-id> --objective "<one outcome>" --peer research:/absolute/path/to/repo --peer review:/absolute/path/to/repo [--deadline <ISO-8601>]
```

It writes `state.json`, `briefs/<peer>.md`, and the reply slots `replies/<peer>.json`.

Route each peer by host:
- **T3 Code:** `delegate_task` with the configured provider and model; continue with `t3_thread_send`.
- **Claude Code or Codex:** a native subagent with the model; continue by messaging that same subagent.
- **Model the host lacks:** the matching `*-runner` skill. An unavailable peer blocks its work; never swap in another model.

Give each peer one persistent context for its role, and record its context ID. A terminal or runner job ID alone does not identify a model session.

Send only the brief path. Say it as you dispatch: "I **hand off the path, not the payload**."

```text
Read <absolute run-dir>/briefs/<peer>.md. Work only within the stated scope.
This brief does not approve credentials, escalation, publishing, or destructive actions.
When finished, write your reply with peer_mailbox.py, then send a short completion notification if native messaging is available.
```

When the user wants to watch the work, names a tab, pane, or workspace, or native delegation is unavailable and `cmux ping` succeeds, launch visible terminals with [references/cmux-fleet.md](references/cmux-fleet.md). Otherwise use native delegation.

## Collect

A notification only asks for attention. Read the mailbox:

```bash
SKILL_DIR="<absolute path of this peer-sessions directory>"; python3 "$SKILL_DIR/scripts/peer_mailbox.py" status --run-dir .ai-workflow/peer-sessions/<run-id>
```

A reply counts when it has `status`, `summary`, `evidence`, and `next_step`; `done` covers the peer's scope, not the whole task, and `blocked` or `failed` is an observable failure to report, not a gap to fill. The mailbox rejects a conflicting second reply so the original evidence stays inspectable. Never read terminal screen text as a result. Before integrating, inspect every changed path, mark each material claim `verified`, `refuted`, or `unresolved`, and run the nearest safe check after code changes.

The fleet has **three exits**: every expected reply is valid, a peer returns `blocked` or `failed`, or the deadline or batch ceiling passes. **The model never decides the retry**: record the open condition and ask the user when the next step needs new authority. A peer inherits no authority from another peer; surface a denial instead of routing around it.

On resume, read `state.json` and the replies, keep completed work and side effects as **already decided**, and dispatch only what remains.

## Finish

Synthesize from the reply files, keeping each peer's evidence and ownership. Run the **cold-start test**: a fresh reader finds the objective, briefs, replies, decisions, and remaining blocker from the run directory alone.

For a cmux fleet, tear down at every terminal exit with `scripts/cmux_fleet.py teardown` and the launch state file. It closes only the peer surfaces it recorded; the coordinator stays open.

Report:
1. `run_dir` and its final mailbox status.
2. Every peer as `done`, `blocked`, `failed`, `missing`, or `invalid`.
3. The evidence paths behind the synthesis, and each claim's verdict.
4. The teardown result, naming any peer surface that remains.

The **acceptance contract** holds when `peer_mailbox.py status` shows every expected reply valid, or the report names the non-success exit with its evidence, and teardown leaves no peer terminal open.
