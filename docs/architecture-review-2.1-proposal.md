# architecture-review 2.1: proposal and change record

Status: implemented on branch `architecture-review-2.1`, not committed
Date: 2026-09-27
Scope: `skills/engineering/review/architecture-review`, plus one CI step and one leitwort guard

## Why

The same private system (a FastAPI and Celery pricing product) was reviewed three ways on the same days:

1. **This skill (2.0).** 20 dimensions, 36 findings across three revisions, an evidence register, and an independent challenge pass.
2. **A free-form prompt** asking for a module-quality review of the backend, with scores for six qualities, a target architecture and guardrails.
3. **Matt Pocock's `improve-codebase-architecture` skill**, built on his `codebase-design` vocabulary.

The comparison showed what 2.0 does well and where it fell short:

- **Strengths to keep:** breadth, evidence discipline, and the only P0/P1 findings on security, data, recovery and operations.
- **Stale checkout:** the review ran on a checkout 11 commits behind upstream and learned this halfway through. One defect already fixed upstream reached the published report, because only P0/P1 findings were rechecked.
- **No measurement toolkit:** each explorer wrote throwaway scripts, and two runs disagreed on the same metric (765 versus 1,023 in-function imports) only because of counting conventions.
- **Hand-written evidence:** about 330 evidence records were written by hand, and line ranges were bounds-checked with an ad hoc script.
- **Weak on module design:** the other two reviews found the costliest design problems, which 2.0 had no step for. They were all one concept spread across many places:
  - a job identity declared in 8 places, the cause of a production bug fixed in #322;
  - a status written by 5 modules;
  - a pause rule copied 5 times with different failure behavior;
  - a safety gate called from unguarded places;
  - 1,424 test path pins that dictate the order of any file move.
- **No target or guardrails:** there was no target architecture, no guardrails, no implementation safety notes, and no "first three PRs".
- **Hard to scan:** 30-plus findings, each with 20 fields, were hard to scan compared with Pocock's one-line problem, solution and wins.
- **Publishing gaps:** the renderer had no dark mode, used a long title, and kept a print button, so publishing as an artifact needed manual patches.
- **Manual merging:** folding the other two reviews in was done by hand twice, with no procedure.

## What changed

| Change | Files | Evidence it addresses |
| :--- | :--- | :--- |
| Revision check before reading: ahead/behind against upstream, uncommitted files, optional `git archive` export of the newer ref; every P0 to P2 finding records `newer_ref_status`, and a finding fixed upstream cannot stay P0/P1 | `scripts/revision_check.py`, `SKILL.md` step 2, `workflow.md`, schema, validator | Stale checkout; upstream-fixed defect in a published report |
| Measurement toolkit with stated counting conventions: `imports` (module, in-function and TYPE_CHECKING edges, cycles, fan-in/out, instability), `writers`, `history` (churn, co-change, fix commits), `test-pins`, `endpoints`, `callers`, `occurrences` | `scripts/measure.py`, `workflow.md` | Ad hoc scripts; convention disagreements. On the reviewed repository it reproduced the manual numbers: a 140-module hidden cycle, 8 writers for two shared tables, 485 endpoints, 1,419 test pins, 3 guard-relaxing callers |
| Evidence assembly from worker JSON lines (IDs, `supports` mapping, deduplication, file, line and excerpt checks) and `validate_report.py --repo` | `scripts/evidence_tool.py`, validator, optional `excerpt` field | Hand-written evidence; ad hoc bounds checks |
| Module design lens: deletion test, leverage, locality, adapter (one is hypothetical, two is real), dependency category, design it twice; tests that cross past an interface; three investigations (concept duplication, safety-critical callers, refactor cost) | `references/module-design.md`, `rubric.md` D02 to D04, D13 and D19, six new terms T69 to T74, sources W21 to W23 | The design findings 2.0 missed |
| Respected decisions, target architecture (modules, rules with status and enforcing guardrails, trade-offs with rejected options), guardrails with baseline strategy and sketches, `must_preserve` and `first_move` on roadmap steps | schema 2.1, renderer, `SKILL.md` step 5, `output-contract.md` | The prompt-driven review's strongest sections |
| Scannable findings: `summary` (problem, solution, short wins), `dependency_category`, `incident`, `adr_conflict` badges and callouts | schema, renderer | Readability; links to real incidents |
| Structured challenge pass with a refutation brief and a newer-ref check, recorded in verification | `workflow.md`, `SKILL.md` step 7 | In the real run it changed 5 of 9 priorities |
| Routing and delegation: model preview line, route mapping, native-first workers, packets that return facts only, and external runners counted as uploads | `SKILL.md`, `workflow.md` | Earlier audit of this skill (routing gap, privacy conflict) |
| Folding in other reviews (`external_reviews`) and comparing audits | `scripts/compare_audits.py`, `workflow.md`, schema | Two manual merges |
| Light and dark themes through tokens; `--artifact` mode (short title, no skeleton, no print control) | `assets/report.html`, renderer | Manual patching before publishing |
| Follow-up offers: design it twice, grilling, record a rejection as an ADR, glossary gaps | `module-design.md`, `SKILL.md` step 9 | Pocock's follow-up loop |
| Seven new behavioral cases EV27 to EV33 | `evals/cases.json` | One per failure above |
| Selftests run in CI; leitwort guard for this skill | `.github/workflows/skill-guards.yml`, `leitworter.json` | Previously no CI coverage |

Schema 2.1 is backward compatible: a 2.0 report still validates, and any 2.1 field requires `schema_version: "2.1"`. Selftests grew from 64 to 91, all passing.

## What was deliberately not adopted

- **Tailwind and Mermaid from a CDN, as Pocock's report uses.** The report stays offline and self-contained. Artifact hosts render Mermaid natively if it is ever needed.
- **Pocock's ban on "boundary", "component" and "service".** This skill needs Bounded Context and the component principles. The new terms sit beside them with an explicit mapping, and a seam is never a Bounded Context.
- **Scores from 1 to 5 per quality, as the prompt-driven review used.** 2.0 rejects overall and quality scores on purpose. Dimension statuses with one-line reasons carry the same information without implying precision.
- **"Strength only" candidates without priorities or evidence IDs.** Priority, confidence and evidence stay mandatory.
- **Proposing interfaces inside the report.** As in Pocock's skill, interface design waits for a follow-up (design it twice) that the user starts.

## Not done yet

- The automated browser suite (`evals/browser-results.json`) and the screenshots were not re-run for 2.1. Only a manual check in both themes was done.
- None of EV01 to EV33 has been executed end to end. The claim that these changes improve review quality is a hypothesis until a bounded comparison runs the old and new skill on one fixture repository.
- `measure.py writers` and `callers` are Python-only; JavaScript import resolution ignores path aliases.
- The installed copy in `~/.agents/skills/architecture-review` is unchanged until `scripts/install-skills.sh` runs.

## Possible follow-ups for the source skills

The research also suggests changes that belong upstream in Pocock's skills, offered here as notes rather than edits:

- **`improve-codebase-architecture`:**
  - record which revision was scanned, and whether it lags its upstream;
  - attach evidence locations to each candidate so a later session can re-verify it;
  - add an explicit "ambiguous external outcome" question alongside the friction questions.
- **`codebase-design`:**
  - name the concept-duplication count (declarations, writers, state changes) as a companion to the deletion test, because it is how the strongest candidates were found in practice.
