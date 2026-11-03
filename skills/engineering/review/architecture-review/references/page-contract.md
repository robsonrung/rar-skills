# Page contract

You write `review.json`; `scripts/render_review.py` turns it into the page. The schema is `SHAPE` in `scripts/validate_review.py` (a key ending in `?` is optional), and `examples/example-review.json` is a complete, passing review. Every value is plain text: the renderer escapes it, turns `` `code` `` into inline code, and links any known `E…`, `F…`, or `Q…` id. Markup in a value shows as literal text. Page-level rules (three depths, `Not reported` for missing data, the safety floor) are in `shared/references/html-page-conventions.md`.

## Sections

One top-level key per section; the renderer fixes the order and ids:

| Key | Holds |
| :--- | :--- |
| `verdict` | The central decision, decisions needed, and the P0/P1 findings and first moves in `top`. The renderer adds the status counts. Answers the reader's question on the first screen. |
| `context` | Purpose and constraints, each marked observed, declared, or assumed; revision, coverage, exclusions; Quality Attribute Scenarios (numbered Q1, Q2, ...); assumptions and open questions. |
| `architecture` | Diagrams of the implemented structure, then the main read, main write, and one failure or integration flow. |
| `dimensions` | All 20 rows, D01 to D20, in order. |
| `findings` | One item per finding; the renderer orders them by priority. |
| `strengths` | Working mechanisms to preserve, and documented decisions the review respects. |
| `options` | Options, the target, and its guardrails. |
| `roadmap` | Steps, at most three with `first_move`. |
| `evidence` | Evidence register, verification checks, glossary. |

## What the validator checks

- **Dimension row:** `status` (`adequate`, `attention`, `critical`, `unknown`, `not_applicable`) and `confidence` (`high`, `medium`, `low`, `unknown`). The renderer adds the title from `assets/dimensions.json`. A rated status cites an evidence record; every row gives its assessment or the reason it is unknown or not applicable in `note`. Unknown cannot carry high confidence. A critical dimension needs a P0 or P1 finding.
- **Finding:** `id` (`F01`, ...), `priority`, `confidence`, `dimension`, and `anchor`, plus non-empty `title`, `summary`, `decision`, `observation`, `impact`, `recommendation`, `when_not`, `acceptance`, `rollback`, and at least one cited record. `alternatives` is optional. The decision anchor appears in the decision and again in the recommendation or acceptance.
- **Evidence record:** `id` (`E001`, ...) and `kind` (`code`, `config`, `documentation`, `measurement`, `user_input`, `inference`, `hypothesis`). Code and config give `locations` as `path:line` or `path:start-end`, relative to the repository; `--repo` confirms the file and line range. A measurement gives its exact `command`. Other kinds name their `source`.
- **Option:** `kind` (`keep`, `incremental`, `structural`) and `position` (`recommended`, `conditional`, `rejected`). One option keeps the current architecture; at most one is recommended.
- **Verification:** each check has `status` (`pass`, `fail`, `not_run`, `blocked`, `not_applicable`). When any P0 or P1 finding exists, one check has `"challenge": true`.
- Every cited id exists, and the rendered page passes `html_guard` (no secret-shaped string, among others).

The validator proves structure, not judgment. It cannot tell whether a finding is right or whether a cited line says what the finding claims; the challenge pass does that.

## Writing the finding

Write the causal chain: existing behavior and where it lives, consequence, affected requirement, the smallest useful change and what it adds, the alternatives including doing nothing, an externally checkable acceptance criterion ("a test that times out the provider after capture ends with one paid order", never "cleaner architecture"), rollback, and when not to act. `summary` comes first on the card: one-sentence problem, one-sentence change, wins as short phrases. Add, when they apply: the seam's dependency category, a linked incident or fix commit, the respected decision it conflicts with, and the status on a newer upstream ref.

**Priority:** P0 is demonstrated urgent severe harm; P1 substantiated high risk; P2 justified improvement, or an investigation where the problem is uncertainty; P3 optional. P0 and P1 need direct evidence and high or medium confidence. Priority, confidence, and effort are independent. Taste and weak hypotheses are never P0 or P1. A finding already fixed on the newer ref is reported as fixed upstream and cannot stay P0 or P1.

**Confidence:** high needs direct evidence with counterevidence considered; medium allows a supported inference or incomplete inspection; low is provisional. These are labels, not probabilities.

## Evidence

Prefer relative paths and short sanitized excerpts. Separate observed fact, executed measurement, declared information, inference, and hypothesis. An inference names the records it rests on; a hypothesis carries the experiment that would test it. A proposed command was not executed. An absence claim states the exact search and its scope: "not found in the sample" is not "absent everywhere". Literature never substitutes for repository evidence.

## Diagrams

Draw what the code shows, with source dependencies and runtime calls as separate `diagrams`; a source import is not a network call. Each node sits on a grid (`col`, `row`, 0 to 12) and an edge joins two node ids. Mark proposed nodes and edges `"proposed": true` (dashed) and say so in the label. Keep each view to roughly 5 to 12 boxes and split larger graphs. A node with `finding` jumps to that finding when clicked. A before-and-after pair for one finding is two diagrams. Never invent a component to complete a picture.

## Metrics and targets

Mark each number measured, declared, estimated, or unknown, and each target agreed or proposed. Unknown is `Not reported`, never zero. Do not chart incomparable runs or describe an untested proposal as a measured improvement. Quote the counting convention `measure.py` reports with every number it produced.

## Target and guardrails

When structure should change, the target lists modules with what each owns, its interface, and its allowed dependencies; the rules with their status today; and the trade-offs, with rejected options and reasons. Back each rule with a guardrail (an import contract, AST test, or other fitness function) that fails only on new violations against a named baseline that can only shrink, with a sketch for any proposed check.

## Publishing

The file opens from disk. Publishing it on a shared host distributes it; findings about exploitable weaknesses stay private unless the owner decides otherwise.
