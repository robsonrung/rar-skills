# GitHub Thread Operations

Exact commands for fetching, normalizing, and resolving PR review threads. The GraphQL shapes here are what `scripts/triage_threads.py` parses — keep them in sync.

## Fetch all review threads

```bash
gh api graphql --paginate \
  -F owner="$OWNER" -F name="$REPO" -F pr="$PR" \
  -f query='
query($owner: String!, $name: String!, $pr: Int!, $endCursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      reviewThreads(first: 50, after: $endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: 50) {
            nodes {
              id body createdAt
              author { login __typename }
              originalCommit { oid }
            }
          }
        }
      }
    }
  }
}' | python3 .agents/skills/review-triage/scripts/triage_threads.py --head-sha "$HEAD_SHA"
```

`--paginate` emits one JSON document per page, concatenated; the script accepts both a single document and a concatenated stream and merges the pages.

The script classifies each comment author as `bot` or `human`:

- `bot` when the login ends in `[bot]`, the author `__typename` is `Bot`, the login (with any `[bot]` suffix stripped) is in the known-bot list, or the body carries an `Automated comment by` header (bot output posted through a human's token — the header outranks the login).
- `human` otherwise — including deleted/ghost authors, which are treated as human so the human-participation gate errs toward deferring.

Extend the known-bot list per repo with `--known-bots "loginone,logintwo"`.

## Resolve a thread (silent — no reply)

```bash
gh api graphql -F id="$THREAD_ID" -f query='
mutation($id: ID!) {
  resolveReviewThread(input: {threadId: $id}) { thread { id isResolved } }
}'
```

There is deliberately no "post a reply" command in this file. Triage resolves or defers; it never speaks in threads.

## Read the swarm baseline

```bash
gh api "repos/$OWNER/$REPO/issues/$PR/comments" --paginate \
  --jq '[.[] | select(.body | contains("<!-- review-swarm-summary -->")) | .body] | first' \
  | grep -o 'swarm-sha: [0-9a-f]*'
```

Null / no match means the swarm has never run on this PR.
