---
name: advanced-react
description: "Plan, implement, or review React component structure, state placement, re-renders, and async behavior using composition first. Use for component design or behavior problems; use react for compiler setup and version-specific APIs."
---

# Advanced React

Apply _Advanced React_ (Nadia Makarevich, 2023) to a React change: a named composition shape, code that matches it, or a review that cites the book's rules by name. The rules, one per name, live in [references/lenses.md](references/lenses.md); check a chapter there before resting a claim on it.

## Detect the target

From `package.json` (and the lockfile if the range is loose), record:

- **React major.** The book matches 17/18. Where the detected version disagrees, follow the detected framework and say so: _"on the detected React 19, `ref` is a prop."_
- **Compiler coverage** of the affected components. A dependency or lint rule is a clue, not proof. Under the compiler, leave render-only `memo` / `useMemo` / `useCallback` to `react`; everything else here still applies.
- **Store**: TanStack Query, SWR, Apollo, RTK Query, Zustand, Jotai, Redux Toolkit, or none.
- **UI library**: MUI, Radix, Headless UI, shadcn/ui, Chakra, Ant, or hand-rolled. A styled-component-heavy library makes parent re-renders expensive; weight the re-render rules higher.

## The two anchors

**Re-renders myth.** A state update re-renders its owner and every nested component, props or not. Props matter only under `React.memo`. A custom hook is a pocket, not a move: its state re-renders whoever calls it.

**Composition-first.** Structure beats memoization. Say it as you decide: _"this is composition-first: the hot state moves down before any memo is added."_ `React.memo` is the last rung, because one recreated non-primitive prop, `children` included, silently defeats it.

Optimize only where state is hot and the subtree is heavy. A cheap, rare render is not a finding, and an unmeasured "expensive" calculation is not a reason.

## Plan

Walk the **composition ladder** and stop at the first rung that isolates the hot state from the heavy tree:

1. **move-state-down**: extract the state and its small consumer into a child.
2. **children-as-props / element-as-prop**: the owner of hot state receives the heavy subtree as an element.
3. **render-prop-for-dom-data**: only when that slot needs the owner's state or DOM data.
4. **split-context / existing-store**: skip the middle of the tree.
5. **memo-last**: only when the consumer is `React.memo`'d or uses the value as a hook dependency.

Write no production code. Emit:

```
## Advanced React plan
- Hot state: <value> owned by <component>; frequency <high|low>
- Ladder stop: <rung>
- Why not the earlier rungs: <one line>
- List identity: <key strategy | none>
- Overlay: <portal | library primitive | none>
- Fetch: <initial|on-demand>; <parallel|waterfall-risk>; race <abort|cleanup-flag|id-compare|key-remount|data-layer|n/a>
- Errors: <boundary locations | none>
- Memo: none | last-resort because <consumer is React.memo | value is a hook dep>
- Detected: React <major>, compiler <yes|no>, store <name|none>, UI <name|none>
```

Acceptance contract: every high-frequency state has an owner; the ladder stop is named and the earlier rungs rejected; every memo cites its justification; no component is defined inside another.

## Implement

Use the planned rung, or plan first when the shape is open. State the ladder stop in one sentence, then write the code.

Acceptance contract: the code matches the stop; components and hooks sit at module scope; a hook owning hot state is called from a leaf, not a page, layout, or provider; every added memo cites a **dead-memo** justification; debounced functions are created once and read fresh values through a ref; every fetch in an effect has a race strategy or uses the repo's data layer.

## Review

Walk the chapters the change touches, in order. Omit the rest.

| Ch | Rule name | Typical trigger |
| --- | --- | --- |
| 1 | move-state-down / hook-hides-state | hot state or a hook in a page or layout |
| 2–3 | children-as-props / element-as-prop | owner of hot state renders a heavy slot |
| 4 | render-prop-for-dom-data | parent must feed state into a slot |
| 5 | dead-memo / defeated-memo | `memo` / `useMemo` / `useCallback` |
| 6 | inner-component / missing-key / state-reset | lists, conditionals, remounts |
| 7 | hoc-for-cross-cutting | component factories |
| 8 | unmemoized-context / unsplits-context | providers |
| 9–11 | stale-closure / debounce-recreated | refs, timers, memoized callbacks |
| 12 | flicker-useEffect | measure-then-mutate |
| 13 | trapped-overlay | modal, tooltip, dropdown |
| 14–15 | waterfall / fetch-race | client fetch |
| 16 | missing-error-boundary | render or async errors |

```
## Advanced React review
- [file:line] <rule-name>: <what's wrong>. Fix: <concrete change>.
- <chapter>: clean
Verdict: <one line>
```

Acceptance contract: every finding carries `file:line`, a rule name from the table, and a fix; an applicable chapter with no finding is marked `clean`.

## Gate verdict

A design-gate or implement-and-review caller gets read-only review mode and its own canonical proceed-or-revise result. Revise on a load-bearing miss: hot state in a layout, a defeated memo counted as real, a fetch race, a render path with no boundary. Proceed past an unmeasured "expensive" calculation.
