# Advanced React — per-chapter cheat sheet

Source: *Advanced React* by Nadia Makarevich (2023). Page-level decision tables and the
canonical code snippets behind each lens in `SKILL.md`. Consult a section when a lens fires
and you need the exact pattern.

---

## Ch 1 — Re-renders

- Re-render = React calling a component's function again. **State update is the only initial
  source** of re-renders (plus parent re-render, context change).
- A re-render flows **down**, never up: a state change re-renders the owner and *every*
  nested component, regardless of props. React never re-renders parents because a child
  changed.
- Without memoization, **props don't matter** — children re-render even with no props.
- A state update inside a hook re-renders the component using that hook, even if the state
  value is never read; and through a chain of hooks, any update re-renders the consumer of
  the first hook.

**"Moving state down"** — the primary fix:
```jsx
// ❌ value lives in App → typing re-renders <VerySlowComponent/>
const App = () => {
  const [value, setValue] = useState('');
  return (<><input value={value} onChange={e => setValue(e.target.value)} /><VerySlowComponent /></>);
};

// ✅ isolate the state + its consumer; App (and the slow tree) no longer re-render on type
const SearchInput = () => {
  const [value, setValue] = useState('');
  return <input value={value} onChange={e => setValue(e.target.value)} />;
};
const App = () => (<><SearchInput /><VerySlowComponent /></>);
```

## Ch 2 — Elements, children as props

- **Component** = a function `(props) => Elements`. **Element** = the object `<B />`
  produced; `type` is a string (DOM) or a component reference.
- A component re-renders when *its element object changes* (by `Object.is`).
- Elements passed **as props** (including `children`) are created by the *parent's* parent,
  so they don't re-render when the receiving component updates its own state.
- `children` is just `props.children`; `<Parent><Child/></Parent>` ≡ `<Parent children={<Child/>}/>`.

```jsx
// state in ScrollDetector changes constantly; {children} passed in does NOT re-render
const ScrollDetector = ({ children }) => {
  const [scroll, setScroll] = useState(0);
  return <div onScroll={e => setScroll(e.target.scrollTop)}>{children}</div>;
};
<ScrollDetector><SlowComponent /></ScrollDetector>;
```

## Ch 3 — Configuration via elements as props

- Push configuration of a rendered child up to the consumer by accepting the whole element:
  `<Button icon={<Error color="red" size="large" />} />`.
- An element stored in a variable but passed to a conditionally-rendered component is only
  rendered when that component actually renders:
  ```jsx
  const footer = <Footer />;                 // not rendered yet
  return isDialogOpen ? <ModalDialog footer={footer} /> : null;
  ```
- To inject/override default props onto an element-prop, use `React.cloneElement`.

## Ch 4 — Render props

- Convert an element-prop to a **render prop** when the parent must control its props or
  feed it state:
  ```jsx
  const Button = ({ renderIcon }) => {
    const [state, setState] = useState();
    return <button>Submit {renderIcon({ size: 'large' }, state)}</button>;
  };
  <Button renderIcon={(props, state) => <Icon {...props} active={state} />} />;
  ```
- `children` can be a render prop: `const Parent = ({ children }) => children(data);`.
- Hooks replaced render-props-for-logic in ~99% of cases. Keep render props mainly for
  logic tied to a **DOM element** (size/position trackers, etc.).

## Ch 5 — Memoization (memo / useMemo / useCallback)

