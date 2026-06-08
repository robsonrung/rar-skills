# ADR, Risk, And Diagrams

Use this reference when the task involves a long lived decision, repeated debate, high risk implementation, or architecture communication.

## ADR Guidance

Create a concise ADR when a decision affects structure, quality attributes, dependencies, interfaces, data ownership, construction technique, cost, security, or more than one team.

Template:

1. Title: short and specific.
2. Status: proposed, accepted, superseded, or request for comments with deadline.
3. Context: forces, constraints, and alternatives.
4. Decision: clear statement of what will be done.
5. Consequences: benefits, costs, and trade offs.
6. Compliance: how the decision will be checked.
7. Notes: author, approval, links, and superseded records.

Decision quality test:

1. Does it explain why, not only how?
2. Does it include business value?
3. Does it name rejected alternatives when useful?
4. Does it say how compliance will be measured?
5. Does it have one system of record?

## Risk Analysis

Use impact and likelihood.

1. Impact: low, medium, high.
2. Likelihood: low, medium, high.
3. Rating: low, medium, high.

Unknown or unproven technology should be treated as high risk until tested.

For each risk:

1. Area.
2. Attribute affected.
3. Impact.
4. Likelihood.
5. Current evidence.
6. Mitigation.
7. Verification.

## Codex Solo Risk Storming

When no team session is possible:

1. Draw or describe the current architecture context.
2. Pick one dimension such as availability, scalability, security, data integrity, performance, deployability, or maintainability.
3. Mark likely risk points from code evidence.
4. Separate confirmed risk from suspected risk.
5. Mitigate through scoped code changes, tests, or explicit follow up.

Do not pretend solo analysis is consensus. Name it as a first pass.

## Diagram Guidance

Prefer a low ritual diagram early. Use C4 style when useful:

1. Context: users and external systems.
2. Container: deployable or runtime units.
3. Component: internal building blocks.
4. Class or code level only when needed.

Diagram rules:

1. Keep view context clear when drilling in.
2. Label every ambiguous element.
3. Distinguish sync and async communication.
4. Show data ownership and direction when relevant.
5. Include a key if symbols are not obvious.
