# Plan a React Change

Paths named below are relative to the loaded skill root.

Read `references/composition.md` first. Then read only the later reference a planned surface needs (`references/memo-recon.md` for lists/keys/memo; `references/context-async.md` for context, refs, overlays, fetch, errors).

Walk the **composition ladder** in order and stop at the first rung that isolates the hot state from the heavy tree:

1. **Move state down** — extract the state and the small consumer into a child.
2. **Children / element-as-prop** — the owner of hot state accepts a pre-created element so that subtree does not re-render with the owner.
3. **Render prop** — only if that slot must receive the owner's state or DOM data. Shared logic alone is a hook, not a render prop.
4. **Context or the existing store** — skip the middle of the tree. Split providers (or `useReducer` + state/API contexts). If a store with memoized selectors already exists, use it for hot cross-tree state; keep Context for low-frequency config.
5. **Memo last** — only when a consumer is `React.memo`'d or uses the value as a hook dep.

Also name, even if the answer is "none":

- list identity / remount `key`
- overlay → Portal or the library's overlay primitive
- fetch: initial vs on-demand; parallel vs waterfall; race strategy
- error-boundary placement

Emit the plan contract below. Do not write production code in this mode.

## Output and acceptance

```
## Advanced React plan
- Hot state: <value> owned by <component>; frequency <high|low>
- Ladder stop: move-state-down | children-as-props | element-as-prop | render-prop | split-context | existing-store | memo-last
- Why not the earlier rungs: <one line>
- List identity: <key strategy or none>
- Overlay: <portal / library primitive / none>
- Fetch: <initial|on-demand>; <parallel|waterfall-risk>; race <abort|cleanup-flag|id-compare|data-layer|n/a>
- Errors: <boundary locations or none>
- Memo: none | last-resort because <consumer is React.memo or value is a hook dep>
- Detected: React <major>, compiler <yes|no>, store <name|none>, UI <name|none>
```

Acceptance: every high-frequency state has an owner; the ladder stop is named; earlier rungs are explicitly rejected; every proposed memo cites a book justification; no component-inside-component is planned.
