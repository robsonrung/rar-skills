# Design Mode

State the abstraction in one sentence (what the caller gets to _not_ know). Then **design it twice**. Functionality matches today's needs; the interface does not — it is _somewhat general_. Over-specialization is the usual source of extra complexity: do not put `backspace`/`deleteKey`/`deleteSelection` on the text module. Answer the three questions in [principles.md](principles.md) before coding. Pull complexity down; define errors out of existence; write the interface comment _before_ the body so a caller need not read the implementation. Read [principles.md](principles.md), then [comments-and-names.md](comments-and-names.md).

## Standalone output

```text
## Philosophy of Software Design
Route: design | improve
Abstraction: <one sentence>
Principles: <which of the 16 you used>
Red flags: <name or clean>
Strategic vs tactical: <one line>
What we rejected: <a real alternative and its cost, or no new choice>
Next move: <one action>
```

If you edited code, add: files touched, **behavior-preserving** or the exact behavior change, checks run.

A `design-gate` invocation uses the read-only gate response from the entry file instead of this standalone output.
