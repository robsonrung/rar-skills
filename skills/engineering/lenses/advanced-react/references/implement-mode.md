# Implement a React Change

Paths named below are relative to the loaded skill root. Use the chosen composition shape, or select it through plan mode when the shape is unresolved.

Execute the named ladder rung. Read the matching reference before writing the pattern (`references/composition.md` for rungs 1–3; `references/memo-recon.md` for keys, inner components, HOCs, last-resort memo; `references/context-async.md` for context, refs, debounce, flicker, portals, fetch, errors).

Invariants while writing:

- Components and hooks are declared at module scope. A component defined inside another component is a new `type` every render → remount, lost state, lost focus.
- Every new `useMemo` / `useCallback` / `React.memo` cites one book justification from `references/memo-recon.md`. No justification → delete it.
- A hook that owns hot or high-frequency state is called from a small leaf, not from a layout, page, or provider that wraps a heavy tree.
- Debounced/throttled functions are created once and read latest values through the ref-refresh escape.
- `setState` after `fetch` / `await` in an effect keyed on a changing id is not shipped without a race strategy.

## Acceptance

State the ladder stop in one sentence, then write the code. Acceptance: the code matches that stop; every added memo cites a justification; hooks that own hot state sit in a leaf; no inner-component definitions; every fetch-in-effect has a race strategy or uses the repo's data layer.
