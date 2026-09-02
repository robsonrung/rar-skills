# Completion, Test, And Release Checklists

Read this at the end of a review when the change is about to be handed off or deployed. Use only the items that are easy to miss and not already automated — anything a linter, type checker, or CI job already enforces does not belong on a manual list. If an item here can be automated, automate it and delete the row.

## Code Completion Checklist

1. Formatting and cleanup are complete.
2. No swallowed exceptions or silent failure paths were added.
3. Public contracts and schemas are updated.
4. Architecture boundaries still hold.
5. Any new dependency has a technical and a business reason.
6. Important logs, metrics, and traces exist for the changed path.
7. Tests cover the risky behavior, not only the happy path.

## Unit And Functional Test Prompts

Prompt for the cases a diff-shaped review tends to miss:

1. Minimum and maximum values.
2. Missing fields.
3. Special characters.
4. Permission boundaries.
5. Retry or duplicate requests.
6. Error and timeout paths.
7. Migration or compatibility behavior.
8. Cross-component contract behavior.

## Release Checklist

Use when the change carries deployment risk:

1. Build and test checks pass.
2. Database migrations have a forward path and rollback notes.
3. Configuration and environment changes are documented.
4. New dependencies are known.
5. Observability exists for the changed path.
6. Data backfill or replay steps are defined.
7. Rollout and rollback risks are named.
8. Owners for follow-up are clear.

A release item with no named owner is not a plan. If the answer to "who does this if it goes wrong" is nobody, that is the finding to report.
