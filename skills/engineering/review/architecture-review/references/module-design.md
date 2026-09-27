# Module design lens

Use this lens for D02, D03, D04 and D13 whenever the review judges how the code is divided, not only whether it is safe. It adds the questions that find the most expensive design problems: one concept spread across many places, modules that are only pass-throughs, and seams that tests cannot use. It adapts the deep-module vocabulary of [W21] and the deepening method of [W22] to this package's evidence contract; Ousterhout [B08] and Feathers [B10] are the underlying sources.

## Vocabulary and how it maps

Use **deep module**, **seam**, **adapter**, **leverage**, **locality** and **deletion test** exactly as defined in `terminology.md`. They sit beside, and do not replace, the canonical architecture terms:

| Question | Use | Not |
| :--- | :--- | :--- |
| Where can behavior change without editing that place? | seam | Bounded Context (a model boundary, not a code location) |
| Does a small interface hide a lot of behavior? | deep module, leverage | line counts |
| Where do change, bugs and verification concentrate? | locality | "cleaner", "easier to maintain" |
| Which package-level principle explains co-change? | Common Closure Principle (CCP) and the other component principles | depth |
| Which way may source dependencies point? | The Dependency Rule | runtime call direction |

An **interface** means everything a caller must know: signatures, invariants, ordering, error modes, configuration and performance limits. A module is anything with an interface and an implementation, at any scale.

## The deletion test

For each suspected shallow module, imagine deleting it. If its complexity vanishes, it was a pass-through; if the complexity reappears in N callers, it was earning its keep. Record the answer as evidence ("deleting `x` would copy its retry rule into 4 callers, E012"), not as a verdict about style. A deletion test that concentrates complexity is a reason to keep a module; one that merely moves it is a candidate for merging.

## The interface is the test surface

Callers and tests should cross the same seam. Look for tests that reach past an interface: they construct internal state by hand, patch private names, or assert on intermediate calls. Those tests pass while the real path is broken. Example from a real review: scheduled jobs were queued forever because tests built each job with the correct identity by hand, so they never exercised the identity lookup that production used. Treat a test that crosses past the interface as weak evidence for the behavior it names.

## Adapters: one is hypothetical, two is real

A seam earns a port when at least two adapters exist or are justified (typically production and a test fake). A single-adapter port is indirection; recommend it only with a concrete second adapter. This is the operational form of the rubric's warning against an interface per class.

## Dependency category for every seam finding

Classify what sits behind the seam, because it decides how the deepened module is tested. Record it in the finding's `dependency_category`.

| Category | Meaning | Test strategy |
| :--- | :--- | :--- |
| `in_process` | Pure computation or in-memory state | Test through the new interface directly |
| `local_substitutable` | Has a local stand-in (a real PostgreSQL in the suite, an in-memory filesystem) | Test with the stand-in; the seam stays internal |
| `ports_and_adapters` | Your own service across a network | Port at the seam; in-memory adapter in tests |
| `true_external` | A third party you do not control | Injected port; mock adapter in tests |

## Three investigations

Run these on the modules chosen for depth. `scripts/measure.py` produces the raw counts; classify each site before counting it.

1. **Concept duplication.** For each core domain concept (a status, an identity, a rule, a policy), count the places that declare it, the modules that write it, and the places that change its state. `measure.py occurrences`, `writers` and `callers` give candidates. A concept declared or written in more than two places, with differences between the copies, is a finding; name the copies and the difference. This pattern produced the most valuable findings in the reviews that shaped this lens: a job identity declared in 8 places, a status written by 5 modules, a pause rule copied 5 times with different behavior on failure.
2. **Safety-critical callers.** Identify calls that must only happen from named places: the gate that authorizes an external effect, an enqueue that starts one, and any parameter that relaxes a check (`allow_inactive=True`, `skip_validation=True`). Use `measure.py callers --function` and `--keyword`. If no test pins the allowed callers, propose one as a guardrail.
3. **Refactor cost.** Before recommending that files move, count the tests that name module paths as strings (`measure.py test-pins`). A high count means entry-point modules must come first and files move later, one package per step, with their pins.

## Knowledge ownership

For each table or durable record on a critical path, list its writer modules (`measure.py writers`). One writer module is a strength to protect with a test. Several writers with different mechanisms (constructor, bulk update, raw SQL) is a finding when rules or audit events differ between them. Remember that bulk updates usually bypass ORM event listeners.

## Relation to history

Weight this lens toward modules that change often or that fix commits keep touching (`measure.py history`). A design problem in a module nobody changes is low priority; the same problem in a hot spot, or linked to an incident through a fix commit, is not. Record the linked incident in the finding's `incident` field.

## Follow-up after the report

These are offers, made after the report is delivered, never actions taken without a request:

- **Design it twice.** For a chosen finding, frame the constraints and dependency category, then have three or more independent designers each produce a radically different interface (minimal, flexible, common-case, ports and adapters). Compare them by depth, locality and seam placement, and recommend one or a hybrid. The `codebase-design` skill's parallel design pattern implements this when installed.
- **Grilling.** Walk the decision tree for the chosen finding with the user: constraints, what sits behind the seam, which tests survive.
- **Record the rejection.** When the user rejects a recommendation for a reason a future reviewer would need, offer to record it as an ADR so later reviews respect it.
- **Glossary gaps.** List domain terms the review had to name that `CONTEXT.md` or the project glossary lacks.
