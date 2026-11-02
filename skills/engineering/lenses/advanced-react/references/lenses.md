# Advanced React rules, by chapter

One entry per rule name in the SKILL.md review table. Each states the decision, not the textbook.

## Composition (ch 1–4)

**re-renders-myth.** State updates start every re-render; parent re-renders and context changes carry it down, never up. Flag any reasoning that blames "props changed" for a re-render of a component that is not `React.memo`'d. React 17 batches updates only inside React event handlers; 18+ batches everywhere, so a double render can be version-specific.

**move-state-down.** Fast-changing state (input value, hover, open flag) held in a page or layout re-renders the whole subtree. Extract the state and its only consumer into a child. The highest-leverage fix in the book; stop here when the state is consumed only next to its control.

**hook-hides-state.** `useState`, `useReducer`, or an effect that sets state inside a custom hook re-renders the hook's caller, even when the caller never reads the value; through a chain of hooks, the outermost caller. A resize listener in a hook called from a layout is hot state in the layout. Fix: call the hook from the leaf that needs it.

**children-as-props / element-as-prop.** An element passed as a prop, `children` included, is created by the parent's parent, so it does not re-render when the receiver's own state changes. Use it when the owner of hot state renders a heavy slot that does not need that state, and to push a child's configuration up to the consumer (`<Button icon={<Error size="large" />} />`). An element held in a variable renders only if the component receiving it renders. `cloneElement` to inject defaults is fragile; keep it to the simplest defaults.

**render-prop-for-dom-data.** Turn an element-prop into a render prop only when the parent must feed the slot its state or DOM data (size and position trackers). Shared logic alone is a hook.

## Memoization, reconciliation, HOCs (ch 5–7)

**dead-memo.** Objects, arrays, and functions compare by reference. A `useMemo` / `useCallback` earns its place only when the value is (a) a prop of a `React.memo` component, (b) a dependency of `useEffect` / `useMemo` / `useCallback`, or (c) passed down into (a) or (b). Otherwise delete it. Memos stacked only to feed each other bury the logic. Measure "expensive" on a representative device before memoizing a calculation: a one-off sort on click is not, a 30 ms regex on every mouse move is.

**defeated-memo.** `React.memo` skips a parent-triggered render only when every prop is referentially unchanged; own state and context still re-render it. One recreated object, array, function, or `children`, or a value derived from an unmemoized prop or hook, defeats it. With the compiler covering the component, keep a manual memo only for a hook dependency, a non-compiled consumer, or a custom `areEqual`; `react` owns that split.

**inner-component.** A component declared inside another is a new `type` every render: remount, lost state, lost focus, at least twice the cost of a re-render. Declare components and hooks at module scope.

**missing-key.** Reconciliation matches by position and type. Dynamic arrays need stable keys; index keys break on reorder, worst under `React.memo`'d items. Static arrays need none.

**state-reset.** A ternary occupies one slot even when a branch is `null`, so `cond ? <Input /> : <Input />` shares state across branches. Give the branches different keys to separate them. Changing a `key` on the same type and position forces a remount: the deliberate reset on route or entity change.

**hoc-for-cross-cutting.** An HOC wraps a component to inject props or wrap events. Keep it for cross-cutting concerns (logging, feature flags, faked context selectors); shared stateful logic belongs in a hook.

## Context (ch 8)

**unmemoized-context.** Context _prevents_ re-renders in the middle of the tree and _forces_ every consumer to re-render when the provider `value` changes; consumer memoization cannot stop that. An inline object `value` is a candidate for an identity check, not a defect by syntax: confirm compiler coverage and measured consumer work, then `useMemo` the value if compilation does not stabilize it.

**unsplits-context.** Split unrelated values into separate providers. `useReducer` gives a stable `dispatch`, so state and API can live in two contexts. Context has no selectors; when hot cross-tree state needs them, use the repo's store with memoized selectors and keep Context for low-frequency config (theme, current entity). React 19 accepts `<Ctx value>`; earlier majors need `<Ctx.Provider>`.

