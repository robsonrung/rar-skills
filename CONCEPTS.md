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
The transport that actually executed (envelope key `effective_runner`) — e.g. the Kimi seat currently executes via the `cline` CLI while keeping seat identity `kimi`.

## Skills and conventions

### Moment skill
One of the `fable-*` skills that captures a workflow moment (intake, diagnosis, decision, implementation, reporting) rather than a domain.

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

### Local config
Per-checkout, user-local preferences for multi-model skills live in `.rar-skills/config.local.yaml` (gitignored; committed example alongside). All keys optional; invalid values fall through to defaults; never credentials; config always loses to direct instructions in chat.

## Provenance

Material adapted from Every's compound-engineering-plugin (MIT) carries a per-file provenance line and is credited in `NOTICE`. Upstream skill names (`ce-*`) appear only in provenance notes, never as skill names here.
