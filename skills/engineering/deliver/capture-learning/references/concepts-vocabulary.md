# CONCEPTS.md vocabulary rules

Read this only when a solution learning may improve an existing `CONCEPTS.md`.

`capture-learning` updates an existing glossary only. Creating or broadly seeding one needs an explicit glossary task because a single solution does not establish the project's domain model.

## What earns an entry

A term qualifies when it has a project-specific meaning that a new engineer needs to understand conversations, tickets, or code. General programming vocabulary and ordinary domain words do not qualify.

Use source evidence for behavioral rules. A solution document can name a term, but it must not create a glossary entry from a guess.

## Entry shape

Keep each entry self-contained:

```markdown
### Canonical term
One sentence defining what the term means in this project and how it differs from nearby terms.

*Avoid:* retired synonym

One short paragraph only when lifecycle, ownership, or transition rules are essential.
```

Do not include paths, implementation details, current counts, links to work items, or version claims. Group related entries together and preserve the file's existing organization.

When the team has settled a distinction between two terms, preserve that distinction. A glossary is an agreed vocabulary, not a record of every synonym ever used.
