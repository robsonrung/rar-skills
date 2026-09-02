# Memoization, reconciliation, HOCs (ch 5–7)

Read this when the change adds or debates `memo` / `useMemo` / `useCallback`, when a list or conditional remounts, when `key` is in play, or when a component is defined inside another component.

## Contents

1. [Memoization (ch 5)](#memoization-ch-5)
2. [Reconciliation and keys (ch 6)](#reconciliation-and-keys-ch-6)
3. [Higher-order components (ch 7)](#higher-order-components-ch-7)

## Memoization (ch 5)

React compares objects, arrays, and functions **by reference** in `React.memo` props and in hook deps. The inline function passed to `useMemo` / `useCallback` is recreated every render — that is expected. `useCallback(fn)` ≈ `useMemo(() => fn)`. `useMemo` memoizes a _result_; `useCallback` memoizes the _function_.

**Dead memo (antipattern).** Memoizing a prop does nothing unless **one** of these holds:

- the consumer is wrapped in `React.memo`, or
- the consumer uses the value as a dependency of `useEffect` / `useMemo` / `useCallback`, or
- the value is passed further down into one of those two situations.

A `useCallback` around `onClick` handed to a plain `<button>` is dead weight. Stacked `useMemo`/`useCallback` that only exist to feed each other bury the logic.

**Defeated memo.** `React.memo` skips a _parent-triggered_ re-render only when **every** prop is unchanged by reference. Own state and context still re-render it. A single non-primitive prop recreated each render — object, array, function, or **`children`** — silently defeats it. A value sourced from another non-memoized prop or hook result breaks the chain.

**Order:** composition (ch 1–4) first. `React.memo` is last resort.

**Expensive calculations.** "Expensive" is not a feeling. Measure on a representative device, in context, compared with the rest of the frame. Sorting 300 items is often <2ms on desktop and still not worth `useMemo` if it runs once on a settings click. A 30ms regex on every mouse move is. Do not add `useMemo` for an unmeasured calculation.

When the React Compiler is present, do not add the memos this chapter would have required for render-only values. Keep a manual memo only when the value is a hook dependency, crosses to a non-compiled consumer, or has a custom `areEqual`. That split is owned by `react`.

Rule names: **dead-memo**, **defeated-memo**.

## Reconciliation and keys (ch 6)

React diffs by **position in the returned children array** + **type**:

- same type + same position → update in place (state kept)
- type change at that position → unmount old, mount new (state lost)

A conditional `cond ? <A /> : <B />` occupies **one** slot, even when a branch is `null`. Two `<Input>`s swapped by a boolean share state unless you force them apart.

**Inner component.** A component declared inside another component is a new function — a new `type` — every render. React unmounts and remounts it: flicker, lost state, lost focus, at least 2× the cost of a re-render. Declare components and hooks at module scope.

```jsx
// ❌ new Input type every render → remount
const Component = () => {
  const Input = () => <input />;
  return <Input />;
};
```

**Dynamic arrays need `key`** — stable identity across reorder/add/remove. Critical when items are `React.memo`'d. Index keys fail on reorder.

**`key` is not array-only:**

- same type + position + **changing** `key` → force remount ("state reset", e.g. on route or entity id change)
- `key` on two same-type conditionals → treat them as different (company vs person tax-id inputs)
- `key` can also force React to reuse an element that moved

Non-dynamic arrays do not need keys. Mixing a dynamic array with sibling elements is fine; the array items still need keys.

Rule names: **inner-component**, **missing-key**, **state-reset**.

## Higher-order components (ch 7)

```jsx
const withSomeLogic = (Component) => {
  return (props) => {
    // hooks are legal here — this is a component
    return <Component {...props} some="data" />;
  };
};
```

An HOC is a function that takes a component and returns a component that renders it, optionally injecting props or wrapping lifecycle/DOM events.

Modern use: cross-cutting concerns (logging, feature flags, fake context selectors). For shared stateful logic, prefer a hook. Do not introduce an HOC to share state that a hook can hold.

Rule name: **hoc-for-cross-cutting**.
