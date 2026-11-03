# Module design lens

Use this lens for D02, D03, D04, and D13 whenever the review judges how the code is divided, not only whether it is safe. It finds the most expensive design problems: one concept spread across many places, modules that are only pass-throughs, and seams that tests cannot use. The vocabulary is Ousterhout's and Feathers': a **deep module** hides much behavior behind a small interface (high **leverage**), a **seam** is a place behavior can change without editing it, an **adapter** fills a seam, and **locality** is how far a change spreads. An **interface** is everything a caller must know, including invariants, ordering, error modes, and limits.

| Question | Use | Not |
| :--- | :--- | :--- |
| Where can behavior change without editing that place? | seam | Bounded Context, which is a model boundary |
| Does a small interface hide a lot of behavior? | deep module, leverage | line counts |
| Where do change, bugs, and verification concentrate? | locality | "cleaner", "easier to maintain" |
| Which way may source dependencies point? | The Dependency Rule | runtime call direction |

## The deletion test

Imagine deleting a suspected shallow module. If its complexity vanishes, it was a pass-through and is a candidate for merging. If the complexity reappears in N callers, it earns its keep. Record the answer as evidence ("deleting `x` would copy its retry rule into 4 callers, E012"), not as a verdict on style.

## The interface is the test surface

Callers and tests should cross the same seam. Tests that build internal state by hand, patch private names, or assert on intermediate calls pass while the real path is broken. In one real review, scheduled jobs queued forever because every test built the job with the correct identity by hand and never exercised the identity lookup production used. Treat such a test as weak evidence for the behavior it names.

## One adapter is hypothetical, two is real

A seam earns a port when at least two adapters exist or are justified, typically production and a test fake. Recommend a single-adapter port only with a concrete second adapter. Never prescribe an interface per class or a Repository per table.

## Dependency category

Every seam finding names what sits behind the seam, because that decides how the deepened module is tested:

| Category | Meaning | Test strategy |
| :--- | :--- | :--- |
| in-process | Pure computation or in-memory state | Through the new interface directly |
| local-substitutable | Has a local stand-in (a real PostgreSQL in the suite) | With the stand-in; the seam stays internal |
| ports and adapters | Your own service across a network | Port at the seam; in-memory adapter in tests |
| true external | A third party you do not control | Injected port; mock adapter in tests |

## Three investigations

Run these on the modules chosen for depth. `scripts/measure.py` gives raw counts; classify each site before counting it, because a textual match can be a read, a write, or a comment.

1. **Concept duplication.** For each core concept (a status, an identity, a rule, a policy), count the places that declare it, the modules that write it, and the places that change its state (`occurrences`, `writers`, `callers`). A concept declared or written in more than two places with differing copies is a finding; name the copies and the difference. Past reviews found a job identity declared in 8 places, a status written by 5 modules, and a pause rule copied 5 times with different failure behavior.
2. **Safety-critical callers.** Identify calls that must only happen from named places: the gate that authorizes an external effect, the enqueue that starts one, and any parameter that relaxes a check (`allow_inactive=True`, `skip_validation=True`). Use `callers --function` and `--keyword`. If no test pins the allowed callers, propose one as a guardrail.
3. **Refactor cost.** Before recommending that files move, count tests that name module paths as strings (`test-pins`). A high count means entry-point modules come first, and files move later, one package per step, with their pins.

For each table on a critical path, list its writer modules. One writer is a strength to protect with a test. Several writers with different mechanisms (constructor, bulk update, raw SQL) are a finding when rules or audit events differ between them.

Weight the lens toward hot spots and modules that fix commits keep touching (`history`). A design problem nobody changes is low priority; the same problem in a hot spot, or linked to an incident through a fix commit, is not.

## Follow-up offers

Offer these after the report, never as actions taken without a request:
- **Design it twice** for a chosen finding: several radically different interfaces compared by depth, locality, and seam placement (`software-design-philosophy`, or `codebase-design` when installed).
- **Grilling** through the finding's decision tree with the user (`grilling` when installed).
- **Record a rejection** as an ADR when the user rejects a recommendation for a reason later reviews need.
- **Glossary gaps**: the terms the review had to name that the project glossary lacks.
