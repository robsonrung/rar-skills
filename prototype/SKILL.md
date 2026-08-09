---
name: prototype
description: >-
  Throwaway prototype (spike) discipline — settle a design unknown that only
  running code can answer, extract the decision and its decision-rich
  snippets, then discard the code. Use when the user says prototype this,
  spike this, try it quick and dirty, test whether this library/data
  model/state machine/UI feel works, or when a pipeline frame phase hits such
  an unknown. Distinct from `coding-design-plan` (owns the
  prototype-vs-tracer-bullet decision rule — a tracer bullet is
  production-quality and kept), `tdd` (rebuilds the production version
  test-first), and `brainstorm` (explores ideas in prose, not code).
---

# Prototype — Spike to Settle a Design Unknown

A prototype exists to answer one question, and only a question that running
code can answer: does this state machine shape hold up, does the data model
fit, is this library viable, does this UI feel right. Reading the code, the
docs, or an ADR answers most design questions — those never earn a prototype.
The governing rule is the leitwort: **prototype code never graduates**. The
deliverable is a decision, not code.

## The discipline

1. **State the prototype question first.** Before writing a line, write the
   question the prototype must answer, in one sentence with a decidable
   outcome: *"can the reducer express undo without a history array?"* — not
   "explore the reducer". No question, no prototype.
2. **Timebox it.** Set the box when you state the question (an hour or two is
   typical; a day is the ceiling). When the box expires, the answer is
   whatever the evidence says so far — "unresolved, and here is why" is a
   valid answer.
3. **Build the cheapest thing that answers the question — and say so out
   loud.** No tests, no error handling, no naming polish: *"skipping error
   handling — this is a prototype and the question is about the state shape."*
   Saying it marks the corners as cut on purpose, so nobody (including you)
   mistakes them for the standard. Hardcode everything the question doesn't
   touch.
4. **Extract the decision.** Record the answer plus the decision-rich snippets
   — the state machine, reducer, schema, or type shape that encodes the
   decision more precisely than prose. These snippets may be pasted into the
   PRD: the one exception to `to-spec`'s no-code-in-the-PRD rule. Trim to the
   decision-rich parts; the demo scaffolding stays behind.
5. **Throw it away.** Delete the branch or directory. **Prototype code never
   graduates** to production — the production version is rebuilt test-first
   via `tdd`, with the extracted decision as its spec. The rebuild is not
   wasted work; the prototype bought the certainty that makes the rebuild
   fast.

## Prototype vs tracer bullet

Deliberately different tools — the decision rule for which one a task needs
lives in `coding-design-plan`, not here:

- A **prototype** answers *"what shape should it be?"* — throwaway by
  contract, quality deliberately absent.
- A **tracer bullet** answers *"does the path work end to end?"* — a
  production-quality **vertical slice** that is kept and grown.

If you catch yourself wanting to keep it, it was a tracer bullet question —
stop, and restart under that discipline instead of promoting junk.

## Output contract

Return: `question` (the one it was built to answer), `answer` (the decision,
including negative or unresolved results), `snippets` (the decision-rich
parts, for the PRD), and `disposition` (discarded — with the deletion done,
not promised).

## Gotchas

1. Do not let a prototype quietly become the implementation branch — the
   moment real work lands on it, you are shipping code with quality
   deliberately absent.
2. Do not prototype what reading the code or docs already answers — the
   prototype question must require *running* code.
3. Record negative results too: "the library can't do X" is exactly the
   decision the prototype existed to buy, and it saves the next person the
   same spike.
4. Do not polish. Time spent on naming, structure, or edge cases in a
   prototype is time stolen from the question.
