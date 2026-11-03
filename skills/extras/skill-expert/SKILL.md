---
name: skill-expert
description: Create, audit, improve, or package SKILL.md workflows and their supporting resources. Use for skill authoring, discovery problems, or workflow simplification.
---

# Skill Expert

Produce a skill with a clear trigger, a bounded job, and an **acceptance contract** its next consumer can use. Loaded text is a **shared budget**: every word earns its place. Keep domain knowledge and enforceable contracts; cut what only repeats normal host behavior.

## Select the work

An audit reports findings without edits. An improvement request authorizes the scoped edits and their supporting references; do not ask again before applying them.

| Request | Read |
| --- | --- |
| Create, improve, move content, or apply feedback | [references/authoring.md](references/authoring.md) |
| Model routing, host capabilities, authority, or a shared protocol | [references/portable-skill-authoring.md](references/portable-skill-authoring.md) |
| Instruction wording, a model migration, or a behavior a skill causes | [references/model-calibration.md](references/model-calibration.md) |
| Package | [references/validation-and-packaging.md](references/validation-and-packaging.md); package without installing or publishing unless asked |
| Evaluate or compare | [references/evaluation.md](references/evaluation.md); report measured results apart from inspection |

When a skill makes a model stall, ask again, drift, or overreach, have the seat that showed it quote the instruction behind that choice, then fix the owning layer rather than adding a counter-rule.

## Audit questions

1. Does the description name the job and separate it from the nearest competing skill, without teaching the method?
2. Does the entry hold only common rules and the selected workflow, with other modes and manuals in references loaded at their point of use?
3. Does each fixed sequence protect a real dependency or invariant? Otherwise let the model choose.
4. Does it teach judgment the model lacks, or textbook content the model already has?
5. Is each rule stated once, in its owner? A rule another skill or shared reference owns is a pointer, not a copy.
6. Does a model dispatch use the short routing pattern in `portable-skill-authoring.md`, one persistent context per role, and **seat fidelity**? A skill that dispatches nothing says nothing about routing.
7. Does each script enforce something a model cannot reliably do by hand? A script that wraps one obvious command is dead weight.
8. Does verification test a changed contract or a required repository gate? Remove generic reread loops and requests to deliberate; effort controls thinking. Never ask for internal reasoning in the response; a rationale field is fine.
9. Does each stop protect an unresolved decision, an external effect, or an authority boundary? Reuse existing authorization and continue independent work.
10. Does the skill say when it is done, and what happens when one part is blocked: finish the rest and report the gap, never quietly narrow, widen, or swap the task?
11. Can an instruction collide with another loaded layer, such as the user's request, AGENTS.md, a shared reference, or a calling skill? Resolve it where it lives, or state precedence: the user's explicit request wins, except for safety and authority boundaries.

Length alone does not make a rule wrong. Keep permanent project facts, security boundaries, team standards, output schemas, and real engineering methods. When moving a rule, keep its trigger and confirm its consumer still loads it.

## Edit

- Preserve the layout, installed names, invocation policy, and useful resources unless the request changes them.
- Inspect the affected script or consumer before changing an executable contract. An audit finding is evidence to assess, not a reason to append a rule.
- Model and effort defaults live only in `shared/model-routing.json`.
- Use the collection's leitwörter, and keep every phrase `leitworter.json` guards in its file. Use a **leitwort** to explain a real decision: "This keeps the acceptance contract while moving the command manual out of the shared budget."
- Replace an obsolete instruction where it lives, across references and templates, and delete what the change made dead. Do not leave an old workflow behind the new router.
- Resolve discoverable facts yourself. Ask only when a material decision or action lies outside the request, and continue the unaffected work meanwhile.

## Verify and report

Run the checks [references/validation-and-packaging.md](references/validation-and-packaging.md) names for the change. A prose or placement change needs no paid model runs.

An audit returns each instruction with its location, consequence, proposed change, and the rules to keep. An edit report names the changed files and their purpose, the validation evidence, the sources used, material assumptions, and remaining limits. When a caller needs structured delivery, keep the keys `created_files`, `validation`, `sources_used`, `assumptions`, and `optional_refinements`. Never claim better model behavior from a word-count reduction or a static check alone.
