---
name: react-performance
description: Advise on and review React code through the lenses of "Advanced React" (Makarevich) — unnecessary re-renders, composition-before-memoization, the memo/useMemo/useCallback traps, Context performance, refs & stale closures, debounce/throttle, useLayoutEffect flicker, portals & stacking context, data-fetching waterfalls & race conditions, and error boundaries. Use when writing or reviewing a React component/hook/context/provider, when chasing "why does this re-render" or "should I memoize this", or when dealing with stale state in a callback, UI flicker, modal clipping, fetch race conditions, or error handling. Frontend is React 17 + MUI + Redux Toolkit. Distinct from model-lens/architect-lens (architecture) and design-patterns (GoF).
---

# React Performance & Patterns Lens

Advise and review React code using the rules from *Advanced React* by Nadia Makarevich.
It asks one set of questions: **will this re-render more than it needs to, is memoization
actually doing anything, is this closure stale, and is the async path safe?** Not a bug
hunt for logic errors — use `code-review` for that.

Two modes, pick by context:

- **Advisor** (while writing new React code): steer the decision *before* the code is
  written — prefer composition over `memo`, place state correctly, structure the fetch.
- **Reviewer** (on existing/changed code): audit against the checks below, report findings
  grouped by lens. Cite `file:line`, name the rule, propose the concrete fix. Skip lenses
  that don't apply rather than padding. If a component is clean, say so plainly.

## Repo context (read before applying)

- Frontend is **React 17** (see `frontend/CLAUDE.md` at the app repo root): no
  automatic batching outside React event handlers, `forwardRef` is still required to pass
  a `ref` prop, and the React 19 "ref as a regular prop" change does **not** apply here.
  The book (2023) matches React 17/18 closely — prefer its advice over half-remembered
  React 19 behavior.
- **MUI** component trees are deep and re-render-sensitive; unnecessary parent re-renders
  cascade through styled components.
- **Redux Toolkit** is already the external store with memoized selectors. For
  cross-tree shared state, reach for RTK selectors over a hand-rolled Context; use Context
  for low-frequency, localized config (theme, current entity), not hot state.

## The golden rule (applies to every lens below)

> Composition first, memoization last. `React.memo` is the **last resort** after
> composition techniques have failed — because memoizing *all* props correctly is harder
> than it looks, and one missed non-primitive prop silently defeats it.

---

## Lens 1 — Unnecessary re-renders (ch 1–4)

A state update re-renders the owning component **and all of its children**, regardless of
props. Props only matter once `React.memo` is involved. So the cheapest fix is structural,
not memoization.

Check, in order:

1. **Move state down.** Is fast-changing state (an input value, a hover flag, an
   open/closed toggle) held high in the tree, forcing a big subtree to re-render? Extract
   the state + the small piece that uses it into a child component. This is the single
   highest-value fix in the book.
2. **Children / elements as props.** When a component owns state but renders a heavy
   subtree that doesn't depend on that state, pass the subtree as `children` (or as an
   element prop). Elements passed in as props **don't re-render** when the parent's own
   state changes — they were created by the parent's parent. Exact pattern: cheatsheet
   ch 2.
3. **Render props** only when the children genuinely need the parent's state/DOM data
   (e.g. logic attached to a DOM element). Hooks replaced ~99% of the old "share stateful
   logic" use case — don't reach for render props just to share logic.

Red flags: a top-level page component holding an input's value; a `useState` in a provider
or layout that wraps half the app; "I'll wrap it in `memo`" as the *first* idea.

## Lens 2 — Memoization that does nothing (ch 5)

React compares objects/arrays/functions **by reference**, in `memo` props and in hook deps.
`useMemo` memoizes a *result*; `useCallback` memoizes the *function itself*.

Flag memoization that buys nothing — `useMemo`/`useCallback` is only justified when **one**
of these holds:

- the value is a dependency of another hook (`useEffect`/`useMemo`/`useCallback`), **or**
- the value is a prop passed to a component wrapped in `React.memo`, **or**
- it's passed down to a component that then hits one of the above.

And flag `React.memo` that is **silently defeated**:

