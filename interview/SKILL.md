---
name: interview
description: >-
  Interactive requirements interview that stress-tests a feature idea against
  the codebase, the repo glossary, and recorded decisions until it is
  spec-ready — the pipeline's specify-phase interview that runs before
  `to-spec`. Use when the user says interview me about this feature, grill me
  on this idea, stress-test these requirements, pin down what to build, make
  this spec-ready, or when a pipeline specify phase needs the interview.
  Distinct from `brainstorm` (decides WHETHER to build — a verdict, not
  requirements) and `to-spec` (synthesizes the PRD from the finished
  conversation — no interview).
---

# Interview — Grill the Feature Until It Is Spec-Ready

Stress-test a feature idea, one question at a time, until it is **spec-ready**:
every question the autonomous phases (`to-tasks` and everything after the
approval gate) would otherwise have to ask is answered, recorded as an explicit
assumption with a default, or descoped. That sentence is the exit test — say it
back while working: *"the data-retention question is not spec-ready yet; the
rollback question is spec-ready as an assumption with a default."* The output
is a decision record `to-spec` can synthesize a PRD from without asking anything.

`brainstorm` decides WHETHER to build; this skill pins down WHAT to build;
`to-spec` writes it down. Arrive here with a BUILD (or REDUCE SCOPE) intent,
leave with the decisions.

## Ground before you grill

Before asking anything, read the project's recorded knowledge and the code:

1. **`CONCEPTS.md`** (repo-root glossary) — use its ubiquitous language in every
   question; a question phrased in the wrong vocabulary collects a wrong answer.
2. **`docs/adr/`** — decisions there are **already decided**: inputs to the
   interview, not questions to re-ask. Challenge one only with new evidence,
   explicitly.
3. **The code the feature touches** — the modules, schemas, tests, and
   integration points involved. If either file is missing, note the gap and
   synthesize from the code; don't block.

**The user's time is the bottleneck** — a question exploration could answer is
not for the user. Every candidate question first passes the filter: *could the
code, the glossary, or an ADR answer this?* If yes, go read; bring the finding,
not the question.

**Glossary upkeep is part of the job.** When the interview surfaces a new
domain term, or reveals a stale one, update `CONCEPTS.md` inline during the
interview — the glossary stays current or it stays useless.

## The grilling — angles that change what gets built

Work the angles below, skipping any with no exposure for this feature. These
are angles, not a ritual checklist — ask only where the answer would change
what gets built.

- **Actors & permissions** — who invokes this, what roles gate each action,
  what happens on wrong-role access.
- **Edge cases & failure modes** — empty, huge, concurrent, partial, offline;
  what the user sees when it breaks.
- **Scope boundaries** — what is explicitly OUT. An unstated boundary is a
  mid-flight scope question waiting to happen.
- **Sequencing & dependencies** — what must exist or ship first; what this
  blocks.
- **Data lifecycle** — created, updated, retained, deleted; who owns each fact
  and where it lives.
- **Integration points** — which existing modules, services, or contracts this
  touches, and what must not change.
- **Non-functional needs** — only the ones that matter here (latency, volume,
  availability); skip the boilerplate.
- **Migration & rollback** — what happens to existing data on deploy, and on
  revert.

Two passes ride along with the angles:

- **Security rows.** Run the `security-gate` **threat-model-lite** checklist
  rows the feature exposes — that skill owns the rows; read them there, never
  copy them here. Record each answer explicitly so `to-spec` lifts them
  straight into the PRD's Security Decisions section.
- **Test seams.** For each major requirement, name the **observable behavior**
  at the **highest seam** possible (per `test-lens`). These become `to-spec`'s
  Testing Decisions and, later, slice acceptance behaviors — naming them now is
  what makes the requirement testable instead of aspirational.

## Interview mechanics

- **One question at a time**, via AskUserQuestion where available: concrete
  options drawn from what you found in the code, plus an explicit "Other".
- **Show, then confirm.** Prefer "the code does X — is that the intended
  behavior here?" over open-ended "what should happen?". A grounded question
  takes seconds to answer; an open one takes a meeting.
- **Batch trivia, never batch decisions.** Three naming confirmations can share
  a message; two decisions that could interact each get their own question, so
  the answer to one can reshape the other.
- Facts established earlier in the conversation are **already decided** — do
  not re-ask them.

## Exit — the spec-ready test and the handoff

Run the exit test: is every question the autonomous phases would have to ask
answered, an explicit assumption with a default, or descoped? If any angle
still hides an open decision, the interview isn't done — name it and ask it.

Then close with a **compact decision record in the conversation**: decisions by
angle, security answers, named seams with their observable behaviors,
assumptions with defaults, and the explicit OUT list. This record is the input
`to-spec` synthesizes from. Hand off with: "run `to-spec`".

## Gotchas

1. Do not ask what exploration could answer — read first, confirm second.
2. Do not batch decisions to feel efficient; batching hides interactions.
3. Do not re-open ADRs or earlier answers without new evidence — **already
   decided**.
4. Do not copy the `security-gate` rows or the `test-lens` rules into the
   conversation — reference them, record only the answers.
5. Do not end without the decision record — an interview that lives only in
   scrollback fails the spec-ready exit for `to-spec`.
6. Do not drift into implementation planning — file-level shape belongs to
   `coding-design-plan`, after the spec.
