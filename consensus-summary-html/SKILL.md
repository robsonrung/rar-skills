---
name: consensus-summary-html
description: Turn a completed models-consensus result into a self-contained, readable HTML decision brief with a clear verdict, agreement map, divergence cards, evidence trace, separate confidence views, and one next step. Use when the user asks to render, visualize, present, or explain a consensus report as HTML or asks for a beautiful consensus summary page. Do not use this skill to run a council, change its decision, or explain a codebase architecture.
---

# Consensus Summary HTML

Create one HTML page that helps a reader understand a council result in under a minute, then inspect the evidence without opening the raw transcript.

## Outcome spine

* **Result:** one self-contained `.html` file with inline CSS and JavaScript.
* **Next consumer:** the person who must adopt the recommendation, challenge it, or hand it to the next workflow step.
* **Done:** the output exists, the bundled validator exits 0, every visible claim has a source or an explicit evidence gap, and the page contains no template tokens.
* **Intent:** build a **decision surface**. A decision surface leads with the outcome, then lets the reader descend from claims to evidence, disagreement, confidence, and action.

When you describe your work, use the leitwort: “The decision surface leads with the outcome and keeps unresolved evidence visible.”
Use **lead with the outcome** as the first layout rule, not as a late summary note.

## Input contract

Use the completed `models-consensus` result. Do not run another council and do not revise the council decision.

1. Use the persisted `report_path` Markdown file as the primary narrative source.
2. Use the persisted `state_path` JSON file when present. It supplies status, mode, rounds, seat fidelity, effective providers and models, independence accounting, and confidence values.
3. If the result is inline, use the supplied report and state sections. If a field is missing, show `Not reported` and name the evidence gap.
4. Read raw round output files only to fill a missing required category. Do not load the full transcript by default.
5. Before normalization, read `references/input-contract.md` from this skill's directory when the artifact mode, report shape, or state keys are unclear.

Evidence has priority over decoration. A missing seat, malformed output, timeout, shared provider, or unresolved divergence must remain visible. Use **seat fidelity**: name a seat only when the result records its effective provider or model. Never infer a model from a requested name or from a self-claim.

## Workflow

### 1. Locate and freeze the result

Find the report and state paths in the result object or in the user's supplied context. Record the session id, question, status, mode, artifact mode, and report date. If the status is not `complete`, label the page as partial, failed, awaiting human input, cancelled, or ceiling hit. Do not present a partial result as a final decision.

### 2. Normalize the evidence

Build a compact internal map before writing HTML. Keep source paths beside each item so provenance is not lost.

* **Question and status:** the task, current status, mode, rounds, and any mode switch.
* **Verdict:** plain language first. For adoption questions, include exactly one grade from `Adopt`, `Trial`, `Hold`, `Reject`, or `Not our problem`, with the grade attached to the plain sentence. For other question shapes, state the direct recommendation without inventing a grade.
* **Agreements:** three to six points that the council supported, with the strongest evidence first.
* **Divergences:** each material disagreement, its strongest sides, and its resolution or open state. Use **flag, never overwrite**: do not hide a minority position because the majority was larger.
* **Blind spots and evidence gaps:** facts the council could not verify, missing context, malformed seats, and limitations of the run.
* **Confidence:** answer confidence and diversity confidence as separate values. Add the reason for each band. Do not convert one into the other.
* **Seats and rounds:** selected, omitted, unavailable, and duplicate seats; effective provider and model when recorded; round outcomes and convergence.
* **Next step:** exactly one concrete action. If the council supplied more than one, select the highest-leverage action and place the other actions under follow-up notes.

Use **selection over compression**. Remove repeated prose, not evidence, caveats, or dissent.

### 3. Assemble the decision surface

Copy `assets/template.html` from this skill's directory to the agreed output path. Replace every marked slot and remove every placeholder.

Use `<report directory>/<session_id>-summary.html` by default when `report_path` is persisted. When there is no report path, use `docs/consensus/<slug>-summary.html`. If that path already exists and was not created in the current run, ask before overwriting it.

