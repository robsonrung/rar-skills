---
name: advanced-react
description: "Plan, implement, and review React components with Nadia Makarevich's Advanced React: composition-first (move state down, children/elements as props, render props) before memo/useMemo/useCallback; Context split-providers; refs and stale closures; debounce/throttle; useLayoutEffect flicker; portals and stacking context; fetch waterfalls and race conditions; error boundaries. Use when planning a React component tree, deciding where state or a hook should live, implementing a list/overlay/context/fetch, reviewing re-renders, or asking should I memoize this, why does this re-render, stale closure, fetch race, modal clipped. Detects React version, compiler, and state/UI libraries first. Distinct from react (React 19 Compiler / Rules of React / 19 APIs) and from react-performance (same book, review-only performance pass)."
---

# Advanced React

Apply *Advanced React* (Nadia Makarevich, 2023) to a React change. The result is a named composition shape, code that matches it, or a review that cites book rules — not a generic React style pass and not a React 19 Compiler setup.

**Next consumer:** the implementer of the plan, the reviewer of the diff, or the user reading findings.

**Done when** the acceptance contract for the active mode is met and every claim that depends on a chapter was checked against that chapter's reference, not restated from memory.

Non-obvious intent: the book inverts the usual "wrap it in `memo`" reflex. State the **composition-first** choice out loud as you work — *this is composition-first: the hot state moves down before any memo is added*.

## Detect the target

Read the repo's `package.json` (and the lockfile if the `react` range is loose). Record four facts before choosing a pattern:

1. **React major** (`react` / `react-dom`).
2. **Compiler** — present if `babel-plugin-react-compiler` (or the equivalent Vite/Next plugin) is a dependency or the eslint compiler rule is on.
3. **Server-state / store** — TanStack Query, SWR, Apollo, RTK Query, Zustand, Jotai, Redux Toolkit, or none.
4. **UI library** — MUI, Radix, Headless UI, shadcn/ui, Chakra, Ant, or hand-rolled.

The book matches React 17/18. Where the detected version or compiler disagrees with a 2023 rule, prefer the detected framework's documented behavior and say so: "on the detected React 19, `ref` is a prop."

Compiler present: still apply **composition-first** (structure, not memo). Do not add `useMemo` / `useCallback` / `memo` the compiler already covers — that decision belongs to `react`. Still own state placement, keys, stale closures, races, waterfalls, portals, flicker, and error boundaries.

## The two anchors

**Re-renders myth.** A state update re-renders the owner and every nested component, props or not. Props are consulted only when `React.memo` is in play. Changing a local variable never updates the screen.

**Composition-first.** Structural isolation beats memoization. `React.memo` is the last resort after the composition ladder has failed, because one non-primitive prop (including `children`) silently defeats it.

Custom hooks do not move state. A hook is a pocket: `useState` / `useEffect` inside it still re-renders the component that called the hook, even if the value is never returned.

## Mode

Pick one from the user request. Default: a request to design or "how should we structure this" is **plan**; a request to write or change components is **implement**; a request to audit existing/changed React is **review**. Mixed requests run plan then implement.

### Plan

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

### Implement

Execute the named ladder rung. Read the matching reference before writing the pattern (`references/composition.md` for rungs 1–3; `references/memo-recon.md` for keys, inner components, HOCs, last-resort memo; `references/context-async.md` for context, refs, debounce, flicker, portals, fetch, errors).

Invariants while writing:

- Components and hooks are declared at module scope. A component defined inside another component is a new `type` every render → remount, lost state, lost focus.
- Every new `useMemo` / `useCallback` / `React.memo` cites one book justification from `references/memo-recon.md`. No justification → delete it.
- A hook that owns hot or high-frequency state is called from a small leaf, not from a layout, page, or provider that wraps a heavy tree.
- Debounced/throttled functions are created once and read latest values through the ref-refresh escape.
- `setState` after `fetch` / `await` in an effect keyed on a changing id is not shipped without a race strategy.

### Review

Identify which chapters the diff actually touches. Read only those sections. Skip the rest.

Report each finding as `file:line` → rule name → concrete fix. A chapter that does not apply is omitted. A chapter that applies and is clean is marked `clean`. Do not invent re-renders that do not matter: cheap, rare renders are not findings.

Walk in this order, stopping a chapter when it does not apply:

| Ch | Rule name | Typical trigger |
|---|---|---|
| 1 | move-state-down / hook-hides-state | hot state or a hook in a page/layout |
| 2–3 | children-as-props / element-as-prop | owner of hot state renders a heavy slot |
| 4 | render-prop-for-dom-data | parent must feed state into a slot |
| 5 | dead-memo / defeated-memo | `memo` / `useMemo` / `useCallback` |
| 6 | inner-component / missing-key / state-reset | lists, conditionals, remounts |
| 7 | hoc-for-cross-cutting | wrap-a-component factories |
| 8 | unmemoized-context / unsplits-context | providers |
| 9–11 | stale-closure / debounce-recreated | refs, timers, memoized callbacks |
| 12 | flicker-useEffect | measure-then-mutate |
| 13 | trapped-overlay | modal/tooltip/dropdown |
| 14–15 | waterfall / fetch-race | client fetch |
| 16 | missing-error-boundary | render errors, async errors |

Read `references/composition.md` for ch 1–4, `references/memo-recon.md` for ch 5–7, `references/context-async.md` for ch 8–16.

## Output contract

### Plan

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

### Implement

State the ladder stop in one sentence, then write the code. Acceptance: the code matches that stop; every added memo cites a justification; hooks that own hot state sit in a leaf; no inner-component definitions; every fetch-in-effect has a race strategy or uses the repo's data layer.

### Review

```
## Advanced React review
- [file:line] <rule-name> — <what's wrong>. Fix: <concrete change>.
- <chapter>: clean
Verdict: <one line>
```

Acceptance: each finding has `file:line`, a rule name from the table, and a fix; unused chapters are omitted; "clean" is allowed.

When a caller asks for a proceed-or-revise verdict (a design gate or equivalent), return exactly: `verdict` (`proceed`|`revise`), `blocking_findings`, `advisory_findings`, `required_changes`. Block on a load-bearing composition or correctness miss (hot state in a layout, defeated memo treated as real, fetch race, missing boundary on a render path). Do not block on an unmeasured "expensive" calculation.

## Gotchas

1. Do not optimize a component that renders cheaply and rarely.
2. Do not treat a custom hook as having moved state. Name **hook-hides-state** when the caller is still a heavy owner.
3. `cloneElement` to inject defaults onto an element-prop is fragile — only for the simplest defaults.
4. `forwardRef` is required before React 19 and unnecessary from React 19. Check the detected major before flagging either shape.
5. Context can *prevent* re-renders (data skips the middle tree) and *force* them (every consumer updates when `value` changes). Both are in chapter 8.
6. The book does not replace `react`. Compiler bailouts, Actions, `use()`, and the Rules of React stay there.