## Refs and closures (ch 9–11)

A ref is a mutable `{ current }` that persists across renders; writing it is synchronous and does not re-render, so it never holds what the UI shows. Pass a `ref` to a function component through `forwardRef` before React 19 and as a plain prop from 19. Expose `useImperativeHandle` methods rather than leaking the node.

**stale-closure.** A function created during render freezes the props and state it read. A missing hook dependency, or a callback stored in a ref once and never refreshed, keeps reading old values. Escape: refresh the latest function into a ref every render and call it from a stable callback. The same move keeps a `React.memo` child's prop stable while running fresh logic.

```jsx
const latest = useRef();
useEffect(() => {
  latest.current = () => save(value);
});
const onClick = useCallback(() => latest.current(), []);
```

**debounce-recreated.** A debounce, throttle, or timer id created in render or in an unmemoized handler resets every render and never fires as intended. Create it once and read fresh values through the ref above: `useMemo(() => debounce(() => latest.current(), 500), [])`. A bare `useMemo(() => debounce(fn), [])` freezes `fn`'s state.

## Layout and overlays (ch 12–13)

**flicker-useEffect.** Measure-then-mutate in `useEffect` lets the browser paint the before-frame. `useLayoutEffect` runs before paint. It does not run during SSR; opt that feature out of SSR rather than expect it to fire.

**trapped-overlay.** `overflow: hidden` clips `position: absolute`; `position: fixed` escapes it but nothing escapes a stacking context (`z-index` with position, `transform`, `opacity`, filters). Render modals, tooltips, and dropdowns through a portal. React events still bubble along the React tree; layout and native form submit follow the DOM. MUI, Radix, and Headless UI overlays already portal; flag hand-rolled ones that do not.

## Async (ch 14–16)

Prefer the repo's server-state layer (TanStack Query, SWR, Apollo, RTK Query) to hand-rolled fetch in effects; it handles caching, dedup, and races. On a stack that already uses `use()` or official Suspense data APIs, follow those over the book's 2023 workarounds.

**waterfall.** Independent requests started in sequence or behind a condition: `await a; await b`, or an effect that waits for A before starting B. Start them together (`Promise.all`, eager promises, a data-provider Context) within browser connection limits; prefetch critical initial data before React mounts. Classify each fetch as initial or on-demand; the loading experience follows from what the user needs first.

**fetch-race.** `setState` after `await` in an effect keyed on a changing value lets an older response overwrite a newer one. `async`/`await` does not help. Fixes, strongest last: `key` remount, compare the resolved id with the current one, a cleanup flag, `AbortController`.

**missing-error-boundary.** An uncaught render error unmounts the whole app, so place boundaries at routes and major panels. Boundaries miss callbacks, timers, and promises; `try/catch` misses render, effects, and children. Bridge them by re-throwing async errors into render, or use `react-error-boundary`:

```jsx
const useAsyncError = () => {
  const [, setError] = useState();
  return useCallback((e) => setError(() => { throw e; }), []);
};
```

### Mutation completion after editor cancellation or replacement

Server outcome and editor ownership are separate facts: closing or replacing an editor does not cancel the write. Derive the cases from the flow: success, definite rejection, uncertain result, permission denial; current, canceled, or replaced editor; same or changed actor, organization, and record. Check cancellation both before the response and after an uncertain result.

A late response never overwrites another draft or restores data the user can no longer see. A committed or uncertain result in the current scope may still need a data refresh after its editor closes. Handle permission loss in the current authorized scope; an old actor's denial must not clear a new actor's draft. Retry an uncertain write with its original request identity and body.

Restore focus on open, save, cancel, replacement, and permission loss to a valid trigger or permitted fallback, without stealing it from another active interaction. Test the observable behavior, not every combination.
