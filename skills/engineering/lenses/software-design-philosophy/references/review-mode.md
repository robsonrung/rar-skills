# Review Mode

Walk the official red flags in [red-flags.md](red-flags.md). Name each finding. Assess conceptual integrity, change ownership, and the smallest coherent shape against the affected boundary. If a category is clean, write `clean`.

## Standalone output

```text
## Design review (Philosophy of Software Design)
### Findings
- [file:line] <red-flag name> (<dependency|obscurity>) — <what's complex>. Fix: <structural change>.
### Conceptual integrity
<which of conceptual integrity / change ownership / smallest coherent shape holds>
### Verdict
<one line>
```

A `design-gate` invocation uses the read-only gate response from the entry file instead of this standalone output.
