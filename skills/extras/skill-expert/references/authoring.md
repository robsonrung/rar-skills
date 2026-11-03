# Authoring a Skill

Use this to create a skill, make a material edit, move content, or apply feedback. For a small change, read only the section it touches.

## Scope

Start from the result, the request that should select the skill, and its next consumer. One skill holds one durable capability; its modes can share a short router. Split skills whose triggers, authority, outcomes, or lifecycles are independent, and merge two whose triggers overlap.

Edit the repository's source skill directory. Never edit a global installation from a repository-only request.

## Metadata

- `name`: lowercase letters and digits joined by single hyphens, at most 64 characters, equal to the directory name.
- `description`: one or two sentences naming the capability and its trigger, with the distinguishing part first, because hosts truncate. Add an exclusion only for a real competing skill. The 1,024-character limit is a ceiling, not a target: no procedures, keyword lists, or templates.
- Quote a YAML value that contains `: `.
- A manual-only skill stays manual-only on every host: `disable-model-invocation: true` pairs with `allow_implicit_invocation: false` in `agents/openai.yaml`.

When discovery fails, compare the intended requests with the nearest requests that belong elsewhere, including terse and explicit invocations, and fix the description before the workflow.

## Layout

`SKILL.md` holds the result, the authority, the acceptance contract, the routing decisions, and the shared invariants. Modes, large schemas, and rare options go in `references/`, each linked where it is needed. A router must reach the whole selected method. `assets/` holds files copied into outputs. Create no empty placeholders, readmes, or changelogs.

A script under `scripts/` is non-interactive and has `--help`. It writes results to stdout and diagnostics to stderr, prefers JSON for data an agent reads, says what failed and what to try, and offers `--dry-run` when it changes state.

## What stays explicit

| Keep explicit | Leave to judgment |
| --- | --- |
| Output paths, fields, enums, schemas | Order of independent investigations |
| Dependencies and required state transitions | Number of alternatives to sketch |
| Approval, mutation, and isolation boundaries | Generic self-checks and reread loops |
| Evidence and coverage a consumer needs | Repeated rationale and quality reminders |
| Bounded retries and terminal outcomes | Choice among valid techniques |

Put each kept rule next to the action it governs. When format matters, one positive example works better than a list of prohibitions. Name load-bearing concepts with [leitwörter](leitworter.md).

## Paths

Keep the source checkout, the installed skill root, and the user's working directory distinct.

| Use | Resolves from |
| --- | --- |
| Prose pointer such as `references/schema.md` | The loaded skill root |
| Markdown link inside a reference | That reference's directory; repair it when moving text |
| Shell command running a bundled script | An absolute `SKILL_DIR` set in the same command |

```bash
SKILL_DIR="<absolute path of this skill directory>"; python3 "$SKILL_DIR/scripts/<script>.py" --help
```

Keep the `;`, because some hosts flatten multiline commands, and set the anchor in every call, because shell state may not persist. A script finds its own resources from its own location. Never use syntax that inlines command output when the skill loads: one failure can abort the load, and other hosts read it as text. A skill's resources stay inside its directory. This collection allows the `shared/` library; a standalone package must bundle it or declare it.

## Apply feedback

Check that the proposed change addresses a real instruction, consumer, or observed failure. An explicit user request needs no invented history. Find the owner (metadata, routing, protocol, loading, script, or shared rule), change it there, and reconcile its callers. Preserve fields, enums, coverage, and authority unless the user asked to change the contract. A rename or merge also updates callers, manifests, tests, links, and leitwörter guards.

---

_Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE._
