# Connascence taxonomy & remedies

Connascence (Meilir Page-Jones, popularized for architecture by Richards & Ford) gives a precise vocabulary for coupling. Two elements are *connascent* if a change to one requires a change to the other for the system to stay correct.

Rank any instance by three axes:
- **Strength** — static (visible in source, easy to find & change) is weaker/better than dynamic (only manifests at runtime).
- **Locality** — close elements (same function/class) tolerate strong coupling; distant elements (across modules/services) do not.
- **Degree** — the number of elements bound together; lower is better.

Most remedies move coupling *up* the tables below (toward Name) and *closer* (toward locality). The review workflow that drives these tables (identify → score strength × locality × degree → weaken → stop early) lives in SKILL.md's Coupling lens section.

## Static connascence (weaker → stronger)

| Type | Meaning | Smell | Remedy (weaken toward →) |
|---|---|---|---|
| **Name** | Multiple places agree on a name (variable, method). | Rename one, must rename all. | Lowest/acceptable form. Most refactors aim *here*. |
| **Type** | Elements must agree on a data type. | Change a type, ripples out. | Strong typing / shared type definitions; usually fine. |
| **Meaning (convention)** | Agreement on what a value *means* (e.g. `0` = inactive, `true` = admin). | Magic numbers/strings; boolean flags. | → Name: named constants, enums, value objects. |
| **Position** | Order matters (positional args, tuple fields). | `f(a, b, c)` where swapping breaks it silently. | → Name: named parameters, options object, named struct fields. |
| **Algorithm** | Two places must implement the *same* algorithm (e.g. both sides hash/serialize/checksum identically). | Duplicated logic that must stay in lockstep. | → Name: extract one shared implementation; share the function, not the recipe. |

## Dynamic connascence (stronger — prefer to eliminate, especially at a distance)

| Type | Meaning | Smell | Remedy |
|---|---|---|---|
| **Execution (order)** | Operations must run in a specific order. | `init()` must precede `use()`; hidden temporal contract. | Make order explicit/enforced (builder, state machine), or remove the requirement. |
| **Timing** | Correctness depends on *when* things run (race conditions). | Works until load increases. | Synchronization, idempotency, removing shared mutable state. |
| **Value** | Several values must change together to stay valid (invariants spanning fields/records). | Update one field, forget the linked one. | Encapsulate the invariant in one object/transaction that owns all the values. |
| **Identity** | Multiple references must point to the *same* instance. | Two caches, two "sources of truth" that drift. | Single source of truth; pass identity explicitly. |

## Cohesion companion check

Connascence describes coupling *between* things; cohesion describes whether things *belong together*. A module has high cohesion when its parts change for the same reason. Low cohesion + strong distant connascence = the classic signal to split, move, or regroup.