Use this section order and keep the ids unchanged:

1. `overview`: question, status, mode, session, and a one-paragraph summary.
2. `verdict`: the recommendation in plain language, plus the adoption grade only when the question is an adoption question.
3. `agreements`: the points that hold across the council.
4. `divergences`: resolved and open disagreements, with the resolution reason when available.
5. `evidence`: round timeline, seat table, effective model receipts, and source paths.
6. `confidence`: separate answer and diversity confidence. Show `Not reported` when the source does not contain a value.
7. `next-step`: one action with an owner or target when the source gives one.
8. `limits`: missing evidence, omitted seats, open questions, and the limits of the run.

The page must work at three depths:

* **Glance:** the hero shows the question, status, verdict, and next step.
* **Scan:** cards and the round timeline show agreements, divergence, seats, and confidence.
* **Descend:** expandable details show source paths, resolution notes, and compact round evidence.

Visual rules:

* Keep the first screen focused. Use a dark, high-contrast layout with one accent for positive agreement, one for caution, and one for open divergence.
* Use CSS and inline SVG only. Do not add a build step, a remote script, a tracking pixel, or a required network resource.
* Use bars or rings only for values present in the source. A visual must not imply precision that the council did not report.
* Keep cards short. Put long text in `<details>` panels. Do not paste the raw transcript.
* Mark status with text as well as color. The page must remain understandable in grayscale and on a narrow screen.
* Keep all source labels readable, such as `report.md`, `state.json`, or `round-2-digest.md`. Use relative links only when they work from the output directory.

Language follows the user's request. For English, use ASD-STE100 Simplified Technical English. For Portuguese, use Brazilian Portuguese in simple language. Keep names, paths, enum values, and quoted council text unchanged when they are evidence.

### 4. Verify the artifact

Run the validator after assembly. Set `SKILL_DIR` to the absolute directory that contains this `SKILL.md` in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>"; python3 "$SKILL_DIR/scripts/validate_consensus_summary.py" <output-file.html>
```

Fix every reported error. The validator checks the required section ids, the separate confidence fields, the seat table, the single next step, local self-containment, and leftover template tokens.

When a browser is available, open the file directly and check the decision surface at desktop and narrow widths. Confirm that the expand and collapse controls work, that each navigation link reaches a real section, and that open divergence remains visible. If no browser is available, report that the mechanical check passed but visual inspection was not available.

### 5. Deliver

Return the absolute output path first. Then report the council status, the verdict, the next step, the validation command and result, and any part that could not be visually checked. Do not claim that the page is final when the council status is not `complete`.

## Output contract

The output is one self-contained HTML file. It must include:

* the default file name pattern `<session_id>-summary.html` beside a persisted report, or `<slug>-summary.html` under `docs/consensus/` for inline results;

* a `title`, `lang`, charset, and viewport;
* one visible question heading and one visible status label;
* all eight section ids listed above;
* exactly one element with `data-role="next-step"`;
* `data-role="answer-confidence"` and `data-role="diversity-confidence"`, each with a value or `Not reported`;
* a seat table with at least one row, even when the only row says that seat data was not reported;
* at least one source label and an explicit evidence gap when source detail is missing;
* no `<!-- SLOT` comments, `{{...}}` tokens, `TODO`, `Replace with` text, or external script or stylesheet dependency.

This is the **acceptance contract**: the validator exits 0, the page opens as a local file without a server, the first screen contains the verdict, and the reader can reach the agreements, divergences, evidence, confidence, next step, and limits sections from the page navigation.

## Gotchas

* Agreement is not proof of independence. Preserve shared-provider and self-paired notes.
* A council with one seat is not a multi-model consensus. Show the reduced diversity confidence.
* A high answer confidence does not repair a low diversity confidence.
* Do not turn an open divergence into a resolved card because a recommendation exists.
* Do not invent percentages, seat names, source links, or a resolution reason.
* Do not use a raw model request name as an effective model receipt.
* Do not use the HTML page to conceal a malformed or unavailable seat. An **observable failure** is part of the result.
