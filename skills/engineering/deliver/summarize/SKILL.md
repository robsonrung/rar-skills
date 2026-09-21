---
name: summarize
description: Create a concise continuity summary from the active session. Use when the user asks to summarize current work, prepare a handoff, or compact session context. Do not use to summarize an unrelated document or to store a handoff.
---

# Summarize

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Create a concise summary from information already visible in this session. The next consumer is a fresh session. The acceptance contract is the **cold-start test**: a reader with only this summary can name the goal, current state, evidence, and next action without guessing.

## Boundary

Use only conversation context, captured command results, and files already opened or produced during this work. Do not search unrelated files. Redact secrets, credentials, personal information, and hidden system details.

## Output

Return the summary in the reply. Write a file only when the user names a destination. Persistent storage belongs to `session-handoff`.

Include only relevant sections:

1. Goal
2. Current status
3. Decisions and constraints
4. Files changed
5. Verification captured
6. Next action
7. Open risk or blocker

Prefer exact paths, command names, and error labels to long quotations. Omit empty sections and filler.
