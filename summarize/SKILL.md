---
name: summarize
description: compresses the current conversation session into a ≤3000-word summary
---

# Context Compress

Condense a long session into a tight briefing, then clear and restore context so work continues without losing state.

## Privacy Boundary

Summarize only the active conversation context and concrete files or outputs that are already visible in the session. Do not invent hidden context, do not fetch unrelated local files, and avoid including secrets, tokens, private keys, or credentials in the summary. If a sensitive value is necessary to identify state, replace the value with a short redacted label.

---

## Step 1 — Analyze Before You Write

Read through the full conversation and extract:

| Category | What to look for |
|---|---|
| **Primary goal** | What is the user ultimately trying to achieve in this session? |
| **Current status** | What was just completed? What is mid-flight? |
| **Decisions made** | Architecture choices, tool selections, pattern preferences, trade-offs settled |
| **Files touched** | Every file created, modified, or deleted — with a one-line note on what changed |
| **Open issues** | Bugs being debugged, open questions, blockers not yet resolved |
| **Recent focus** | The specific thing being worked on at the moment of compression |
| **Key context** | Tech stack details, non-obvious constraints, anything a fresh instance would have to rediscover |

Spend a moment on this analysis before writing. The quality of the summary depends on getting the important bits right, not just listing everything that happened.

---

## Step 2 — Write the Summary

Produce a summary of **at most 3000 words** using this exact structure:

```
## Primary Goal
[1–2 sentences: what is this session trying to accomplish overall]

## Current Status
[2–3 sentences: where things stand right now — what just got done, what is in flight]

## Key Decisions & Context
- [Decision or constraint — be specific, not generic]
- [Pattern being used — e.g. "Using SQLAlchemy + Alembic for all new backend models"]
- [Non-obvious fact a fresh instance would waste time rediscovering]
- ...

## Files Modified
- `path/to/file.py` — [one-line: what changed]
- `path/to/other.tsx` — [one-line: what changed]
- ...

## Work Completed
- [Task or milestone finished, in order]
- ...

## In Progress / Next Steps
- [What was being worked on when compression happened]
- [What comes immediately after]
- ...

## Open Issues / Blockers
- [Bug being debugged, with error message if relevant]
- [Unresolved question]
- ...

## Important Notes
- [Anything else a fresh instance needs to be effective]
```

### Writing principles

**Density over completeness.** Cut anything that can be trivially re-derived by reading the code. Keep anything that took exploration to discover.

**Use exact values.** File paths, function names, error messages, config keys — spell them out. Vagueness forces re-investigation.

**Skip resolved back-and-forth.** If a wrong path was explored and abandoned, don't document the detour — only document where you ended up.

**Reference files instead of quoting code.** "See `backend/app/services/login.py:L45`" is better than a 30-line code block.

**Write as briefing notes to yourself.** Assume the reader has full codebase access and just needs state restoration, not explanation.

---

## Step 3 — Present the Summary

Write the summary as an output block inline that the user can copy-paste.

---

## Edge Cases

**Conversation is very short (< 10 exchanges):** Still produce the summary, but note in the Current Status section that the session was early-stage. Don't pad it.

**No files were changed:** Omit the "Files Modified" section rather than saying "none".

**Multiple active tasks:** The summary should still fit in 3000 words. If needed, collapse completed tasks into a single line each and expand only what is current.
