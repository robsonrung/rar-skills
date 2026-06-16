---
name: security-gate
description: Shift security left in a development workflow — ask a threat-model-lite checklist while specifying a feature, then deterministically decide which tasks need a deep security review pass before delivery. Use during spec or planning interviews, when a pipeline phase requires the security gate, or when the user asks to threat model a feature, run a security checklist, or decide whether a change needs a security review. Do not use to perform the deep review itself — that is full-review's security dimension or a dedicated security audit.
---

# Security Gate

Two small jobs: (1) run the **threat-model-lite** at spec time, while the human is still in the room, to collect the security answers autonomous phases would otherwise have to guess; (2) run the **deep-pass trigger list** at verify time to decide deterministically whether a change gets the deep security pass. This skill never performs the review — `full-review` does.

The two leitwörter below are what you name as you work: a **threat-model-lite** question is something you ask the human now; a **deep-pass trigger** is a property of the change that forces a deeper review later.

## Threat-model-lite — spec-time checklist (interactive)

During the phase 1 interview (`grill-with-docs` or `collaborative_discovery`), ask only the questions relevant to the feature; skip rows with no exposure. Record every answer in the PRD's Implementation Decisions so phases 3–6 never have to ask.

1. **Actors & auth**: who can invoke this? What roles/permissions gate each action? What happens for unauthenticated or wrong-role access?
2. **Untrusted input**: what data arrives from users or external systems? Where is it validated, and what is rejected?
3. **Data sensitivity**: does this touch PII, credentials, tokens, or financial data? Where is it stored, logged, or sent? What must never appear in logs or error messages?
4. **Secrets**: any new keys, tokens, or credentials? Where do they live (env, secret manager) and who rotates them?
5. **Dependencies**: any new packages or services? Why this one, and what is its blast radius if compromised?
6. **Tenancy & access scope**: can one user's request ever read or write another user's data? What enforces the boundary?
7. **Abuse**: what does a malicious or careless user do with this feature? Rate limits, quotas, idempotency?
8. **Failure exposure**: on error or timeout, what leaks (stack traces, internal IDs, partial writes)?

## Deep-pass triggers (deterministic)

At planning time (the `to-tasks` Slice Contract), mark a slice `security: deep` when it touches any of:

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

At verify time: `deep` slices run `full-review` with `security_focus=true`, passing the threat-model-lite answers as the recorded security decisions to verify against (the implementation must match the recorded auth, validation, logging, and tenancy decisions). `standard` slices rely on `full-review`'s normal security coverage with no extra pass.

## Output contract

At spec time, return the answered checklist as `security_decisions` for the PRD. At planning time, return per-slice `security: deep|standard` with the matched trigger. At verify time, return the prioritization instruction handed to `full-review`.

## Gotchas

1. Do not ask all eight checklist questions ritually — only the ones the feature exposes.
2. Do not downgrade a `deep` flag during autonomous phases; flags only escalate after planning.
3. Do not duplicate review content here — findings, exploits, and fixes belong to `full-review`.
4. A slice that grows scope mid-implementation re-checks the trigger list before verify.
