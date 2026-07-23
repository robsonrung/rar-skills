---
name: capture-learning
description: Documents one recently solved problem as a durable solution doc in docs/solutions/ with searchable YAML frontmatter, and captures new domain vocabulary into the repo-root CONCEPTS.md. Use when the user says capture this learning, document what we learned, document what we solved, compound the knowledge, or write a solution doc — or when a pipeline invokes it with mode:headless after a verified fix. Not for ephemeral chat-only lesson extraction with no durable store (that is lesson-learned) and not for session continuity or handoff summaries (that is summarize / context-compress).
---

# capture-learning

Document ONE recently solved problem while context is fresh, as a structured doc in `docs/solutions/` with YAML frontmatter for searchability. The first time a problem is solved takes research; documented, the next occurrence takes minutes. Knowledge compounds.

**One learning per run.** Grounding, overlap detection, and cross-referencing all assume a single solved problem. If a session produced multiple distinct learnings, run this skill once per learning, sequentially — each run grounds fresh against the tree. Never batch several learnings through one run: drafting-context numbering ("Learning 3") leaking into written docs is the failure this rule prevents.

**Preconditions (advisory):** the problem is solved (not in progress), the solution is verified working, and it is non-trivial (not a typo or obvious error). In headless mode, an unmet precondition produces the `Documentation skipped` report instead of a doc.

## Modes

**Interactive (default).** Runs the full workflow, auto-picks Full vs Lightweight (below), and asks exactly one question in the whole run: consent for the Discoverability Check edit.

**Headless.** Enter headless mode when the invocation arguments contain the `mode:headless` token, or when the caller makes non-interactive intent unmistakable ("headless", "non-interactively", "unattended", "without prompts"). Ambiguous or absent signals default to interactive. In headless mode: ask no blocking questions, never edit instruction files (report gaps instead), skip optional reviews, and end with a structured report whose last line is the terminal signal `Documentation complete` (or `Documentation skipped` when no doc was written) so pipelines can detect the outcome.

Depth is a headless-only selector: `depth:lightweight` runs Lightweight Mode, `depth:full` (or no depth token) runs Full Mode. An unknown or duplicated `depth:` token means do not guess — emit the failure report and end with `Documentation skipped`. Tokens starting with `mode:` or `depth:` are flags; strip them before treating the remaining arguments as a context hint.

## Full vs Lightweight — decide it, don't ask it

The agent chooses; the user is never asked. Default to **Full** — its token cost is small next to the engineering work that produced the learning. Choose **Lightweight** (single pass, no subagents) only under real context pressure (session near its context limit) or when the fix is trivial enough that cross-referencing adds nothing — conditions the agent can observe and the user cannot. State the chosen mode and a one-line reason as the first line of the completion output. If Lightweight was the wrong call, re-running is a cheap correction.

## Auto memory

Before research, check the auto-memory block injected into the system prompt (and only that block — do not open memory files) for notes relevant to the problem being documented; if the block is absent or empty, skip. Memory ranks below conversation history and codebase evidence: pass relevant entries to research as supplementary context labeled "additional context, not primary evidence", and if memory contradicts the conversation, note the contradiction rather than adopting the memory claim. Any memory-derived content that lands in the final doc is provenance-tagged "(auto memory)" so future readers know its origin.

## Support files

Read on demand at the step that needs them — do not bulk-load at skill start. When spawning subagents, pass the relevant file contents into the task prompt.

- `references/schema.yaml` — canonical frontmatter fields, enum values, track rules
- `references/yaml-schema.md` — quick reference and problem_type → directory category mapping
- `references/resolution-template.md` — section structure for new docs (bug and knowledge tracks)
- `references/concepts-vocabulary.md` — CONCEPTS.md format and inclusion rules (Phase 2.4)
- `references/grounding-validation.md` — flag adjudication rules and the semantic validator prompt (Phase 2.45)
- `scripts/validate-frontmatter.py` — parser-safety validator for written frontmatter
- `scripts/validate-doc-claims.py` — mechanical claims validator: cited paths, SHAs, relative links, drafting scaffold

**Script resolution.** Set `SKILL_DIR` to the absolute path of the directory containing this SKILL.md and run the bundled scripts from there. If a script is not resolvable on the current platform, apply its documented checks manually and say so in the output — never silently skip.

## Invariants

