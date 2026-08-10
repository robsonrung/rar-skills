---
name: decide-about-disagreements
description: >-
  Resolve unresolved topics from a models-consensus result with the user. Use
  when a result contains contradictions, material disagreement, open
  divergence, blind spots, contested unique insights, or disagreement points
  that need a human choice. Read the result, show every recorded model
  opinion, analyze the tradeoffs, list all distinct options, add a combined
  option when it is the best approach, recommend one option, and ask one
  interactive question per topic. Do not rerun the council, hide dissent, or
  implement the decision.
---

# Decide About Disagreements

Use this skill after `models-consensus` returns at least one topic without a
shared position. The result is a decision aid, not a second council. The skill
does not edit the council artifacts or implement the user's choice.

## Outcome spine

1. **Result:** turn each unresolved topic into a short decision packet. Each
   packet contains the neutral topic, all recorded seat opinions, an analysis,
   every distinct option, one recommendation, and the user's choice.
2. **Next consumer:** the user chooses one option for one topic at a time.
3. **Done:** every material unresolved topic is either decided, explicitly
   deferred, or marked `awaiting_human`; no topic is silently skipped.
4. **Boundary:** do not rerun `models-consensus`, change its report or state,
   or start implementation.

Say **recommendation, not survey** while working. The user asked for the full
option set, so show it, then close each packet with one clear pick and the
trade that decides it.

## Read the result

Accept either the inline result supplied by the caller or the persisted result
paths in that result object. If neither is present, ask for the report or state
path with the host's blocking question tool. Do not guess a latest file from a
directory listing.

1. Use the report as the primary narrative source. Use the state object for
   mode, status, rounds, seats, effective providers and models, convergence,
   and confidence.
2. Read raw round files only when the report and state do not contain a
   required opinion or resolution. Read the smallest file set that fills the
   gap. Do not load the full transcript by default.
3. Record the question, session, mode, status, and artifact paths before
   analysis. If status is not `complete`, label the work as partial, failed,
   awaiting human input, cancelled, or ceiling hit as recorded. A partial
   result is not a final consensus.
   If `mode` is missing or contains `interactive` or `autonomous`, treat that
   value as the interaction mode. Derive the council mode from the available
   fields and report headings: `contradictions` and `material_gaps` indicate
   `poll`, `disagreement_points` and `convergence` indicate `debate`, and the
   fixed council verdict headings indicate `personas`. If the mode remains
   unknown, use only items explicitly marked unresolved.
4. Apply **seat fidelity**. Name a model or provider only when the result
   records its effective receipt. Never infer an effective model from a
   requested name, a prompt, or a seat's self claim. If the receipt is absent,
   label the seat as unverified and preserve the reported seat name.
5. Apply **flag, never overwrite**. Keep minority positions, unresolved
   caveats, missing evidence, malformed seats, duplicate providers, and shared
   transport notes visible. A larger count does not erase a dissent.
6. Match the user's language. Use ASD-STE100 Simplified Technical English for
   English and Brazilian Portuguese with simple wording for Portuguese. Keep
   paths, enum values, model names, and short quoted evidence unchanged.

## Find topics that are not consensus

Extract only material topics that remain open. Do not ask about a point that
the council resolved, a point all seats support, or a decision the user has
already made. That is **already decided** territory.

Use the mode-specific fields below. Field names can appear in the report,
state, or inline result.

| Mode | Ask about | Do not ask about |
| --- | --- | --- |
| `poll` | Open `contradictions` such as `C1`, material `partial_coverage` such as `P1`, unresolved `blind_spots` such as `B1`, and `unique_insights` such as `U1` when they remain contested or can change the choice. Include open caveats when they change the choice. | `consensus` points and points resolved by both judges. An additive point that cannot change the choice is a caveat, not a question. |
| `debate` | `disagreement_points` with material scope, behavior, architecture, cost, or risk differences; an `open divergence` at the round ceiling; `blocked_on_context` items that require a user choice about evidence or assumptions. | `full_agreement` and `converging` detail differences that do not change the direction. |
| `personas` | Material items in `Where the Council Clashes` that the chairman did not resolve, plus a blind spot that still blocks the user's choice. | A clash already settled by the chairman. Do not reopen it unless the user explicitly asks to revisit the final verdict. |

For older or custom result shapes, accept `disagreements`, `open_points`,
`remaining_objections`, and `open_caveats` only when the surrounding text marks
the item as unresolved. Treat `follow_up_questions` and `evidence_gaps` as
evidence gaps, not as model disagreement. Include a coverage or evidence gap
as a question when it requires a user assumption or can change the choice;
otherwise list it as a non-blocking caveat.

