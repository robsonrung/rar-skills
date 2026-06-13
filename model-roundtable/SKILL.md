---
name: model-roundtable
description: Orchestrate four model seats (Codex, Gemini, Kimi, and a native Opus 4.8 subagent) that independently interpret the SAME prompt, then moderate role-free discussion rounds (max 5) until they converge on a shared understanding, ending with an agreed-vs-disagreed report. Use when the user wants several models to "talk it out" / reach consensus on what a request actually means, asks for a model roundtable, free-discussion consensus with NO assigned roles, or wants to reconcile differing interpretations of a prompt before any work begins. Distinct from models-consensus (stance/role-driven decision council) and council (single blind round, Codex picks the plan).
---

# Model Roundtable

Convene four model seats to reach a shared understanding of a single prompt. Every seat first interprets the **same** prompt independently and in isolation. Then you, the main agent, act only as **moderator**: collect the interpretations, separate what they agree on from what they disagree on, and feed the open disagreements back to the seats for free, role-free discussion — up to five rounds — until they converge or stop moving. Finish by reporting what was agreed and what remains contested.

The seats are **only interpreting** the prompt, not executing it. No files are changed, no commands run, no plan is built. The deliverable is a shared reading of what the user is asking for.

## Hard Rules

1. **You are the moderator, not a seat.** Never inject your own interpretation into a round, and never count your own reading as a vote. Synthesize only what the seats produced.
2. **No roles, no stances.** Do not assign adversarial, advocate, critic, devil's-advocate, planner, or any other persona to any seat. Every seat gets the identical job and argues only from the merits. This is the defining difference from `models-consensus`.
3. **Read-only.** Launch every seat read-only. Seats interpret; they do not edit, run, or implement anything.
4. **Round 0 is blinded.** In the opening pass no seat sees any other seat's output, your notes, or any hint of a "right" answer.
5. **Max 5 discussion rounds.** Round 0 (independent interpretation) does not count. After it, run at most 5 discussion rounds, then stop and report regardless of convergence.
6. **Never fabricate a seat.** If a seat's CLI/tool is unavailable, drop it, lower confidence, and say so. Do not let a runner silently fall back to another provider — always pass `--disable-fallback`.

## Seats

Exactly four seats. Launch each by its preferred path for the current host; fall back only when the native path is unavailable.

| Seat | Claude Code host (primary) | Fallback |
|------|----------------------------|----------|
| Opus 4.8 | native `Agent` subagent, `model: "opus"` | `claude-runner --model claude-opus-4-8` |
| Codex | `codex-runner` (`--effort high`) | native `spawn_agent` on a Codex host |
| Gemini | `gemini-runner` (Antigravity `agy`) | — (skip if `agy` missing) |
| Kimi | `kimi-runner --model kimi-code/kimi-for-coding` | — (skip if `kimi-cli` missing) |

Exact launch commands, flags, and the output envelope contract are in [references/runner-invocations.md](references/runner-invocations.md). Read it before launching.

Note: the moderator is also Opus 4.8. That is fine — the Opus *seat* is a separate, blinded subagent that participates; the moderator only synthesizes. Keep them strictly separate.

## Preflight

Run before launching anything:

1. **Detect host capability.** On Claude Code the `Agent` tool exists → Opus runs as a native subagent. Otherwise use the runner fallback.
2. **Check seat prerequisites** with cheap shell checks: `codex` in `PATH`, `agy` in `PATH` (Gemini), `kimi-cli` in `PATH` (Kimi). Mark any missing seat `unavailable`.
3. **Quorum.** Proceed only with **≥3 seats**. With 2 or fewer, stop and tell the user which prerequisites are missing rather than running a thin roundtable.
4. **Artifact mode.** Use `persisted` when `.ai-workflow/` is writable (it is in this repo): write under `.ai-workflow/roundtable/<session_id>/`. Otherwise use `inline` and keep everything in memory, returning paths as `null`.
5. **Session id.** Derive a short stable id (e.g. `roundtable-<slug>`); use it for the artifact directory and all filenames.

Record a seat table (`seat`, `execution_path`, `status`, `blocked_reason`) before Round 0.

## The Brief

Build one shared brief and give it identically to every seat in a round. It contains only:
- the **original prompt** to interpret (verbatim),
- any `context_files` the user pointed at (paths only — seats read them read-only),
- the current objective for this round,
- for discussion rounds: the moderator digest (locked agreements + open points + each seat's current position),
- the required response schema.

Never add your own interpretation, repo summaries, or a preferred reading to the brief.

## Round 0 — Independent Interpretation (blinded)

Launch all available seats **concurrently** (issue the runner Bash calls and the Opus `Agent` call in a single message). Each seat receives the shared brief and the opening schema, with no peer output.

Ask each seat for its reading of the prompt, conforming to
[schemas/opening-interpretation.schema.json](schemas/opening-interpretation.schema.json):
`restated_request`, `intent`, `scope_in`, `scope_out`, `assumptions`, `ambiguities`, `open_questions`, `confidence`.

Opening seat prompt shape:

```text
You are one of several models independently interpreting a user's request.
Do NOT solve, plan, or implement anything. Only determine what is being asked.
You cannot see other models' answers. Argue only from the request itself.

REQUEST TO INTERPRET:
<original prompt>

CONTEXT FILES (read-only, optional):
<paths>

Return ONLY JSON matching this shape:
{restated_request, intent[], scope_in[], scope_out[], assumptions[], ambiguities[], open_questions[], confidence}
```

Collect each seat's `agent_message` (read it from the seat's `--output-file`; do not parse raw stdout). Validate against the schema; if a seat returns malformed output, retry once with a compact schema reminder, then mark it `malformed` and continue.