<critical_requirement>
**The primary deliverable is ONE file — the final solution doc. Only the orchestrator writes product files.**

Phase 1 subagents write their full structured output to a per-run scratch directory and return only a compact confirmation containing the artifact path; the orchestrator Reads the artifacts back in Phase 2. Subagents must not touch `docs/`, `CONCEPTS.md`, instruction files, or any tracked path.

There are exactly three write-target classes; only the first is unconditional:

1. **`docs/solutions/...`** — the primary deliverable (always).
2. **`CONCEPTS.md` at repo root** — create or update in Phase 2.4 when a qualifying domain term surfaces.
3. **A project instruction file** (AGENTS.md or CLAUDE.md) — a small Discoverability Check edit, **only in interactive Full mode after explicit consent**. Headless and Lightweight report or tip instead.

**Why the scratch artifact:** a subagent asked to return a long prose body inline intermittently returns an executive summary instead, and the full prose is then unrecoverable. Writing to disk first means the full output always survives; the inline return is a pointer. A subagent returns its full output inline only when the artifact write itself failed — then the orchestrator uses the inline return as the fallback.
</critical_requirement>

---

## Full Mode

### Phase 1: Research

**Run dir first.** Create a per-run scratch directory under the session scratchpad directory (listed in your environment context); fall back to `mktemp -d` when no scratchpad is listed:

```bash
RUN_DIR="<session-scratchpad>/capture-learning/$(date +%Y%m%d-%H%M%S)-$RANDOM"
mkdir -p "$RUN_DIR" && echo "$RUN_DIR"
```

If `CONCEPTS.md` exists at repo root, read its relevant terms and pass them to the Context Analyzer. Then launch three subagents **in parallel**, passing each the resolved absolute `RUN_DIR`. Each writes its full structured output to its own artifact file, confirms the file exists and is non-empty, and returns only a one-line confirmation with the path.

1. **Context Analyzer** → `$RUN_DIR/context.json`
   - Reads `references/schema.yaml` and `references/yaml-schema.md` (passed in by the orchestrator); never invents enum values, categories, or fields from memory.
   - Determines the track (bug vs knowledge) from problem_type, and the track-appropriate fields — bug: symptoms, root_cause, resolution_type; knowledge: applies_when.
   - Writes the YAML frontmatter skeleton (including `category:` mapped from problem_type), the category directory path, and a suggested filename: `[sanitized-problem-slug].md`, no date suffix — the `date:` field is the canonical creation date.

2. **Solution Extractor** → `$RUN_DIR/solution.md`
   - Writes the full doc-body prose for the track's sections (see `references/resolution-template.md`): bug — Problem, Symptoms, What Didn't Work, Solution, Why This Works, Prevention; knowledge — Context, Guidance, Why This Matters, When to Apply, Examples.
   - **Grounds code-behavior claims in source, not conversation memory.** Before asserting how code behaves (enum values, limits, defaults, semantics), Read the defining line at the current tree and cite `file:line`. A claim that cannot be verified is softened or attributed ("per this session's conclusion…"), never stated as fact.
   - **Writes merge-state claims for time.** Cite PR numbers over bare commit SHAs (SHAs are rewritten by rebase/squash). A "fixed in X" claim requires the fix to be reachable from the current tree; otherwise phrase it as pending.

3. **Related Docs Finder** → `$RUN_DIR/related.json`
   - Greps `docs/solutions/` fresh this run — frontmatter-targeted patterns first (`title:.*<keyword>`, `tags:.*(<k1>|<k2>)`, `module:.*<module>`), reads only frontmatter of candidates to score relevance, fully reads only strong matches.
   - **Assesses overlap** with the doc being created across five dimensions: problem statement, root cause, solution approach, referenced files, prevention rules. **High** = 4–5 dimensions match; **Moderate** = 2–3; **Low** = 0–1.
   - Writes links, relationships, and the overlap assessment (score + matched dimensions).

### Phase 2: Assembly & Write

Wait for all Phase 1 subagents, then the orchestrator:

1. **Collect results**: Read each artifact under `$RUN_DIR/`. Fall back to a subagent's inline return only when its artifact is absent or empty.
2. **Act on the overlap assessment**:

   | Overlap | Action |
   |---------|--------|
   | **High** | **Update the existing doc** with fresher context instead of creating a duplicate — two docs for the same problem inevitably drift. Preserve its path, structure, and title; add `last_updated: YYYY-MM-DD` to the frontmatter. |
   | **Moderate** | Create the new doc; note the overlap in the Refresh recommendation line. |
   | **Low / none** | Create the new doc normally. |

