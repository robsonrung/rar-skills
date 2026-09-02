# Context, refs, UI, fetch, errors (ch 8–16)

Read the section that matches the surface. Do not load the whole file into a subagent when only one section applies — quote the section name in the handoff.

## Contents

1. [Context (ch 8)](#context-ch-8)
2. [Refs (ch 9)](#refs-ch-9)
3. [Stale closures (ch 10)](#stale-closures-ch-10)
4. [Debounce / throttle (ch 11)](#debounce--throttle-ch-11)
5. [Flicker / useLayoutEffect (ch 12)](#flicker--uselayouteffect-ch-12)
6. [Portals (ch 13)](#portals-ch-13)
7. [Fetch waterfalls (ch 14)](#fetch-waterfalls-ch-14)
8. [Race conditions (ch 15)](#race-conditions-ch-15)
9. [Error handling (ch 16)](#error-handling-ch-16)

## Context (ch 8)

Context passes data through the tree without prop-wiring the middle. That **prevents** re-renders of components in between. It also **forces** every consumer to re-render when the provider `value` changes — and standard memoization cannot stop that.

Always memoize the provider `value` (and callbacks inside it):

```jsx
const value = useMemo(() => ({ user, setUser }), [user]);
return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
```

An inline `value={{...}}` / `value={[a, b]}` makes every parent render update every consumer.

**Split providers** so unrelated values do not co-trigger. `useState` → `useReducer` yields a stable `dispatch`; put state and API in two contexts.

No real selectors exist. You can fake them with `React.memo` + an HOC. If you need that, use the repo's **external store** (Redux Toolkit, Zustand, Jotai, TanStack Query, …) with memoized selectors instead. Context stays for low-frequency, localized config (theme, current entity). Larger apps should start with a selector-capable store.

On React 19, `<Ctx value={…}>` is valid; before 19 it is `<Ctx.Provider>`. Use the detected major.

Rule names: **unmemoized-context**, **unsplits-context**.

## Refs (ch 9)

A ref is a mutable `{ current }` preserved across renders. Writing `ref.current` is **synchronous** and does **not** re-render. Use it for timers, latest-callback, previous value, DOM nodes. Do not use it for anything that should appear in the UI.

`<div ref={r} />` → `r.current` is the node after commit. Refs can be passed as ordinary props.

To pass the real `ref` prop into a function component: `forwardRef` **before React 19**. From React 19, `ref` is a regular prop. Check the detected major before flagging either shape.

Expose a controlled imperative API rather than leaking the node:

```jsx
useImperativeHandle(apiRef, () => ({ focus() {}, shake() {} }), []);
```

Mutating `apiRef.current = {…}` in `useEffect` is the same idea without the hook.

## Stale closures (ch 10)

A function created during render freezes the props and state it closes over. `useCallback` / `useMemo` / a ref assigned once all form closures. Missing a dep, or never refreshing `ref.current`, leaves a **stale closure**.

Escape: keep the latest function in a ref, refresh it every render, call through the ref from a stable callback:

```jsx
const ref = useRef();
useEffect(() => {
  ref.current = () => console.log(value);
});
const onClick = useCallback(() => ref.current(), []);
```

This is also how a `React.memo` child stays referentially stable while still invoking fresh logic.

Rule name: **stale-closure**.

## Debounce / throttle (ch 11)

`debounce` / `throttle` / a `setTimeout` id must be created **once** for the component's life. Created inline in render or in a non-memoized handler, the timer resets every render and never fires correctly.

A naive `useMemo(() => debounce(fn, 500), [])` freezes `fn`'s closed state. Combine "create once" with the ch 10 ref-refresh:

```jsx
const ref = useRef();
useEffect(() => {
  ref.current = latestHandler;
});
const onChange = useMemo(() => debounce(() => ref.current(), 500), []);
```

Rule name: **debounce-recreated**.

## Flicker / useLayoutEffect (ch 12)

Measure-then-hide / measure-then-move inside `useEffect` lets the browser paint the "before" frame. `useLayoutEffect` runs synchronously before paint, so the browser sees one unbreakable task.

`useLayoutEffect` does not run in SSR. The glitch returns; opt that feature out of SSR rather than hoping the hook fires on the server.

Rule name: **flicker-useEffect**.

## Portals (ch 13)

- `position: absolute` → positioned ancestor; clipped by `overflow: hidden`.
- `position: fixed` → viewport (unless a containing block forms); escapes `overflow: hidden`, **not** a Stacking Context.
- **Nothing escapes a Stacking Context** (`position`+`z-index`, `transform`, `translate`, `opacity`, filters, …).

A Portal renders the node outside the current DOM subtree so the stacking context cannot trap it. React events still bubble on the **React** tree; layout and native form submit follow the **DOM**.

MUI `Modal`/`Popper`/`Tooltip`, Radix, Headless UI overlays already portal. Flag hand-rolled overlays that do not.

Rule name: **trapped-overlay**.

## Fetch waterfalls (ch 14)

Two categories: **initial** (needed before the page means anything) and **on-demand** (search, autocomplete, after a click).

Plain `fetch` works; you then reimplement cache, dedup, and races. A "performant" app is subjective — it depends on the message you owe the user, not a universal spinner policy.

A **waterfall** is requests started in sequence or behind a condition when they could start together. Independent `await a; await b` or an effect that waits for data A before starting B is the usual shape.

Fixes: `Promise.all`, start both promises immediately, or a data-provider Context. Respect browser parallel-connection limits. Critical initial resources can be prefetched before React mounts, still within those limits.

When the repo already has TanStack Query, SWR, Apollo, or RTK Query, prefer it over hand-rolled `fetch` in effects for server state.

Suspense-for-data was not ready in the book (2023). On a detected modern stack that already uses `use()` / official Suspense data APIs, prefer those documented APIs over inventing a 2023 workaround.

Rule name: **waterfall**.

## Race conditions (ch 15)

`setState` after `await` / `.then` in an effect keyed on a changing value (url, id) is racy: a slower earlier request can resolve last and overwrite fresh data.

```jsx
useEffect(() => {
  fetch(url)
    .then((r) => r.json())
    .then(setData); // racy
}, [url]);
```

Fixes, preferred last:

1. Remount via `key` to drop the old instance.
2. Compare the resolved id with the current id before `setState`.
3. Cleanup flag in `useEffect` — ignore results after unmount / dep change.
4. **`AbortController`** — cancel the previous request.

```jsx
useEffect(() => {
  const ac = new AbortController();
  fetch(url, { signal: ac.signal })
    .then((r) => r.json())
    .then(setData)
    .catch(() => {});
  return () => ac.abort();
}, [url]);
```

`async`/`await` does not fix this. A server-state data layer handles it.

Rule name: **fetch-race**.

## Error handling (ch 16)

After React 16, an uncaught **render** error unmounts the whole app. Place Error Boundaries at strategic points (route, major panel). That is non-negotiable.

| Mechanism | Catches | Misses |
| --- | --- | --- |
| `try/catch` | callbacks, promises | nested render, `useEffect` body, JSX |
| Error Boundary | render errors down the tree | callbacks, `setTimeout`, promises |

Bridge them: catch async errors, then re-throw into render so the boundary sees them:

```jsx
const useAsyncError = () => {
  const [, setError] = useState();
  return useCallback((e) => {
    setError(() => {
      throw e;
    });
  }, []);
};
```

Or use `react-error-boundary`, which does the same.

Rule name: **missing-error-boundary**.
