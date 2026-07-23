---
name: decision-council
description: "Pressure-test a high-stakes decision through a persona council — one model wearing five fundamentally different thinking lenses (Contrarian, First Principles, Expansionist, Outsider, Executor) that answer independently, peer-review each other anonymously, then get synthesized into a single decisive verdict. Adapted from Karpathy's LLM Council. MANDATORY TRIGGERS: 'council this', 'run the council', 'war room this', 'pressure-test this', 'stress-test this', 'debate this'. STRONG TRIGGERS (when paired with a real decision or tradeoff): 'should I X or Y', 'which option', 'what would you do', 'is this the right move', 'validate this', 'get multiple perspectives', 'I can't decide', 'I'm torn between'. For business/product/strategy/life decisions where being wrong is expensive. Do NOT trigger on factual lookups, creation tasks, or casual 'should I' with no real tradeoff. Distinct from models-consensus / models-roundtable / council, which run multiple REAL models on repo/code decisions — this runs ONE model across five thinking lenses on a judgment call."
---

# Decision Council

Ask one AI a question, get one answer. You can't tell if it's great or mid because you only saw one angle.

The council fixes that. It runs your decision through five advisors, each thinking from a fundamentally different angle. They peer-review each other's work anonymously. Then a chairman synthesizes everything into a verdict that tells you where the advisors agree, where they clash, and what you should actually do.

Adapted from Andrej Karpathy's LLM Council. He dispatches a query to multiple *models*, has them peer-review anonymously, then a chairman produces the final answer. Here the diversity comes from five **thinking lenses** on one model, not five different models — that is the whole distinction from the model-diversity skills (`models-consensus`, `models-roundtable`, `council`). Reach for those when you want genuinely independent providers on a repo/code decision; reach for this when you want independent *angles* on a judgment call.

## When to run it

The council is for decisions where being wrong is expensive and there is genuine uncertainty.

Good council questions:
- "Should I launch a $97 workshop or a $497 course?"
- "Which of these 3 positioning angles is strongest?"
- "I'm thinking of pivoting from X to Y. Am I crazy?"
- "Here's my landing page copy. What's weak?"

Bad council questions:
- "What's the capital of France?" (one right answer)
- "Write me a tweet" (creation task, not a decision)
- "Summarize this article" (processing task, not judgment)

If you already know the answer and just want validation, the council will likely tell you things you don't want to hear. That's the point. For repo/architecture/code decisions, hand off to `models-consensus` instead.

## The five advisors

Not job titles or personas — thinking styles that naturally create tension with each other.

1. **The Contrarian** — actively looks for what's wrong, missing, or will fail. Assumes a fatal flaw and hunts for it. Not a pessimist; the friend who saves you from a bad deal by asking the questions you're avoiding.

2. **The First Principles Thinker** — ignores the surface question and asks "what are we actually trying to solve?" Strips assumptions, rebuilds from the ground up. Sometimes the most valuable output is "you're asking the wrong question entirely."

3. **The Expansionist** — looks for upside everyone else is missing. What could be bigger? What adjacent opportunity is hiding? Doesn't care about risk (that's the Contrarian's job) — cares what happens if this works better than expected.

4. **The Outsider** — has zero context about you, your field, or your history. Responds purely to what's in front of them. The most underrated advisor: experts develop blind spots, and the Outsider catches the curse of knowledge — things obvious to you but confusing to everyone else.

5. **The Executor** — only cares whether this can actually be done and the fastest path to doing it. Ignores theory and big-picture strategy. Looks at every idea through "OK, but what do you do Monday morning?" If it sounds brilliant but has no clear first step, the Executor says so.

**Why these five:** three natural tensions. Contrarian vs Expansionist (downside vs upside). First Principles vs Executor (rethink everything vs just do it). The Outsider sits in the middle keeping everyone honest.

## How a session works

### Step 1: Enrich context, then frame the question

**A. Scan the workspace (≤30s).** The user's question is usually the tip of the iceberg. Quickly `Glob`/`Read` for the 2–3 files that would let advisors give specific, grounded advice instead of generic takes:
- `CLAUDE.md` / `claude.md` in the project root (business context, constraints, preferences)
- any `memory/` folder (audience, voice, business details, past decisions)
- files the user referenced or attached
- recent council transcripts here (avoid re-counciling old ground)
- topic-relevant files (asking about pricing → revenue data, past launch results)

Don't spend more than 30 seconds. You're looking for context, not doing research.

