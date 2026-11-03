# Authoring a Skill

Use this guide to create a skill, make a material edit, move content, or apply feedback. For a small change, apply only the sections it touches.

## Scope

Start from the result, the request that should select the skill, and the next consumer. Keep one durable capability per skill; distinct modes of it can share a short router. Split skills only when their triggers, authority, outcomes, or lifecycles are independent, and merge two whose triggers overlap.

Work in the repository's source skill directory. Preserve an installed skill's directory, name, and invocation policy unless the user authorized a change, and never edit a global installation from a repository-only request.

## Metadata

- `name`: lowercase letters and digits joined by single hyphens, at most 64 characters, equal to the directory name.
- `description`: one or two sentences naming the capability and the concrete trigger. Front-load what distinguishes it, because hosts truncate. Add an exclusion only for a real competing skill. The 1,024-character limit is a ceiling, not a target: no procedures, keyword catalogues, or templates.
- Keep the YAML valid; quote a value that contains `: `.
- A manual-only skill stays manual-only on every host: `disable-model-invocation: true` pairs with `allow_implicit_invocation: false` in `agents/openai.yaml`.

When discovery fails, compare intended requests with the nearest requests that belong elsewhere, including terse and explicit invocations, and fix the description before the workflow. Claim measured trigger accuracy only from runs that observed skill selection ([evaluation.md](evaluation.md)).

## Entry and resources

`SKILL.md` holds the result, the authority, the **acceptance contract**, the routing decisions, and the common invariants. Detailed modes, large schemas, and rare command options go in `references/`, each pointed to at the moment it is needed. A router must reach the complete selected method.

`assets/` holds files copied into outputs. `scripts/` holds operations a model cannot reliably do by hand: fragile, deterministic, security-sensitive, or repeated. A one-off command with a few flags stays inline. A script is non-interactive, has `--help`, writes results to stdout and diagnostics to stderr, prefers JSON for data an agent reads, gives errors that say what failed and what to try, and offers `--dry-run` when it changes state. Create no empty placeholders, readmes, or changelogs.

## Instructions

Give the model freedom, not procedure. Fix an order only when it protects a dependency or invariant. Keep status values, required fields, permission boundaries, and failure outcomes explicit. State the purpose, the completion condition, and what happens when one part is blocked: finish the rest and report the gap.

Teach the judgment the model lacks, not textbook content it already has. Give a rule its reason instead of emphasis; one principle generalizes, so don't list every variant. When format matters, one positive example steers better than a list of prohibitions. Wording current models over-follow is in [model-calibration.md](model-calibration.md).

State each rule once, in its owner. Fix a shared cause where it lives instead of appending the same workaround to several skills. Keep a local duplicate only when its placement protects a real boundary.

Use the collection's vocabulary: check `LEITWORTER.md` and `leitworter.json` before renaming a named concept, and keep every guarded phrase in the file that guards it.

## Paths

Keep the source checkout, the installed skill root, and the user's working directory distinct.

| Use | Resolves from |
| --- | --- |
| Prose pointer such as `references/schema.md` | The loaded skill root |
| Markdown link inside a reference | That reference's directory; repair it when moving text |
| Shell command running a bundled script | An absolute, model-filled `SKILL_DIR` set in the same command |

```bash
SKILL_DIR="<absolute path of this skill directory>"; python3 "$SKILL_DIR/scripts/<script>.py" --help
```

Keep the `;` separator, because some hosts flatten multiline commands, and set the anchor in every call, because shell state may not persist. A script finds its own resources from its own location. Never use load-time command syntax that inlines output while the skill loads: a normal failure can abort loading, and other hosts read it as text.

A skill's resources stay inside its directory. This collection permits the `shared/` library; a standalone package must bundle it or declare it.

## Apply feedback

Check that a proposed change addresses a real instruction, consumer, or observed failure; an explicit user request needs no invented history. Find the owner (metadata, routing, protocol, loading, script, or shared rule), change it there, and reconcile callers. Preserve fields, enums, coverage, and authority unless the user asked to change the contract. For a rename or merge, update callers, manifests, tests, links, and leitwörter guards, and delete what the change made obsolete rather than leaving an old workflow behind the new one.

Report a simplification as a structural change, not a proven runtime improvement.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
