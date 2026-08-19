# Design principles

Read on `design`, and on `improve` when the change is a new or reshaped interface. These are Ousterhout's official 16 (2nd ed. summary), stated as checks you can fail.

## Contents

1. [The sixteen](#the-sixteen)
2. [How to apply them](#how-to-apply-them)
3. [Taking it too far](#taking-it-too-far)

## The sixteen

1. **Complexity is incremental** — sweat the small stuff. A "this'll do" that leaks one decision is how systems rot. If you cannot name the small increment you just accepted, you are not **strategic**.
2. **Working code isn't enough** — the goal is a system that stays cheap to change. A green test suite is not a design.
3. **Continual small investments** — spend a steady slice of each change on design (about 10–20%). Not a big-upfront phase. Not a someday rewrite.
4. **Modules should be deep** — simple interface, lots of hidden functionality. Unix I/O is deep; a class you must wrap in three others to read a line is shallow (**classitis**).
5. **Common usage must be simple** — the 90% path is default-laden. Rare options stay reachable and out of the way (**overexposure** if not).
6. **Simple interface over simple implementation** — one implementer suffers once; every caller suffers forever. This *is* pull complexity downward.
7. **General-purpose modules are deeper** — a slightly general interface ("insert text at a position") hides more than a special-purpose one ("handle backspace"). Do not speculative-configure.
8. **Separate general-purpose and special-purpose code** — specialization is pushed to the caller that owns it, or down into a helper that does not pollute the general API.
9. **Different layer, different abstraction** — adjacent layers that share an abstraction are a missing boundary. Pass-through methods and pass-through variables are the usual evidence.
10. **Pull complexity downward** — when complexity is unavoidable, the module absorbs it. Do not export config knobs the module could decide. Do not over-pull a policy the module cannot know.
11. **Define errors out of existence** — redesign so the error is a normal case (delete a missing range succeeds; unset returns the default). Then mask low, aggregate, or crash. Do not thread recovery through every caller.
12. **Design it twice** — two or three *meaningfully different* shapes, compared on interface simplicity and the three symptoms (change amplification, cognitive load, unknown unknowns). Skipping this on a public interface is a process defect.
13. **Comments describe what is not obvious** — an **earned comment**. Repeating tokens is a red flag.
14. **Design for ease of reading, not ease of writing** — the writer pays once; readers pay forever. Cleverness that saves keystrokes fails this.
15. **Increments are abstractions, not features** — each change should leave behind a deeper module, not a new special case. This is how **stay strategic** looks in a pull request.
16. **Decide what matters** — name the few things this situation depends on, minimize that set, emphasize only those. Everything else is noise.

## How to apply them

On `design`, you must hit 4, 12, and 13 (deep, twice, comments first). Hit 11 if the interface has error cases. Hit 16 if the user cannot say what is important.

On `improve`, prefer 15 over adding a feature-shaped branch. If you cannot leave a deeper abstraction, say so and keep the change **smallest coherent shape**.

Name the principle you used in the brief. Do not list all sixteen.

## Somewhat-general gate (ch. 6)

From the official 2nd-edition extract (Stanford, ch. 6). Over-specialization is often the largest source of extra complexity. A general-purpose interface is usually *simpler, deeper, and smaller* than a special-purpose one — even if the class is only ever used one way.

Answer all three before locking an interface. A miss on any one is a reason to **design it twice** again.

1. **Simplest interface that covers today's needs?** Fewer methods with the same capability usually means more general methods — only while each method's own API stays simple. `backspace` + `delete` + `deleteSelection` is three methods for one job; one `delete(start, end)` is the general form.
2. **How many call sites will this method have?** One planned call site is a red flag that the method is too special-purpose. Put that knowledge in the caller.
3. **Is it easy to use for today's job?** If callers must write a lot of extra code, you over-generalized. A text API of only single-character insert/delete forces the editor to loop; range operations belong on the text module.

Functionality reflects current needs. The interface does not — it stays usable for other callers without encoding today's *specific* one. The word *somewhat* is load-bearing: do not build a framework that is hard to use for today's job.

### False abstraction

If callers must read the method body to learn a fact they need (which characters `backspace` removes), the method is a **false abstraction**. That is obscurity, not hiding. When the details matter, make them explicit (`delete(start, end)`).

### Push specialization up or down

Specialization cannot be eliminated. Separate it from the general mechanism:

- **Up** — UI/feature code owns backspace, selection, and "what a fence means." The lower module keeps `insert`/`delete`.
- **Down** — device drivers implement a general "read/write a block" interface using device-specific commands, so the OS never learns each device.

A class may mix *this* mechanism's special case with *that* mechanism's general core when they are the same knowledge (text-undo handlers live next to text; the history list does not).

### Eliminate the special case

Design the normal case so the edge needs no extra `if`. An empty selection is `start == end`, not a boolean `hasSelection`. Copying an empty selection inserts zero bytes; deleting it rewrites the same line. Chapter 10 is the same move for exceptions.

## Taking it too far

Ousterhout flags over-application in several chapters. Do not:

- hide information the caller must actually know (ch. 5.9)
- pull a policy the module cannot decide (ch. 8.3)
- define away an error the caller must handle (ch. 10.9)
- enforce consistency that fights a better local design you are not converting (ch. 17.3)
