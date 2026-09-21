---
name: advanced-react
description: "Plan, implement, or review React component structure, state placement, re-renders, and async behavior using composition first. Use for component design or behavior problems; use react for compiler setup and version-specific APIs."
---

# Advanced React

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Apply _Advanced React_ (Nadia Makarevich, 2023) to a React change. The result is a named composition shape, code that matches it, or a review that cites book rules — not a generic React style pass and not a React 19 Compiler setup.

**Next consumer:** the implementer of the plan, the reviewer of the diff, or the user reading findings.

**Done when** the acceptance contract for the active mode is met and every claim that depends on a chapter was checked against that chapter's reference, not restated from memory.

Non-obvious intent: the book inverts the usual "wrap it in `memo`" reflex. State the **composition-first** choice out loud as you work — _this is composition-first: the hot state moves down before any memo is added_.

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

## Select the mode

| Request | Read only the selected method |
| --- | --- |
| Design the component shape | [references/plan-mode.md](references/plan-mode.md) |
| Write or change components | [references/implement-mode.md](references/implement-mode.md); use plan mode only for an unresolved shape |
| Review a plan or diff | [references/review-mode.md](references/review-mode.md) |

A design-gate or implement-and-review frontend invocation uses read-only review mode. Weight the re-render lens higher for a styled-component-heavy UI library. A standalone implementation request permits the scoped component edits.

## Gate output

When a caller asks for a proceed-or-revise verdict (a design gate or equivalent), return exactly: `verdict` (`proceed`|`revise`), `blocking_findings`, `advisory_findings`, `required_changes`. Block on a load-bearing composition or correctness miss (hot state in a layout, defeated memo treated as real, fetch race, missing boundary on a render path). Do not block on an unmeasured "expensive" calculation.

## Shared constraints

1. Do not optimize a component that renders cheaply and rarely.
2. Do not treat a custom hook as having moved state. Name **hook-hides-state** when the caller is still a heavy owner.
3. `cloneElement` to inject defaults onto an element-prop is fragile — only for the simplest defaults.
4. `forwardRef` is required before React 19 and unnecessary from React 19. Check the detected major before flagging either shape.
5. Context can _prevent_ re-renders (data skips the middle tree) and _force_ them (every consumer updates when `value` changes). Both are in chapter 8.
6. The book does not replace `react`. Compiler bailouts, Actions, `use()`, and the Rules of React stay there.

## Focused references

Load these only for the concern selected by the method:

- [references/composition.md](references/composition.md): composition ladder.
- [references/memo-recon.md](references/memo-recon.md): keys, inner components, HOCs, and justified memoization.
- [references/context-async.md](references/context-async.md): context, refs, overlays, async work, and errors.
- [references/lenses.md](references/lenses.md): detailed review checks for affected chapters.
- [references/cheatsheet.md](references/cheatsheet.md): decision tables and code examples when needed.
