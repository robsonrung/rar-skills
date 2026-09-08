---
name: security-gate
description: Identify security decisions during an interview and classify slices for deep or standard review. Use when defining an exposed security surface or planning its review; full-review performs the code review.
---

# Security Gate

Two small jobs: (1) run the **threat-model-lite** while the user is still choosing the feature, so later phases do not guess security decisions; (2) apply the **deep-pass trigger list** to each slice, then verify deep slices against those decisions. This skill never performs the review — `full-review` does.

The two leitwörter below are what you name as you work: a **threat-model-lite** question is something you ask the human now; a **deep-pass trigger** is a property of the change that forces a deeper review later.

## Threat-model-lite — spec-time checklist (interactive)

Run this inside the requirements interview. Resolve repository facts from evidence and return only unresolved security decisions to the interview's frontier. These questions share its five-question limit; do not send a second question batch. Record the answers in the decision record. `to-prd` carries them into the PRD's Security Decisions section.

1. **Actors & auth**: who can invoke this? What roles/permissions gate each action? What happens for unauthenticated or wrong-role access?
2. **Untrusted input**: what data arrives from users or external systems? Where is it validated, and what is rejected?
3. **Data sensitivity**: does this touch PII, credentials, tokens, or financial data? Where is it stored, logged, or sent? What must never appear in logs or error messages?
4. **Secrets**: any new keys, tokens, or credentials? Where do they live (env, secret manager) and who rotates them?
5. **Dependencies**: any new packages or services? Why this one, and what is its blast radius if compromised?
6. **Tenancy & access scope**: can one user's request ever read or write another user's data? What enforces the boundary?
7. **Abuse**: what does a malicious or careless user do with this feature? Rate limits, quotas, idempotency?
8. **Failure exposure**: on error or timeout, what leaks (stack traces, internal IDs, partial writes)?

## Deep-pass triggers (deterministic)

At task planning time, mark a slice `security: deep` when it touches any of:

- authentication, authorization, session, or permission logic
- parsing or deserializing untrusted input (request bodies, file uploads, webhooks, query params used in queries)
- secrets, tokens, credentials, or cryptography
- PII or regulated data, or what gets logged about it
- new third-party dependencies or external service integrations
- CORS, CSP, security headers, cookies, redirects
- SQL/NoSQL query construction, shell command construction, or template rendering from variables
- database migrations or data backfills
- file system paths derived from user input

Otherwise mark `security: standard`.

At verification, cover every `deep` slice with `full-review` and `security_focus=true`, passing its recorded security decisions. Include this focused review in the approved reviewer plan. It can run at task completion or in the feature review when that review covers the same final code and risks; do not duplicate it without changed evidence. `standard` slices use the normal scoped review, without an extra panel. If implementation expands a slice, recheck the triggers; flags can escalate but never downgrade.

For the stage boundary, read `shared/references/workflow-stage-routing.md`: interview collects decisions, the PRD preserves them, task planning classifies slices, and implementation verifies the result.

## Output contract

At spec time, return the answered checklist as `security_decisions` for the PRD. At planning time, return per-slice `security: deep|standard` with the matched trigger. At verify time, return the prioritization instruction handed to `full-review`.

## Gotchas

1. Do not ask all eight checklist questions ritually — only the ones the feature exposes.
2. Do not downgrade a `deep` flag during autonomous phases; flags only escalate after planning.
3. Do not duplicate review content here — findings, exploits, and fixes belong to `full-review`.
