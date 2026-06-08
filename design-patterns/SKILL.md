---
name: design-patterns
description: Recognize when a Gang-of-Four design pattern genuinely fits the code at hand, name it in shared vocabulary, and translate it into a concrete design — while guarding against overengineering. Distilled from Head First Design Patterns (Freeman & Robson). Use when choosing how to structure new code, when a design feels rigid or repetitive (sprawling if/switch, duplicated behavior, hard-to-extend classes, tangled notifications), when refactoring for extensibility, or when someone asks "which pattern fits here", "is there a pattern for this", "how should I structure this so it's easy to change". Triggers on "what pattern", "design pattern", "strategy/observer/decorator/factory/adapter/state/etc. pattern", "make this extensible", "this is getting hard to change". Do NOT use for pure bug-fixing, formatting, or when a plain function already does the job.
---

# Design Patterns

A pattern-recognition lens distilled from *Head First Design Patterns* (Freeman & Robson, 2nd ed). The goal is not to apply patterns — it's to **see where a pattern naturally fits and where it doesn't**, then reach for the simplest thing that solves the real problem.

## The guardrail comes first

The book's most important lesson lands in its final chapter, not its first: **most code should not use a named pattern.**

- **Keep it simple (KISS).** When you design, solve the problem the simplest way possible. The goal is simplicity, not "how can I apply a pattern here?" A plain function, a `map`, or an early return is often the right answer, and other developers will admire the simplicity.
- **Patterns are not free.** Each one adds classes, indirection, and layers — more to read, more to trace, sometimes less efficient. That cost is worth paying only when it buys flexibility the design *actually needs*.
- **Introduce a pattern when the need has emerged, not in anticipation of it.** If a simpler solution might work, give it the chance. You reach for a pattern when you're sure it addresses a real problem you're hitting now — repeated change in one spot, an extension point you keep fighting — not a hypothetical future one.
- **Falling back on a design principle (below) often dissolves the problem** without any named pattern at all. If that happens, don't fight it.

So the honest answer to "which pattern should I use here?" is sometimes **"none — here's the simpler structure."** Say that when it's true. A pattern recommendation should always come with the cost it imposes and why that cost is worth paying *here*.

## How to use this lens

When code structure is the question, work in this order:

1. **Name the pressure.** What is actually hard? Usually one of: behavior that varies and keeps changing, duplication across similar classes, something rigid that resists extension, tight coupling, or object creation that's scattered and conditional.
2. **Check the design principles.** These are the foundation patterns are built on. Often applying a principle directly is the whole fix — no named pattern required.
3. **Only then, match to a pattern** using the symptom table. Confirm the pattern earns its complexity. If two patterns fit, prefer the one with less machinery.
4. **Use the shared vocabulary.** Once a pattern genuinely fits, *name it* — "this is a Strategy," "that's a Decorator." A shared name communicates an entire design (intent, structure, trade-offs) in one word to the next developer. That communication value is half of why patterns are worth knowing.

## The design principles (check these first)

These are more broadly useful than any individual pattern. Most good refactors are just one of these applied directly.

1. **Encapsulate what varies.** Identify the parts that change and separate them from the parts that stay the same, so change is localized.
2. **Program to an interface, not an implementation.** Depend on a capability (a type/abstraction), not a concrete class, so you can swap implementations.
3. **Favor composition over inheritance.** "HAS-A is often better than IS-A." Composing behavior is more flexible than locking it into a class hierarchy.
4. **Strive for loosely coupled designs** between objects that interact — they should know as little about each other as possible.
5. **Open–Closed:** classes should be open for extension but closed for modification — add new behavior without editing tested code.
6. **Dependency Inversion:** depend on abstractions, not concrete classes — high-level code shouldn't hinge on low-level details.
7. **Principle of Least Knowledge (Law of Demeter):** talk only to your immediate friends — avoid long chains of `a.getB().getC().doThing()`.
8. **The Hollywood Principle:** "Don't call us, we'll call you" — let high-level components control when low-level ones are invoked (inversion of control), rather than the reverse.
9. **Single Responsibility:** a class should have only one reason to change. One responsibility per class.

## Symptom → pattern map

Match the *pressure you named* to a candidate. This is a starting point, not a verdict — read the pattern's entry in `references/patterns.md` (which includes "when it's overkill") before committing.

| What's hurting | Candidate pattern(s) |
|---|---|
| A sprawling `if/else`/`switch` selecting between interchangeable behaviors | **Strategy** (behavior chosen by caller/config) or **State** (behavior driven by the object's own state, with transitions) |
| Behavior must change at runtime, or many combinations of optional behaviors | **Strategy**; for stackable add-ons, **Decorator** |
| One object's change must notify many others; you're hand-wiring callbacks | **Observer** |
| You want to wrap/layer responsibilities onto objects without subclass explosion | **Decorator** |
| `new ConcreteThing()` scattered across code; creation logic is conditional and duplicated | **Factory Method** (one product), **Abstract Factory** (families of related products), or just a creation function |
| Exactly one shared instance / single point of coordination | **Singleton** (but a module-level value or DI is usually simpler & more testable) |
| You want to parameterize, queue, log, or undo *actions* | **Command** |
| Two incompatible interfaces need to work together | **Adapter** |
| A complex subsystem needs one simple entry point | **Facade** |
| Several methods share the same skeleton but differ in a few steps | **Template Method** (inheritance) or pass the varying steps in (Strategy-style) |
| Traverse a collection without exposing its internals | **Iterator** (most languages give you this for free) |
| Part-whole tree where clients should treat leaves and branches uniformly | **Composite** |
| Control access to an object — lazy-load, remote, permission-check, cache | **Proxy** |
| Abstraction and implementation each vary independently and multiply | **Bridge** |
| Building a complex object step by step / many optional fields | **Builder** |
| A request should pass along a chain until something handles it | **Chain of Responsibility** |
| Add new operations to a fixed object structure without editing those classes | **Visitor** |
| Capture and restore an object's state (undo/snapshots) | **Memento** |
| Many objects communicating many-to-many; coordination is tangled | **Mediator** |
| Huge numbers of similar fine-grained objects burning memory | **Flyweight** |
| Create new objects by copying a configured instance | **Prototype** |
| Interpret sentences in a small language/grammar | **Interpreter** |

For the full catalog — each pattern's one-line definition, the smells that suggest it, a structure sketch, related patterns, and **when it's overkill** — read `references/patterns.md`. Read only the entries relevant to the situation; it's organized so you can jump to one pattern.

## Output shape

When advising on structure, prefer this form so the recommendation is honest and actionable:

- **The pressure:** what's actually hard to change here, in one sentence.
- **Simplest option:** the plainest thing that could work (often no pattern). Say whether it's enough.
- **Pattern (if warranted):** name it, in shared vocabulary, and sketch how it maps onto this code.
- **The cost:** what indirection/classes it adds, and why that's worth paying *here*. If you can't name a cost, look harder.

A recommendation of "none needed, here's the three-line version" is a success, not a cop-out.
