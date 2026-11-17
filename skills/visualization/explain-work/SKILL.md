---
name: explain-work
description: Explain completed coding work as an interactive HTML report of what was built, why, how it departs from the plan, and what evidence supports it. Use after implementation; use explain-plan before it and full-review for a defect audit.
disable-model-invocation: true
---

# Explain Work

Explain what was actually built, why it takes this shape, how it differs from the plan, and what evidence supports its behavior. Organize around decisions and behavior so the reader can understand it without reading the diff.

## Working contract

1. Treat this as implementation explanation. Inspect changes and existing validation results. Run relevant local checks when safe and authorized. Do not change implementation or reconcile review threads unless requested.
2. Keep explanation distinct from independent correctness review. If an audit is also requested, run `full-review` and link its actual findings and reviewed revision.
3. Follow repository instructions and user preferences. Preserve existing specifications, plans, ADRs, and references. Accepted decisions are **already decided**: report deviations from them, never re-litigate them.
4. Separate actual results from intent. Label inferred rationale as inferred when no plan, design record, or author statement establishes motivation.
5. Use proportional detail and meaningful change groups. Account for every changed path, including routine or generated changes with an explicit reason for abbreviated treatment.

## Supporting material

The report machinery is shared with explain-plan under `shared/explain-report/`, resolved as `shared/SKILL.md` describes. Read `references/evidence_playbook.md` there before investigation and `references/report_contract.md` before preparing data. Apply `references/review_rubric.md` before delivery. Read `references/research_basis.md` for format rationale or attribution. `shared/references/grounded-evidence.md` owns what counts as evidence, and `shared/references/html-page-conventions.md` owns the page floor: self-containment, navigation, the safety floor, and verification.

Every command below sets `SHARED_DIR` to the resolved absolute `shared` directory in the same command.

## 1. Define the inspected scope

Establish the comparison base from the user request, PR, or explicit project context. Resolve refs to full commits. Do not silently choose a merge base or assume every local change belongs to the task. Distinguish committed comparison from working tree changes and identify relevant untracked paths.

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/snapshot_repo.py" --repo /absolute/repository --base BASE_REF --head HEAD_REF --output /absolute/artifacts/repo_snapshot.json
```

Add `--merge-base` only when the intended scope is branch changes since the common ancestor. Add `--worktree` for authorized local work. Read collector limitations, including ignored files and submodule contents.

Write reports outside the inspected repository or into an already ignored directory so they do not change their own input; the collector refuses any other path inside the repository. If no base can be established, explain the bounded available scope and missing comparison rather than inventing one.

## 2. Inspect actual implementation

Read changed paths, surrounding symbols, callers, consumers, tests, and configuration. Check behavior instead of trusting commit messages or a prior agent's summary. Inspect contracts, schema, authorization, tenant isolation, concurrency, performance, event delivery, and rollout when affected.

Map every changed path to an explained area or explicit exclusion with reason. Account for old and new rename paths, generated files, binary files, lockfiles, migrations, and deletions. Keep unexplained paths visible and qualify completeness until resolved.

For repository consistency claims, inspect real precedents and explain both similarities and differences. An analogous module is evidence of a pattern, not proof the decision is optimal.

## 3. Compare plan and outcome

Load the exact original plan when available. Record its report ID, revision, and SHA256 of its exact bytes, and keep its path. Preserve its requirement and decision IDs. Classify planned decisions as implemented, revised, deferred, or dropped. Identify added decisions. Keep the original plan intact; never rewrite it to match the implementation.

Show planned behavior, actual behavior, the reason for each departure, and its consequence. Distinguish an observed difference from an inferred explanation. Include removed scope and newly introduced operational obligations.

Without a plan, say comparison is unavailable. Reconstruct a useful implementation explanation without inventing original intent, approval, or adherence.

## 4. Explain four depths

The report is a **decision surface**: it moves the reader from what was built to its evidence and what remains. The four depths refine the conventions' glance, scan, and descend: depth 1 is the glance, depths 2 and 3 are the scan, depth 4 is the descend layer.

1. Outcome, original problem, actual result, principal decisions, material risks, and remaining gaps.
2. System change, before and after responsibilities, contracts, runtime relationships, and failure behavior.
3. Decisions and areas, why the design fits, alternatives, costs, precedents, and behavioral changes.
4. Evidence, exact paths and symbols at the inspected revision, focused excerpts or diffs, checks, findings, and unresolved questions.

Start each group with the semantic change and its consequence. Put focused diffs behind disclosure controls. Use actual diff excerpts with sufficient context, identify omissions, and link to the complete source location when available. Never present reconstructed snippets as exact diffs.

Use exact diagrams with named relationships and links to code areas. For UI changes use real screenshots when available. Preserve a textual relationship list for accessibility and Markdown.

**Lead with the outcome**: the overview cards say what was built and what is still open before any mechanism. Keep them concise, usually around 120 to 180 words together. Explain behavior in ordinary language first and keep exact symbols in deeper sections unless essential. State material risks directly without repeating all detailed evidence.

## 5. Reconcile evidence

Build acceptance coverage against each requirement's **acceptance contract**: the work is done only when its criteria pass. Distinguish planned, passed, failed, blocked, and not run checks. Link passed checks to observed evidence with command or procedure, environment, executed revision, time, outcome, and relevant output. Builds, reviewer opinions, screenshots, tests, and proofs establish different things.

Reuse suitable existing evidence. Execute only targeted checks needed for a concrete uncertainty or required project gate. Do not deploy, alter external systems, run unsafe project scripts, or expand testing indefinitely for a report.

For formal verification, name the property, model or code artifact, assumptions, tool, and proof or bounded result. Otherwise say no formal verification was performed when relevant. Ordinary tests do not prove correctness.

Surface failed checks, critical unrun checks, requirement gaps, unexplained paths, and stale evidence in the overview. Separate implementation completeness from release readiness. Explain deployment ordering, monitoring, compatibility, rollback, and irreversible data consequences when relevant.

## 6. Render, inspect, and deliver

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/render_report.py" /absolute/artifacts/implementation.json --html /absolute/artifacts/implementation.html --markdown /absolute/artifacts/implementation.md
```

The renderer writes the HTML only when it passes `shared/scripts/html_guard.py`; fix the data until it does. It checks structure and evidence references, not source truth. Audit consequential claims against their actual evidence, then check the page as the conventions' Verification section and the rubric describe.

Before delivery, run the freshness check and cross check the report against the snapshot. Pass `--source-plan` when the report records the plan's SHA256:

```sh
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/snapshot_repo.py" --repo /absolute/repository --check /absolute/artifacts/repo_snapshot.json
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/audit_report.py" /absolute/artifacts/implementation.json --snapshot /absolute/artifacts/repo_snapshot.json --source-plan /absolute/original/plan.md
```

If the snapshot is stale, reassess affected claims and regenerate; a static report only detects later changes when its check is rerun. The audit detects missing changed paths, revision mismatches, broken references, and mismatched plan bytes. It does not prove narrative truth. Explain or resolve warnings; do not hide them.

Save through the host's durable artifact mechanism and preserve artifact identity on revisions. Deliver HTML as the main report and Markdown as a portable companion. In chat, lead with the main choices, deviations, evidence, and remaining limitations, then give the paths and how to navigate. This intentionally reverses the conventions' path-first delivery, so the summary stands without opening the file. A report is not merge or release approval. Reader notes remain feedback until the corresponding action is authorized.
