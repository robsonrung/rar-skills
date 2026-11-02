# Structural review

Structural findings are regressions that make the next change riskier, slower, or harder to reason about. Taste, naming nits, and formatting stay out.

Be ambitious. There is often a **code judo** move: a reframing that uses the existing architecture better and deletes concepts, branches, wrappers, state modes, and special cases while staying **behavior-preserving**. Prefer the shape that feels inevitable once seen. For simplification cues, read the `Quality pass` section of the `coding-review-simplify` skill; name smells with the `clean-code` vocabulary (primitive obsession, data clump, feature envy, and the rest).

## Look for

- Ad hoc special cases, one-off flags, or nullable modes added to a busy flow.
- Feature checks scattered through shared code instead of behind one boundary.
- Wrappers, identity helpers, or generic mechanisms that add indirection without removing complexity.
- Casts, loose optionality, `any`, `unknown`, or silent fallbacks hiding the real invariant.
- Logic outside its canonical owner.
- Refactors that move complexity without reducing what a reader must hold.
- Copied logic where a canonical helper exists.
- Related updates split so a failure leaves partial state.
- Independent async work serialized in a way that obscures orchestration.
- File growth with a concrete cohesion or ownership cost. Crossing 1000 lines is a cue to inspect, never a finding; an explicit repository size gate still applies.

## Remedies

Delete a layer. Reframe the state model so conditionals disappear. Move logic to its owner. Fold special cases into the default flow. Replace condition chains with a typed model or dispatcher. Separate orchestration from business logic. Make related updates atomic. Split a large file into cohesive modules.

## Evidence

A structural finding cites the changed lines, the concrete indicator (new branch, flag, wrapper, cast, leak, duplicate, partial update), the future change cost, the specific simpler shape, and the checks to run after the refactor.

**HIGH** is a demonstrated risk to safe change, shared ownership, or state consistency. **MEDIUM** is real and local. **LOW** is reserved for unusually clear quick wins.
