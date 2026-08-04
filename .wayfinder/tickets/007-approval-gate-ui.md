---
id: "007"
title: The approval gate in the browser
type: prototype
status: open
parent: map
blocked_by: ["003", "004"]
---

# The approval gate in the browser

## Question

The phase-2 breakdown approval is the last human gate in the whole pipeline, and the one thing a restart must never assume. What does granting it look like in a board?

To settle: how the slice breakdown renders for judgement — acceptance commands, gate flags, dependencies, HITL/AFK — without becoming a wall; whether a human can edit slices there or only approve and reject; and how approval is written into the ledger's `gates` so a restarted board treats it as already decided rather than re-asking.

The rule from the run-state contract holds without exception: a gate absent from the ledger was never granted, whatever the screen appeared to show.

Blocked by The streaming protocol and The interview card, whose transport and visual grammar this reuses.