- Reference comparison only: objects/arrays/functions differ every render unless memoized.
  An inline fn passed to `useMemo`/`useCallback` is recreated each render (that's expected —
  the *output* is what's stabilized). `useCallback(fn)` ≈ `useMemo(() => fn)`.
- **Memoizing a prop helps only if** the consumer is `React.memo` *and uses it as a dep*, or
  it's passed further down into such a situation. Otherwise the memo is dead weight.
- `React.memo` skips a re-render triggered *by the parent* only when **all** props are
  unchanged by reference. Triggers from own state/context still re-render.
- Memoizing *all* props is harder than it looks: avoid passing non-primitive values sourced
  from other props/hooks; **`children` is non-primitive too** and must be memoized.
- **Order of preference:** composition (ch 1–4) → then `React.memo` as a last resort.

## Ch 6 — Diffing & reconciliation

- React diffs by **position in the returned array** + **type**: same type+position → update
  in place; type change at a position → unmount old, mount new (state lost).
- Conditional `cond ? <A/> : <B/>` occupies one array slot (even a `null` branch).
- **Dynamic arrays need `key`** — stable identity across reorder/add/remove; critical when
  items are `React.memo`'d.
- `key` is a general tool, not array-only:
  - same type+position + changing `key` → force a **remount** ("state reset", e.g. on route
    change).
  - use `key` to make React treat two same-type elements as the same/different deliberately.

## Ch 7 — Higher-order components

- HOC = `(Component) => (props) => <Component {...props} injected="x" />`. Can inject props
  and logic (hooks allowed inside the returned component).
- Modern use: cross-cutting concerns (logging, feature flags, fake context selectors). For
  shared stateful logic, prefer hooks.

## Ch 8 — Context & performance

- Every consumer re-renders when provider `value` changes; **memoization in consumers can't
  stop it**.
- **Always memoize the provider value** (and any callbacks in it):
  ```jsx
  const value = useMemo(() => ({ user, setUser }), [user]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
  ```
- **Split providers** so unrelated values don't co-trigger; `useReducer` separates stable
  `dispatch` from changing state, enabling two contexts (state vs API).
- No native selectors; emulate with `React.memo` + HOC, but for anything non-trivial use
  **RTK** (already in this repo) with memoized selectors.

## Ch 9 — Refs

- Ref = mutable `{ current }` preserved across renders; updates are **synchronous** and do
  **not** re-render. Good for: timers, latest-value tracking, previous value, DOM nodes.
- `<div ref={r} />` → `r.current` is the DOM node after render. Refs can be passed as normal
  props.
- To pass the real `ref` prop to a function component (React 17): `forwardRef`.
  ```jsx
  const InputField = forwardRef((props, ref) => <input ref={ref} />);
  ```
- Expose a controlled imperative API with `useImperativeHandle` instead of leaking the node:
  ```jsx
  useImperativeHandle(apiRef, () => ({ focus: () => {}, shake: () => {} }));
  ```

## Ch 10 — Closures

- A closure forms whenever a function is created inside another; React components are
  functions, so `useCallback`/`useMemo`/`useRef` callbacks all close over render-time data.
- When called later, that data is a **frozen snapshot**. To refresh it, re-create the
  function — that's what hook **deps** do. Missing dep → **stale closure**.
- **Stale-closure escape via ref:**
  ```jsx
  const ref = useRef();
  useEffect(() => { ref.current = () => console.log(value); }); // refresh every render
  const onClick = useCallback(() => ref.current(), []);          // stable, yet sees latest
  ```

## Ch 11 — Debounce / throttle with refs

- Debounced/throttled fns must be created **once** (component mount), else the internal
  timer resets every render and never fires.
- Memoize the debounced fn, but a naive memo freezes state — combine with the ref-refresh
  trap so it reads the latest value:
  ```jsx
  const onChange = useMemo(() => debounce(() => ref.current(), 500), []);
  ```

## Ch 12 — useLayoutEffect (flicker)

- `useEffect` runs async → browser may paint the pre-mutation frame → visible glitch when
  you measure-then-move/resize/hide DOM.
- `useLayoutEffect` runs **synchronously before paint** → one unbreakable task, no glitch.
- Doesn't run in SSR (React skips it); opt out of SSR for that feature if needed. (N/A for
  this Amplify SPA.)

## Ch 13 — Portals & stacking context

- `position: absolute` → relative to positioned ancestor; clipped by `overflow: hidden`.
- `position: fixed` → relative to viewport; escapes `overflow: hidden` **but not** a
  Stacking Context.
- **Nothing escapes a Stacking Context** (formed by `position`+`z-index`, `transform`,
  `translate`, `opacity`, filters, …).
- **Portal** renders DOM outside the subtree (modals, tooltips). React events bubble along
  the React tree; layout follows the portal target. MUI `Modal`/`Popper`/`Tooltip` already
  portal — flag hand-rolled overlays that don't.

## Ch 14 — Data fetching & waterfalls

- Two categories: **initial** vs **on-demand**. Plain `fetch` works but you reimplement
  caching/dedup/race handling manually.
- **Waterfall** = requests that run in sequence/conditionally when they could be parallel.
  Avoid with `Promise.all`, parallel-started promises, or a data-provider Context.
- Mind browser parallel-connection limits; prefetch critical resources before React mounts
  (within those limits).

## Ch 15 — Race conditions

- Risk: `setState` after an `await`/`.then` in an effect keyed on a changing value. An older
  request can resolve last and clobber newer data.
  ```jsx
  useEffect(() => { fetch(url).then(r => r.json()).then(setData); }, [url]); // ⚠
  ```
- Fixes (best last):
  1. remount component (key change) to discard old data,
  2. compare resolved id vs current before `setState`,
  3. cleanup flag in `useEffect` drops stale results,
  4. **`AbortController`** cancels previous requests.
  ```jsx
  useEffect(() => {
    const ac = new AbortController();
    fetch(url, { signal: ac.signal }).then(r => r.json()).then(setData).catch(() => {});
    return () => ac.abort();
  }, [url]);
  ```
- **Prefer RTK Query** for server state — it handles dedup, caching, and stale-response
  discarding for you.

## Ch 16 — Error handling

- Post-React-16: an uncaught render error **unmounts the whole app**. Place several
  `ErrorBoundary`s at strategic points (route, major panel).
- `ErrorBoundary` catches errors from anywhere **down** the tree, but **not** in callbacks,
  `setTimeout`, or promises.
- `try/catch` catches async/callback errors, but **not** errors from nested components,
  render, or `useEffect`.
- Merge them: catch async errors with `try/catch`, then **re-throw into render** so the
  boundary catches them:
  ```jsx
  const useAsyncError = () => {
    const [, setError] = useState();
    return useCallback(e => setError(() => { throw e; }), []);
  };
  ```
  Or use the `react-error-boundary` library.
