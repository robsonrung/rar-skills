# Targeted review-thread route

Use this route only for a URL that identifies one discussion.

1. Parse the host, owner, repository, pull request number, and comment identifier from the URL.
2. Fetch the comment from the code host and map its node identifier to a review thread with scripts/get-thread-for-comment. Pass the parsed host on every host-specific command.
3. Run scripts/get-pr-comments for the same pull request before replying. Stop if it reports a pending personal review.
4. Evaluate only the selected thread with references/evaluation-rubric.md. Read enough surrounding code to relocate an outdated comment or refute it.
5. For an accepted fix, validate, stage only affected files, commit, and push before replying and resolving the thread.
6. For reply, declined, or not-addressing outcomes, post the evidence and resolve only the selected thread. Leave needs-human open and unchanged.
7. Re-fetch the thread and report its state.
