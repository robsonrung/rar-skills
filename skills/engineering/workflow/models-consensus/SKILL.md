---
name: models-consensus
description: Run a read-only council of independent model opinions as a poll, debate, or personas panel, return one recommendation, and walk the user through any open disagreement.
disable-model-invocation: true
---

# Models Consensus

Turn one decision into independent model opinions, let them meet, and return a recommendation the user can act on. The council deliberates; implementation is a separate request.

## Plan

1. Choose the mode: `poll` by default, `debate` for a contested direction, `personas` for five lenses from one model.
2. Choose the seats: the models the user names, then the `seats` preferences in `.rar-skills/config.local.yaml` when it exists, then `python3 shared/scripts/model_routing.py council <technical|analysis|routine|security>` for the question's shape. Poll and debate open with three seats on distinct models.
3. Show the neutral question, mode, each role with its model, effort, and host route, and the expected and maximum calls. Ask: **"Approve this council plan, or specify changes."** Dispatch after a clear yes.

**Seat fidelity**: a seat speaks only through its approved model. A failed seat stays an **observable failure** in the report; a model change needs a new approval. Stop when fewer than two opening seats remain.

## Seats

Each seat is one context that lives for the whole run. Its later turns (gap repair, the next debate round, a format retry) go to that same context, so it remembers what it argued. Every other role (organizer, moderator, judge, reviewer, synthesizer, chairman) gets its own fresh context, even on a model already seated. Contexts start without this conversation; they see the brief and what the protocol hands them. Peers appear only as anonymized digests labeled A, B, C.

Route each seat by host:

- **T3 Code**: `delegate_task` with the seat's configured provider and model; continue with `t3_thread_send` to its thread.
- **Claude Code or Codex**: a native subagent with the seat's model; continue by messaging that same subagent.
- **A model the host lacks**: `cli-runner`, `pi-runner`, or `muse-runner`; continue by resuming its session.

Every call carries the brief:

```text
You are seat <label> in a read-only council. Read whatever helps; leave every file unchanged. Your reply is your only output.

QUESTION: <neutral question>
CONTEXT: <paths or facts>

<phase instruction>
```

## Poll

1. **Blind openings**, in parallel: answer, key points, assumptions, confidence 0-100.
2. **Organizer** reads every opening: consensus, contradictions, partial coverage, unique insights, blind spots, and whether material gaps remain.
3. **Gap repair**, once, only for material gaps: each opening seat gets the anonymized open points and resolves, qualifies, or rejects each with evidence. This is repair, not a new vote.
4. **Judges**: two, isolated from the openings and each other, rule on every remaining open point with rationale and confidence. Skip them only for a low-risk question whose organizer found no contradictions, no gaps, and high confidence; security, money, migrations, public contracts, and data loss always get judges.
5. **Synthesis** writes the recommendation with an attribution map tracing each material claim to a seat or ruling. Split judges stay split: the synthesis states the confidence limit.

## Debate

1. Each opening seat argues from a distinct stance: position, key arguments, risks, recommended direction, confidence, and questions for the council.
2. A **moderator** digests the round anonymously: agreements, disagreements, options, evidence gaps, follow-up questions.
3. Each later round, up to the approved one to three, sends every seat the digest and a new stance. It must rebut, concede, refine, or integrate, returning its updated position, what changed, concessions, remaining objections, and best next step.
4. Classify the end state: full agreement, converging, material disagreement, or blocked on context. Reaching the round ceiling is reported disagreement.

Stances (rotate so no seat repeats one):

- **supportive with integrity**: the strongest honest case for
- **critical with responsibility**: what fails, and what would fix it
- **balanced synthesis**: weigh the options against each other
- **devil's advocate**: the position the council is drifting away from
- **pragmatic engineering**: what ships, at what cost
- **outsider fresh eyes**: what is unclear without insider context; suits a seat given no repository

## Personas

One model, the user's choice or else the council's synthesis model, plays five isolated advisors, one lens each:

- **Contrarian**: what can fail, and which assumption is unsafe?
- **First Principles**: what problem are we actually solving?
- **Expansionist**: what upside or adjacent option is missed?
- **Outsider**: what is unclear without insider context?
- **Executor**: what is the first practical move, and its constraint?

Freeze your own view before reading any advisor. Each advisor argues only its lens and states assumptions, evidence limits, and one recommendation. Five reviewers then read the shuffled, anonymized answers and name the strongest and why, the largest blind spot, and what everyone missed; the user may drop this step. A **chairman** weighs advisors, reviews, and your frozen view. Five lenses are angles, not votes.

## Report

Write `.ai-workflow/consensus/<session>.md`, leading with the outcome:

1. Recommendation and one next step. An adoption question gets one grade: Adopt, Trial, Hold, Reject, or Not-our-problem; thin evidence gives "Hold: insufficient evidence" with what to inspect.
2. Agreements, dissent, blind spots, evidence gaps, plus the judge rulings or debate end state.
3. A reversal trigger when the decision is costly to undo.
4. Answer confidence and diversity confidence, separately. Diversity counts distinct models that answered; personas is low by construction.
5. Each seat's model, host route, and any failure.

## Open disagreements

When material dissent survives the report, walk the user through it: one packet per open point, in the report's order. A packet holds the neutral topic, each seat's position with its evidence (or "no position recorded"), and every distinct option, adding a combined option when it beats each part. Lead with the pick: "I recommend option N, because <decisive trade>; the strongest alternative costs <cost>." This is a **recommendation, not survey**: a majority is not proof, and thin evidence makes "defer and collect <evidence>" a valid pick. Ask one question per topic with the host's question tool. With no answer, mark the point `awaiting_human`; never default to the recommendation. Skip points the council settled, and leave the report unchanged.
