# Test Lens — Decision Trees & Worked Examples

Detailed reference for `test-lens`. All examples are TypeScript + Jest. Source: Khorikov,
*Unit Testing: Principles, Practices, and Patterns*.

---

## 1. Observable behavior vs. implementation details — worked

**Brittle (couples to the algorithm / internal structure):**

```ts
// BAD — asserts WHICH sub-renderers exist and in what order
test('renderer uses correct sub-renderers', () => {
  const sut = new MessageRenderer();
  expect(sut.subRenderers).toHaveLength(3);
  expect(sut.subRenderers[0]).toBeInstanceOf(HeaderRenderer);
  expect(sut.subRenderers[1]).toBeInstanceOf(BodyRenderer);
  expect(sut.subRenderers[2]).toBeInstanceOf(FooterRenderer);
});
```

Swapping `BodyRenderer` for an equivalent `BoldRenderer`, or inlining the rendering, keeps
the HTML identical but turns this test red. Zero resistance to refactoring.

**Resistant (asserts the observable outcome):**

```ts
// GOOD — asserts WHAT the renderer produces
test('renders message as HTML', () => {
  const sut = new MessageRenderer();
  const html = sut.render({ header: 'h', body: 'b', footer: 'f' });
  expect(html).toBe('<h1>h</h1><b>b</b><i>f</i>');
});
```

Same brittleness trap with generated SQL: asserting the exact `SELECT` string fails on any
equivalent rewrite (`*` vs explicit columns, `[User]` vs `User`). Assert the **rows returned**,
not the SQL text.

---

## 2. Mock vs. stub vs. real — the flowchart

```
Is the test double standing in for a dependency the SUT TALKS TO?
│
├─ It provides INPUT the SUT reads (incoming interaction)?
│    → STUB it. Set up a canned return value.
│    → NEVER assert it was called. (Asserting a stub = overspecification = fragile.)
│
└─ The SUT CAUSES A SIDE EFFECT on it (outcoming interaction)?
     │
     ├─ Is that side effect OBSERVABLE OUTSIDE your system?
     │   (SMTP email, message-bus event, third-party API write)
     │      → It's an UNMANAGED dependency. The interaction IS the contract.
     │      → MOCK it and assert the call. This is legitimate communication-based testing.
     │
     └─ Is it only reachable THROUGH your app? (your own database)
            → It's a MANAGED dependency. The interaction is an implementation detail.
            → Do NOT mock in integration tests — use the REAL thing (e.g. a test DB).
            → In unit tests, prefer redesigning so this I/O isn't in the unit at all.
```

Two more rules:
- **Mock only at the system edge.** If the interface you're mocking wraps another interface
  that does the real I/O, mock the *outermost* one (closest to the edge) — it exercises more
  code and better preserves the contract.
- **Mock only types you own.** Don't mock a third-party SDK directly. Wrap it in your own
  thin adapter interface and mock the adapter. (Lets you encode only the behavior you rely on
  and survive SDK upgrades.)

**A double can be both:** set up a return on one method (stub role) AND assert a call to a
*different* method (mock role). That doesn't violate "never assert a stub" — different methods.

---

## 3. The three styles — transition example

Goal: move tests toward **output-based** by extracting a functional core.

**Start — communication/state-based, hard to test (logic tangled with file I/O):**

```ts
class AuditManager {
  constructor(private maxPerFile: number, private dir: string) {}

  addRecord(name: string, time: Date): void {
    const files = fs.readdirSync(this.dir);              // I/O mixed in
    // ...decide which file, whether to create a new one...
    fs.appendFileSync(path, `${name};${time.toISOString()}`); // side effect
  }
}
```

Testing this needs file-system mocks or a real temp dir — slow, brittle, communication-based.

**Refactor — functional core (pure decision) + mutable shell (does I/O):**

```ts
// FUNCTIONAL CORE — pure: files in, instructions out. Trivial to output-test.
type FileUpdate =
  | { kind: 'create'; name: string; content: string }
  | { kind: 'append'; name: string; content: string };

function addRecord(
  files: { name: string; lines: string[] }[],
  maxPerFile: number,
  visitor: string,
  time: Date,
): FileUpdate { /* pure decision, no I/O */ }

// MUTABLE SHELL — no logic, just glue. Covered lightly by integration tests.
class AuditManager {
  addRecord(name: string, time: Date): void {
    const files = readAllFiles(this.dir);
    const update = addRecord(files, this.maxPerFile, name, time); // delegate decision
    applyUpdate(this.dir, update);                                 // do the action
  }
}
```

Now the valuable logic is **output-tested** with plain values — no mocks, fast, refactor-proof:

