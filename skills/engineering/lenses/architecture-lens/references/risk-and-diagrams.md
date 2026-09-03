# Risk And Diagrams

Read this when a decision carries real risk (unproven technology, a data or availability boundary, a migration) or when the review needs a picture to be understood. Not needed for a routine placement or coupling finding.

For the decision record itself, use `adr-template.md` — the repo-canonical ADR template.

## Risk Pass

Rate every named risk on impact and likelihood with one scale:

1. **Low**: small impact, or unlikely.
2. **Medium**: meaningful impact, or plausible.
3. **High**: severe impact and plausible — or unknown technology. Treat unknown or unproven technology as high risk until it has been tested in this context.

For each high risk, give a mitigation, a verification step, and an owner. When the work is code only, the owner is the current change set.

Record each risk with these seven fields:

1. Area.
2. Attribute affected.
3. Impact.
4. Likelihood.
5. Current evidence.
6. Mitigation.
7. Verification.

Evidence is the field most often skipped and the one that separates a real risk from a worry. Cite the file, query, config, or dashboard that makes the risk plausible.

## Risk storming with a single reviewer

Risk storming is normally a group exercise. When one reviewer is doing it alone — a single agent or a single person — run it as a first pass:

1. Draw or describe the current architecture context.
2. Pick one dimension: availability, scalability, security, data integrity, performance, deployability, or maintainability.
3. Mark likely risk points from code evidence, not from intuition.
4. Separate confirmed risk from suspected risk, and label which is which.
5. Mitigate through scoped code changes, tests, or an explicit follow-up.

Do not pretend solo analysis is consensus. Name it as a first pass.

## Diagram Guidance

Prefer a low-ritual diagram early over a polished one late. Use C4 levels when they help:

1. **Context**: users and external systems.
2. **Container**: deployable or runtime units.
3. **Component**: internal building blocks.
4. **Class or code level**: only when the code structure is itself the point.

Diagram rules:

1. Keep the view context clear when drilling in — say which level you are at.
2. Label every ambiguous element.
3. Distinguish sync from async communication.
4. Show data ownership and direction when relevant.
5. Include a key if the symbols are not obvious.
