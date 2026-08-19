---
name: software-design-philosophy
description: >
  Reduce long-term complexity in an app or codebase using Ousterhout's
  Philosophy of Software Design (2nd ed.) — deep modules, information hiding,
  strategic investment, comments as design, and deciding what matters — with
  Brooks' conceptual integrity. Use when designing, improving, or maintaining
  modules, APIs, or codebases; when code works but is expensive to change;
  when choosing a boundary, writing comments first, renaming for precision,
  adding a feature into existing design, or reviewing design quality; or when
  the user says deep modules, shallow modules, tactical tornado, design it
  twice, pull complexity down, information leakage, or decide what matters.
  Distinct from clean-code (local smell refactoring), tdd (the red-green loop),
  design-patterns (GoF), and architecture-lens (connascence and layer
  placement). Under design-gate this skill is read-only.
---

# A Philosophy of Software Design

Grounded in Ousterhout, *A Philosophy of Software Design*, 2nd ed. (all 22 chapters plus the official principle and red-flag summaries). Brooks' **conceptual integrity** stays as the second anchor.

Complexity is anything about structure that makes software hard to understand or modify. It is incremental. The job is to keep the system cheap to change.

## Outcome

- **Result:** a named design (or a named fix) that lowers complexity, plus the next move.
- **Next consumer:** the user, or `design-gate` / an implementation skill after they accept the shape.
- **Done:** the route's required fields are filled; every finding uses an official red-flag or principle name; rejected alternatives are named; if this turn edited code, the project's checks that you ran are reported (or you say you could not run them).
- **Intent:** stop two failures — shipping working code that is expensive to live with, and treating a local cleanup (`clean-code`) as if it were a module-boundary decision.

State these **leitwörter** by name as you act, not only in headings:

- **strategic** — invest a little design now so the next change is cheaper. The opposite is **tactical** ("just make it work") and the **tactical tornado** (the person who ships fastest by leaving a mess).
- **deep module** — a simple interface hiding a lot of functionality. Cost is the interface; benefit is what it hides. A **shallow module** costs about as much to learn as to inline.
- **information leakage** — one design decision reflected in two or more modules. That *is* a **change ownership** failure; give the decision one owner.
- **design it twice** — for any consequential interface, sketch two or three *meaningfully different* shapes before coding.
- **stay strategic** — when modifying existing code, do not tack on a special case that makes the design worse. Fit the change, or improve the design.
- **decide what matters** — name the few things this situation depends on, minimize that set, and emphasize only those.
- **reader, not writer** — complexity is judged by the next person to change the code. If it is simple only to you, it is complex.
- **conceptual integrity** / **smallest coherent shape** — one model, no larger than the problem.

Modelled sentence: *"This is **tactical** — a special case on a **shallow module**. **Design it twice** keeps **conceptual integrity**; the cost is one extra hour now vs **information leakage** later."*

A second modelled sentence, from the official extract: *"`backspace(cursor)` is a **false abstraction** — the UI still has to know which characters vanish. One `delete(start, end)` has **leverage**; the special methods do not."*

## Classify the job

Pick one route and stay on it:

| Route | Signal |
|---|---|
| `design` | New module, API, or feature shape; "how should this be structured" |
| `improve` | Existing code that works; add a feature, rename, deepen, pull complexity down |
| `review` | Diff, plan, or PR; design-gate; "is this too complex" |

If the user asked only for a local tidy (rename, extract, flatten) with no boundary question, stop and say this is `clean-code`. If they asked for red-green tests, stop — that is `tdd`.

**Authority.** `review` and any `design-gate` invocation are read-only: findings only, no edits, no test runs. `design` and `improve` may edit the files in the user's request (or the files a named finding requires). They do not authorize drive-by refactors of unrelated modules.

## Evidence

Inspect the live code or the stated design. Do not invent a module.

