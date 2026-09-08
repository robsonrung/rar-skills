# Skill Authoring Contract

Use this reference when applying feedback, moving content, or changing bundled paths. Reuse it when already available in the current context.

## Admit useful instructions

Keep a line when it supplies domain knowledge, a project standard, or a falsifiable contract that changes execution. A cue for a known model limitation needs evidence that it still helps the supported runtime.

Remove vague effort language and repeated rationale. Fix a shared cause at its owner instead of appending the same workaround to several skills. Preserve an intentional duplicate only when its local placement protects a real consumer or boundary.

## Reuse project context

Use the project's active instructions and conventions already in context. Do not require a fresh read of root instruction files before each edit.

A concrete file is appropriate when the job is to write or audit it, when its relevant content is not loaded, or when a fresh worker needs instructions it did not inherit. Inspect only the changed paths and the boundaries that can affect them.

Describe the required capability before naming an adapter. One missing binary or environment variable does not prove that every supported interface is unavailable.

## Resolve bundled paths

Keep the source checkout, installed skill root, and user's working directory distinct.

| Use | Resolution |
| --- | --- |
| Prose pointer such as `references/schema.md` | Relative to the loaded skill root; say which file is needed and when. |
| Markdown link inside a reference | Relative to that reference's directory. Repair the link when moving text. |
| File copied or used by a tool | Resolve the named path from the loaded skill directory before acting. |
| Shell command invoking a bundled script | Set an absolute, model-filled `SKILL_DIR` in that command. Do not assume the shell starts in the skill directory. |

Example:

```bash
SKILL_DIR="<absolute path of the loaded skill directory>";
python3 "$SKILL_DIR/scripts/example.py" --help
```

The example script is a placeholder, not a promised bundled file. In a real skill, name its actual script. Keep the assignment separator because some hosts flatten multiline commands. Shell state may not persist between tool calls, so each invocation sets its own anchor. A script resolves its own resources from its location rather than assuming that `SKILL_DIR` was exported.

Do not rely on a host-specific skill-root variable without a working alternative when the variable is absent or unresolved.

## Avoid load-time commands

Do not use the skill syntax that executes a command during loading and inlines its output. A normal missing-PR or detached-branch result can abort loading on a supporting host, and other hosts treat the syntax as text.

Collect that context through runtime tools and interpret the result. Prefer structured arguments or simple commands that fit the active shell. Load-time command substitution is not a path-resolution mechanism.

## Preserve package boundaries

A skill's references, scripts, and assets belong inside its directory. Do not use absolute cache paths or traverse into a sibling skill from an independently installed package.

This collection explicitly permits the `shared/` library. Resolve it through the shared skill's convention. A standalone package must include the dependency or document it explicitly; it cannot silently skip the contract.

## Apply feedback at the owning layer

Check whether a proposed change addresses an actual instruction, consumer, or observed failure. An explicit user request can define a new behavior; it does not need an invented historical failure to justify it.

For audit findings, distinguish supported changes, risks needing verification, and optional ideas. Do not present an unverified concern as a confirmed defect. User-approved changes remain authorized; ask only if the concrete result would exceed that scope.

Identify the owner: metadata, routing, execution protocol, loading, script enforcement, or shared rule. Change that owner and reconcile affected callers and references. Preserve fields, enums, required coverage, and authority unless the user requested the contract change.

Report the material change and its evidence. A formal per-line classification or new review round is not required for a routine edit.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
