# Red flags — descriptions and fixes

Each red flag is a *symptom*, not a law. Its value is that it is easy to spot, names a likely
complexity problem, and points at a structural fix. Use the name to make the problem concrete,
then change the structure — don't just paper over it with a comment.

For each flag below: what it looks like, why it raises complexity (its root cause —
**dependency** or **obscurity**), and how to fix it.

## Shallow module
**Looks like:** a class or function whose interface is nearly as much to learn as the work it
saves. A `FileInputStream` you must wrap in three other streams to actually read a line; a
method that takes ten parameters to do one obvious thing.
**Why:** the benefit (functionality hidden) barely exceeds the cost (interface to learn), so the
module adds net complexity. Often appears as **classitis** — a style that rewards many small
classes, each shallow.
**Fix:** make it deeper. Fold trivial wrappers into their caller, raise the abstraction so the
common path needs fewer arguments, or merge the module with the one it mostly delegates to.

## Information leakage
**Looks like:** the same design decision — a file format, a wire protocol, an assumed ordering,
a magic constant — appears in two or more modules, so a change to one forces a change to the
others. (Root cause: **dependency**.)
**Why:** the modules can't be understood or changed in isolation. Back-door leakage (a shared
assumption neither module documents) is worst because it's invisible until something breaks.
**Fix:** find the single module that should own the decision and hide it there. If two modules
genuinely share knowledge, pull that knowledge into a new module both depend on, or merge them.

## Temporal decomposition
**Looks like:** modules named for *when* things happen — `readFile`, then `processFile`, then
`writeFile` — each handling a slice of the same data structure or format.
**Why:** execution order is not a good axis for boundaries; the format knowledge leaks across all
the time-ordered pieces (leakage again). (Root cause: **dependency**.)
**Fix:** organize around the knowledge each module hides, not the sequence. One module that owns
the format and exposes read/write is deeper than three that each half-know it.

## Overexposure
**Looks like:** doing the common, simple thing forces the caller to confront rarely-used options
or configuration first.
**Why:** raises cognitive load for the 90% case to serve the 10% case. (Root cause: **obscurity**
of the simple path.)
**Fix:** give the common case a simple default-laden entry point; keep the rare options reachable
but out of the main path.

## Pass-through method
**Looks like:** a method whose body just calls another method, often with the same signature,
adding nothing.
**Why:** more interface to learn, more coupling between the two classes, no decision hidden.
(Root cause: **dependency** + shallow interface.)
**Fix:** let the caller invoke the deeper method directly; or, if the layers don't earn their
separation, combine them; or give the method a real, distinct responsibility.

## Pass-through variable
**Looks like:** a parameter threaded down through a chain of methods that don't use it, only to
reach the one deep method that does.
**Why:** every method in the chain now has interface it doesn't need, and adding a new variable
later means editing the whole chain. (Root cause: **dependency**.)
**Fix:** introduce a context object the chain already shares, or otherwise give the deep method
access without threading.

## Repetition
**Looks like:** the same non-trivial snippet appears in several places.
**Why:** a change must be made consistently in every copy (change amplification), and it's easy to
miss one.
**Fix:** extract the snippet into a method or module that *owns* that piece of knowledge — but
only when the copies are the same concept with the same reason to change, not coincidental
look-alikes.

## Special-general mixture
**Looks like:** a general-purpose mechanism with a special case wired into it, or a general
helper that reaches back into the specific caller it was extracted from.
**Why:** neither layer is clean; the general part is no longer reusable and the special part is
hard to find. (Root cause: **obscurity** + leakage.)
**Fix:** keep the general mechanism free of special knowledge; push the special case up to the
caller that owns it.

## Conjoined methods
**Looks like:** two methods you can't understand independently — to read one you must hold the
other in your head (shared temporary state, ping-ponging calls, interleaved invariants).
**Why:** splitting added interface without adding independence; the cut went through a joint, not
a seam.
**Fix:** either recombine them into one coherent method, or re-cut along a boundary where each
half stands alone. Length alone never justifies a split.

## Comment repeats the code
**Looks like:** `i++; // increment i`. The comment restates tokens already on the line.
**Why:** adds reading cost with zero information; trains readers to ignore comments.
**Fix:** delete it, or replace it with a comment that adds what the code can't say — the *why*,
the units, the invariant, the boundary condition.

## Implementation detail in an interface comment
**Looks like:** a method's doc describing *how* it works (which data structure, which algorithm)
rather than only *what* a caller needs.
**Why:** callers start depending on internals; you've leaked an implementation decision through
the comment. (Root cause: **dependency**.)
**Fix:** interface comments describe the abstraction (what + contract); put how-it-works notes
inside the implementation.

## Vague name / hard to pick a name
**Looks like:** `data`, `obj`, `tmp`, `manager`, `info`; or sitting stuck unable to name a
variable or method well.
**Why:** a name is a form of abstraction — a fuzzy name means a fuzzy concept. The struggle to
name something often means the thing itself is doing two jobs or has no clear identity. (Root
cause: **obscurity**.)
**Fix:** name the precise concept; if no precise name exists, that's a signal to reshape the
entity until one does. Names should be precise *and* consistent (same word, same meaning,
everywhere).

## Hard to describe
**Looks like:** an interface comment that runs long or needs many caveats and special-case
clauses to be accurate.
**Why:** the documentation is complex because the *interface* is complex; the words just expose
it.
**Fix:** simplify the interface (pull complexity down, split responsibilities, define errors out
of existence) until it can be described simply.

## Nonobvious code
**Looks like:** a reader has to stop, re-read, and reverse-engineer what a piece of code does or
why it's there.
**Why:** obscurity — the meaning isn't on the surface, so every reader pays a re-derivation tax
and some will guess wrong (unknown unknowns).
**Fix:** improve names, add the missing *why* comment, restructure to match expectations, or
remove the cleverness. If you can't make it obvious, that itself is the warning.
