---
name: skill-expert
description: Create, audit, improve, or package SKILL.md workflows and their supporting resources. Use for skill authoring, discovery problems, or workflow simplification.
---

# Skill Expert

Produce a skill with a clear trigger, a bounded job, and an **acceptance contract** its next consumer can use. Loaded text is a **shared budget**.

## House style

- **Every word earns its place.** Keep domain knowledge, contracts, project facts, and boundaries; cut what repeats host behavior. Length alone does not make a rule wrong.
- **Freedom, not procedure.** Fix an order only where it protects a dependency or invariant; leave the rest to the orchestrator. State the purpose, the completion condition, and what happens when one part is blocked: finish the rest and report the gap.
- **Judgment, not textbook content.** Teach what the model lacks, and give a rule its reason instead of emphasis. One principle generalizes; do not list every variant.
- **Scripts only where they enforce.** Script only what a model cannot reliably do by hand: fragile, deterministic, security-sensitive, or repeated work.
- **One owner per rule.** State each rule once, where it lives; others point to it.
- **Short routing.** A dispatching skill runs `model_routing.py resolve`, asks "Approve this plan, or specify changes.", then uses T3 `delegate_task`, a native subagent, or `cli-runner`, `pi-runner`, or `muse-runner` ([pattern](references/portable-skill-authoring.md)). Others say nothing about routing.

## Select the work

An audit reports findings without edits. An improvement request authorizes its scoped edits without asking again.

| Request | Read |
| --- | --- |
| Create, edit, move content, or apply feedback | [references/authoring.md](references/authoring.md) |
| Model dispatch or host capabilities | [references/portable-skill-authoring.md](references/portable-skill-authoring.md) |
| Wording, model migration, or a behavior the skill causes | [references/model-calibration.md](references/model-calibration.md) |
| Named concepts and their guards | [references/leitworter.md](references/leitworter.md) |
| Check, evaluate, compare, or package | [references/verification.md](references/verification.md) |

## Audit

Apply the house style, then ask:

1. Does the description name the job and separate it from the nearest competing skill, without teaching the method?
2. Does the entry hold only shared rules and the selected workflow, with modes and manuals in references?
3. Does verification test a changed contract or a required gate, not a reread loop? Effort controls thinking; ask for a rationale field, never internal reasoning.
4. Does each stop protect an unresolved decision, an external effect, or an authority boundary?
5. Can an instruction collide with another loaded layer (AGENTS.md, a shared reference, a caller)? Resolve it at its owner, or state precedence: the user's explicit request wins, except at safety and authority boundaries.

## Edit

- Preserve the layout, installed names, invocation policy, and useful resources unless the request changes them. Inspect the script or consumer before changing an executable contract.
- An audit finding is evidence to weigh, not a reason to append a rule.
- Use the collection's leitwörter and keep every guarded phrase in its file: "This keeps the acceptance contract while moving the command manual out of the shared budget."
- Replace an obsolete instruction where it lives and delete what the change made dead. A moved rule keeps its trigger and a consumer that loads it.
- Resolve discoverable facts yourself. Ask only about a material decision outside the request, and keep working meanwhile.

## Verify and report

Run the checks [references/verification.md](references/verification.md) names; a prose or placement change needs no model runs.

An audit returns each instruction's location, consequence, and proposed change, plus the rules to keep. An edit report names the changed files, validation evidence, sources, material assumptions, and remaining limits. Structured delivery keeps the keys `created_files`, `validation`, `sources_used`, `assumptions`, and `optional_refinements`.
