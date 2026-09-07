# Audit checklist, budget dashboard & validation

This checklist is the self-check for a proposed or written instruction set and the audit rubric for an existing file.

## Audit / self-check checklist

1. **Requested scope honored**: audits do not write files; create and update requests write only their named scope.
2. **WHAT/WHY/HOW present**: stack and structure, purpose and component roles, and exact build, test, and typecheck commands are covered when known.
3. **Only universal instructions in root**: every root line applies to essentially every session.
4. **Within budget or justified**: see the dashboard below; overflow items each have a destination.
5. **No style or formatting rules as prose**: they point to a linter, formatter, or hook instead.
6. **No copied code snippets**: replace them with verified `file:line` pointers to stable sources.
7. **All pointers resolve**: every `file:line` and Markdown link points at a file or line that exists.
8. **agent_docs are referenced, not inlined**: each linked file has a one-line read-when-needed note.
9. **Conditionality dominates size**: short but niche rules were demoted.
10. **No invented facts**: unverifiable claims were removed and unresolved facts are named.
11. **No attribution text.**
12. **Dual-file coherence**: one canonical file and a text pointer stub when the project does not require separate content.
13. **Tiny-project check**: skip the `agent_docs/` scaffold when the project does not warrant it.
14. **Staleness**: documented commands still run and pointers are valid.

## Budget dashboard format

Report current vs target with a status band — **never** pass/fail:

```
Budget (HumanLayer defaults — overridable)
  Instructions: <N>  target ≤150–200 (minus ~50 system prompt)   [🟢 / 🟡 / 🔴]
  Root lines:   <N>  target <300 (ideal <60)                     [🟢 / 🟡 / 🔴]
  → 🔴 items: <list each over-budget block + recommended destination (cut / agent_docs/X.md / hook)>
```

Bands: 🟢 within target · 🟡 approaching / mild overflow · 🔴 over — list remediation. Always explain the _cost_ of bloat (diluted attention, ignored instructions), then let the user decide.

## Optional validation script

For the two mechanically-checkable risks, a tiny script (no LLM needed) can count root lines and check that every `file:line` pointer and markdown link resolves. Keep it optional and proportional.

## Lightweight regression set

Bundle 2–3 golden **before/after** examples so behavior stays stable and reviewers can eyeball quality:

- a bloated `/init`-style file → de-bloated result (good case),
- an over-budget file → demotion into `agent_docs/` (budget case),
- a **dual-file** project (AGENTS.md + CLAUDE.md) → canonical + pointer stub (drift case),
- include at least one **stale `file:line` pointer** to exercise the link check. Plus a few trigger cases (create / optimize / staleness) confirming the skill activates and routes correctly. No heavy eval harness — reuse `skill-expert`'s eval tooling later if deeper measurement is wanted.
