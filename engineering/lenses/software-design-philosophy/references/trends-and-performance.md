# Trends and performance

Read only when the user asks about a practice (TDD, patterns, inheritance, agile, getters) or about speed. Chapters 19–20.

## Contents

1. [The one test](#the-one-test)
2. [Trends](#trends)
3. [Performance](#performance)

## The one test

Judge any trend, pattern, or rule by: _does it reduce complexity here, or add it?_

## Trends

| Trend | When it reduces complexity | When it adds it |
| --- | --- | --- |
| Inheritance | A real, stable is-a, interface-only | Implementation inheritance that couples a hierarchy; prefer composition |
| Agile | Small increments, feedback | Feature-completion that crowds out design. Reserve design moments. |
| Unit tests | They make design change safe — they are a **strategic** tool | Tests that pin structure instead of **observable behavior** |
| TDD | When the interface is already clear | Tests-first on an undesigned interface. **Design it twice**, then test. Hand the loop to `tdd`. |
| Design patterns | A named pattern removes a real complexity | Pattern-for-its-own-sake. That is `design-patterns`'s "fits" test plus this chapter's veto. |
| Getters and setters | Rare, when the field _is_ the abstraction | A field wrapped in two shallow methods. Usually **classitis**. |

Do not start a trends lecture. Apply the row that matches the ask and move on.

## Performance

Usually simpler code is also faster (ch. 20).

1. **Think in critical paths**, not in micro-tweaks scattered through the system.
2. **Measure before and after.** An unmeasured "optimization" is a complexity donation.
3. **Design around the critical path** — give the hot path a **deep module** with a simple interface; keep the rare path out of it.
4. Do not complicate the 90% case to win a cycle on the 10% case.

If the user asked for a speedup and you cannot measure, say so and stop. Do not "optimize" on a story.
