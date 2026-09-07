# Feedback evaluation

Evaluate feedback against the current code, tests, project rules, and accepted decisions. The reviewer identity and the wording of a comment are not proof.

## Classification

| Result | Use when | Action |
| --- | --- | --- |
| fix | Evidence confirms a scoped improvement. | Implement and validate it. |
| reply | A question has an evidence-backed answer. | Reply, then resolve the thread when complete. |
| not-addressing | The concern is absent, already handled, or no longer applies. | Reply with the evidence, then resolve. |
| declined | The suggested change conflicts with a project rule or causes a concrete harm. | Reply with that evidence, then resolve. |
| needs-human | A product, security, or design decision remains after investigation. | Leave the thread open and present the decision context. |

## Evidence check

1. Read the changed line and the smallest useful surrounding context.
2. Read callers, tests, history, or the accepted plan only when the concern is contestable or changing it could alter an intended behavior.
3. For an outdated thread, search the same file for a concrete anchor. If the concern moved, re-evaluate it there. If it disappeared, use not-addressing. If locating it would require guessing across files, use needs-human.
4. Keep a class fix limited to changed sites with the same verified invariant. Do not broaden it to older unrelated code.

## Reply and decision context

Reply with the smallest relevant quote, the evidence, and the result. Do not post a reply for needs-human.

For needs-human, state the reviewer request, the evidence found, the exact decision, the viable options, and a recommendation when evidence supports one.
