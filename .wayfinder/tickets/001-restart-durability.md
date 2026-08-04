---
id: "001"
title: Surviving a server restart
type: grilling
status: closed
parent: map
blocked_by: []
---

# Surviving a server restart

## Question

A long-lived streaming session per board is not restart-safe: kill the server mid-interview and the conversation dies with it. Every other long-running thing in this repo follows the opposite rule — progress lives in the ledger, not the transcript, and a killed run resumes at its recorded phase.

What happens to an in-flight board when its server dies?

Options to put to the human: journal every turn to disk so a restarted server can replay the conversation into a fresh session; fall back to `--resume` on reconnect and lose only the live stream; or accept the loss and make restart an explicit "start this station over".

This is the first ticket because the answer shapes the streaming protocol — a protocol designed without durability in mind cannot have it retrofitted cheaply.

## Resolution

The premise was too pessimistic. Verified against the machine before grilling:

- Claude Code persists **every session as a JSONL** under `~/.claude/projects/<repo>/` — 24 present in this repo — independent of any server process.
- `run_claude.py` already captures `session_id` from CLI output and can `--resume` it; persistence is on by default (`--no-session-persistence` is the opt-out).
- `runner_jobs.py` already launches detached jobs with `start_new_session=True`, tracked by a pid-and-result manifest.

So a long-lived streaming session never put the **conversation** at risk. Killing the server loses the live stream, not the history. The durability concern raised when the streaming design was chosen is therefore **narrower than stated** — it is a reattachment problem, not a data-loss one.

Recording the `session_id` in the board's ledger is taken as given; there is no sensible alternative.

### On reattach, the board shows the gap

A restarted board reattaches to its session but **says so**, naming the last question asked and stating plainly that any answer in flight was not recorded, then waits for the human before continuing.

Chosen over silent auto-reattach: a silent reattach cannot distinguish "your answer landed" from "your answer died with the process", so it would let a human believe a decision was recorded when it was not. One click is a fair price for never guessing. This follows the same rule the pipeline applies elsewhere — a gate absent from the ledger was never granted, whatever the screen appeared to show.

Rejected for now: journalling and replaying the visual stream. Full fidelity, but it buys replay of *pixels* when the *conversation* is already durable, at one disk write per streamed event.

### Builds are detached and outlive the server

Scheduler runs launch in their own process session, so a server restart does not touch a build in flight. A restarted board reattaches by reading the run-state ledger and the job manifest — the board is a **window onto** the run, never its owner.

This reuses `launch_background()` rather than inventing a lifecycle, and it means the two halves of a board degrade differently and correctly: an interview needs a human, so it pauses and asks; a build does not, so it keeps going.

Rejected: child processes that die with the server (the scheduler would resume at its recorded phase, but twenty minutes of in-flight slice work dies with a UI restart), and a supervising auto-restarter (buys robustness by adding process-health machinery and the question of when restarting is the wrong call).

### Consequence for the map

No new tickets. This answer **sharpened two existing ones** rather than surfacing anything new — see the amendments to The streaming protocol and Driving the scheduler from a board.