If no material topic remains, lead with the outcome: state that no user choice
is needed and list any non-blocking caveat. Do not ask an empty question.

## Build one decision packet per topic

Process topics in the order used by the result. Do not merge two topics unless
the result says they are the same decision. For each topic, build this packet
before asking the user.

### 1. State the neutral topic

Use the council's point id and a one sentence statement of the contested issue.
Remove loaded wording. Example: `C1: choose a shared queue or an outbox table
for durable delivery`.

### 2. Present every recorded opinion

List every seat that addressed the topic. For each seat, show:

1. the recorded seat name;
2. the effective provider and model when receipt verified;
3. the position in plain language;
4. the evidence, assumption, or risk that supports it.

If the full seat table contains a participating seat with no position for this
topic, write `No position recorded`. If a raw output is missing or malformed,
write `Unavailable in the supplied result` and name the evidence gap. Do not
turn silence into agreement. Keep opinions separate even when two seats use the
same effective model. Mark the duplicate for diversity context, but do not
remove its text.

### 3. Analyze the disagreement

Use the supplied question and context to test each position against the
decision criteria that can change the choice. Prefer criteria that are
observable in the result, such as behavior, scope, architecture, cost,
operational risk, reversibility, evidence quality, and implementation burden.

Separate three cases:

1. **Different conclusions:** the seats choose different directions.
2. **Different assumptions:** the seats would converge if one fact were known.
3. **Different coverage:** one seat raised an additional risk or benefit.

Name the strongest evidence for each side and the material weakness. Do not
score a seat by majority count alone. If the result lacks the fact needed to
choose, say so as an evidence gap and include an evidence-first option.

### 4. List every option

Create a numbered option list. Include every distinct direction suggested by a
seat, the council, or the original question. Preserve a meaningful minority
option even when it is not the leading view. Remove only duplicate wording.

Then test whether the best approach is a combination of suggestions. If the
combination is better, add it as a new option named `Recommended synthesis` and
state which parts it takes from which positions. The recommendation must point
to a listed option. Never recommend an option that is absent from the list.

### 5. Recommend one approach

Use this compact shape:

`I recommend option <id>, because <decisive evidence and trade>. The strongest
alternative is option <id>, but it costs <material cost or risk>.`

This is **recommendation, not survey**. The recommendation is an analysis call,
not a claim that the majority is correct. If evidence is not sufficient, the
recommended option can be `defer and collect <specific evidence>`. State the
smallest evidence that would change the recommendation.

### 6. Ask the user

Use the host's blocking interactive question capability first. In Codex, use
`request_user_input` when it is exposed. In Claude Code, use
`AskUserQuestion`. Otherwise use the host's equivalent. Use plain text only
when no interactive tool exists or the tool call fails.

Ask one topic per question. Put the recommended option first. The question
must be a single sentence, such as `Which approach should we adopt for C1?`

The full option list must appear before the question. If the tool supports only
two or three choices, offer the recommendation and the strongest alternative
as choices, then rely on the tool's free text `Other` choice for every other
listed option or combination. Never hide an option from the narrative because
the tool has a short choice limit. If the tool supports all choices, include
all of them.

When the user chooses `Other`, capture the exact text and map it to a listed
option or a new combination. If the text is not actionable, ask one focused
clarification question. If the tool returns no answer, do not select the
recommendation by default. Stop with `awaiting_human` and identify the topic.

## Continue and finish

After each answer:

1. Record the user's selection in the current response context. Do not write
   to the council report or state unless the user separately asks for a
   decision record.
2. If the user selected a different option, state the change without arguing
   again. If the user selected a combination, restate its exact boundaries.
3. Move to the next unresolved topic. Do not ask about resolved topics again.

End with **lead with the outcome**:

1. topics decided and the user's chosen option for each;
2. topics deferred or `awaiting_human`;
3. the original recommendation where it differed from the user's choice;
4. evidence gaps, seat fidelity limits, and unresolved dissent;
5. one next step only when the result or the user's choice supplies one.

The acceptance contract is observable: every material open topic has a packet,
every packet shows all recorded opinions and all distinct options, each packet
has one recommendation, each asked topic has a captured user answer or an
explicit `awaiting_human` status, and the source council artifacts are
unchanged.

## Gotchas

1. A majority is not proof. Use the evidence and the decision criteria.
2. Missing output is an **observable failure**, not consensus. Show the gap and
   choose evidence first when it blocks a safe call.
3. A blind spot is not automatically a disagreement. Ask about it only when it
   changes the decision or requires a user assumption.
4. Do not infer a model identity. Use **seat fidelity** for every attribution.
5. Do not turn a recommendation into an implementation. This skill ends when
   the user has chosen, deferred, or left a topic awaiting an answer.
