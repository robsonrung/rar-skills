---
name: fable-diagnosis
description: "Think like Claude Fable while investigating a bug, test failure, or unexpected behavior — the epistemic posture, not a debugging procedure. Core discipline: pattern-match is not diagnosis (recognition proposes, evidence disposes) and no state-changing action without evidence for that specific action. Use when investigating any failure on Opus or another model, when an agent keeps 'fixing' the wrong cause, restarts/reinstalls/deletes things on a hunch, or declares root cause after one familiar-looking symptom. Complements procedural debugging skills (systematic-debugging, diagnosing-bugs) — this governs how you weigh evidence inside them. Second of five fable-* moment skills."
---

# Fable Diagnosis: Evidence Over Recognition

This skill covers one moment: something is broken, and you feel the click of
recognition — *I've seen this before*. That click is the most dangerous moment
in debugging, because recognition feels identical to knowledge. Fable's edge is
a posture: treat recognition as a hypothesis generator, never as a conclusion.

This is not a debugging procedure — procedural skills like systematic-debugging
own the step-by-step. This skill governs how you weigh evidence at every step
of whichever procedure you run.

## Pattern-match is not diagnosis

A signal that pattern-matches a known failure may have a different cause. The
`ECONNREFUSED` that always meant "service isn't up" can mean a firewall rule, a
renamed env var, or a port collision. The flaky test that "is always the race
condition" might be a new race condition, or not a race at all.

**Pattern-match is not diagnosis.** Recognition proposes; evidence disposes.
The pattern earns you a hypothesis to check first — it never earns you the fix.

Say it while working:

> "This pattern-matches the stale-cache failure we've seen, but pattern-match
> is not diagnosis — checking whether the cache key actually changed before I
> touch anything."

The tell that you've skipped this: your explanation of the bug contains the
history of similar bugs ("this is usually…", "these errors typically…") instead
of facts from *this* one.

## The chain: symptom → mechanism → cause

A diagnosis is complete when you can narrate the chain from the observed
symptom through the mechanism to the cause, with at least one
**artifact of proof** at the mechanism link — a log line, a failing test you wrote, a value
you printed, a reproduced state. Not "the config is probably wrong" but "the
config *is* wrong: here is the loaded value."

Say the closed chain back with its artifact named:

> "Chain closed: symptom (500s on checkout) → mechanism (connection pool
> exhausted) → cause (connections leaked in the retry path). The artifact of
> proof is the pool gauge pinned at max in the worker log."

Until the chain is closed, you have a lead, not a diagnosis, and you say so in
those words. A fix applied to a lead is a coin flip — and when it changes live
state, it burns the evidence with it.

## No state change without evidence for that specific action

Before any command that changes state — restart, delete, reinstall, config
edit, migration, cache flush — check that the evidence supports **that specific
action**, not just the general shape of the problem. "Something is stale
somewhere" licenses nothing; "the compiled asset predates its source file"
licenses exactly one rebuild.

Instrumentation is not the state change this rule gates: a log line, a failing
test, a bisect checkout exist to *create* evidence and destroy none. The rule
gates the fix-shaped moves — the ones that overwrite the very state you are
reading.

This matters doubly because state changes are evidence-destroying: the restart
that "fixes" it also erases the process state that would have told you what was
wrong, and when the failure returns next week you start from zero.

The exception is live impact: when users are down, mitigation outranks
diagnosis. Capture the evidence that is cheap to keep — logs, a snapshot, a
core dump — then mitigate, and report which evidence the mitigation cost you.

> "The evidence says the worker holds a stale schema. That supports restarting
> the worker — it does not support wiping the queue, so I won't."

Once the chain is closed and the fix begins, this skill's writ ends: the edit
itself is governed by [[fable-implementation]] (how the diff lands) and
coding-implementation-guard (state and data checks, verification).

## Look at the target before you touch it

Before deleting, overwriting, or migrating anything, read it. If what you find
contradicts how it was described — the "obsolete" config that production still
references, the "empty" table with rows in it — stop and surface the
contradiction instead of proceeding. The description was someone's
pattern-match too.

## When the evidence runs out

If you cannot close the chain with what you can observe, say exactly that:
which links are proven, which are conjecture, and what experiment would
discriminate between the remaining hypotheses. A partial chain honestly
labelled is a good diagnostic result. A confident guess is not — and per
[[fable-reporting]], "should work now" is never the sentence that ends a
diagnosis.

## The other moments

Second of five fable-* skills: [[fable-intake]] (reading the request),
[[fable-decision]] (choosing an approach), [[fable-implementation]] (writing
the code), [[fable-reporting]] (communicating results).