3. **Assemble** the complete markdown file, following the section order in `references/resolution-template.md` for new docs.
4. **Validate** the frontmatter against `references/schema.yaml`, applying the YAML-safety quoting rules in `references/yaml-schema.md`.
5. `mkdir -p docs/solutions/[category]/` and write the file.
6. **Parser-safety check** on the written frontmatter:

   ```bash
   SKILL_DIR="<absolute path of the directory containing this SKILL.md>"
   python3 "$SKILL_DIR/scripts/validate-frontmatter.py" <output-path>
   ```

   Exit 0 means parser-safe. Exit 1 names the offending field(s) — quote the value(s), rewrite, and re-run until clean; do not declare success while validation fails. If the script cannot run, apply its checks manually at the same scope (delimiters are exact `---` lines; unquoted top-level scalar values contain no ` #` and no `: `) and note the manual fallback in the output.

### Phase 2.4: Vocabulary Capture (CONCEPTS.md)

**First, read `references/concepts-vocabulary.md` — unconditionally.** Do not pre-judge from memory that nothing qualifies; the criteria are non-obvious and qualifying terms often live in the surrounding conversation rather than the doc itself.

Applying those criteria, scan the new doc **and** the conversation for qualifying domain terms. If `CONCEPTS.md` exists at repo root, add missing qualifying terms and refine existing entries when new precision surfaced; also refresh the coherence neighborhood of any entry touched (cluster siblings, cross-referenced terms) — on evidence already in hand only, never a full-file audit. If it does not exist and at least one term qualifies, create it, seeding the core domain nouns of the learning's area (per the reference's Seed rules) so the new term does not dangle against undefined siblings — hold borderline terms to a conservative bar at creation. Verify behavior assertions against source before writing them into an entry.

Apply edits silently in every mode — vocabulary capture is a side effect of compounding, not a per-run user decision. If no terms qualified, record that explicitly (e.g., "Vocabulary: scanned, no qualifying terms") — the visible no-result record is the audit signal that the reference was consulted.

### Phase 2.45: Grounding Validation

The doc (and any CONCEPTS.md entries) is about to become permanent, trusted knowledge. **Read `references/grounding-validation.md` now** — it holds the adjudication table and the validator prompt.

1. **Mechanical claims check (every mode).** Optionally `git fetch --quiet` first (best-effort; the network is never a correctness dependency). Then:

   ```bash
   python3 "$SKILL_DIR/scripts/validate-doc-claims.py" <doc-path>
   ```

   Exit 1 means flags to **adjudicate, not auto-fix** — each flagged path, SHA, link, or scaffold token is fixed, annotated as historical, or confirmed intentional per the reference's table. A doc may legitimately cite a path deleted by the very fix it documents; a flag is a question, not a failure.

2. **Semantic grounding validator (Full mode only; Lightweight skips).** Dispatch one read-only generic subagent built from the prompt template in the reference, covering the written doc plus any CONCEPTS.md entries from this run. Apply its verdicts (fix contradicted claims from quoted evidence; soften or drop unverifiable ones; mark offline merge-state checks degraded), then re-run the mechanical check if the body changed.

### Refresh recommendation

Cross-doc maintenance (consolidating moderate overlaps, refreshing docs the new learning contradicts or supersedes) belongs to **refresh-learnings — a future skill, gated on this pilot graduating** (see `docs/solutions/README.md`). Do not attempt it here. When the Related Docs Finder surfaced stale or overlapping candidates, record a narrow scope hint (specific file, module, or category) in the `Refresh recommendation:` output line; otherwise record `none`. Always capture the new learning first — refresh is never a prerequisite.

### Discoverability Check

The knowledge store only compounds value when agents can find it. After the doc is written:

1. Identify the root-level instruction file (AGENTS.md, CLAUDE.md, or both — if one is a shim that `@`-includes the other, the substantive file is the target). If neither exists, skip.
2. Assess **semantically** (not by string match) whether an agent reading it would learn: that a searchable store of documented solutions exists; enough structure to search it (categories, frontmatter fields like `module`, `tags`, `problem_type`); and when it is relevant (implementing or debugging in documented areas). If the spirit is met, no action.
3. If not, draft the smallest addition that communicates those three things — a single line in the closest existing section (directory listing, architecture tree, conventions block) is almost always better than a new headed section. Keep the tone informational, not imperative ("relevant when implementing or debugging in documented areas", not "always search before implementing"). Example calibration:

   ```
   docs/solutions/  # documented solutions to past problems, organized by category with YAML frontmatter (module, tags, problem_type)
   ```

