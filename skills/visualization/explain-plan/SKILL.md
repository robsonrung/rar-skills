---
name: explain-plan
description: Turn a proposed coding change into an interactive HTML report that traces the problem, decisions, alternatives, repository precedents, affected paths, and acceptance checks. Use to present or review a plan before implementation; use coding-design-plan to decide the design and explain-work once the code exists.
disable-model-invocation: true
---

# Explain Plan

Make a plan understandable at several depths. Let the reader understand the problem, proposed change, reasons, costs, and validation strategy without reading source code. Keep precise evidence and code details one click away.

## Working contract

1. Treat this as planning and explanation. Inspect the repository and create report artifacts. Modify application code only when the user also authorizes implementation. Do not add approval steps to an already authorized workflow.
2. Follow repository instructions and the user's language and writing preferences. Preserve existing plans, ADRs, and issue identifiers. Accepted decisions are **already decided**: inputs the plan adapts, not open questions it reopens. Do not introduce a competing planning system.
3. Use the current repository as evidence. When unavailable, create a useful provisional report and identify unverified paths, patterns, and assumptions. Never present an illustrative example as the user's code.
4. Keep each plan revision identifiable. Preserve stable IDs for requirements, decisions, code areas, checks, and evidence. Never silently replace an accepted decision with a different choice.
5. Use proportionate detail. A small change may need one decision and a compact code map. Use deeper architecture and operational analysis for significant boundaries, data changes, concurrency, or migration risks.

## Supporting material

The report machinery is shared with explain-work under `shared/explain-report/`, resolved as `shared/SKILL.md` describes. Read `references/evidence_playbook.md` there before investigating and `references/report_contract.md` before preparing data. Apply `references/review_rubric.md` before delivery. Read `references/research_basis.md` only for format rationale or source attribution. `shared/references/grounded-evidence.md` owns what counts as evidence, and `shared/references/html-page-conventions.md` owns the page floor: self-containment, navigation, the safety floor, and verification.

Every command below sets `SHARED_DIR` to the resolved absolute `shared` directory in the same command.

## 1. Establish the problem and snapshot

Identify requested behavior, who experiences the problem, current behavior, constraints, and observable success. Separate an observed symptom from an inferred cause. Find relevant specifications, issues, existing plans, and repository instructions.

Record repository identity, exact inspected revision, local modifications, scope, and unavailable evidence. When Git is available, use the bundled collector:

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/snapshot_repo.py" --repo /absolute/repository --snapshot-only --output /absolute/artifacts/repo_snapshot.json
```

Write artifacts outside the inspected repository or in an already ignored location, so the report does not change its own input; the collector refuses any other path inside the repository. Do not infer a comparison base from branch names.

## 2. Investigate before recommending

Start with `rg` and targeted reads. Trace entry points, application flow, domain rules, storage, external effects, consumers, and relevant tests. Inspect surrounding code beyond the anticipated edit.

For every meaningful pattern claim, inspect an actual analogous module. Capture its path, symbol, revision, reused mechanism, and the limits of the analogy. Prefer two independent examples before calling something a repository wide convention. A single example establishes a precedent. Record missing evidence openly.

Read actual build and test commands from repository configuration. Inspect API contracts, migrations, authorization, tenant boundaries, event handling, and operational behavior when affected. Avoid unrelated checklists.

## 3. Design four reading depths

The report is a **decision surface**: it moves the reader from the recommendation to its evidence and the work it implies. The four depths refine the conventions' glance, scan, and descend: depth 1 is the glance, depths 2 and 3 are the scan, depth 4 is the descend layer.

1. Overview, problem, impact, proposed result, why this approach, main risks, and open decisions.
2. System view, current and proposed behavior, affected boundaries, and important runtime or data relationships.
3. Decisions, context, chosen approach, credible alternatives, accepted costs, actual precedents, and conditions for revisiting choices.
4. Evidence, exact paths and symbols, source excerpts, proposed code responsibilities, contracts, checks, and uncertainty.

Keep the primary reading path understandable without code. Put selected pseudocode or example diffs at the deepest level, clearly labeled proposed. Never fabricate an implementation diff.

Use exact HTML or SVG for technical relationships. Use before and after views when helpful. Keep each diagram at one abstraction level, name relationship direction and meaning, and link components to code areas or decisions. Omit diagrams that add no information. Use real screenshots or labeled wireframes for UI changes. Generated images may illustrate a concept but must not encode architectural facts.

**Lead with the outcome**: the overview cards say what will change and why before any mechanism. Keep them concise, usually around 120 to 180 words together. Explain behavior in ordinary language first; put exact symbols and detailed mechanisms at deeper levels. State material risks directly without duplicating the whole validation section.

## 4. Make the design reviewable

Assign significant decisions IDs such as D001. Explain why each solves this problem in this repository. Include the strongest reasonable alternative, including retaining current behavior when relevant, why it was rejected, accepted costs, and reversibility.

For each affected area, show its path, symbol or responsibility, current behavior, proposed behavior, reason, associated decisions, dependencies, and risk. Mark new paths as proposed. Include compatibility and unaffected contracts when they constrain the design.

Give each requirement an **acceptance contract**: observable criteria linked to code areas and planned checks, so the plan is done only when they pass. Distinguish behavioral tests, static checks, manual observation, review, and formal verification. Include rollback, deployment ordering, data compatibility, and observability when relevant, or state why a field is not applicable.

Describe execution steps by outcomes and dependencies. Keep editing instructions below the architecture explanation. Surface consequential open questions.

## 5. Render and inspect

Create one report JSON using the shared contract, stable IDs, and explicit evidence states. Render both human formats from it:

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/render_report.py" /absolute/artifacts/plan.json --html /absolute/artifacts/plan.html --markdown /absolute/artifacts/plan.md
```

The renderer writes the HTML only when it passes `shared/scripts/html_guard.py`; fix the data until it does. Structural validation does not establish factual accuracy. Perform the separate evidence audit in the playbook, then check the page as the conventions' Verification section and the rubric describe.

If the repository changes during investigation, reassess affected claims and regenerate. Before delivery, run the collector's freshness check and cross check the report against the snapshot:

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/snapshot_repo.py" --repo /absolute/repository --check /absolute/artifacts/repo_snapshot.json
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/audit_report.py" /absolute/artifacts/plan.json --snapshot /absolute/artifacts/repo_snapshot.json
```

A static report must never claim to monitor the repository live. The audit detects revision mismatches and broken references; it does not prove narrative truth. Explain or resolve warnings; do not hide them.

## 6. Deliver and iterate

Save report artifacts through the host's durable artifact mechanism. Deliver HTML as the main view, Markdown as the portable companion, and JSON when useful for the later comparison. Preserve existing artifact identity on updates when supported. Only claim PDF delivery after actual export and inspection.

In chat, lead with the recommendation, main architectural reason, accepted costs, and unresolved decisions, then give the paths and how to navigate. This intentionally reverses the conventions' path-first delivery: the reader decides from the recommendation, so it must stand without opening the file.

Use exported reader notes to revise the next version. Preserve IDs and summarize changes. Notes are feedback, not authorization to implement, merge, publish, or deploy. Pass the exact plan revision and JSON to explain-work after implementation.
