# Lens 2 — Coupling / connascence (coupling reviewer)

Goal: replace vague "this is too coupled" with a precise diagnosis and a concrete way to weaken it.

**Connascence** = two pieces of code are connascent if changing one forces a change in the other to keep the system correct. Three questions rank any coupling:

- **Strength** — how hard is it to refactor? Static (visible in source) is weaker than dynamic (only shows at runtime).
- **Locality** — how far apart are the connascent elements? The _same_ coupling is far worse across module/service boundaries than within one function.
- **Degree** — how many elements are involved?

**The rule:** the farther apart two elements are, the weaker the connascence between them should be. Strong coupling is fine locally, dangerous at a distance.

Review workflow:

1. Identify the coupled elements and **name the connascence type** (see [connascence.md](connascence.md) for the full taxonomy and each type's remedy).
2. Judge it by strength × locality × degree. Local + static = usually leave it. Distant + dynamic = flag it.
3. For each thing worth fixing, suggest a concrete weakening — e.g. magic value → named constant (meaning→name).
4. Don't over-refactor: removing all coupling is impossible and chasing it creates indirection. Weaken the _strong, distant, high-degree_ cases; leave the rest.
