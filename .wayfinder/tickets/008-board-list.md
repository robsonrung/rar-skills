---
id: "008"
title: The board list
type: prototype
status: open
parent: map
blocked_by: ["002"]
---

# The board list

## Question

With several features in flight, what does the view above the boards look like?

To settle: what one row tells you at a glance — station, status, how long it has been stuck, whether it needs you; how boards needing a human are made unmissable, given `awaiting_human` is the whole reason to look; how a new board is started from here; and what archived boards do to the list over time.

The existing board already renders `awaiting_human` as a NEEDS YOU badge — carry that, do not reinvent it.

Blocked by Board lifecycle and storage layout, which defines what a board record even contains.
