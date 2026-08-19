# Concepts

Shared domain vocabulary for this repository — entities, named processes, and conventions with repo-specific meaning. Glossary only, not a spec or catch-all. Direct edits are fine; the capture-learning skill accretes entries as learnings surface domain terms.

## Seats and runners

### Seat
One model's chair at a multi-model table (council, roundtable, review panel). A seat is an identity ("the Kimi seat"), not a transport: it may be served natively (host `Agent` tool) or by a runner skill wrapping a local CLI.

### Native seat vs runner seat
A native seat runs through the host's own agent-spawning tool (e.g. `Agent` in Claude Code). A runner seat shells out to a local CLI through a `*-runner` skill. Deterministic preference: native over runner, always.

### Runner skill / runner shim
A skill (`claude-runner`, `codex-runner`, `gemini-runner`, `kimi-runner`, `glm-runner`, `cline-runner`, …) whose script wraps one CLI and emits the shared envelope. Some runners delegate to another runner's transport (a shim) while keeping their own seat label.

### Envelope
The normalized JSON wrapper every runner script returns (`_shared/runner-envelope.schema.json`): success, stdout/stderr, `runner`, `effective_runner`, `effective_model`, `effective_provider`, `agent_message`, and friends. The family-wide contract locked by `_shared/tests/test_runner_parity.py`.

### Seat fidelity
The invariant that a seat never silently answers with a different provider's model. Missing CLI or failed auth blocks the seat explicitly (`seat_unavailable`) instead of falling back. `--disable-fallback` enforces it in councils.

### Model identity receipt
The serving backend's own report of which model actually handled a run (`effective_model` / native model id in the envelope), recorded alongside the requested model so the two can disagree visibly. Cross-model agreement is weighted by the receipt, never by the request or the model's self-claim.

### Cross-model pass
An additive delegated run that sends a review or judgment brief through a different provider's seat and folds the structured result back into the host synthesis. Counts as independent corroboration only with a verified model identity receipt.

### Quorum
The minimum count of independent seats a multi-model skill needs before its output claims full strength (`discover_runners.py` emits advisory light/quality quorum signals). Below quorum, skills proceed under a declared degraded posture.

### Effective runner
The transport that actually executed (envelope key `effective_runner`) — e.g. the Kimi seat currently executes via the `pi` CLI while keeping seat identity `kimi`.

## Skills and conventions

### Moment
One of the five points in a working turn that `fable-mindset` governs — intake, diagnosis, decision, implementation, reporting. A moment is about *posture* (how a request is read, how evidence is weighed, how a result is reported) rather than a domain or a procedure; the procedural counterpart of each moment lives in its own skill (`diagnose`, `coding-design-plan`, `tdd`, `summarize`).

### Panel mode
The opt-in multi-model path inside a pipeline skill (`brainstorm`, `to-prd`, `to-tasks`) and the whole of `collaborative-delivery`. Panel mode fans a phase out to real model seats through `_shared/scripts/panel_round.py` and writes an auditable artifact set; it replaces drafting, never the human approval gate. A generated prompt is not participation — see the status taxonomy in `_shared/collaborative-panel-runner.md`.

### Seat tier
Whether a seat joins a default fan-out (`default`) or is probed only when named explicitly (`backup`, currently qwen / muse / gemma / minimax). Declared in `discover_runners.py`; adding a backup seat never silently enlarges or re-prices an existing council.

### Leitwort (pl. leitwörter)
A deliberately distinctive word planted in a skill's prose to make routing and provenance greppable. Registered in `leitworter.json`; guarded by `scripts/check_leitworter.py` in CI. Deleting one from its owning skill fails the build.

### `_shared/`
The one sanctioned cross-skill directory: envelope schema, runner discovery, parity tests, common references. Everything else in a skill stays self-contained — no `../other-skill` paths.

### Model tier
A semantic cost class for a dispatched subagent — extraction (cheapest capable), generation (mid-tier), ceiling (orchestrator's own model, inherited by omission) — declared once per skill and referenced by tier name so concrete model ids never hardcode into skill content. (See skill-expert's portable-skill-authoring reference.)

### Learning
A documented solution to a past problem, stored under `docs/solutions/` with structured frontmatter by the capture-learning skill — the unit of compounded knowledge. The refresh sibling (`refresh-learnings`) is gated on the pilot's graduation signal.

### Script ownership
Every ported or shared script has a named owner skill; a script reused by more than one skill lives in `_shared/`, never as per-skill byte-identical copies.

### Run state
The durable JSON file a long-running orchestration skill keeps at `.ai-workflow/<skill>/<run-id>/run-state.json`, holding status, phase, attempt counters, ceilings, gate decisions, side-effect keys, and the step trace. Contract in `_shared/references/run-state-contract.md`. It is the source of truth for progress — **the ledger, not the transcript** — so a run survives a crash, a compaction, or a restart.

### Station handoff
The file-based contract between two steps of an orchestrated run: a **brief** the orchestrator writes, a **report** the worker writes (seven fixed sections), and a **station envelope** — under 15 lines — that is the only thing crossing back into the orchestrator's context. Contract in `_shared/references/handoff-contract.md`; `ship`'s per-station binding in `ship/references/station-dispatch.md`. The rule it enforces is **hand off the path, not the payload**: inputs and outputs are file paths, never pasted bodies. Distinct from the runner [Envelope](#envelope), which is a transport wrapper around one CLI call.

### Thin conductor
An orchestrator that owns routing, gates, integration, and the final report — and nothing else. Every step that does not need the user runs in its own subagent, so the conductor's context grows by one envelope per step rather than by the size of each step's work. `ship` is the pipeline's thin conductor; `dynamic-harness`'s manager mode is the general form.

### Ceiling
A bound on a run counted outside the model's judgment — cycles, dispatched agents, spend, or a deadline — recorded in the run state's `ceilings`. Distinct from a stop condition, which depends on the work converging. Every run ends through one of **three exits**: success, retries exhausted, or ceiling hit.

### Local config
Per-checkout, user-local preferences for multi-model skills live in `.rar-skills/config.local.yaml` (gitignored; committed example alongside). All keys optional; invalid values fall through to defaults; never credentials; config always loses to direct instructions in chat.

## Provenance

Material adapted from Every's compound-engineering-plugin (MIT) carries a per-file provenance line and is credited in `NOTICE`. Upstream skill names (`ce-*`) appear only in provenance notes, never as skill names here.
