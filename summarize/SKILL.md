---
name: summarize
description: Create a concise handoff summary from visible session context. Use when the user asks to summarize the session or current work, compact the session, prepare a handoff, or write continuity notes for resuming later. Not for summarizing documents, articles, or code unrelated to the active session.
---

# Summarize

Create a short handoff from information already visible in the active session, written so a fresh agent session can resume the work without other context.

## Privacy Boundary

Use only conversation context, command results, and files that were already opened or produced during the active work. Do not search unrelated local files. Do not include secrets, tokens, private keys, credentials, personal identifiers, or hidden system details. Replace any sensitive value with a short redacted label.

## Output

Output the summary directly in the reply; only write it to a file if the user asks, defaulting to `./HANDOFF.md`.

Write a compact Markdown summary with these sections when relevant:

1. Goal
2. Current status
3. Decisions and constraints
4. Files changed
5. Verification already run
6. Next steps
7. Open risks or blockers

Keep it brief. Prefer paths, command names, and exact error labels over long quotations.

If no files changed, omit that section. If the session is short, say so plainly and avoid filler.
