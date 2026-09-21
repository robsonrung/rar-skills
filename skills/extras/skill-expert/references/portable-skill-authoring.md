# Portable Skill Authoring

Use this reference when changing model routing, host capabilities, authority, or contracts shared by skills. Preserve the result across supported hosts without prescribing how a capable model must reason.

## Model routing

Keep maintained model mappings in one roster or configuration. Workflow prose names the role or semantic route; dispatch uses the exact model and effort selected for that run.

In this collection, `shared/model-routing.json` owns all maintained model and effort mappings. The routing references define selection, execution, and approval procedure. Resolve `shared/` through the collection's shared-library convention.

- Use the maintained task and effort defaults for each role. Preserve the user's quality or cost priority; a generic low-effort default cannot replace a supplied task route. Do not assume the current model is strongest for every task.
- Resolve native delegation before external runners through `shared/references/host-model-execution.md`. Prefer exposed native tools for the exact selected model. Reuse a task and role's persistent context for later turns, while keeping independent roles separate.
- Explicit model, reviewer, effort, receipt, and budget approvals take precedence over a generic cost tier.
- Inheritance by omission is valid only when the workflow permits it and no approved exact route is being replaced.
- If the selected route is unavailable, use only an already-approved fallback or return the affected route for a decision. Do not silently switch to the host model.
- Concrete model IDs belong in the central configuration, approved run snapshots, receipts, and test fixtures. Adapters read them from the configuration. Avoid duplicating them in general workflow prose.
- Distinguish configured model labels, observed serving-model receipts, provider guidance, and local benchmark evidence.

Semantic tiers such as extraction, generation, and synthesis may express task needs. They are not a universal quality ranking or authority to downgrade a model.

## Protocol and judgment

Keep rules whose omission could change authority, state, coverage, counts, output fields, or a downstream handoff. Preserve domain knowledge that changes the decision.

| Keep explicit | Leave to task judgment |
| --- | --- |
| Output paths, fields, enums, and schemas | Order of independent investigations |
| Dependencies and required state transitions | Number of speculative alternatives |
| Approval, mutation, and isolation boundaries | Generic self-check or reread loops |
| Evidence and coverage required by consumers | Repeated rationale and quality reminders |
| Bounded retries and terminal outcomes | Technique selection when several are valid |

Scope a rule beside the action it governs. A real engineering method can require an order; a numbered list alone is not a defect. A runtime constraint or team standard does not become obsolete because a newer model understands it.

## Context and resources

Keep common rules and route selection in the entry. Load the selected method, schema, or tool reference at its point of use. Reuse active project instructions and already-read evidence. Expand inspection only when the changed boundary requires it.

When moving text, retain reachable source knowledge and correct paths. Do not create a hidden chain of skills that a fresh consumer must reconstruct. Refer to capabilities before host-specific adapters unless exact API semantics are part of the contract.

## Authority

An explicit change request authorizes its necessary reversible work. An audit request does not authorize edits. Reuse prior approval for the same scope and action; silence is not new approval.

Use `shared/references/model-preview.md` for each direct invocation; nested skills reuse the selected snapshot without another prompt or unlisted workers. Preserve user-requested model previews and genuine security boundaries. Carry bounded authority through dependent work without widening it. Continue independent work when one action needs a decision.

Keep skill invocation separate from delegation. The presence of a multi-agent tool is not itself a reason or authorization to use it. When delegation is authorized, each worker needs a scope, output contract, and owner for integration.

## Portability checks

Inspect the actual adapter or consumer when a change depends on its behavior. A prompt-only restriction is not an enforced sandbox. A missing command is not proof that the host lacks every equivalent capability.

Use deterministic checks for metadata, paths, schemas, and script contracts. Use bounded behavioral comparisons for a material uncertainty or a requested performance claim. No measured improvement can be inferred from fewer words, fewer tools, or a single successful run.

When testing across models, record the actual model, host, relevant constraints, evidence, and limits. No standard pre-edit narration or exhaustive model matrix is required.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
