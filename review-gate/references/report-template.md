# Report template

The human report renders the result JSON; it introduces no content of its own. Counts and verdicts must match the JSON exactly.

```markdown
# Review Gate — <PR/branch/range>

**Verdict: <Approve | Request Changes> — <verdictReason>**

<summary: the spec in one line, what was verified and how, what could not be assessed>

## Scope

<scope.claim>

Methodology: <scope.methodology>

| Persona | Seat (effective) | Covered |
|---|---|---|
| <agents[].persona> | <seat / execution_path / status> | <agents[].scope> |

<details><summary>Files included (<n>)</summary>

<filesIncluded as a list>
</details>

<details><summary>Spot-check (<n>) — <spotCheck.sampling></summary>

<spotCheck.files as a list>
</details>

<details><summary>Files excluded (<n>)</summary>

<filesExcluded as `path — reason` lines>
</details>

## Coverage

<details><summary>Coverage table (<n> files)</summary>

| File | Outcome | Note |
|---|---|---|
| <path> | clean / finding / spot-checked / skipped | <note> |
</details>

## Checks

| Command | Result | Note |
|---|---|---|
| `<command>` | pass / fail / skipped / not-applicable / timeout | <outputTail or note, abbreviated> |

## Preview verification

<previewVerification: URL, flows exercised, what was observed — or why skipped>

## Findings (<n>)

### <severity> — <title> (<path>:<line>, confidence <c>, <agent>)

<body>

## Comments (<n>)

- **<title>** — <body> (<agent>)

## PR quality

**<prQuality.rating>** — <prQuality.notes: spec-vs-implementation assessment plus scope-creep/style-churn callout>
```

Order findings by severity (P0 first), then path. Omit the Comments and Preview sections when empty; never omit Coverage or Checks — an empty checks table with `verify: true` is itself a red flag the reader must see.
