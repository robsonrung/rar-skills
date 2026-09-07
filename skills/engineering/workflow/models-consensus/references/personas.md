# Personas Protocol

Use this mode only when the user approves a single-model council of five independent thinking lenses. It supplies angle diversity, not provider diversity. The final report must state that diversity confidence is low by construction.

## Approved plan

The preview names one seat, its requested model and provider, serving-receipt requirement, effort for advisors, reviewers, and chairman, whether peer review runs, and the full call budget. Do not change that model or add a second model after approval.

The default plan is five advisors, five peer reviewers, and one chairman. A user may approve a lean plan without peer review. The plan records this choice before the first call.

## Lenses

| Lens | Question it must answer |
| --- | --- |
| Contrarian | What can fail, and what assumption is unsafe? |
| First Principles | What problem are we actually solving? |
| Expansionist | What upside or adjacent option is being missed? |
| Outsider | What is unclear without insider context? |
| Executor | What is the first practical move and its constraint? |

## Protocol

1. Build one neutral question from the user input and approved read-only context. If the orchestrator has a view, freeze it before reading any advisor output.
2. Run five fresh advisor contexts in parallel. Each receives one lens, the neutral question, and the approved output budget.
3. When peer review is approved, randomize advisor labels and run five fresh reviewer contexts in parallel. Each reviewer identifies the strongest response, its blind spot, and what all advisors missed.
4. Run one fresh chairman context. It sees de-anonymized advisor outputs, anonymized reviews, and the frozen host position only when the approved plan allows it.
5. Write the verdict and record requested, configured, effective, and observed model fields with receipt status and source.

Advisor prompt:

```text
You are the <lens> lens in a decision council.

QUESTION:
<neutral question>

Analyze only from this lens. Be direct. State assumptions, evidence limits,
and one recommendation. Do not try to balance the other lenses.
```

Reviewer prompt:

```text
Review the anonymized council responses for this question.

1. Which response is strongest, and why?
2. Which response has the largest blind spot?
3. What did all responses miss?
```

## Verdict

The chairman returns:

1. Where the council agrees.
2. Where the council clashes.
3. Blind spots the council caught.
4. A direct recommendation.
5. One thing to do first.
6. A reversal trigger when the decision is costly to undo.

If the question is an adoption decision, use one grade: Adopt, Trial, Hold, Reject, or Not-our-problem. Insufficient evidence produces "Hold: insufficient evidence" and a numbered inspect list.

Do not treat five lenses as five independent model votes. Record the single requested, configured, effective, and observed model fields; receipt status and source; complete call list; and `diversity confidence: low`.
