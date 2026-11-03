# Page contract

`assets/report.html` is the template; `examples/example-report.html` is a filled, passing example. Copy the template, replace every `<!-- SLOT -->` and `{{...}}`, and keep the hooks below: `scripts/validate_review.py` reads them. Page-level rules (self-containment, three depths, escaping, `Not reported` for missing data) are in `shared/references/html-page-conventions.md`.

## Sections

Nine sections in this order, ids fixed:

| id | Holds |
| :--- | :--- |
| `sec-verdict` | The central decision, status counts, decisions needed, links to P0/P1 findings and first moves. Answers the reader's question on the first screen. |
| `sec-context` | Purpose and constraints, each marked observed, declared, or assumed; revision and coverage; Quality Attribute Scenarios; assumptions and open questions. |
| `sec-architecture` | An inline SVG of the implemented structure, then the main read, main write, and one failure or integration flow. |
| `sec-dimensions` | All 20 rows, D01 to D20. |
| `sec-findings` | One `article.finding` per finding, by priority. |
| `sec-strengths` | Working mechanisms to preserve, and documented decisions the review respects. |
| `sec-options` | Options, the target, and its guardrails. |
| `sec-roadmap` | Steps, at most three marked `data-first-move`. |
| `sec-evidence` | Evidence register, verification, glossary, and any folded-in review. |

## Hooks the validator checks

- **Dimension row:** `tr.dim#Dnn` with `data-status` (`adequate`, `attention`, `critical`, `unknown`, `not_applicable`) and `data-confidence` (`high`, `medium`, `low`, `unknown`), the status repeated as text, and the title from `assets/dimensions.json`. A rated status links an evidence record; unknown and not applicable fill `.d-note` with the reason. Unknown cannot carry high confidence. A critical dimension needs a P0 or P1 finding.
- **Finding:** `article.finding#Fnn` with `data-priority`, `data-confidence`, `data-dimension`, and `data-leitwort`, plus non-empty `.f-decision`, `.f-observation`, `.f-impact`, `.f-recommendation`, `.f-when-not`, `.f-acceptance`, `.f-rollback`, and an `.f-evidence` that links at least one record. The anchor named in `data-leitwort` appears in the decision and again in the recommendation or acceptance.
- **Evidence record:** `tr.evidence#Ennn` with `data-kind` (`code`, `config`, `documentation`, `measurement`, `user_input`, `inference`, `hypothesis`). Code and config cite `<code class="loc">path:line</code>` or `path:start-end`, relative to the repository; `--repo` confirms the file and line range. A measurement gives its exact command in `<code class="cmd">`.
- **Option:** `article.option` with `data-kind` (`keep`, `incremental`, `structural`) and `data-position` (`recommended`, `conditional`, `rejected`). One option keeps the current architecture; at most one is recommended.
- **Verification:** `tr.check` with `data-status` (`pass`, `fail`, `not_run`, `blocked`, `not_applicable`). When any P0 or P1 finding exists, one row has `data-check="challenge"`.
- Every `href="#..."` and `jump('...')` target exists, ids are unique, and no secret-shaped string appears.
- Keep the template's Content-Security-Policy and its single inline script. Write repository text as escaped text, never as markup: the only event handlers are the template's `jump`, `setAll` and `filterPriority` calls, and URLs are only fragments, relative paths, `https:` or `data:image/`.

The validator proves structure, not judgment. It cannot tell whether a finding is right or whether a cited line says what the finding claims; the challenge pass does that.

## Writing the finding

Write the causal chain: existing behavior and where it lives, consequence, affected requirement, the smallest useful change and what it adds, the alternatives including doing nothing, an externally checkable acceptance criterion ("a test that times out the provider after capture ends with one paid order", never "cleaner architecture"), rollback, and when not to act. `.f-summary` comes first on the card: one-sentence problem, one-sentence change, wins as short phrases. Add, when they apply: the seam's dependency category, a linked incident or fix commit, the respected decision it conflicts with, and the status on a newer upstream ref.

**Priority:** P0 is demonstrated urgent severe harm; P1 substantiated high risk; P2 justified improvement, or an investigation where the problem is uncertainty; P3 optional. P0 and P1 need direct evidence and high or medium confidence. Priority, confidence, and effort are independent. Taste and weak hypotheses are never P0 or P1. A finding already fixed on the newer ref is reported as fixed upstream and cannot stay P0 or P1.

**Confidence:** high needs direct evidence with counterevidence considered; medium allows a supported inference or incomplete inspection; low is provisional. These are labels, not probabilities.

## Evidence

Prefer relative paths and short sanitized excerpts, escaped as the page conventions require. Separate observed fact, executed measurement, declared information, inference, and hypothesis. An inference names the records it rests on; a hypothesis carries the experiment that would test it. A proposed command was not executed. An absence claim states the exact search and its scope: "not found in the sample" is not "absent everywhere". Literature never substitutes for repository evidence.

## Diagrams

Draw what the code shows, with source dependencies and runtime calls as separate views; a source import is not a network call. Mark proposed elements `class="proposed"` (dashed) and label them. Keep each view to roughly 5 to 12 boxes and split larger graphs. Give clickable boxes `onclick="jump('F..')"` to their finding. A before-and-after pair for one finding is two diagrams. Never invent a component to complete a picture.

## Metrics and targets

Mark each number measured, declared, estimated, or unknown, and each target agreed or proposed. Unknown is `Not reported`, never zero. Do not chart incomparable runs or describe an untested proposal as a measured improvement. Quote the counting convention `measure.py` reports with every number it produced.

## Target and guardrails

When structure should change, the target lists modules with what each owns, its interface, and its allowed dependencies; the rules with their status today; and the trade-offs, with rejected options and reasons. Back each rule with a guardrail (an import contract, AST test, or other fitness function) that fails only on new violations against a named baseline that can only shrink, with a sketch for any proposed check.

## Publishing

The file opens from disk. Publishing it on a shared host distributes it; findings about exploitable weaknesses stay private unless the owner decides otherwise.
