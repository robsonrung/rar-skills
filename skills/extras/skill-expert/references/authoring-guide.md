# Create or Improve a Skill

Use this guide for a new skill or a material edit. For a small change, apply only the sections it affects.

## Scope and location

Start from the intended result, user request, and next consumer. Concrete use cases help distinguish the skill from nearby skills; use existing requests and artifacts when available.

Use the repository's source skill directory and naming conventions. Use a personal installation only when requested. Preserve an installed skill's directory and frontmatter name unless renaming is authorized; if a read-only installed copy must be revised, work on a writable copy and report that the installation is unchanged.

Keep one durable capability per skill. Distinct modes of that capability can share a short router. Separate skills when their triggers, authority, outcomes, or lifecycles are independent.

## Metadata

- `name`: lowercase letters and numbers separated by single hyphens, at most 64 characters, matching the directory.
- `description`: one or two short sentences stating the capability and concrete trigger. Front-load the distinction that survives truncation. Add an exclusion only for a real competing skill.
- Treat the repository's 1,024-character limit as a ceiling, not a target. Do not put procedures, chapter lists, or output templates in descriptions.
- Keep YAML valid; quote scalar values containing YAML punctuation such as `: `.
- Preserve supported invocation controls and host metadata. A manual-only skill must remain manual-only on every supported host.
- Do not invent optional metadata or duplicate the same policy across files without a consumer requirement.

## Entry and resources

Keep the result, authority, acceptance contract, routing decisions, and common invariants in `SKILL.md`. Put detailed modes, large schemas, examples, and uncommon command options in `references/`; label when each file is needed. A router must point to the complete selected method, not merely link to an archive of the old entry.

Use `scripts/` for deterministic, fragile, or repeated operations. Use `assets/` for templates and files copied into outputs. Use `evals/` only for a useful repeatable comparison. Do not create empty placeholders or unrequested readmes and changelogs.

Check path resolution when moving text. Markdown links inside a reference resolve from that reference's directory; executed commands must resolve scripts from the loaded skill root. The detailed path rules are in `references/authoring-contract.md`.

## Instructions

State domain rules and protocols directly. Specify sequence only when order affects correctness. Keep status values, required fields, permission boundaries, and failure outcomes explicit.

Give defaults with a reason to depart from them. Do not demand a ritual, invented alternative, new approval, or full evaluation for a routine scoped edit. Do not invent a fallback that changes the requested model, authority, or output.

Follow the project's active language and vocabulary standards. In this collection, consult the repository's `LEITWORTER.md` and `leitworter.json` when changing a named concept. Preserve the name and its decision role rather than adding repeated narration.

## Update existing work

Reuse useful evidence and resources. Remove duplicates and obsolete directions from the affected files. For a rename or split, update callers, manifests, tests, and links that consume it. Leave unrelated behavior and user changes intact.

Before delivery, use the relevant checks in `references/validation-and-packaging.md`. Describe an unmeasured simplification as a structural change, not a proven runtime improvement.