```ts
test('appends to the latest file when it has room', () => {
  const update = addRecord(
    [{ name: 'audit_1.txt', lines: ['Peter;...'] }], 3, 'Jane', new Date('2026-06-07'),
  );
  expect(update).toEqual({ kind: 'append', name: 'audit_1.txt', content: 'Jane;2026-06-07...' });
});
```

This is the same idea as `refactor-to-testability` (extract logic from hard deps) but aimed
specifically at producing **output-based** tests.

---

## 4. The code quadrant → Humble Object refactor

```
            Few collaborators            Many collaborators
          ┌────────────────────────┬────────────────────────┐
   high   │ DOMAIN MODEL /         │ OVERCOMPLICATED        │
 complex/ │ ALGORITHMS             │ (fat controller doing  │
 domain   │ → unit-test hard       │  logic + I/O)          │
 signif.  │   (best ROI)           │ → SPLIT (see below)    │
          ├────────────────────────┼────────────────────────┤
   low    │ TRIVIAL                │ CONTROLLERS            │
          │ → don't test           │ → a few integration    │
          │                        │   tests                │
          └────────────────────────┴────────────────────────┘
```

To drain the overcomplicated quadrant, apply **Humble Object**: pull the logic into a
pure algorithm/domain object (lands in top-left, unit-tested), leaving a humble wrapper that
only orchestrates dependencies (lands in bottom-right, integration-tested). Aim for *nothing*
in the top-right. "The more important the code, the fewer collaborators it should have."

Do **not** chase 100% coverage. Coverage is a poor target — it's possible to have high
coverage and worthless tests (and vice versa). Target value per test.

---

## 5. Anti-pattern catalog (before → after)

| Anti-pattern | Smell | Fix |
|---|---|---|
| **Testing private methods** | test reaches into a private helper that holds real logic | the helper is a missing abstraction — extract it into its own class and test *that* publicly |
| **Exposing private state** | added a getter/`public` only so a test can assert it | test observable behavior; if you can't observe it, you may not need to test it |
| **Leaking domain knowledge** | test recomputes the expected value with the same formula the SUT uses | hardcode expected results as literals derived independently |
| **Code pollution** | `if (isTestEnv)` / test-only flags in production code | inject the varying behavior (e.g. a strategy or a dependency) instead |
| **Mocking concrete classes** | mock a real class but keep half its behavior | SRP violation — split into a logic class + an I/O class; mock only the I/O one |
| **Time as ambient context** | code calls `Date.now()` / `new Date()` directly, tests are flaky | inject a `Clock`/`() => Date` dependency; pass a fixed time in tests |
| **Asserting interactions with stubs** | `expect(stub.getX).toHaveBeenCalled()` | delete it — only assert outcomes / mocks of unmanaged deps |
| **Coverage as a goal** | "we need 100%" | set a value bar per test; delete low-value tests even if coverage drops |

### Time as explicit dependency — example

```ts
// BAD — untestable, flaky
class InactivityChecker {
  isInactive(user: User): boolean {
    return Date.now() - user.lastSeen > THRESHOLD; // hidden time dependency
  }
}

// GOOD — inject time
class InactivityChecker {
  constructor(private now: () => number) {}
  isInactive(user: User): boolean {
    return this.now() - user.lastSeen > THRESHOLD;
  }
}
// test: new InactivityChecker(() => FIXED_NOW)  → deterministic, output-based
```

---

## 6. Integration test rules (chapters 8–10)

- An integration test covers a controller plus at least one **real out-of-process** dependency.
- Use **real managed** deps (your DB), **mock unmanaged** deps (SMTP, bus). Test the worst
  case path (the one touching the most deps) and one shortest happy path.
- Make domain-model boundaries explicit; reduce layers; no circular dependencies.
- Don't over-test logging: only test logging that is part of observable behavior (e.g. an audit
  log other systems consume — that's effectively an unmanaged dependency); treat diagnostic
  logging as an implementation detail.
- The Test Pyramid still holds: many fast unit tests on the domain model, fewer integration
  tests on controllers, very few end-to-end tests on the critical happy paths.

---

## Relationship to sibling skills

- `tdd` — the red-green-refactor *cadence*. `test-lens` judges whether the resulting test is
  *valuable*; use them together.
- `refactor-to-testability` — making scary legacy code safe to change. Overlaps on Humble
  Object / extracting logic; `test-lens` focuses on what makes the *new* test valuable.
- `clean-code` — production-code readability, not test value.
- `code-review` — finds bugs; `test-lens` finds *low-value or fragile tests*.
- `model-lens` / `architect-lens` — the functional-core/mutable-shell split here is the same
  separation-of-concerns those lenses reward.