**B. Frame the question.** Reframe the raw question + enriched context as one clear, neutral prompt all five advisors receive. Include: the core decision, key context from the user, key context from workspace files (stage, audience, constraints, numbers, past results), and what's at stake. Don't add your own opinion or steer it — but give each advisor enough to be specific.

If the question is too vague ("council this: my business"), ask exactly one clarifying question, then proceed. Save the framed question for the transcript.

**C. Classify the reversal cost.** State how expensive this decision is to undo, and size the run accordingly:

- **Cheap** — a two-way door; walking it back costs little. Lighter workspace scan, advisors at the short end of their word budget; the peer-review round may be skipped when the five responses substantially agree. No reversal trigger needed.
- **Medium** — reversible, but with real switching cost. Full council; the verdict must document a reversal trigger (what observation would flip it).
- **Expensive** — hard or impossible to undo: public commitments, money spent, people affected. Full council, deeper workspace scan before framing, and the verdict documents both a reversal trigger and the earliest checkpoint at which it will be evaluated.

Name the tier in the verdict; the user can override it. Do not give a cheap decision the expensive workup, or vice versa.

**D. Freeze your own position.** If you — the orchestrator — already hold a view on the question, write it down **now**, before a single advisor spawns or any advisor/peer output is read. The frozen position may be handed to the chairman labeled "host position (frozen pre-council)" as one more input, but it must never shape the framed question, and it is never revised after exposure to council output. A position written after reading the council is anchored, not independent. If you hold no position, skip this — do not manufacture one.

### Step 2: Convene the council (5 sub-agents in parallel)

Spawn all 5 advisors **simultaneously** as sub-agents (one message, five `Agent` calls). Sequential spawning wastes time and lets earlier responses bleed into later ones. Each gets its lens, the framed question, and an instruction to lean fully in.

Sub-agent prompt template:
```text
You are [Advisor Name] on a decision council.

Your thinking style: [advisor description from above]

A user has brought this question to the council:

---
[framed question]
---

Respond from your perspective. Be direct and specific. Don't hedge or try to
be balanced. Lean fully into your assigned angle — the other advisors cover the
angles you don't. If you see a fatal flaw, say it. If you see massive upside,
say it.

Keep your response between 150-300 words. No preamble. Go straight into your
analysis.
```

### Step 3: Anonymized peer review (5 sub-agents in parallel)

This is the step that makes it more than "ask 5 times" — the core of Karpathy's insight.

Collect all 5 responses. Label them Response A–E, **randomizing** which advisor maps to which letter so there is no positional or persona bias. Spawn 5 fresh sub-agents; each sees all 5 anonymized responses and answers three questions.

Reviewer prompt template:
```text
You are reviewing the outputs of a decision council. Five advisors
independently answered this question:

---
[framed question]
---

Here are their anonymized responses:

**Response A:**
[response]

**Response B:**
[response]

... (C, D, E)

Answer these three questions. Be specific. Reference responses by letter.

1. Which response is strongest? Why?
2. Which response has the biggest blind spot? What is it missing?
3. What did ALL five responses miss that the council should consider?

Keep your review under 200 words. Be direct.
```

Anonymizing matters: if reviewers know who said what, they defer to certain thinking styles instead of judging on merit.

### Step 4: Chairman synthesis

One agent gets everything: the framed question, all 5 advisor responses (now **de-anonymized** so it knows who said what), and all 5 peer reviews. It produces the final verdict.

The chairman may disagree with the majority. If 4 advisors say "do it" but the lone dissenter's reasoning is strongest, side with the dissenter and explain why.

Chairman prompt template:
```text
You are the Chairman of a decision council. Synthesize the work of 5 advisors
and their peer reviews into a final verdict.

The question:
---
[framed question]
---

ADVISOR RESPONSES:
**The Contrarian:** [response]
**The First Principles Thinker:** [response]
**The Expansionist:** [response]
**The Outsider:** [response]
**The Executor:** [response]

PEER REVIEWS:
[all 5 peer reviews]

HOST POSITION (frozen before the council ran; omit this block if none):
[frozen host position]

REVERSAL COST: [cheap / medium / expensive]

Two validity rules:
1. The verdict is INVALID unless it is grounded in the actual context (facts
   read from the workspace or supplied by the user, constraints named) AND it
   answers the question in its own shape. If grounding is missing, return
   "Hold — insufficient grounding" plus a numbered list of exactly what to
   inspect — not a confident recommendation.
2. If the question is an adoption question (adopt / switch to / start / buy X),
   the Recommendation must carry exactly one grade — Adopt / Trial / Hold /
   Reject / Not-our-problem — stated in plain language first, label attached.

Produce the council verdict using this exact structure:

## Where the Council Agrees
[Points multiple advisors converged on independently. High-confidence signals.]

## Where the Council Clashes
[Genuine disagreements. Present both sides. Explain why reasonable advisors disagree. Don't smooth them over.]

## Blind Spots the Council Caught
[Things that only emerged through peer review — what individuals missed that others flagged.]

## The Recommendation
[A clear, direct recommendation. Not "it depends." A real answer with reasoning. You may side with the minority if its reasoning is strongest.]

## The One Thing to Do First
[A single concrete next step. Not a list. One thing.]

## Reversal Trigger
[Medium/expensive reversal cost only — what observation would flip this
verdict, and (expensive only) the earliest checkpoint to evaluate it. Omit
this section entirely for cheap decisions.]

Be direct. Don't hedge. The whole point is to give clarity a single perspective couldn't.
```

