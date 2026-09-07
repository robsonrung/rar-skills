---
name: open-pr
description: Commit scoped changes, push a branch, and open or update a GitHub pull request. Use when the user asks to open a pull request, commit and push work, or write or update a pull request description. Do not use to implement work or merge a pull request.
---

# Open Pull Request

Create a reviewable pull request whose title, body, and commits explain the change and its evidence. The next consumer is the reviewer. Done means the requested description is returned or the remote pull request URL is confirmed.

## Mandate

A description-only request is read-only. A request to open a pull request authorizes creating a feature branch when needed, staging only the task's files, committing those files, pushing the branch, and creating or updating its pull request. It does not authorize staging unrelated work, rewriting another contributor's work, merging, or changing remote settings.

## Workflow

1. Read repository state, current branch, intended changed files, remote, default branch, and any open pull request for the current head. Treat a failed pull-request lookup as unknown, not as proof that no pull request exists.
2. Choose the route:
   1. Description only: compose and return the title and body. Do not modify the remote.
   2. Existing pull request: push the scoped commits, then update its body only when the request includes that change.
   3. New pull request: create a feature branch if the current branch is the default branch or detached, then commit, push, and create it.
3. When a branch must be created from the default branch, read `references/branch-creation.md`. Do not stash, reset, or switch through conflicting local changes automatically.
4. Stage explicit files only. Keep unrelated working-tree changes out of the commit. Split commits only when the change has clearly independent reviewer value.
5. Read `references/pr-description-writing.md`. Compose from the complete change range, not the latest commit. Lead with the outcome, state validation or its limitation, and retain required project template fields.
6. Recheck the branch and existing pull request immediately before pushing or creating one. If the state is still unknown, stop and report the blocker rather than risk a duplicate pull request.
7. Apply the body through a temporary file so its literal content survives the command. Confirm the resulting URL, title, and body when the platform allows it.

## Boundaries

Use the repository's active conventions for commit messages and pull request structure. Never add generated-by text, authorship claims, or co-author trailers to a commit message, title, or body. Do not claim a check ran unless captured output proves it.

## Output

Lead with the pull request URL or the drafted title. State the branch, commits made, validation evidence, and any known limitation. For description-only work, return the title and body without applying it.
