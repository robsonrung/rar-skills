# Branch creation from the default branch

Use this only when the requested pull request starts from the default branch or detached HEAD.

1. Fetch the remote default branch when available.
2. If the local default branch contains commits absent from the remote, show those commits and ask whether the new branch should include them. There is no safe default because the answer changes the pull request's scope.
3. Create the feature branch from the selected base and confirm the current branch.
4. If local changes would be overwritten, stop and report the conflict. Do not stash, reset, discard, or replay work automatically.

When the remote base cannot be fetched, branch from the current checked-out commit and state that base freshness was not verified. Creation may continue, but pull-request creation still requires a reachable remote.
