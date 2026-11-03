# Red flags

Ousterhout's catalog with the structural fix. Each flag is a symptom whose root cause is **dependency** or **obscurity**. Name it, then change the structure; a comment that explains the trap is not a fix.

| Flag | Symptom | Fix |
| --- | --- | --- |
| Shallow module | Interface barely simpler than the implementation; often many tiny classes | Fold wrappers into the caller, raise the abstraction, or merge with the module it delegates to |
| Information leakage | One decision reflected in several modules; worst when the shared assumption is undocumented | Give the decision one owner. Merge small classes bound to that knowledge; extract only when the shared knowledge gets a simple interface |
| Temporal decomposition | Modules follow execution order (`read`/`process`/`write`), so format knowledge spreads across them | Organize around the knowledge each module hides |
| Overexposure | Common use requires confronting rare options | Default-laden entry point; rare options stay reachable and out of the way |
| Pass-through method | Forwards arguments to a method with a similar signature | Call the deeper method directly, merge the layers, or give the method a distinct job. Follow one operation down the stack: the abstraction should change at each call |
| Pass-through variable | A parameter threaded through methods that ignore it | A context the chain already shares, or another path to the method that needs it |
| Repetition | Nontrivial code copied | Extract into an owner only when the copies are the same concept with the same reason to change |
| Special-general mixture | Special-case logic inside a general mechanism; a boolean plus a dozen `if`s | Push the special case up to the feature or down to a driver; make the edge the normal case |
| False abstraction | A general-sounding method whose callers still need its body to know a fact | Expose the general operation the caller actually needs |
| Conjoined methods | Neither half can be understood without the other | Recombine, or re-cut where each half stands alone |
| Comment repeats code | The comment says what the adjacent code says | Delete it or replace it with an **earned comment** |
| Implementation in interface docs | Interface comment describes internals | Interface comments state the contract; how-it-works goes in the body |
| Vague name | `data`, `info`, `manager`, `tmp` | Name the precise concept; same word, same meaning everywhere |
| Hard to pick name | No precise name exists | The entity does two jobs or has no identity; reshape it |
| Hard to describe | Complete documentation must be long | Simplify the interface until it can be described simply |
| Nonobvious code | A reader must re-derive behavior or guesses wrong | Precise names, structure that matches expectation, less cleverness. If it can't be made obvious, that is the finding |

Taking it too far is also a defect: hiding information the caller must know, pulling down a policy the module cannot decide, defining away an error the caller must handle, or enforcing consistency that blocks a better local design you are not converting.
