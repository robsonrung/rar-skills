# Isolation and Integration

One track in the current working tree is the default. It is the **smallest reversible move** because it avoids branches, merges, and cleanup that the task did not need.

Use worktrees when independent tracks can run concurrently. Creating them is reversible and is within an implementation request. Commit-based integration remains a separate authorized action.

## Before Parallel Work

Confirm all of these facts:

1. The tracks have disjoint file scopes and no shared type, API, migration, generated artifact, lockfile, registry, or environment singleton.
2. The expected merge and verification cost is lower than sequential work.
3. Each track has a distinct approved implementation and review route.
4. Any commit-based integration has separate user authorization.

If any fact is uncertain, work sequentially. **Decline parallelism on uncertainty.**

## Launcher Behavior

For worktree isolation, the launcher creates one branch and worktree per explicit `--track` pair and records each path in its manifest. It does not commit, merge, push, or open a pull request.

If an existing worktree or branch has the chosen name, the launcher stops unless the caller explicitly uses `--force`. The cleanup command removes only branches and worktrees named in that manifest. It reports any failed removal instead of claiming success.

## Integration

Integrate only after each track meets its acceptance contract and the user has authorized the required git action. Verify the combined result after integration. If a seam or high-risk boundary needs a broader review, use the user-selected `full-review` plan after the combined checks are green.

Do not delete worktrees or branches after a run unless that cleanup was explicitly requested. Report their paths so the user can inspect them.
