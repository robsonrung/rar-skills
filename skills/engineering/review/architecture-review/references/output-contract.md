# Report output contract

## Deliverables and workflow

`audit.json` is the structured source. `report.html` is the self-contained visual report. `evidence.jsonl` preserves the system evidence register. `verification.md` records procedures and results. An optional `inventory.json` contains repository metadata. Store outputs in a permitted directory outside the product tree by default; never overwrite an existing audit.

Validate the JSON before rendering. The renderer performs no network access and installs no dependencies. For the same validated input and package version, generated content is deterministic. Neither schema validation nor rendering proves that the architectural diagnosis is correct.

After rendering, check cross-references, evidence, source links, observed versus proposed views, absence of secrets, readability, and consistency between executive summary and details. Where a browser is available, test desktop and narrow layouts, search, priority filters, keyboard access, disclosure controls, SVG diagrams, and print layout. Record unavailable checks as not run.

## Version and language

This package uses schema version `2.0` and language `en`. Version 2.0 adds finding decision anchors and `concept_applications`. Version 1.0 reports require explicit migration: translate all narrative, retain evidence provenance, add and review the new decision fields, and change the version only after the record is complete. Do not silently relabel an old file as version 2.0.

All human-readable content is English. Preserve real identifiers, paths, commands, and source titles. Technical hyphenation and syntax remain intact. Avoid decorative dash punctuation in prose.

## Required groups

| Field | Contents and rules |
| :--- | :--- |
| `schema_version`, `language` | `2.0` and `en`. |
| `meta` | System, date, revision, execution mode, demo flag, scope, coverage, exclusions, limitations. Identify commit and dirty worktree when relevant. |
| `context`, `questions` | Context facts with origins and evidence; material unanswered questions only. |
| `verdict` | Current adequacy, future limits, confidence, and evidence. Keeping the design or withholding judgment are valid conclusions. |
| `dimensions` | Exactly D01 through D20, once each, with canonical title, status, confidence, explanation, and evidence. |
| `strengths` | Concrete working mechanisms worth preserving, supported by evidence. |
| `findings` | Actionable observations with the complete finding contract below. |
| `concept_applications` | Decision checkpoints that connect canonical terminology to evidence, an action, and verification. |
| `scenarios` | Relevant quality requirements: stimulus, environment, response, target, observation, status, and evidence. Include stimulus source and artifact in the stimulus/description where needed. |
| `diagrams`, `diagram_gaps` | Current and proposed views with provenance, plus views that could not be reconstructed. |
| `options` | Include `keep`; at most one `recommended`; other positions are `conditional` or `rejected`. |
| `roadmap` | Steps, actions, responsible role, relative effort, dependencies, acceptance, rollback, and related findings. No dependency cycles. |
| `agent_checks` | Capability, method, status, result, and evidence, separate from static legibility. |
| `metrics` | Values, targets, units, provenance, environment, and evidence. Use null for unknown numbers, not zero. |
| `capacity`, `cost` | Supported conclusion, assumptions, missing measurements, and a capacity reassessment trigger. |
| `evidence` | System sources with location and revision. Literature belongs in `sources`. |
| `sources` | Applied references only: ID, title, author, URL, application, access level, and check date. |
| `verification` | Procedures, status, exit code, environment, artifact, date, and notes, including material blocked/not-run procedures. |
| `decisions_needed`, `glossary` | Outstanding business/team decisions and relevant canonical definitions. |

Lists may be empty where allowed by the schema; explain material omissions. Item IDs must be unique across sections. Use E for evidence, F for findings, S for strengths, Q for scenarios, G for diagrams, O for options, R for roadmap, A for agent checks, M for metrics, V for verification, and C for concept applications. D01 through D20 are fixed. B/W IDs refer to bibliography records. Term IDs L/T are catalog references, not report navigation IDs.

## Status, confidence, and priority

Dimension statuses: `adequate`, `attention`, `critical`, `unknown`, `not_applicable`. Confidence: `high`, `medium`, `low`, `unknown`. Unknown quality cannot have high confidence merely because the absence of evidence is certain. Not applicable needs an actual reason.

P0/P1 findings require substantiated risk, direct evidence, and sufficient confidence. P2 can be an investigation where the problem is uncertainty, not demonstrated failure. P3 is optional improvement. Priority is independent of implementation effort and confidence.

Do not produce an arbitrary overall score, quality percentages, radar values, or averages that hide a critical risk. A status chart counts dimensions; it does not measure system performance. Inspection coverage, quality, and confidence are different.

## Finding contract

Required fields: `id`, `dimension`, `title`, `priority`, `confidence`, `leitwort`, `decision_statement`, `observation`, `impact`, `recommendation`, `tradeoff`, `alternatives`, `effort`, `why_now`, `when_not`, `validation`, `acceptance`, `rollback`, `evidence`, `sources`.

