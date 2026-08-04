---
id: "003"
title: The streaming protocol
type: prototype
status: open
parent: map
blocked_by: ["001"]
---

# The streaming protocol

## Question

What flows between server and browser while a board is live, and over what transport?

To settle: SSE versus WebSocket (SSE is one-way and simpler, but answers must travel upstream somehow); the event vocabulary — question, token, station change, tool call, gate reached, run complete, error; how a browser reconnecting mid-stream catches up; and how many concurrent boards one server can stream before it degrades.

Resolve by building a rough end-to-end spike: one board, one live agent, tokens reaching a browser. Link the spike from this ticket.

### Sharpened by [Surviving a server restart](001-restart-durability.md)

Streamed events are **ephemeral** — the conversation is already durable in the CLI's own session file, so the protocol carries no replay obligation and needs no per-event journal.

But the protocol must express one thing it otherwise would not: **the reattach frame**. On reconnect the board announces the gap — naming the last question asked and stating that any answer in flight was not recorded — so the event vocabulary needs a way to say "you are rejoining, here is where you actually are", distinct from a question arriving fresh.

That in turn fixes the minimum a board must persist between turns: its `session_id`, the last question asked, and whether the last answer was acknowledged. Anything beyond that is optional.
