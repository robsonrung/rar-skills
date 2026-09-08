# Project Instruction Principles

Use these principles to place durable project knowledge. Earlier guidance was adapted from HumanLayer's [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md). Numeric instruction budgets from that guidance are not a model-capacity guarantee.

## Keep project knowledge

Keep verified facts that change how work is done: project purpose, layout, supported tools, required commands, security boundaries, and team standards. Do not replace an enforceable standard with a vague request to use good judgment.

The WHAT / WHY / HOW questions help identify missing context:

- WHAT: the stack and relevant project structure.
- WHY: the purpose and responsibilities that code alone does not establish.
- HOW: the actual tooling, required checks, and constraints on execution.

Inspect available evidence before asking the user. An unknown component purpose does not require a new interview when the current edit does not depend on it.

## Place by scope

Keep the root short and broadly useful. Put subsystem rules and conditional procedures in the project's existing instruction hierarchy or focused supporting files. Link each with a concrete loading condition. A small project may need no supporting directory.

Security and authority boundaries must remain visible where the governed action can occur, even when that action is rare. Do not move a rule merely because it is specific or used less often.

Use `agent_docs/` when the project needs supporting files and has no convention. Create only the files that carry real content; a fixed set of build, test, style, and architecture documents is not required.

## Remove obsolete scaffolding

- Replace generic quality reminders, exhaustive pre-read lists, and repeated self-checks with the actual project contract.
- Reuse active instructions and evidence. A small edit does not require reading the whole repository or rerunning every documented command.
- Refer to existing linters and formatters for rules they enforce. Keep team standards that tools cannot express; adding tooling is a separate implementation choice.
- Prefer stable file or symbol pointers to copied code. Include line numbers only when useful and verified.
- Preserve existing authorization. A request to update instructions authorizes the scoped rewrite; an audit remains read-only.
- Do not add attribution or generated-by text to project instructions.

## Assess size without invented limits

Report line or word counts when they help compare a revision. Judge bloat by duplicate content, unrelated workflows, and mandatory reading cost. Do not infer runtime reliability from a fixed instruction count or line threshold.

A shorter file is useful only if its required knowledge remains reachable at the right moment. Preserve rules before optimizing size.
