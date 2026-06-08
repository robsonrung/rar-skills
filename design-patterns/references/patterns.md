# Pattern catalog

The full set from *Head First Design Patterns* (2nd ed) — the twelve core-chapter patterns plus the appendix "leftover" patterns. Examples are language-neutral (object/interface terms); translate to your language's idioms (a Strategy is often just a function; a Singleton is often just a module).

Each entry follows the same shape:
- **Intent** — the book's one-line definition.
- **Reach for it when** — the smell that signals it.
- **Structure** — the minimal cast of participants.
- **Overkill when** — the simpler thing to do instead. *Read this before recommending.*
- **Related** — patterns it's confused with or combines with.

## Contents

Core: [Strategy](#strategy) · [Observer](#observer) · [Decorator](#decorator) · [Factory Method](#factory-method) · [Abstract Factory](#abstract-factory) · [Singleton](#singleton) · [Command](#command) · [Adapter](#adapter) · [Facade](#facade) · [Template Method](#template-method) · [Iterator](#iterator) · [Composite](#composite) · [State](#state) · [Proxy](#proxy) · [Compound / MVC](#compound--mvc)

Leftover: [Bridge](#bridge) · [Builder](#builder) · [Chain of Responsibility](#chain-of-responsibility) · [Flyweight](#flyweight) · [Interpreter](#interpreter) · [Mediator](#mediator) · [Memento](#memento) · [Prototype](#prototype) · [Visitor](#visitor)

---

## Strategy

**Intent.** Defines a family of algorithms, encapsulates each one, and makes them interchangeable. Strategy lets the algorithm vary independently from the clients that use it.

**Reach for it when.** A class needs to choose among interchangeable behaviors, especially at runtime or by configuration; or a `switch` over a "type" keeps selecting which algorithm to run. The varying behavior is *injected*, not inherited.

**Structure.** A `Context` holds a reference to a `Strategy` interface; concrete strategies implement it; the context delegates to whichever it currently holds. The classic example: a `Duck` composed with a `FlyBehavior` and a `QuackBehavior` it can swap at runtime.

**Overkill when.** There's only one behavior, or two that will never grow — an `if` is clearer. In most languages a strategy is just a function/lambda passed in; you rarely need a class hierarchy. This is the default first pattern to consider and the cheapest to apply.

**Related.** *State* has the same structure but the object changes its own strategy as state transitions; Strategy is chosen from outside. *Template Method* solves a similar "vary a step" problem via inheritance instead of composition.

---

## Observer

**Intent.** Defines a one-to-many dependency between objects so that when one object changes state, all of its dependents are notified and updated automatically.

**Reach for it when.** One object's change must fan out to many interested others, and you don't want the source to know their concrete types. You're otherwise hand-maintaining lists of callbacks and manually poking each listener.

**Structure.** A `Subject` keeps a list of `Observer`s, with register/remove/notify. Observers implement an `update` method. The subject pushes (or observers pull) on change. Loose coupling is the whole point: the subject knows only that observers implement the interface.

**Overkill when.** There's a single, fixed listener — just call it. Built-in event emitters, signals, or reactive streams already *are* this pattern; use them rather than rebuilding it. Watch for memory leaks from observers that never unregister.

**Related.** The backbone of most UI/event systems and MVC (the view observes the model).

---

## Decorator

**Intent.** Attaches additional responsibilities to an object dynamically. Decorators provide a flexible alternative to subclassing for extending functionality.

**Reach for it when.** You need many optional, combinable add-ons and subclassing would explode into a class per combination (`CondimentBeveragePlusWhipPlusSoy…`). Wrapping lets you stack behaviors at runtime. Embodies Open–Closed: add behavior without touching the wrapped class.

**Structure.** Decorator implements the *same* interface as the component it wraps, holds a reference to an inner component, and adds behavior before/after delegating. The book's example: `Beverage` wrapped by `Mocha`, `Whip`, etc., each adding to `cost()`.

**Overkill when.** Only one or two fixed extensions exist — a parameter or subclass is plainer. Many small wrapper layers can make debugging and identity checks confusing.

**Related.** Same structure as *Proxy* but different intent (Proxy controls access; Decorator adds responsibility). *Composite* also wraps same-interface objects but for trees.

---

## Factory Method

**Intent.** Defines an interface for creating an object, but lets subclasses decide which class to instantiate. Factory Method lets a class defer instantiation to subclasses.

**Reach for it when.** A class needs to create objects but the concrete type should be decided by subclasses/variants — e.g. `PizzaStore` defines `orderPizza()` but `NYStore` and `ChicagoStore` decide which `Pizza` to make. Encapsulates the `new` so calling code depends on the abstraction.

**Structure.** A creator class declares an abstract `factoryMethod()` returning the product interface; subclasses override it to return concrete products.

**Overkill when.** Creation isn't varying by subtype — a plain factory *function* (a "simple factory") or even direct construction is enough. Don't introduce a class hierarchy just to wrap a `new`.

**Related.** *Abstract Factory* groups multiple factory methods for families of products. All factory patterns share the principle: encapsulate object creation.

---

## Abstract Factory

**Intent.** Provides an interface for creating families of related or dependent objects without specifying their concrete classes.

**Reach for it when.** You need to create a *family* of things that must be used together and stay consistent (e.g. all the ingredients for a regional pizza — dough, sauce, cheese — from one regional factory). Swapping the factory swaps the whole family.

**Structure.** An `AbstractFactory` interface with a creation method per product; concrete factories produce a matching set; clients use products only through their interfaces.

**Overkill when.** There's only one family, or the products aren't actually interdependent — separate factory functions are simpler. This is one of the heavier patterns; be sure the "family must be consistent" constraint is real.

**Related.** Often *implemented with* Factory Methods. Compare to *Builder* (which assembles one complex object step by step rather than producing a family).

---

## Singleton

**Intent.** Ensures a class has only one instance and provides a global point of access to it.

**Reach for it when.** Exactly one instance must coordinate something (a registry, a connection pool) and a single access point genuinely matters.

**Structure.** Private constructor + a static accessor that lazily creates and caches the one instance. Beware thread-safety in the lazy-init path.

**Overkill when.** This is the most-criticized pattern. In most modern languages a *module-level value* gives you one instance for free, without the global-state and testability problems. A global singleton is effectively hidden global state — it complicates testing (no easy substitution) and coupling. Prefer dependency injection: create one instance and pass it in. Reach for the classic Singleton rarely and deliberately.

**Related.** Often replaced by DI containers or module scoping.

---

## Command

**Intent.** Encapsulates a request as an object, thereby letting you parameterize clients with different requests, queue or log requests, and support undoable operations.

**Reach for it when.** You want to decouple the thing that *invokes* an action from the thing that *performs* it — to queue actions, log them, schedule them, support undo/redo, or build macros. The book's example: a remote control whose buttons hold `Command` objects.

**Structure.** A `Command` interface with `execute()` (and often `undo()`); concrete commands bind a receiver + parameters; an invoker holds and triggers commands without knowing what they do. A *Meta/Macro Command* holds a list of commands.

**Overkill when.** You just need to call a method now — call it. Command earns its keep specifically when you need to *store, pass around, queue, or reverse* actions. A closure often serves as a lightweight command.

**Related.** Undo pairs with *Memento* (snapshot state to restore).

---

## Adapter

**Intent.** Converts the interface of a class into another interface the clients expect. Adapter lets classes work together that couldn't otherwise because of incompatible interfaces.

**Reach for it when.** You have an existing class (often third-party) whose interface doesn't match what your code expects, and you can't or don't want to change either side. The adapter translates calls.

**Structure.** The adapter implements the *target* interface the client wants and internally delegates to the *adaptee*, converting the calls.

**Overkill when.** You control both sides — just align the interfaces directly. An adapter is for when one side is fixed.

**Related.** *Facade* also wraps but to *simplify* a subsystem, not to *convert* one interface to another. *Decorator* wraps to *add behavior* keeping the same interface.

---

## Facade

**Intent.** Provides a unified, simplified interface to a set of interfaces in a subsystem. Facade defines a higher-level interface that makes the subsystem easier to use.

**Reach for it when.** Clients must orchestrate many subsystem classes to do one common task (the "home theater" example: dim lights, lower screen, start projector…). A facade offers one easy entry point while leaving the subsystem accessible for advanced use. Supports Principle of Least Knowledge.

**Structure.** One facade class with convenience methods that call into the subsystem in the right order. It adds no new behavior — just simplification.

**Overkill when.** The subsystem is already simple, or there's only one client that needs only one call. A facade that just forwards a single method earns nothing.

**Related.** Unlike *Adapter* (convert interface) it simplifies; unlike *Mediator* it's one-directional convenience, not coordination.

---

## Template Method

**Intent.** Defines the skeleton of an algorithm in a method, deferring some steps to subclasses. Template Method lets subclasses redefine certain steps of an algorithm without changing the algorithm's structure.

**Reach for it when.** Several variants share the *same overall sequence* but differ in a few steps (e.g. `CaffeineBeverage.prepare()` = boil → brew → pour → addCondiments, where brew/addCondiments vary). The skeleton lives in the base class; subclasses fill the holes. Often exposes optional "hooks." Embodies the Hollywood Principle — the base class calls the subclass steps, not vice versa.

**Structure.** A base class with a final `templateMethod()` that calls abstract/overridable step methods.

**Overkill when.** Composition fits better — passing the varying steps in as functions (Strategy-style) avoids an inheritance hierarchy and is usually more flexible. Use Template Method when inheritance is already the natural model.

**Related.** *Strategy* solves the same "vary a step" problem via composition. *Factory Method* is a specialization (a step that creates an object).

---

## Iterator

**Intent.** Provides a way to access the elements of an aggregate object sequentially without exposing its underlying representation.

**Reach for it when.** Clients should traverse a collection without knowing whether it's an array, list, tree, or something else — and you want uniform traversal across different collection types.

**Structure.** An `Iterator` interface (`hasNext()`/`next()`); the aggregate returns one. Decouples traversal from storage; supports Single Responsibility (the collection isn't also responsible for iteration logic).

**Overkill when.** Your language already provides iteration (iterators, generators, `for…of`, enumerables) — use it instead of hand-rolling. You almost never implement this from scratch in modern languages; recognize that the built-in *is* the pattern.

**Related.** *Composite* is often traversed with an iterator.

---

## Composite

**Intent.** Composes objects into tree structures to represent part-whole hierarchies. Composite lets clients treat individual objects and compositions of objects uniformly.

**Reach for it when.** You have a recursive part-whole structure (menus containing menu items *and* sub-menus; files and folders) and want clients to call the same operations on a leaf or a whole branch without special-casing.

**Structure.** A `Component` interface implemented by both `Leaf` and `Composite`; the composite holds children (also `Component`s) and typically forwards operations to them.

**Overkill when.** The structure isn't actually recursive/nested, or is only ever two levels — a list is simpler. The transparency-vs-safety trade-off (do leaves expose `add()`/`remove()`?) is a real cost; weigh it.

**Related.** Frequently paired with *Iterator* (to traverse) and *Visitor* (to operate over the tree).

---

## State

**Intent.** Allows an object to alter its behavior when its internal state changes. The object will appear to change its class.

**Reach for it when.** Behavior depends on a mode/state and you have big conditionals branching on a state variable in every method (the gumball machine: `NoQuarter`, `HasQuarter`, `Sold`, `SoldOut`). Each state becomes a class; transitions move the context from one state object to another.

**Structure.** A `Context` holds a current `State` object and delegates to it; each concrete state implements the behavior for that state and decides the next state. Structurally identical to Strategy — the difference is intent: here the *states themselves drive transitions* and the context's behavior changes over its lifetime.

**Overkill when.** Few states with trivial transitions — a simple enum + `switch` may be clearer and easier to see whole. State shines when transition logic is complex or duplicated across many methods.

**Related.** *Strategy* (same structure, externally chosen, doesn't self-transition).

---

## Proxy

**Intent.** Provides a surrogate or placeholder for another object to control access to it.

**Reach for it when.** You need to interpose on access to an object: lazy-create an expensive object (*virtual proxy*), stand in for a remote object (*remote proxy*), enforce permissions (*protection proxy*), or cache/count calls. The client uses the proxy as if it were the real subject.

**Structure.** The proxy implements the *same* interface as the real subject, holds (or creates) a reference to it, and adds access control around the delegation.

**Overkill when.** No access concern exists — direct use is fine. Don't add a proxy "just in case" you'll later need caching/remoting; add it when that need is real.

**Related.** Same structure as *Decorator* (different intent: control access vs. add behavior) and *Adapter* (which changes the interface; a proxy keeps it identical).

---

## Compound / MVC

**Intent.** Patterns that work together to solve a recurring problem. *Model-View-Controller* is the canonical compound pattern.

**Reach for it when.** Building interactive applications where you want to separate data/business logic (Model) from presentation (View) from input handling (Controller). It's not one pattern but a collaboration: the **View observes the Model** (*Observer*), the **Controller is the View's strategy** (*Strategy*), and a View made of nested components is a *Composite*.

**Overkill when.** Tiny scripts or single-purpose UI — the ceremony of three layers outweighs the benefit. Most UI frameworks already impose an MVC-like structure; lean on theirs rather than inventing one.

**Related.** *Observer*, *Strategy*, *Composite* (the patterns it composes).

---

# Leftover patterns (appendix)

Less commonly needed, but worth recognizing. Listed with the book's intent and the key "reach for it when."

## Bridge

**Intent.** Lets you vary the implementation *and* the abstraction independently, by putting them in separate class hierarchies.

**Reach for it when.** Two dimensions both vary and a single hierarchy would multiply into a class per combination (e.g. shape × rendering API). Bridge keeps them on separate axes connected by composition. **Overkill when** only one dimension actually varies.

## Builder

**Intent.** Encapsulates the construction of a complex product, allowing it to be built step by step.

**Reach for it when.** An object has many optional parts or a multi-step assembly and a giant constructor (or telescoping constructors) is getting unreadable. A fluent builder makes construction explicit. **Overkill when** the object has a few fields — a plain constructor or options object is simpler. Compare *Abstract Factory* (a family of products vs. one complex product).

## Chain of Responsibility

**Intent.** Gives more than one object a chance to handle a request, by passing it along a chain of handlers until one handles it.

**Reach for it when.** A request could be handled by one of several handlers and you want to decouple sender from receiver — middleware pipelines, event bubbling, escalation logic. **Overkill when** there's a single handler, or order doesn't matter — a list/loop is clearer.

## Flyweight

**Intent.** Uses sharing to support large numbers of fine-grained objects efficiently, by separating intrinsic (shared) from extrinsic (per-context) state.

**Reach for it when.** You'd otherwise create millions of near-identical objects and memory is the bottleneck (characters in a document, particles, tree instances on a map). **Overkill when** object counts are modest — this trades simplicity and clarity for memory and should be driven by a real measurement.

## Interpreter

**Intent.** Defines a class-based representation for a grammar along with an interpreter to evaluate sentences in that language.

**Reach for it when.** You have a simple, stable little language to evaluate (rules, expressions, queries) and a class per grammar rule is manageable. **Overkill when** the grammar is non-trivial — use a real parser/grammar tool instead; Interpreter doesn't scale to complex languages.

## Mediator

**Intent.** Centralizes complex communications and control between related objects, so they no longer refer to each other directly.

**Reach for it when.** A cluster of objects has tangled many-to-many references (a form where every field affects others). A mediator becomes the hub each object talks to, cutting the web of dependencies. **Overkill when** interactions are few — a mediator can itself bloat into a god object; watch that the complexity moves rather than disappears.

## Memento

**Intent.** Captures and externalizes an object's internal state — without violating encapsulation — so the object can be restored to this state later.

**Reach for it when.** You need undo/redo, checkpoints, or snapshots and want to save/restore state without exposing the object's internals. **Overkill when** state is trivial to copy directly. Pairs naturally with *Command* for undo.

## Prototype

**Intent.** Creates new objects by copying an existing instance (the prototype), rather than constructing from scratch.

**Reach for it when.** Object creation is expensive or configuration-heavy and cloning a ready-made instance is cheaper/clearer, or the concrete type should be decided at runtime by which prototype you copy. **Overkill when** plain construction is cheap. Mind deep-vs-shallow copy semantics.

## Visitor

**Intent.** Lets you add new operations to an object structure without changing the classes of the elements on which it operates.

**Reach for it when.** You have a stable set of element classes (often a *Composite* tree) but keep needing to add *new operations* across all of them, and you'd rather not edit every class each time. The visitor gathers an operation in one place via double-dispatch. **Overkill when** the element classes change often (Visitor makes *adding element types* hard — the opposite trade-off), or there's only one operation. It's one of the heaviest patterns; be sure the "stable types, growing operations" shape really holds.
