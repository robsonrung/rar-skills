# Composition ladder (ch 1–4)

Read this in **plan** before choosing a structure, and in **implement** / **review** when the change places state, children, or a configurable slot.

## Contents

1. [Re-renders myth (ch 1)](#re-renders-myth-ch-1)
2. [Move state down (ch 1)](#move-state-down-ch-1)
3. [Hook-hides-state (ch 1)](#hook-hides-state-ch-1)
4. [Children / elements as props (ch 2–3)](#children--elements-as-props-ch-2-3)
5. [Render props (ch 4)](#render-props-ch-4)

## Re-renders myth (ch 1)

- A re-render is React calling the component function again. Without it there is no interactivity.
- **State update is the initial source** of every re-render (then parent re-render, then context change).
- A re-render flows **down**, never up. The owner and every nested component re-render, **regardless of props**.
- Without memoization, **props do not matter**. Children with no props still re-render.
- A local variable change (`let isOpen = true`) never updates the screen — React is not watching it.

Rule name: **re-renders-myth**. Flag any plan or review that treats "props changed" as the reason a child re-rendered, unless that child is wrapped in `React.memo`.

## Move state down (ch 1)

Highest-leverage fix in the book. Fast-changing state (input value, hover, open/closed) held in a page, layout, or other heavy owner forces the whole subtree to re-render.

```jsx
// ❌ typing re-renders VerySlowComponent
const App = () => {
  const [value, setValue] = useState('');
  return (
    <>
      <input value={value} onChange={(e) => setValue(e.target.value)} />
      <VerySlowComponent />
    </>
  );
};

// ✅ isolate state + its only consumer
const SearchInput = () => {
  const [value, setValue] = useState('');
  return <input value={value} onChange={(e) => setValue(e.target.value)} />;
};
const App = () => (
  <>
    <SearchInput />
    <VerySlowComponent />
  </>
);
```

Rule name: **move-state-down**. Stop here when the state is only consumed next to its control.

## Hook-hides-state (ch 1)

`useState` / `useReducer` / an effect that `setState`s inside a custom hook still re-renders the **component that called the hook**, even if the hook returns nothing and the caller never reads the value. Extracting `useModalDialog()` into `App` does not isolate the dialog; it only hides the state.

A resize listener or other high-frequency `setState` buried in a hook called from a layout is the same bug as putting that state in the layout.

Rule name: **hook-hides-state**. Fix: call the hook from the small leaf that actually needs the state (`<DialogTrigger />`), not from the page.

## Children / elements as props (ch 2–3)

- **Component** = `(props) => Elements`. **Element** = the object `<B />`; `type` is a string (DOM) or a component reference.
- A component re-renders when *its element object* changes (`Object.is`).
- An element passed as a prop (including `children`) was created by the **parent's parent**. When the receiving component updates its own state, that element does not re-render.

```jsx
// ScrollDetector state is hot; {children} does not re-render with it
const ScrollDetector = ({ children }) => {
  const [scroll, setScroll] = useState(0);
  return <div onScroll={(e) => setScroll(e.target.scrollTop)}>{children}</div>;
};
<ScrollDetector>
  <SlowComponent />
</ScrollDetector>;
```

`children` is `props.children`:

```jsx
<Parent><Child /></Parent>
// same as
<Parent children={<Child />} />
```

**Element-as-prop for configuration (ch 3).** Push configuration of a rendered child up to the consumer:

```jsx
const Button = ({ icon }) => <button>Submit {icon}</button>;
<Button icon={<Error color="red" size="large" />} />;
```

An element stored in a variable is only rendered if the component it is passed to actually renders:

```jsx
const footer = <Footer />; // not rendered yet
return isDialogOpen ? <ModalDialog footer={footer} /> : null;
```

`cloneElement` can inject default props onto an element-prop. It is fragile — use only for the simplest defaults.

Rule names: **children-as-props**, **element-as-prop**. Stop here when the owner of hot state has a heavy slot that does not need that state.

## Render props (ch 4)

Convert an element-prop to a render prop only when the parent must control that element's props or feed it state / DOM data:

```jsx
const Button = ({ renderIcon }) => {
  const [state, setState] = useState();
  return <button>Submit {renderIcon({ size: 'large' }, state)}</button>;
};
<Button renderIcon={(props, state) => <Icon {...props} active={state} />} />;
```

`children` can be a function: `const Parent = ({ children }) => children(data)`.

Hooks replaced render-props-for-shared-logic in ~99% of cases. Keep a render prop when the logic is **attached to a DOM node** (size/position trackers). Do not introduce a render prop just to share a hook.

Rule name: **render-prop-for-dom-data**.
