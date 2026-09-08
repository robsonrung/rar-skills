# Improve Mode

**stay strategic**. Design is never finished: the first cut is usually wrong, and implementation is how you find that. If the change is a special case that fights the design, fix the design (or say why you will not). Keep comments next to the code they describe; check the diff for comment drift. Read [modifying.md](modifying.md). Load [comments-and-names.md](comments-and-names.md) when names or comments are the work. Load [trends-and-performance.md](trends-and-performance.md) only when the question is a trend (TDD, patterns, inheritance) or a hot path.

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
