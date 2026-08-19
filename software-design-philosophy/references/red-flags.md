# Red flags

Read before a thorough `review`, and when a `design` or `improve` finding needs a name. Official 2nd-edition catalog, plus the fix. Each flag is a *symptom*. Name it, then change the structure — do not paper over it with a comment.

Root cause is **dependency** or **obscurity**.

## Contents

1. [Shallow Module](#shallow-module)
2. [Information Leakage](#information-leakage)
3. [Temporal Decomposition](#temporal-decomposition)
4. [Overexposure](#overexposure)
5. [Pass-Through Method](#pass-through-method)
6. [Pass-through variable](#pass-through-variable)
7. [Repetition](#repetition)
8. [Special-General Mixture](#special-general-mixture)
9. [Conjoined Methods](#conjoined-methods)
10. [Comment Repeats Code](#comment-repeats-code)
11. [Implementation Documentation Contaminates Interface](#implementation-documentation-contaminates-interface)
12. [Vague Name](#vague-name)
13. [Hard to Pick Name](#hard-to-pick-name)
14. [Hard to Describe](#hard-to-describe)
15. [Nonobvious Code](#nonobvious-code)

## Shallow Module

The interface for a class or method isn't much simpler than its implementation.
**Why:** benefit barely exceeds cost; net complexity goes up. Often **classitis** — many tiny classes, each shallow.
**Fix:** deepen it. Fold trivial wrappers into the caller, raise the abstraction so the common path needs fewer arguments, or merge with the module it mostly delegates to.

## Information Leakage

A design decision is reflected in multiple modules.
**Why:** **dependency** — the modules cannot be understood or changed in isolation. Back-door leakage (a shared assumption neither documents) is worst.
**Fix:** one module owns the decision. If the leaking classes are small and bound to that knowledge, **merge** them — information hiding often improves by making a class a bit larger so one feature lives in one place. If they are large, extract the shared knowledge into a new class *only* when you can give it a simple interface. This *is* the **change ownership** check.

`private` is not hiding. A getter/setter that exposes the field puts it in the informal interface. The best hidden information is irrelevant to callers.

## Temporal Decomposition

The code structure is based on the order operations run, not on information hiding (`readFile` / `processFile` / `writeFile`).
**Why:** execution order is a bad axis; format knowledge leaks across the time-ordered pieces.
**Fix:** organize around the knowledge each module hides. One module that owns the format and exposes read/write is deeper than three that each half-know it.

## Overexposure

An API forces callers to confront rarely-used features in order to use common ones.
**Why:** **obscurity** of the simple path.
**Fix:** a default-laden entry point for the common case; rare options stay reachable and out of the way. Classes should *do the right thing without being asked*. The best features are ones the caller gets without knowing they exist.

## Pass-Through Method

A method does almost nothing except pass its arguments to another method with a similar signature.
**Why:** more interface, more coupling, no decision hidden.
**Fix:** caller invokes the deeper method; or combine the layers; or give the method a real, distinct responsibility. (Duplicating an interface *is* OK when the layer adds a different abstraction — ch. 7.2.)

Adjacent layers with the *same* abstraction are a class-decomposition problem (ch. 7). Follow one operation down the stack: the abstraction should change at each call. If it does not, the cut is wrong.

Decorators that only forward are this flag wearing a pattern (ch. 7.3).

## Pass-through variable

A parameter is threaded through methods that do not use it, only to reach the one that does. (Not in the printed one-line summary; it is ch. 7.5 and the same family.)
**Why:** every method gains interface it does not need; adding a new value edits the whole chain.
**Fix:** a context the chain already shares, or another way for the deep method to get the value without the thread.

## Repetition

A nontrivial piece of code is repeated over and over.
**Why:** change amplification; easy to miss a copy.
**Fix:** extract into a module that *owns* that knowledge — only when the copies are the same concept with the same reason to change, not coincidental look-alikes.

## Special-General Mixture

Special-purpose code is not cleanly separated from general-purpose code.
**Why:** neither layer is clean; the general part is no longer reusable.
**Fix:** keep the general mechanism free of special knowledge; push the special case **up** (feature/UI) or **down** (driver/action subclass). A `hasSelection` boolean plus a dozen `if`s is this flag inside one method — represent the empty case as the normal one (`start == end`).

A **false abstraction** is this flag wearing a general name: `backspace(cursor)` claims to hide a UI detail the caller still must know. Replace it with the general operation the caller actually needs.

## Conjoined Methods

Two methods have so many dependencies that it is hard to understand one without the other.
**Why:** the cut went through a joint, not a seam.
**Fix:** recombine, or re-cut where each half stands alone. **Depth before length** (ch. 9.8): first make the function deep, then shorten it only if it stays independent. After a few dozen lines, further cuts rarely reduce *system* complexity.

## Comment Repeats Code

All of the information in a comment is immediately obvious from the code next to it.
**Why:** reading cost, zero information; trains readers to ignore comments.
**Fix:** delete it, or replace it with an **earned comment**.

## Implementation Documentation Contaminates Interface

An interface comment describes implementation details not needed by users of the thing being documented.
**Why:** callers start depending on internals; a decision leaked through the comment.
**Fix:** interface comments describe the abstraction and contract. How-it-works notes go inside the implementation.

## Vague Name

The name of a variable or method is so imprecise that it doesn't convey much useful information (`data`, `obj`, `tmp`, `manager`, `info`).
**Why:** a name is an abstraction; a fuzzy name is a fuzzy concept.
**Fix:** name the precise concept. Same word, same meaning, everywhere.

## Hard to Pick Name

It is difficult to come up with a precise and intuitive name for an entity.
**Why:** the entity is probably doing two jobs or has no identity.
**Fix:** reshape the entity until a precise name exists. Do not settle for a compromise name on a compromise module.

## Hard to Describe

In order to be complete, the documentation for a variable or method must be long.
**Why:** the words are exposing an interface that is too complex.
**Fix:** simplify the interface (pull complexity down, split, define errors out of existence) until it can be described simply.

## Nonobvious Code

The behavior or meaning of a piece of code cannot be understood easily.
**Why:** every reader re-derives it; some guess wrong (**unknown unknowns**).
**Fix:** names, the missing *why* comment, structure that matches expectation, or less cleverness. If you cannot make it obvious, that is the finding.
