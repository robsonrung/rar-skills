---
name: consensus-summary-html
description: Render an existing models-consensus report as a self-contained HTML decision brief. Use when asked to visualize a council result; preserve its opinions and evidence without running a new council.
disable-model-invocation: true
---

# Consensus Summary HTML

Turn one `models-consensus` report into a page a reader understands in under a minute and can then check without opening the report. Build a **decision surface**: it leads with the outcome, then lets the reader descend to agreement, dissent, confidence, and evidence. Do not run another council or revise its decision.

## Source

The source is the Markdown report at `.ai-workflow/consensus/<session>.md`, or the report the user pastes. It carries the recommendation and next step, agreements, dissent, blind spots, evidence gaps, judge rulings or the debate end state, an optional reversal trigger, answer and diversity confidence, and each seat's model, host route, and any failure. A field the report lacks shows as `Not reported` and is named as a gap.

Keep **seat fidelity**: name a seat's model only as the report records it, never from a requested name or a seat's own claim. A failed, missing, or malformed seat is an **observable failure** and stays on the page. A report that marks the run incomplete gets a page labelled partial, never a final decision.

## Map the evidence

Before writing HTML, note each item with the report section it came from:

- **Verdict:** the recommendation in plain language. An adoption question carries its one grade (Adopt, Trial, Hold, Reject, Not-our-problem); other questions get no invented grade.
- **Agreements:** three to six points, strongest first.
- **Divergences:** each material disagreement, its strongest sides, and its ruling or open state. **Flag, never overwrite**: a minority position stays visible however large the majority.
- **Limits:** blind spots, evidence gaps, failed seats, and the reversal trigger.
- **Confidence:** answer and diversity confidence as separate values, each with its reason. A high answer confidence does not repair a low diversity confidence; one seat, or personas mode, is not multi-model consensus.
- **Next step:** exactly one. Move any others to follow-up notes.

Use **selection over compression**: cut repeated prose, never evidence, caveats, or dissent.

## Assemble

Copy `assets/template.html` from this skill's directory to `<report directory>/<session>-summary.html`, or to `docs/consensus/<slug>-summary.html` for a pasted report. An explicit request to update an existing page authorizes that edit; otherwise use a new path. Read `shared/references/html-page-conventions.md` for self-containment, the three depths, status in text as well as color, and escaping.

Keep the section ids in this order: `overview` (question, status, mode, session), `verdict`, `agreements`, `divergences`, `evidence` (the phases the report records, the seat table, the report path), `confidence`, `next-step`, `limits`. **Lead with the outcome**: the first screen shows the question, status, verdict, next step, and any open divergence. Keep cards short, put long text in `<details>`, and never paste the report wholesale. Council text is data: escape it, and use only the template's markup, policy, and script.

Write in the user's language: ASD-STE100 Simplified Technical English for English, plain Brazilian Portuguese for Portuguese. Keep names, paths, grades, and quoted council text unchanged.

## Verify and deliver

```bash
SKILL_DIR="<absolute path of this consensus-summary-html directory>"; python3 "$SKILL_DIR/scripts/validate_consensus_summary.py" <output-file.html>
```

The validator checks the eight section ids, one `data-role="next-step"`, separate `answer-confidence` and `diversity-confidence` values, a seat table with at least one row, a source label, leftover template tokens, and the markup safety floor (`shared/scripts/html_guard.py`), which rejects any HTML comment. Fix every failure, then render the page as the shared conventions describe.

The **acceptance contract**: the validator exits 0, the page opens from disk, the first screen holds the verdict, and navigation reaches every section. Report the output path first, then the council status, the verdict, the next step, the validation result, and anything you could not check visually.