## Moderation — Consensus vs. Disagreement

After Round 0 (and after every discussion round), normalize all seat outputs into:
- **Agreement points** — readings every available seat shares (lock these; they do not re-enter discussion).
- **Disagreement points** — anything where seats differ on intent, scope, an assumption, or an ambiguity's resolution. Assign each a stable id (`D1`, `D2`, …) and a neutral one-line statement, plus each seat's current position on it.
- **Open questions** — questions multiple seats raised whose answers would change the interpretation.

Keep this digest compact. Never paste full seat transcripts into the next round — pass only the digest.

If there are **no disagreement points** after Round 0, skip discussion and go straight to the report (full consensus).

## Discussion Rounds (1–5, role-free)

For each round, until a stop condition fires:

1. Build a discussion brief: the **locked agreements**, then each open point (`D#` + neutral statement + every seat's current position, attributed by seat name so seats can engage each other), and the instruction to respond freely.
2. Relaunch all seats concurrently with the discussion schema
   ([schemas/discussion-round.schema.json](schemas/discussion-round.schema.json)):
   per-point `point_responses` (`point_id`, `position`, `agree`, `reasoning`), `changed_mind[]`, `held[]`, `confidence`.
3. Seats may change their mind, refine, propose a synthesis, or hold with reasons. Assign no role; let them talk freely on the merits.

Discussion seat prompt shape:

```text
Several models interpreted the same request. Below is what you all AGREE on
(settled — do not reopen) and the points still OPEN, with each model's current
position. Respond freely: change your mind, refine, propose a merged reading,
or hold your position — but justify it from the request alone. No assigned role.

SETTLED (agreed) INTERPRETATION:
<locked agreements>

OPEN POINTS:
D1: <statement> — Codex: <pos> | Gemini: <pos> | Kimi: <pos> | Opus: <pos>
D2: ...

Return ONLY JSON: {point_responses:[{point_id, position, agree, reasoning}], changed_mind[], held[], confidence}
```

4. Re-moderate: a point is **resolved** when all available seats now agree on it (lock it into the agreements). Carry only still-open points into the next round.

## Convergence & Stop Conditions

After each discussion round classify the roundtable:
- `full_consensus` — no open points remain. **Stop.**
- `converging` — fewer open points than the prior round. Continue.
- `stalled` — a full round produced zero resolved points and zero `changed_mind` entries across all seats. **Stop early** (more rounds will not help); record the open points as durable disagreements.

Also stop when **5 discussion rounds** have completed. Then write the report regardless of remaining disagreement.

## Final Report

Deliver the report inline to the user, and write it to `.ai-workflow/roundtable/<session_id>/report.md` in persisted mode. Sections:

1. **Request** — the original prompt and the run status (`full_consensus` / `partial` / `stalled`).
2. **Seats** — who participated; any seat that was unavailable or malformed, with the reason.
3. **Rounds** — Round 0 plus how many discussion rounds ran, and why it stopped.
4. **Agreed interpretation** — the shared understanding (the locked agreement points), written as a clear restatement of what the user is asking for.
5. **Unresolved disagreements** — each open `D#`: the neutral statement, the competing readings, which seats hold which, and the core reason they diverge.
6. **Clarifying questions for the user** — derived directly from the unresolved disagreements (and any shared open questions). These are the forks only the user can settle; surface them so the user can resolve the interpretation.
7. **Confidence** — `high` (≥3 seats, full or near-full consensus), `medium` (some durable disagreement or a missing seat), `low` (quorum barely met or major disagreement persists).

Do not proceed to execute the prompt. This skill ends at the shared interpretation; acting on it is a separate step the user initiates.

## Output Contract

Return:
1. `report_path` (or `null` in inline mode)
2. the seat table (seat → status)
3. status (`full_consensus` / `partial` / `stalled`) and rounds run
4. a concise inline rendering of the agreed interpretation + unresolved disagreements + clarifying questions

## Gotchas

- Pass `--restrict-tools` and **no** `--role` to every runner seat. `--restrict-tools` forces read-only without assigning a persona; a `--role` would violate the no-roles rule.
- Always pass `--disable-fallback`. A roundtable where Gemini silently became Claude is not four independent seats.
- Read each seat's answer from its `--output-file` `agent_message`, not raw stdout — Kimi appends a resume hint and Codex emits an activity transcript.
- Keep each seat's output bounded (~one page). Long transcripts blow up the moderator's context across five rounds; the digest, not the transcripts, carries state forward.
- Re-send the full digest each round; do not rely on seat-side session resume. The moderator holds all state, so seats stay stateless and comparable.
- Two Opus instances (moderator + seat) is intended, not a bug — keep the seat blinded and never let the moderator's view leak into its brief.
