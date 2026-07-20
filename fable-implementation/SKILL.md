---
name: fable-implementation
description: "Think like Claude Fable while writing code — the discipline of landing changes, not a style guide. Core discipline: produce a native diff (a change indistinguishable from the surrounding authors' work in naming, idiom, comment density, and trust level), write only earned comments (constraints the code can't show — never notes to the reviewer), and keep the diff to what the task requires. Use during any code edit on Opus or another model, when an agent's diffs are recognizably machine-written (over-commented, defensively padded with checks the codebase doesn't use, renamed beyond the task), or when reviewing why a change 'smells like AI'. Distinct from clean-code (refactoring existing mess) and coding-implementation-guard (safety/verification) — this governs how new lines land. Fourth of five fable-* moment skills."
---

# Fable Implementation: The Native Diff

This skill covers one moment: hands on the code. Fable's edge here is a single
test applied line by line: could a reviewer tell where the existing code ends
and your change begins? When the answer is no, you have written a **native
diff** — a change that reads as if the codebase's own authors wrote it.

A native diff is not a style preference. Every seam a reviewer can spot — a
sudden comment burst, a foreign idiom, an unprompted defensive check — is a
line they must stop and interrogate: *is this load-bearing, or is it noise?*
Seams tax every future reader. Writing the native diff is a correctness
courtesy.

The neighbors carve the edges: clean-code repairs code that already exists,
and coding-implementation-guard checks that the change is safe and verified.
This skill governs one thing — how the new lines read.

## Match what is actually there

Before writing, read the neighborhood — the function above, the sibling module,
the nearest test — and match three things:

- **Naming and idiom.** If the file uses early returns, use early returns. If
  errors bubble as exceptions, don't introduce result tuples. If tests build
  fixtures with a helper, don't inline your own.
- **Comment density.** Match the surrounding rate. A codebase that comments
  once per hundred lines does not want your change commented once per five.
  Density never vetoes an earned comment, though — a constraint the code
  can't show gets written down even in a file with no comments at all.
- **Trust level.** Match how much the surrounding code defends itself. If
  callers are trusted with non-null inputs, your function trusts them too.
  Unprompted null checks, try/except wrappers, and fallback branches the
  codebase doesn't use are **defensive theater** — they read as safety but are
  really seams, and they bury the checks that *are* load-bearing. Matching
  applies between trusted internal callers only: data crossing a trust
  boundary — user input, an external API's response, anything deserialized —
  gets validated however lax the neighbors are. A check at a trust boundary is
  load-bearing, not theater, even when it is the first of its kind in the file.

Say it while working:

> "This file handles absence with a sentinel, not exceptions — my change
> follows, even though I'd default to raising."

> "I was about to wrap this in try/except — that is defensive theater here;
> errors bubble as exceptions everywhere else in this module."

House style wins ties. Your better idiom, applied to one function, makes the
codebase worse — improving the idiom everywhere is a different task with its
own mandate (that task is clean-code).

## Earned comments only

A comment is **earned** when it carries a constraint the code cannot show: an
invariant, an external system's quirk, a non-obvious *why*. Everything else is
noise, and two kinds are poison:

- **Narration** — `// increment the counter`. The code already says it.
- **Notes to the reviewer** — `// moved from utils.py`, `// this now handles
  the edge case correctly`, `// updated to use the new API`. These talk to the
  person reading the PR, not the person reading the code next year. They are
  stale the moment the PR merges. The diff itself is where provenance lives.

The test, said out loud:

> "This comment isn't earned — it says what the next line does. Deleting."

> "This one is earned: nothing in the code explains why the retry cap is 3
> — it's the payment gateway's idempotency window."

## The diff is scoped by the task

Touch what the task requires. The adjacent misnamed variable, the dead import
two functions down, the function that begs to be split — noticing them is
good judgment; fixing them inside this diff is scope creep that makes the
change harder to review and riskier to revert. Note them for a separate
change and keep the diff at its **smallest coherent shape**.

The exception is honest necessity: when the task genuinely cannot land without
a wider change (the signature you must alter has nine call sites), then the
wider change *is* the task — say so as you do it, don't smuggle it.

## Read the diff back

Before reporting done, run the native-diff test once on the whole change: read
it as the reviewer will, hunting seams. Say the verdict:

> "Rereading the diff as the reviewer will: the comment at line 40 narrates,
> the null check at 82 is defensive theater — trimming both. Now it reads as a
> native diff."

## The other moments

Fourth of five fable-* skills: [[fable-intake]] (reading the request),
[[fable-diagnosis]] (investigating failures), [[fable-decision]] (choosing an
approach), [[fable-reporting]] (communicating results).