- a non-primitive prop (object/array/function/**`children`**) passed to the memo'd
  component is recreated each render → memo is useless. *All* props must be primitive or
  stable. `children` is a prop too — memoizing it is easy to forget.
- the value came from another non-memoized prop or hook result → memoization chain is
  broken.

Rule of thumb: if you're memoizing a prop, prove the consumer is `React.memo`'d or uses it
as a dep. Otherwise delete the memo.

Memo'd list items, or state mysteriously resetting/persisting across renders → keys &
reconciliation, cheatsheet ch 6.

## Lens 3 — Context performance (ch 8)

Every consumer of a Context re-renders when the provider `value` changes — and **standard
memoization can't stop it**.

- Flag a provider whose `value={{...}}` / `value={[a, b]}` is an **unmemoized inline
  object/array** — every parent render forces every consumer to re-render. Wrap it in
  `useMemo` (and callbacks in `useCallback`).
- For multiple unrelated values, **split into multiple providers** so a change to one
  doesn't re-render consumers of the other. `useState` → `useReducer` helps keep the data
  and the API in separate stable contexts.
- No real selectors exist for Context; you can fake them with `React.memo` + HOCs (see
  cheatsheet ch 7), but if you find yourself doing that, **use RTK** (this repo already
  has it) instead.

## Lens 4 — Refs, closures & stale state (ch 9–11)

- A **ref** is a mutable box preserved across renders; mutating `ref.current` does **not**
  re-render and is synchronous. Use it for values that must persist but shouldn't trigger
  renders (timers, latest-callback, previous value, DOM nodes). Don't use it for anything
  that should appear in the UI.
- **`forwardRef`** is required (React 17) to pass a `ref` prop to a function component;
  expose a controlled imperative API with `useImperativeHandle` rather than leaking the
  DOM node.
- **Stale closure** = the #1 bug here. A function created in render "freezes" the state and
  props it closed over. If it's memoized (`useCallback`/`useMemo`) with a missing dep, or
  stored in a ref once, it keeps reading old values.
  - Detect: a `useCallback`/`useEffect`/`useMemo` reading state/props but missing them from
    deps; a callback stored in `ref.current` that's never refreshed.
  - Escape: refresh the closed function in `ref.current` inside a `useEffect` on every
    render, then call `ref.current()` — it always sees the latest data. This is also how
    you keep a `React.memo` child stable while still calling fresh logic.

## Lens 5 — Debounce / throttle (ch 11)

`debounce`/`throttle` only work if the **same instance** lives across the component's life.

- Flag `debounce(...)` / `throttle(...)` / `setTimeout` id created **inline in render** or
  in a non-memoized handler — the timer is recreated every render and never fires
  correctly.
- Fix: memoize the debounced function once (`useMemo`/ref), and access the latest state via
  the ref-refresh trap from Lens 4 (a naive memo freezes state at creation time).

## Lens 6 — Flickering UI / useLayoutEffect (ch 12)

Measure-then-mutate DOM work (size/position) in `useEffect` lets the browser paint the
"before" frame first → visible glitch. Use **`useLayoutEffect`** — it runs synchronously
before paint. SSR caveat and exact pattern: cheatsheet ch 12.

## Lens 7 — Portals & stacking context (ch 13)

Modals/tooltips/dropdowns clipped by an ancestor's `overflow` or trapped in a Stacking
Context (nothing escapes one, not even `position: fixed`) → render via a **Portal**.
MUI's `Modal`/`Popper` already portal — flag hand-rolled overlays that don't. CSS rules
and event-bubbling behavior: cheatsheet ch 13.

## Lens 8 — Data fetching: waterfalls & race conditions (ch 14–15)

- **Waterfall:** sequential/conditional `await`s that could be parallel. Flag dependent
  `useEffect` fetches and `await a; await b` where `a` and `b` are independent → use
  `Promise.all`, parallel promises, or a data-provider Context. Mind browser parallel
  request limits; critical resources can be prefetched before React mounts.
- **Race condition:** `setState` after an `await`/`.then` in an effect keyed on a changing
  value (e.g. `url`, an id). A slow earlier request can resolve after a newer one and
  overwrite fresh data. Fixes (prefer the last two): compare the resolved id before
  `setState`; cleanup-flag in `useEffect`; **`AbortController`**. Exact patterns:
  cheatsheet ch 15. (RTK Query handles this for you — prefer it over hand-rolled `fetch`
  in effects when the data is server state.)

## Lens 9 — Error handling (ch 16)

After React 16, an **uncaught render error unmounts the whole app** — a few
`ErrorBoundary`s in strategic places are non-negotiable. Boundaries miss
callbacks/`setTimeout`/promises; `try/catch` misses render/`useEffect`/nested components.
Bridge by re-throwing async errors into the render lifecycle, or use the
`react-error-boundary` library. Exact hook and coverage matrix: cheatsheet ch 16.

---

## How to apply

1. Identify which lenses the change touches (a fetch hook → 8; a provider → 3; a memo'd
   component → 1, 2, 4).
2. In **advisor** mode, recommend the structural option first (move state down /
   composition) and only escalate to memoization when the checks in Lens 2 are met.
3. In **reviewer** mode, report per lens: `file:line` → which rule → concrete fix.
4. Don't invent re-renders that don't matter — a component that renders cheaply and rarely
   needs no optimization. Optimize where state is hot and the subtree is heavy.

See `references/cheatsheet.md` for the per-chapter decision tables and code snippets.
