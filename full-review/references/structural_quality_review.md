# Structural Quality Review

Use this reference when evaluating maintainability, abstraction quality, file growth, and branching complexity. This is not a style pass. It is for structural regressions that make future changes riskier, slower, or harder to reason about.

## Review Stance

Be ambitious.

Assume there is often a "code judo" move available: a re-organization that uses the existing architecture more effectively and makes the change dramatically simpler and more elegant.

Do not stop at "this could be cleaner." Look for ways to preserve behavior while deleting concepts, branches, helper layers, state modes, wrappers, and special cases. Prefer the implementation that feels inevitable once seen.

## Blocking Bar

Treat these as presumptive blockers unless the author has a clear reason:

1. The PR pushes a file from below 1000 lines to above 1000 lines.
2. The PR adds ad hoc special cases into an already busy flow.
3. The PR scatters feature checks across shared code instead of putting the concept behind a clear boundary.
4. The PR adds wrappers, identity helpers, or generic mechanisms that increase indirection without reducing complexity.
5. The PR adds casts, loose optionality, `any`, `unknown`, or silent fallback paths that obscure the real invariant.
6. The PR puts logic in the wrong layer when there is an obvious canonical owner.
7. The PR preserves a lot of incidental complexity when a simpler model could delete it.
8. The PR splits related updates in a way that can leave state partially applied when a cleaner atomic structure is obvious.

## Primary Questions

Ask these before approving maintainability sensitive changes:

1. Can this be reframed so fewer concepts are needed?
2. Can whole branches, modes, helpers, or layers disappear?
3. Is the new logic living in the canonical layer for this concept?
4. Did a cohesive module become more coupled, more stateful, or harder to scan?
5. Are repeated conditionals pointing to a missing model, dispatcher, helper, or policy object?
6. Does this abstraction earn its keep, or is it just an extra name for pass through behavior?
7. Is optionality or casting hiding a contract that should be explicit?
8. Is independent work serialized in a way that makes orchestration harder to reason about?
9. Are related updates non atomic when one transaction, one command, or one state transition would be cleaner?
10. Did file size cross a healthy boundary because the new code was appended instead of decomposed?

## What To Flag

Flag aggressively when the changed code introduces:

1. A complicated implementation where a clearer framing could delete large pieces of complexity.
2. Refactors that move complexity around without reducing the number of concepts a reader must hold.
3. File growth across the 1000 line threshold.
4. New one off booleans, nullable modes, flags, or feature checks in unrelated flows.
5. Feature specific logic leaking into general purpose modules.
6. Generic magic that hides a simple data shape.
7. Thin wrappers that do not clarify ownership, naming, validation, or reuse.
8. Cast heavy contracts and silent fallbacks.
9. Copy pasted logic where the codebase already has a canonical helper or pattern.
10. Narrow edge case handling inserted into an already busy function.
11. Sequential async work that is independent and would be clearer as a grouped operation.
12. Partial update flows that make failure states hard to reason about.

Do not flag cosmetic taste, minor naming, local formatting, or broad refactor dreams without a concrete safer shape. The finding must point to changed code and explain the simpler path.

## Preferred Remedies

Prefer remedies that remove complexity instead of decorating it:

1. Delete a layer of indirection.
2. Reframe the state model so conditionals disappear.
3. Move ownership to the package, service, module, or component that already owns the concept.
4. Turn special cases into a simpler default flow.
5. Extract a focused helper, pure function, subcomponent, or policy object.
6. Split a large file into cohesive modules.
7. Replace condition chains with a typed model or explicit dispatcher.
8. Separate orchestration from business logic.
9. Collapse duplicate branches into one direct flow.
10. Make type boundaries explicit so control flow gets simpler.
11. Group independent work when it also simplifies orchestration.
12. Make related updates atomic when partial state would be harder to operate.

## Evidence Requirements

A structural finding must include:

1. The exact changed line range where complexity is introduced.
2. A concrete indicator such as a new branch, flag, wrapper, cast, file length threshold, layer leak, duplicated block, or partial update sequence.
3. The future change cost: what becomes harder, riskier, or more coupled.
4. The simpler framing, stated as a specific refactor path.
5. Validation to run after the refactor, usually the nearest tests plus any relevant typecheck, lint, or build command.

## Severity Guidance

Use `HIGH` when the structure is likely to block future safe changes, crosses the 1000 line threshold without justification, leaks feature logic into shared code, or makes state consistency harder to reason about.

Use `MEDIUM` when the issue is real and actionable but localized.

Use `LOW` only for unusually clear quick wins. Suppress ordinary nits.
