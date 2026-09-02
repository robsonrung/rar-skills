---
name: to-prototype
description: Build a throwaway prototype (spike) that answers one design question only running code can settle — a shareable single-file HTML demo for a state model or business logic, or several radically different UI variants on one route — then extract the decision and discard the code. Use when the user says prototype this, spike this, try it quick and dirty, sanity-check whether this state machine / data model / logic feels right, or show me a few options for this page; or as the workflow's detour when `interview-me` hits a frontier question only running code can settle, or `coding-design-plan` needs a spike for one slice. Distinct from `coding-design-plan` (owns the prototype-vs-tracer-bullet decision — a tracer bullet is production-quality and kept), `tdd` (rebuilds the production version test-first), and `brainstorm` (explores ideas in prose, not code).
---

# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape, and the governing rule is the leitwort: **prototype code never graduates**. The deliverable is a decision, not code.

## Pick a branch

Identify which question is being answered, using the user's prompt, the surrounding code, or by asking if the user is around:

- **"Does this logic / state model feel right?"** → read [references/logic.md](references/logic.md). Build a single shareable HTML file (free-play buttons plus tabbed guided walkthroughs) that pushes the state machine through cases that are hard to reason about on paper, and that a non-developer can drive.
- **"What should this look like?"** → read [references/ui.md](references/ui.md). Generate several radically different UI variations on a single route, switchable via a URL search param and a floating bottom bar.

The two branches produce very different artifacts, so getting this wrong wastes the whole prototype. If the question is genuinely ambiguous and the user isn't reachable, default to whichever branch better matches the surrounding code (a backend module → logic; a page or component → UI) and state the assumption at the top of the prototype.

A question that reading the code, the docs, or a recorded decision already answers never earns a prototype. And if you catch yourself wanting to keep the code, it was a tracer-bullet question — the rule for choosing between the two lives in `coding-design-plan`, not here.

## Rules that apply to both

1. **Throwaway from day one, and clearly marked as such.** Locate the prototype code close to where it will actually be used (next to the module or page it's prototyping for) so context is obvious, but name it so a casual reader can see it's a prototype, not production. For throwaway UI routes, obey whatever routing convention the project already uses; don't invent a new top-level structure. Say the rule out loud when you cut a corner: _"skipping error handling — prototype code never graduates, and the question is about the state shape."_
2. **Trivial to run.** A UI prototype starts from one command in the project's task runner: `pnpm <name>`, `python <path>`, `bun <path>`, etc. A logic demo is a single HTML file the user double-clicks. Either way, no thinking required to start it.
3. **No persistence by default.** State lives in memory. Persistence is the thing the prototype is _checking_, not something it should depend on. If the question explicitly involves a database, hit a scratch DB or a local file with a clear "PROTOTYPE, wipe me" name.
4. **Skip the polish.** No tests, no error handling beyond what makes the prototype _runnable_, no abstractions. The point is to learn something fast.
5. **Surface the state.** After every action (logic) or on every variant switch (UI), print or render the full relevant state so the user can see what changed.
6. **Capture it when done.** Fold any validated decision into the real code, then capture the prototype itself as a **primary source**: commit it to a throwaway branch, out of main, and leave a context pointer to that branch on the implementation issue. Capture the answer too (the verdict and the question it settled) in the issue or a commit. The main branch keeps only the validated decision.

## Output contract

When the prototype has done its job, report four things — this is what the caller consumes (`interview-me` records the answer as a settled node; `coding-design-plan` folds it into the slice plan; `to-prd` may paste the snippets):

- `question` — the one sentence it was built to answer, with a decidable outcome.
- `answer` — the decision, including negative or unresolved results ("the library can't do X" is exactly the decision the prototype existed to buy).
- `snippets` — the decision-rich parts only (the state machine, reducer, schema, or type shape that encodes the decision more precisely than prose). These may be pasted into the PRD: the one exception to `to-prd`'s no-code-in-the-PRD rule. Demo scaffolding stays behind.
- `disposition` — where the prototype now lives (the throwaway branch) and confirmation that nothing from it landed on main except the validated decision.

Then hand back to the caller: "return to `interview-me` — Q<n> is settled" when the interview invoked the detour, "return to `coding-design-plan`" when a slice did, or simply the report when the user asked for the spike directly. A prototype is never the last thing that happens; the decision goes somewhere.