`leitwort` refers to an ID in `assets/terms.json`. `decision_statement` names its exact canonical term, then connects the observation to a decision. Repeat the term in at least one of `recommendation`, `validation`, or `acceptance`. A corresponding applied `concept_applications` record must link the finding and use the same term.

Write the causal sequence: existing behavior, consequence, affected requirement, smallest useful change, added cost, alternative, observable improvement, and reversal. State relative effort with its basis and uncertainty. `when_not` explains when the change is not justified. Acceptance must be externally checkable, not “cleaner architecture.”

## Concept application contract

Fields: `id`, `term_id`, `status`, `decision`, `action`, `verification`, `evidence`, `sources`, `related_findings`.

`status` is `applied`, `unknown`, or `not_applicable`. `decision` includes the exact canonical term. An applied decision needs evidence and repeats the term in `action` or `verification`. Unknown and not applicable decisions explain the gap or reason and identify the evidence needed or simpler option preserved. They must not masquerade as applied support for a finding.

Do not create an entry for every term merely to fill the catalog. Include the material concepts that affect an assessment, plus explicitly important applicability decisions. The renderer shows their definitions, decisions, actions, verification, and linked evidence. Definitions come from the canonical catalog, not conflicting copies in the data.

The validator checks catalog membership, structural completeness, references, and literal recurrence. It cannot prove semantic correctness or reject every cosmetic use. The critical review must check that the term actually changes the action or verification.

## Evidence contract

Kinds: `code`, `config`, `documentation`, `measurement`, `user_input`, `inference`, `hypothesis`, `demo`.

Every record contains `location`, `revision`, `line_start`, `line_end`, `observation`, `captured_at`, `environment`, `command`, `artifact`, and `supports`. Nullable fields use null. Code/config records require actual relative paths and verified lines at the stated revision. Documents need section and version. Measurements need the exact procedure, date, environment, workload, units, and sanitized result artifact; a stakeholder's number is declared until its collection is available.

Derived inferences identify supporting evidence and limitations, without self-reference or cycles. Hypotheses remain hypotheses with a proposed experiment. Demo evidence is allowed only when `meta.is_demo` is true. Literature is never substituted for repository evidence.

Absence requires adequate search coverage. “Not found in the sample” is not “absent everywhere.” Sanitize sensitive evidence and disclose limits on reproducibility; never put private code or credentials into public URLs.

## Diagrams

Views: `context`, `component`, `dependency`, `sequence`, `deployment`, `data`. States: `observed`, `proposed`, `demo`. Prefer a context view, component/layer/interface view, main flow, and failure flow; add deployment, ownership, Context Map, or trust boundaries when they change a conclusion. Do not invent components to complete a diagram.

Each node has `id`, `label`, `detail`, `col`, `row`, `kind`, and `evidence`. Integer columns run from 0 through 5 and rows from 0 through 15; one node per cell. Kinds: `actor`, `ui`, `service`, `domain`, `data`, `external`, `worker`. Keep labels short; accessible tables retain full text. Split extensive graphs into smaller views, typically 5 to 12 nodes.

Edges have `from`, `to`, `label`, `kind`, `basis`, and `evidence`. Kinds: `sync`, `async`, `dependency`. Bases: `observed`, `inferred`, `proposed`, `demo`. Source dependency is not runtime control flow or data flow. A background worker can still issue synchronous HTTP requests. Do not label a dependency edge as proof that data traverses it.

Explain protocol, contract, direction, exchanged data, authorization, transaction boundary, and relevant failure behavior. Sequence views use numbered flow steps, not formal UML lifelines. Represent return steps explicitly instead of unsupported self-edges.

Observed and inferred edges require evidence. Proposed topology stays labeled proposed even when it reuses actual components. Diagrams use deterministic local SVG and accessible tables, without Mermaid or external rendering services. The views are informed by C4 questions, not certified as formal notation.

## Metrics and capacity

Current kinds: `measured`, `declared`, `estimated`, `unknown`. Target kinds: `agreed`, `proposed`, `unknown`. Unknown means null. Measured values require measurement evidence. Distinguish agreed targets from suggestions.

Provide percentiles, throughput, concurrency, errors, saturation, data volume, and cost only with provenance. Do not chart incomparable runs or describe an untested proposal as measured improvement. Registered users and active sessions cannot be converted into RPS without explicit assumptions.

## Verification and script limits

Verification and agent-check statuses: `pass`, `fail`, `not_run`, `blocked`, `not_applicable`. Not-run procedures have null exit codes; passed procedures have zero. Scenario statuses: `verified`, `failed`, `unknown`, `proposed`. Agent success needs task artifacts and observed final state, not an AGENTS.md file.

The Python tools use only the standard library. The validator implements the keywords used by this package and additional semantic/reference checks, not arbitrary JSON Schema. It cannot prove that a source exists, a command ran, or a judgment is correct.

Inventory is metadata-only, does not read source contents, follow symlinks, or execute the project. Conservative exclusions may hide relevant files; disclose scope. The renderer escapes report content rather than evaluating it. These precautions do not create a sandbox or replace execution authorization.