Read budget: enough to name the abstraction, the *informal* interface (everything a caller must know — not just the signature), and one red flag or principle. Stop when another file would not change the decision.

Ask **reader, not writer**: would a second developer need a fact that is not in the interface? That fact is either leakage or obscurity.

If there is no repo, use the user's constraints. Mark those `assumed`.

## Routes

**`design`** — state the abstraction in one sentence (what the caller gets to *not* know). Then **design it twice**. Functionality matches today's needs; the interface does not — it is *somewhat general*. Over-specialization is the usual source of extra complexity: do not put `backspace`/`deleteKey`/`deleteSelection` on the text module. Answer the three questions in `references/principles.md` before coding. Pull complexity down; define errors out of existence; write the interface comment *before* the body so a caller need not read the implementation. Read `references/principles.md`, then `references/comments-and-names.md`.

**`improve`** — **stay strategic**. Design is never finished: the first cut is usually wrong, and implementation is how you find that. If the change is a special case that fights the design, fix the design (or say why you will not). Keep comments next to the code they describe; check the diff for comment drift. Read `references/modifying.md`. Load `references/comments-and-names.md` when names or comments are the work. Load `references/trends-and-performance.md` only when the question is a trend (TDD, patterns, inheritance) or a hot path.

**`review`** — walk the official red flags in `references/red-flags.md`. Name each finding. Then run the three Brooks checks. If a category is clean, write `clean`.

Load `references/chapter-map.md` only when you need to route a question to a specific chapter.

## Output contract

Standalone `design` or `improve`:

```text
## Philosophy of Software Design
Route: design | improve
Abstraction: <one sentence>
Principles: <which of the 16 you used>
Red flags: <name or clean>
Strategic vs tactical: <one line>
What we rejected: <one alternative and its cost>
Next move: <one action>
```

If you edited code, add: files touched, **behavior-preserving** or the exact behavior change, checks run.

Standalone `review`:

```text
## Design review (Philosophy of Software Design)
### Findings
- [file:line] <red-flag name> (<dependency|obscurity>) — <what's complex>. Fix: <structural change>.
### Conceptual integrity
<which of conceptual integrity / change ownership / smallest coherent shape holds>
### Verdict
<one line>
```

When run as a **reviewer** under `design-gate`:

1. `verdict`: `proceed` or `revise`
2. `conceptual_integrity_check`
3. `blocking_findings`
4. `advisory_findings`
5. `required_changes`

`revise` when a leaked decision, a shallow public interface on a new module, or a tactical special-case that will have to be undone is load-bearing. Cosmetic naming is advisory.

## Gotchas

1. Do not turn a one-line bug fix into a design exercise. Match effort to stakes.
2. Do not preserve an existing pattern when the broken model *is* the request.
3. Do not confuse consistency with conceptual integrity — repeating a mistake consistently is still a defect.
4. Do not invent findings to fill a category. `clean` is valid.
5. Do not quote or reconstruct source text from the book this skill distills.
6. **Depth before length** (ch. 9.8). After a few dozen lines, shortening a function rarely helps the system. More tiny functions means more interfaces and **conjoined methods**. Do not replace an **earned comment** with a ten-word method name. Small classes that leak one format are usually *too many* classes — merge them.
7. Do not hide a design decision in a commit message. Comments belong in the code.
8. `private` plus a getter is not information hiding. If callers must know the field exists, it is in the interface.
9. Lots of documentation is often a **hard to describe** flag, not a virtue. Simplify the design.

## References

Load only the file the current step names:

- `references/principles.md` — the 16 official principles as operational checks
- `references/red-flags.md` — official red-flag catalog and fixes
- `references/comments-and-names.md` — comments (ch. 12–15) and names (ch. 14)
- `references/modifying.md` — existing code, consistency, obviousness, what matters (ch. 16–18, 21)
- `references/trends-and-performance.md` — trends and performance (ch. 19–20)
- `references/chapter-map.md` — chapter → file, when a question does not fit a route