### Step 5: Present the verdict in chat

Present the full verdict directly in chat as markdown. Do **not** generate an HTML report or any file. Keep it scannable — bullet points, the before/after where relevant.

```
## Council Verdict: {short topic}

### Where the Council Agrees
{content}

### Where the Council Clashes
{content}

### Blind Spots the Council Caught
{content}

### The Recommendation
{content}

### The One Thing to Do First
{content}

### Reversal Trigger  *(medium/expensive reversal cost only)*
{content}
```

### Step 6: Save the transcript (optional)

Only if the user asks, or the decision is significant enough to reference later. If saving, write `council-transcript-[timestamp].md` to the project's `active/` directory (or the scratchpad if none exists).

## The grounding gate

A verdict is **invalid** unless it clears two independent floors. They are pass/fail, not a balance: strength on one never compensates for the other.

1. **Grounded in the actual context.** The verdict rests on something actually inspected: workspace files read in Step 1A, numbers or constraints the user supplied, named specifics from the conversation — not on generic knowledge about the topic. If the council ran on a vague question with nothing read and no constraint named, the chairman returns **"Hold — insufficient grounding"** with a numbered list of exactly what to inspect, never a confident recommendation.
2. **Grounded in the actual question shape.** The verdict answers the question in its own shape: an adopt-or-not question gets a graded verdict (below); a choose-between-options question gets a position on the supplied options, or an honest "either is viable" with the tradeoffs; an open judgment call gets a direct recommendation. A generic essay about the topic fails this floor no matter how insightful.

### Verdict vocabulary for adoption questions

When the question is whether to adopt, switch to, buy, or start something, the Recommendation carries exactly one grade — and is always rendered in plain language first, with the label attached, never as a bare token:

- **Adopt** — "do it": proven fit, go ahead.
- **Trial** — "pilot it first": promising; prove it on a low-risk slice before committing.
- **Hold** — "wait, deliberately": a complete decision not to move now, with the condition that would reopen it. "Hold — insufficient grounding" is the gate-failure subtype.
- **Reject** — "don't": judged not worth it for this user.
- **Not-our-problem** — "this doesn't reach you": the pressure prompting the question doesn't actually apply.

Write "Hold — wait, don't switch now; revisit when X", not "Grade: Hold". The fixed vocabulary makes verdicts comparable across transcripts; it tags a plain-language call, it does not replace one.

## Important rules

- **Always spawn the 5 advisors in parallel**, and the 5 reviewers in parallel. One message, five calls each.
- **Always anonymize and randomize for peer review.** Named responses make reviewers defer to favored thinking styles.
- **The chairman can overrule the majority** when the dissenter's reasoning is stronger.
- **Don't council trivial questions.** One right answer → just answer it. The council is for genuine uncertainty where multiple angles add value.
- **Freeze any host position before exposure.** If the orchestrator holds its own view, it is written before any advisor or peer output is read (Step 1D) and never revised afterward — otherwise it is anchoring dressed up as agreement.
- **Cross-model agreement needs receipts.** If a session extends the council with real model seats through the repo's runner skills, agreement across seats counts as *independent* corroboration only when each seat's serving model is verified by the backend's own report — the runner envelope's `effective_model` — never by the model requested or by the model's self-claim. An unverified seat's agreement is weighed as if it came from the same model as the host.
- **This is one model across five lenses, not five models.** For genuine model diversity on a repo/code/architecture decision, use `models-consensus` (multi-round, real seats) or `models-roundtable` (blind poll + synthesis).

---
*Grounding gate, verdict vocabulary, reversibility tiers, position-freezing, and receipt-verified independence adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
