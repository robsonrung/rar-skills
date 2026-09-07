# Adversarial verification

Use this only when the approved deep review plan includes an independent skeptic route. It protects against a plausible high-risk finding that cannot be reproduced directly.

## Trigger

Run one skeptic pass when all conditions hold:

1. The finding is security, correctness, reliability, or performance related.
2. It is critical or high severity.
3. One seat raised it and execution neither verified nor refuted it.
4. The approved plan names an independent skeptic route.

Do not add a reviewer from a convenience pool. The selected skeptic must be a distinct approved route and must not be the seat that originated the finding.

## Input and result

Give the skeptic the finding, its diff slice, and the surrounding source. Do not provide the originating rationale. Ask whether the evidence refutes the finding.

Record one of these results:

| Result | Effect |
| --- | --- |
| `refuted` | Drop the finding. |
| `survived` | Keep it and state that independent review did not refute it. |
| `inconclusive` | Keep the original confidence and record the coverage limit. |

Run at most one skeptic pass per finding and only for the highest-risk findings selected by the plan. A skeptic is evidence, not a replacement for a runnable reproduction.
