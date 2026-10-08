# Design Mode

State the abstraction in one sentence: what can the caller safely ignore? Use **design it twice** only for a consequential unresolved interface. Reuse settled choices and examine new evidence that challenges them. Apply the interface checks in [principles.md](principles.md) to the changed boundary, including its invariants, error behavior, and compatibility.

Keep the interface somewhat general for current needs. For example, one range deletion can cover backspace and selection deletion without separate text APIs. Pull complexity into the module when it owns that knowledge. Preserve errors the caller must handle. When implementation is authorized and an interface comment is needed, use [comments-and-names.md](comments-and-names.md) before the body. An interview records decision fields only; a gate returns its canonical result.

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
