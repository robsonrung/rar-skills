# Team Checklists

Use this reference when architecture work affects developer guidance, pull request review, release readiness, or team workflow.

## Boundary Guidance

The architect role in a coding session should give enough constraint to protect the architecture and enough freedom for implementation.

Too much control:

1. Specifies implementation detail that belongs to the developer.
2. Blocks useful libraries or tools without a clear quality reason.
3. Creates friction without improving risk.

Too little control:

1. Leaves architectural decisions to accidental local choices.
2. Gives diagrams with no actionable constraints.
3. Avoids hard decisions until the team has to decide under pressure.

Effective guidance:

1. Gives clear boundaries.
2. Explains why the boundary matters.
3. Allows local choice inside the boundary.
4. Turns repeated guidance into a check or decision record.

## Code Completion Checklist

Use only for items that are easy to miss and not already automated:

1. Formatting and cleanup are complete.
2. No swallowed exceptions or silent failure paths were added.
3. Public contracts and schemas are updated.
4. Architecture boundaries still hold.
5. New dependency has a technical and business reason.
6. Important logs, metrics, and traces exist.
7. Tests cover the risky behavior.

## Unit And Functional Test Checklist

Prompt for missed cases:

1. Minimum and maximum values.
2. Missing fields.
3. Special characters.
4. Permission boundaries.
5. Retry or duplicate requests.
6. Error and timeout paths.
7. Migration or compatibility behavior.
8. Cross component contract behavior.

If a checklist item can be automated, prefer automation and remove it from the manual checklist.

## Release Checklist

Use when deployment risk exists:

1. Build and test checks pass.
2. Database migrations have a forward path and rollback notes.
3. Configuration and environment changes are documented.
4. New dependencies are known.
5. Observability exists for the changed path.
6. Data backfill or replay steps are defined.
7. Rollout and rollback risks are named.
8. Owners for follow up are clear.
