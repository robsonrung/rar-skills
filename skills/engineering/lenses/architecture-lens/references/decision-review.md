# Lens 1 — Decision / trade-off (trade-off coach)

Use for an unresolved architecture choice. Settled task decisions remain inputs unless new evidence invalidates them. The result is an explicit choice and its cost.

1. **Name what actually matters here.** Identify the 2–4 _architecture characteristics_ (the "-ilities") this decision really trades on — not all of them, the ones in tension (performance, scalability, testability, maintainability, fault-tolerance, simplicity, deployability, security, evolvability). Most decisions trade two against each other. See [architecture-characteristics.md](architecture-characteristics.md).
2. **List the real options.** Compare meaningfully different viable options; "do nothing / keep current" can be one. Do not invent an alternative when a settled contract or repository constraint already determines the move.
3. **For each option, state the trade-off explicitly** — what you _gain_ and what you _give up_. Record an actual cost or constraint; do not invent a drawback to fill a field.
4. **Decide against the characteristics from step 1**, and say _why_ in one sentence. The reasoning is the deliverable, not the choice.
5. **Watch for decision anti-patterns:** re-deciding the same thing repeatedly ("Groundhog Day" → record it); deciding to avoid blame rather than for the system ("covering your assets"); decisions that live only in chat/email (if significant, write it down).
6. Apply **all three or no ADR**: record a decision only when it is hard to reverse, surprising without context, and a real tradeoff. **Record on settle** with [adr-template.md](adr-template.md); routine choices stay in the task or review note.
7. **If a decision encodes a rule future code could violate, suggest a fitness function** — an automated guard (lint rule, arch test, CI check) so the rule enforces itself. See [fitness-functions.md](fitness-functions.md).
