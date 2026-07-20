# Posting Findings to a Pull Request

## Bot header (mandatory)

Every body posted to GitHub — inline comment or summary — starts with:

```markdown
> [!NOTE]
> 🤖 Automated comment by **review-swarm** — not written by a human
```

This header is also how `review-triage` recognizes swarm threads; changing it breaks triage.

## Inline comments

Post all inline findings as **one** review with event `COMMENT` (never `APPROVE` or `REQUEST_CHANGES` — verdicts are summary text; approval state belongs to `approval-gate`):

```bash
gh api "repos/$OWNER/$REPO/pulls/$PR/reviews" \
  --input - <<'JSON'
{"event": "COMMENT", "body": "review-swarm inline findings — see summary comment for the verdict.",
 "comments": [
   {"path": "src/file.py", "line": 42, "side": "RIGHT",
    "body": "<bot header>\n\n**[security/codex]** 🟠 HIGH\n<problem>\n\nEvidence: <evidence>\n\nSuggested fix: <fix>"}
 ]}
JSON
```

Body format per comment: `**[<reviewer tag>]** <emoji> <severity>` then problem, evidence, suggested fix. Convergent findings use `**[convergent: <seat1> + <seat2>]**`. For multi-line anchors add `start_line`/`start_side`. A comment must anchor to a line the diff touched; if the API rejects an anchor, fold that finding into the summary instead of dropping it.

## Summary comment (upserted)

Exactly one summary comment per PR, found by its marker:

```bash
gh api "repos/$OWNER/$REPO/issues/$PR/comments" --paginate \
  --jq '.[] | select(.body | contains("<!-- review-swarm-summary -->")) | .id'
```

Update in place when found, create otherwise:

```bash
gh api "repos/$OWNER/$REPO/issues/comments/$COMMENT_ID" -X PATCH -F body=@summary.md   # update
gh api "repos/$OWNER/$REPO/issues/$PR/comments" -F body=@summary.md                    # create
```

Summary template:

```markdown
<bot header>
<!-- review-swarm-summary -->
<!-- swarm-sha: <reviewed HEAD sha> -->

## Verdict: <emoji> <VERDICT>

**Blast radius:** <overall> — <one-line routing story, e.g. "router cleared 9/11 files; auth region delegated">

### Findings
<grouped by severity: `path:line` — [reviewer] problem (one line each)>

### Convergent findings
<list, or "none">

### Seats
| Seat | Role | Status |
|---|---|---|
<router + each delegate; absent seats listed as `absent` — seat fidelity>

### Already under discussion
<topics skipped because an unresolved thread covers them, or "none">

<details><summary>Prior rounds</summary>
<one line per previous round: sha, verdict, findings count — prepend the round being replaced>
</details>
```

The `swarm-sha` marker line is the re-run baseline: `review-triage` and `pr-shepherd` read it to decide whether the swarm must run again. Update it on every round; move the replaced round's one-line record into the history block.

## Public-repo metric hygiene

On public repositories, findings and comments must not contain absolute production numbers (event volumes, user counts, revenue). Express scale as percentages or ratios. When in doubt, treat the repo as public.

## No PR / no gh

Emit the identical summary content (minus markers) as the terminal report, findings ordered by severity with `path:line` anchors. State that posting was skipped and why.
