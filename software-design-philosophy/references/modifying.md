# Modifying existing code

Read on `improve`, and on `review` when the diff is a feature landing on an old module. Chapters 16–18 and 21.

## Contents

1. [Stay strategic](#stay-strategic)
2. [Comments during change](#comments-during-change)
3. [Consistency](#consistency)
4. [Obviousness](#obviousness)
5. [Decide what matters](#decide-what-matters)

## Stay strategic

The default failure when maintaining a codebase is a tactical special case: the new feature is bolted on because changing the design would take an hour.

**Stay strategic** (ch. 16.1): the increment should be an abstraction, not a feature (principle 15). If the current design cannot absorb the change cleanly, improve the design *as part of this change*, or state why you will not (time-box, risk, **smallest coherent shape**).

Do not:

- add a boolean that forks a **deep module** into two models
- copy a block "just this once" (that is **repetition** plus a future **information leakage**)
- leave the old model and the new model both in place without a name for the split

If tests are missing and the structural change is risky, pin behavior first (`safe-incremental-coding` / a **characterization test**), then change structure.

## Comments during change

- Keep comments **next to the code** they describe. Distant comments will not be updated (ch. 16.2).
- Comments belong in the code, not the commit log (ch. 16.3).
- Do not duplicate a comment across modules (ch. 16.4).
- Before you finish, read the diff *as comments*: every changed behavior should leave the nearby comment still true (ch. 16.5).
- Higher-level comments survive change better than line-by-line narration (ch. 16.6). Prefer those.

A comment that the diff made false is a defect in this change.

## Consistency

Consistency is how readers form correct expectations (ch. 17). Names, file layout, error style, and invariants should match the codebase's strongest local pattern — unless that pattern is what you are fixing.

Ensure it with conventions already in the project's context, linters, and review. Do not invent a second style in the files you touch.

Taking it too far: do not preserve a bad convention for consistency, and do not mix two conventions in one change. Convert or leave it.

## Obviousness

Code is obvious when a reader goes at full speed with correct assumptions and no backtracking (ch. 18).

Makes code more obvious: precise names, consistency, white space that matches structure, **earned comments**, code that matches the reader's expectation.

Makes code less obvious: event-driven control flow with hidden callbacks, generics or inheritance that hide the actual behavior, cleverness, violation of a reasonable expectation, a name that means something else nearby.

**Nonobvious code** is a red flag. If you cannot make it obvious, that is the finding.

## Decide what matters

Chapter 21 (full text in the official Stanford extract). Structure the system around what matters. Emphasize those things; hide the rest.

On every `improve` or `design` of any size:

1. **What matters here?** Name two to four things. Prefer items with **leverage**: one interface or invariant that solves many problems (`insert`/`delete` of a range, not `backspace`). An invariant is leverage — once you know it, you can predict the structure in many situations.
2. **If it is not obvious, hypothesize.** State "I think X is what matters most," build under that assumption, then record why it was right or which clue you missed. That is how taste is trained.
3. **Minimize that set.** Fewer constructor parameters; defaults for common usage; hide the rest inside the module; handle an exception at one low place; compute a config instead of exposing a knob. Information hidden in a module does not matter outside it.
4. **Emphasize only those**, three ways:
   - *prominence* — they appear where people look (interface, names, hot methods)
   - *repetition* — the idea shows up more than once
   - *centrality* — the rest of the structure is organized around them
5. **De-emphasize the rest** — hide it, make it rare, keep it off the system's spine.

Two mistakes (both defects):

| Mistake | Looks like | Cost |
|---|---|---|
| Too many things treated as important | Unused arguments, Java I/O's buffered/unbuffered split, **shallow modules** | Cognitive load |
| Something important not recognized | Hidden invariant, missing capability, tribal knowledge | **Unknown unknowns** |

State it as: *"**decide what matters**: X and Y (leverage); Z does not — hide it."*
