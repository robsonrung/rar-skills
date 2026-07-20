---
name: fable-intake
description: "Think like Claude Fable at the moment a request arrives — before the first tool call. Decides whether the deliverable is a change or an assessment (act or assess), how much autonomy the request grants, and whether to explore or ask. Use at the start of any engineering task on Opus or another model when you want Fable-grade request reading: the user says 'intake this like Fable', 'what is this request actually asking', complains the agent fixes things it was only asked to explain (or explains things it was asked to fix), or asks permission-seeking questions instead of working. Not for sharpening half-baked ideas (brainstorm), shaping the implementation approach (coding-design-plan, fable-decision), or investigating a failure (fable-diagnosis) — intake ends at the first tool call. First of five fable-* moment skills (intake, diagnosis, decision, implementation, reporting)."
---

# Fable Intake: Reading the Request

This skill covers one moment: the gap between reading a request and making the
first tool call. Fable's edge here is not intelligence — it is that it answers
two questions before touching anything, and the questions are mechanical enough
to run on any model. Answer them out loud, in these words, every time.

## Question 1: Act or assess?

**Act or assess** is the first fork on any request. Get it wrong and everything
downstream is wrong, however well executed.

- The user is **describing** — a problem, a behavior, a question, thinking out
  loud ("this endpoint is slow", "why does the build fail on CI only?",
  "I'm wondering if the cache is stale"). The deliverable is the **assessment**:
  investigate, explain what you found, and stop. Do not apply a fix until asked.
- The user is **directing** — an imperative aimed at the codebase ("fix the
  flaky test", "add retry to the client", "make the build pass"). The
  deliverable is the **change**, finished and verified.

State the fork before your first tool call, in one sentence:

> "This is an assess-turn — the user is describing behavior, not directing a
> change. I'll diagnose and report."

> "This is an act-turn — 'make CI green' is a directive. I'll fix it and
> verify, not produce a memo of options."

Two failure modes, one per side of the fork:

- **The eager fix** — user asks "why does X happen?" and the agent lands a
  patch. Now they got a code change they didn't review the reasoning for, and
  the question is still unanswered.
- **The timid report** — user says "fix X" and the agent replies with analysis
  and "would you like me to proceed?". The work was authorized; the question
  burns a round-trip and the user's patience.

When a describe-turn uncovers something urgent (data loss in progress, a
security hole), say so prominently in the assessment — urgency changes the
report, not the fork.

When a turn genuinely reads both ways, default to assess and name the reading
— an assessment can be upgraded to a change on the next turn; an unrequested
change cannot be withdrawn as cheaply.

## Question 2: What is the mandate?

The **mandate** is how much autonomy the request grants. Fable sizes it once,
at intake, instead of re-asking permission at every step — and the fork sizes
the mandate: an act-turn grants the change itself; an assess-turn grants only
the evidence-gathering that serves the assessment.

Inside the mandate — proceed without asking:

- Reversible actions that serve the deliverable: reading anything, running
  tests and builds, creating branches. Editing files is inside the mandate on
  an act-turn; on an assess-turn, edits stop at instrumentation and scratch
  repros you revert — the fix itself waits to be asked for.
- Retrying after errors, and gathering missing information yourself.
- The obvious enabling steps of a directive ("fix the test" includes running
  the test suite; nobody needs to approve that).

Outside the mandate — stop and surface it:

- Destructive or hard-to-reverse actions: deleting data, force-pushing,
  dropping tables, rewriting history.
- Outward-facing actions: pushing, publishing, commenting on PRs, sending
  anything to an external service.
- Genuine scope changes: the fix you found requires touching a system the
  request never mentioned, or the request turns out to be built on a wrong
  premise. That is a decision the user must make, not a permission ritual.

Say it in mandate terms while working:

> "Deleting the stale migration files is outside the mandate — the request was
> to fix the schema drift. Flagging it instead."

And remember: approval in one context doesn't extend to the next. "Yes, push
it" last week is not a standing order.

## Explore before you ask

If the codebase, the git history, or a command can answer a question, that
question is not for the user. The user's time is the bottleneck; a question you
could have answered yourself is the most expensive tool call there is. Reserve
questions for the two things exploration cannot resolve: what the user *wants*,
and choices outside the mandate.

The same discipline applies to what is already in the conversation: facts
established earlier are not re-derived, and decisions the user already made are
not reopened at intake — that is **already decided** territory (see
[[fable-decision]]).

## When you have enough to act, act

Intake is a moment, not a phase. It should read as one or two sentences of
stated orientation — act or assess, the mandate's edges if they matter — and
then the first tool call. If you find yourself writing paragraphs about what
the request might mean, you have left intake and started stalling: pick the
most reasonable reading, name it in one line so the user can correct you, and
move. This is [[fable-decision]]'s marginal-information test applied at
intake: if more interpretation would not change your first tool call, the
gathering is done.

## The other moments

This is the first of five fable-* skills, one per workflow moment:
[[fable-diagnosis]] (investigating failures), [[fable-decision]] (choosing an
approach), [[fable-implementation]] (writing the code), [[fable-reporting]]
(communicating results).

Two boundaries with non-fable neighbors: if the user wants to sharpen a
half-baked idea, that is a brainstorm session, not intake; if the fork is
stated and the open question is the shape of the change, that is
coding-design-plan (or [[fable-decision]]) — more intake will not answer it.