4. **Interactive Full mode:** show the proposed change and where it goes, then get consent via the platform's blocking question tool before editing. Never silently skip the question, and never edit without consent. **Headless:** report `Instruction-file edit: gap noted, not applied`. **Lightweight:** emit a one-line tip, no edit.
5. If `CONCEPTS.md` exists at repo root, run the same check for it (same target file, same consent shape per mode); skip entirely when it does not exist — never nag for an artifact the project has not adopted.

### Optional reviews

Optionally, for security-flavored or code-heavy learnings, the local `security-gate` and `clean-code` skills can review the written doc's guidance and code examples (documentation review only — never mutate product code from this skill). Skip in headless mode.

---

## Lightweight Mode

Single-pass alternative — same artifact type, no subagents, reduced research and validation. The orchestrator does everything sequentially:

1. **Extract from conversation** (plus the auto-memory rules above). Ground code-behavior claims by Reading the defining source line; cite PR numbers over SHAs; phrase unmerged fixes as pending.
2. **Classify**: read `references/schema.yaml` and `references/yaml-schema.md`; determine track, category, filename.
3. **Write the doc** using the track template from `references/resolution-template.md` (bug: problem, root cause, solution with key snippets, one prevention tip; knowledge: context, guidance with key examples, one applicability note). Exact-path collision handling only: if the proposed path exists and covers the same problem, update it (add `last_updated:`); otherwise pick a distinct filename. No semantic overlap research.
4. **Vocabulary capture, update-only**: if `CONCEPTS.md` exists, apply Phase 2.4 against it; do not create or seed it — creation is a Full-run responsibility.
5. **Mechanical claims check** and **parser-safety check** exactly as in Phase 2.45 step 1 and Phase 2 step 6. Lightweight skips only the semantic validator, not these deterministic checks.
6. **Read-only discoverability check**: assess from context already in hand; report `no gap`, `gap noted — tip emitted`, or `not applicable`. Never open-and-edit instruction files from Lightweight.

Lightweight may create a doc that semantically overlaps an existing one; that is acceptable — note it for refresh-learnings rather than broadening the run.

## Success Output

End the turn after the summary — no "What's next?" menu. The doc is written; if the user wants follow-ups, they will ask.

**Interactive:** a short summary — mode chosen + reason, file written (created/updated), track, category, overlap outcome, grounding result, vocabulary outcome, discoverability outcome, refresh recommendation.

**Headless:** a structured report, ending with the bare terminal signal:

```
✓ Documentation complete (headless <full|lightweight> mode)

File: docs/solutions/<category>/<filename>.md  (created | updated)
Track: <bug | knowledge>
Overlap: <none | low | moderate — see <path> | high — existing doc updated | not assessed (lightweight)>
Grounding: <clean | N flags adjudicated | N claims softened or corrected | degraded — merge-state unverified offline>
Instruction-file edit: <none needed | gap noted, not applied>
CONCEPTS.md: <not present | scanned, no qualifying terms | created with N entries | updated — N added, N refined>
Refresh recommendation: <none | scope hint for refresh-learnings (future, gated)>

Documentation complete
```

When no doc was written (problem not solved, solution unverified, bad depth token):

```
✗ Documentation skipped (headless mode)

Reason: <one sentence>

Documentation skipped
```

## Common Mistakes

| Wrong | Correct |
|-------|---------|
| Subagents write into `docs/` or tracked paths | Subagents write only scratch artifacts under `$RUN_DIR` and return the path; the orchestrator writes the one doc |
| Subagent returns long prose only inline | Full output goes to the run artifact; inline return is fallback only |
| New doc created when an existing doc covers the same problem | High overlap → update the existing doc |
| Code behavior or merge state asserted from conversation memory | Read the defining source line; cite PR numbers; soften unverifiable claims |
| Several learnings batched through one run | One learning per run, sequential runs for the rest |
| Headless run edits AGENTS.md/CLAUDE.md | Headless reports the gap; only interactive Full edits, after consent |

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
