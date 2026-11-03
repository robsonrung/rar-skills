---
name: response-unslop
description: Remove AI writing patterns from prose, a draft, or your own reply. Use when the user asks to unslop, de-AI, or plain-speak text. For code cleanup use coding-review-simplify.
disable-model-invocation: true
---

# Response unslop

Edit text to remove AI patterns. The result is the rewritten text, returned in place of the original, or written back to the file the user named.

## Process

1. Scan for the patterns below.
2. Rewrite. Preserve meaning, match the intended tone, and leave code, identifiers, quotations, and numbers unchanged.
3. Write every report to the user, and any rewritten text that is a reply to the user, in the register under "Reporting language". A document the user supplied for editing keeps its intended tone and language.
4. When a pattern hides a missing fact (rules 1, 2, 22), name the fact if the source supplies it. Otherwise cut the sentence and say what you cut.

## Patterns to detect and fix

### Content

1. **Superficial -ing phrases.** "highlighting...", "ensuring...", "reflecting...", "showcasing...", "fostering...". Delete or expand with real sources.
2. **Vague attributions.** "Experts believe", "Industry reports suggest", "Some critics argue". Name the source or delete.

### Language

3. **AI vocabulary.** Additionally, crucial, delve, enduring, enhance, fostering, garner, interplay, intricate, landscape (abstract), pivotal, showcase, tapestry (abstract), testament, underscore, vibrant. Replace with plain words.
4. **Fancy ways to say "is".** "serves as", "stands as", "boasts", "features". Just say "is" or "has".
5. **"Not just X, but Y."** State the point directly instead.
6. **Rule of three.** Forcing ideas into groups of three. Use the natural number.
7. **Synonym cycling.** Protagonist, main character, central figure, hero all in one paragraph. Pick one, repeat it.
8. **False ranges.** "from X to Y" where X and Y aren't on a meaningful scale. List topics directly.

### Style

9. **Em dash overuse.** Avoid em dashes entirely. End the sentence or use a comma; not parentheses, en dashes, or hyphens as dashes.
10. **Colon overuse.** Colons are fine before a list or example, not as mid-sentence connectors. "If you're coming from traditional automation: instead of registering handlers, you describe conditions" leans on the colon and the comparison. Let the point stand on its own.
11. **Boldface overuse.** Don't bold every proper noun or acronym.
12. **Inline-header lists.** A bold label and colon that restates the line ("**Performance:** Performance improved...") becomes prose. A bold lead-in that ends in a period and is followed by new detail is fine.
13. **Title case headings.** Use sentence case.
14. **Decorative emojis.** Remove from headings and bullets.
15. **Curly quotes.** Replace with straight quotes.

### Communication artifacts

16. **Chatbot phrases.** "I hope this helps!", "Let me know if...", "Of course!", "Certainly!", "Found the smoking gun!" Remove.
17. **Sycophantic tone.** "Great question! You're absolutely right!" Respond directly.

### Filler

18. **Filler phrases.** "In order to" becomes "To". "Due to the fact that" becomes "Because". "It is important to note that" gets deleted.
19. **Excessive hedging.** "could potentially possibly be argued that it might" becomes "may".
20. **Generic conclusions.** "The future looks bright." State specific plans or facts.

### Jargon

21. **Abstract metaphor nouns.** Substrate, wedge, vector, locus, vantage, nexus, primitive (as noun), harness (as metaphor), surface (as in "API surface"), bedrock, scaffolding (as metaphor), modality, paradigm, gold-plating, ratchet (as metaphor), evacuate (for moving code), endgame, north star, flywheel. They sound technical but usually stand in for a plainer word: "substrate" becomes "base", "wedge in" becomes "add", "gold-plating" becomes "more than the job needs". Pick the concrete word.

### Plain speech

22. **Say what it does, not how it feels.** "SQL you can read" names a feeling; "`.toSQL()` returns the exact string sent to the database" names the mechanism. Write what the reader should do or know. If the sentence can't become an instruction, fact, or number, or could appear unchanged in another project's docs, cut it.
23. **Shorten or split dense sentences.** If the reader has to backtrack to parse a sentence, break it in two or drop clauses. One idea per sentence.
24. **Active voice.** Name the actor: "queries are validated" becomes "the compiler validates queries". Passive is fine only when the actor is unknown or doesn't matter.
25. **Cut adverbs, or use a stronger verb.** "runs quickly" becomes "is fast" or the number; "significantly improves" becomes the measured delta.
26. **Prefer the plain word.** "utilize" and "leverage" become "use", "facilitate" becomes "help", "in the event that" becomes "if".
27. **Mannered prose.** Flourish where a literal phrase exists: aphorisms ("wire it or delete it"), rhetorical fragments, personified code ("the plan holds it"), figurative verbs ("rides along"). "A dial worth turning" becomes "a parameter worth varying". Rule 21 covers the metaphor nouns.
28. **Over-compression.** Dropped articles, verbless fragments, arrows, and abbreviations make the reader decode. "Parser rejects bad date → exit 2, no write" becomes "The parser rejects a bad date, exits with code 2, and writes nothing."

### Reporting language

29. **Controlled language for reports.** Match the language the user writes in. For English, use ASD-STE100 Simplified Technical English: approved words, short sentences, one idea each, active voice, present tense. For Portuguese, use Linguagem Simples per ABNT NBR ISO 24495-1: plain words, short sentences, direct order, main point first. For other languages, apply rules 1 to 28 only. Keep technical names, commands, and code as they are.
