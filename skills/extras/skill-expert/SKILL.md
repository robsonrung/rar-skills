---
name: skill-expert
description: Create, audit, improve, or package SKILL.md workflows and their supporting resources. Use for skill authoring, discovery problems, or workflow simplification. For project instruction files, use agents-md-craft.
---

# Skill Expert

Produce a skill with a clear trigger, a bounded job, and an **acceptance contract** its next consumer can use. Treat loaded text as a **shared budget**. Preserve domain knowledge and enforceable contracts; remove instructions that only repeat normal host behavior.

## Select the work

Infer the route from the user's request. An audit reports findings without edits. An improvement request authorizes the scoped edits and their supporting references; do not ask again to apply the requested changes.

| Request | Work and references |
| --- | --- |
| Audit or review | Inspect the entry file, its selected references, and any script or consumer needed to verify a finding. Apply the audit questions below. |
| Create or improve | Read [references/authoring-guide.md](references/authoring-guide.md). Load [references/authoring-contract.md](references/authoring-contract.md) when moving content, changing paths, or applying feedback. |
| Package | Read [references/validation-and-packaging.md](references/validation-and-packaging.md). Package the requested skill and its dependencies without installing or publishing it unless requested. |
| Evaluate or compare | Read [references/evaluation.md](references/evaluation.md). Choose a bounded comparison and report measured results separately from inspection. |
| Fix discovery | Read [references/description-optimization.md](references/description-optimization.md). Inspect trigger metadata before changing the execution workflow. |

Load [references/portable-skill-authoring.md](references/portable-skill-authoring.md) when a change affects model routing, host capabilities, authority, or a shared protocol. Load [references/script-standards.md](references/script-standards.md) when adding or changing scripts. Do not reload references already available in the current context.

## Audit questions

Judge each instruction by its purpose and current effect:

1. Does the description identify the job and distinguish the nearest competing skill, without teaching the method?
2. Does the entry load only common rules and the selected workflow? Move other modes, command manuals, and large templates to supporting files.
3. Does a required sequence protect a real dependency or invariant? Keep that order; let the host choose the rest.
4. Does context loading follow the changed surface? Reuse active project instructions and evidence instead of requiring a full read before every edit.
5. Does verification test a changed contract or required repository gate? Remove generic reread loops and duplicate checks.
6. Does a stop protect an unresolved decision, external effect, or authority boundary? Reuse existing authorization and continue independent work.

Keep permanent project facts, security boundaries, team standards, output schemas, and real engineering methods. Length alone does not make a rule wrong. When moving a rule, preserve its trigger and ensure the consumer still loads it.

## Edit within the contract

- Preserve the source layout, installed names, invocation policy, and useful resources unless changing them is part of the request. Do not edit global installations from a repository-only request.
- Inspect the affected script or consumer before changing an executable contract. An audit's recommendation is evidence to assess, not a reason to append another rule.
- Keep model and effort defaults only in `shared/model-routing.json`; preserve exact choices in each approved run snapshot. A generic tier or inherited model cannot override a user-approved route.
- Follow the repository's canonical vocabulary and named-concept rules when present. Use a **leitwort** to explain a real decision: "This keeps the acceptance contract while moving the command manual out of the shared budget."
- Replace obsolete instructions where they live, including affected references and templates. Do not leave a conflicting old workflow behind the new router.
- Resolve discoverable facts directly. Ask only when a material decision or action lies outside the user's request; proceed with unaffected work.

## Verify and report

Use [references/validation-and-packaging.md](references/validation-and-packaging.md) for checks relevant to the edit. A prose or placement change does not require paid model runs. Test changed scripts and consumer contracts; use behavioral evaluation when requested or when a material execution risk needs it.

An audit returns the instruction and location, consequence, proposed change, and rules to keep. An edit report names the changed files, purpose, validation evidence, sources used, material assumptions, and remaining limits. Preserve structured delivery keys when a caller needs them: `created_files`, `validation`, `sources_used`, `assumptions`, and `optional_refinements`. Do not claim better model behavior from a word-count reduction or static check alone.
