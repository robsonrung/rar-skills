# Review a React Change

Paths named below are relative to the loaded skill root.

Identify which chapters the diff actually touches. Read only those sections. Skip the rest.

Report each finding as `file:line` → rule name → concrete fix. A chapter that does not apply is omitted. A chapter that applies and is clean is marked `clean`. Do not invent re-renders that do not matter: cheap, rare renders are not findings.

Walk in this order, stopping a chapter when it does not apply:

| Ch | Rule name | Typical trigger |
| --- | --- | --- |
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

Read `references/composition.md` for ch 1–4, `references/memo-recon.md` for ch 5–7, `references/context-async.md` for ch 8–16. For the full per-chapter checklists (re-render sources, memo that buys nothing, Context value identity, stale closures, flicker, portals, waterfalls, races, boundaries) read `references/lenses.md`; `references/cheatsheet.md` has the decision tables and snippets.

## Standalone output and acceptance

```
## Advanced React review
- [file:line] <rule-name> — <what's wrong>. Fix: <concrete change>.
- <chapter>: clean
Verdict: <one line>
```

Acceptance: each finding has `file:line`, a rule name from the table, and a fix; unused chapters are omitted; "clean" is allowed.
