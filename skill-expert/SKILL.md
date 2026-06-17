---
name: skill-expert
description: Create, improve, evaluate, package, and debug portable Agent Skills with strong trigger metadata, progressive disclosure, bundled resources, scripts, and validation. Use when the user wants to create, write, author, merge, audit, package, troubleshoot, or optimize a skill, SKILL.md, skill description/frontmatter, skill discovery behavior, or reusable skill workflow.
---

# Skill Expert

Create skills that are small enough to load, specific enough to trigger correctly, and complete enough for another agent to execute without guessing.

## Operating Principles

- Treat the context window as a shared budget. Add only instructions, examples, scripts, references, and assets that materially improve execution.
- Assume the host agent is capable. Preserve space for non-obvious domain knowledge, fragile command sequences, exact validation steps, and reusable artifacts.
- Keep one skill focused on one durable capability. Split unrelated domains into separate skills.
- Prefer runtime-neutral language such as "host agent" unless the target repository explicitly requires Claude Code, Codex, or another runtime.
- Preserve existing repository conventions for skill locations, metadata, validators, and invocation style.
- Design for composability. A skill may load alongside other skills, so avoid global claims, broad ownership of unrelated work, or instructions that conflict with normal agent behavior.
- Keep the skill unsurprising. Its files, scripts, and instructions should match the user's stated intent; never create misleading skills, hidden exfiltration, unauthorized access workflows, or disguised harmful behavior.
- Inspect external or third-party skills before use, especially when network access, shell tools, secrets, or hosted execution are involved.
- Do not create extra human-facing files such as `README.md`, `CHANGELOG.md`, `INSTALLATION.md`, or quick-reference documents unless the repo already requires them, and leave out unused placeholder directories and files.

## Workflow

1. Determine the scope.

   - Identify the task or domain the skill should cover.
   - Start from 2-3 concrete use cases, including trigger phrases, expected steps, inputs, outputs, and edge cases.
   - Ground the skill in real project artifacts where possible: runbooks, docs, schemas, previous fixes, execution traces, review comments, or repeated user corrections.
   - Match the explanation level to the user's context. Briefly define terms like eval, benchmark, JSON, or assertion when the user has not shown they use that vocabulary comfortably.
   - Ask at most the blocking questions. If the user asked for autonomous work or provided enough context, make reasonable assumptions and continue.
   - In non-interactive or headless mode, proceed with explicit assumptions and report them at the end.

2. Choose the skill location.

   - Use the current repo's skill directory when editing project skills.
   - Use `.agents/skills/<name>` for Codex repo skills and `.claude/skills/<name>` for Claude Code project skills unless the repo already uses another convention.
   - Use a personal skill directory only when the user asks for personal/global installation.
   - Match the existing naming and metadata conventions before inventing new ones.
   - For distributable Codex workflows, consider whether the skill should later be bundled in a plugin rather than left as a local folder.

3. Design the reusable contents.

   - Use `SKILL.md` for the essential workflow and navigation.
   - Add `scripts/` when operations are deterministic, fragile, repetitive, parse-heavy, destructive enough to need dry-run behavior, or need explicit error handling.
   - Add `references/` for detailed docs, schemas, policies, variants, examples, or rare advanced paths that should be loaded only when needed.
   - Add `assets/` for templates, fixtures, boilerplate, fonts, images, or files copied into outputs rather than read as instructions.
   - Add `evals/` only when the skill needs repeatable quality or trigger testing; keep initial evals small and realistic.

4. Initialize or update the skill.

   - If the repo provides an initializer, prefer it. Example from a repo root:
     ```bash
     .agents/skills/skill-creator/scripts/init_skill.py <skill-name> --path .agents/skills
     ```
   - If no initializer exists, create `<skills-dir>/<skill-name>/SKILL.md` manually.
   - When updating an existing skill, preserve useful resources and change only what supports the requested behavior.
   - Preserve the original directory name and frontmatter `name` when updating an installed skill. If the installed copy is read-only, copy it to a writable temp path, edit there, then package from the copy.

5. Write the metadata.

   - `name`: lower-case letters, numbers, and hyphens only; max 64 characters; do not start/end with hyphen; avoid consecutive hyphens; match the directory name.
   - `description`: max 1024 characters; include what the skill does and when to use it.
   - Front-load the core use case and trigger words so the skill still works if clients shorten descriptions in crowded skill lists.
   - Prefer this formula: `<capability>. Use when <specific triggers, file types, tasks, or user phrases>.`
   - Focus on user intent, not internal implementation details.
   - Make descriptions assertive enough to avoid under-triggering, but not so broad that they hijack adjacent tasks.
   - Add negative triggers only when they prevent realistic conflicts with nearby skills.
   - Avoid optional frontmatter unless the current runtime or repo already uses it. If used, treat runtime-specific fields as portability tradeoffs.
   - Examples of runtime-specific extras: Claude Code may use invocation controls, arguments, paths, hooks, or subagent context; Codex may use `agents/openai.yaml` for UI metadata, implicit invocation policy, and dependencies; OpenAI API skills are versioned bundles mounted in hosted or local shell environments.

6. Write `SKILL.md`.

   - Use imperative instructions for the host agent.
   - Do not put discovery-only "when to use" guidance in the body; the body loads only after the skill is selected.
   - Start with the smallest useful mental model, then the execution workflow.
   - Anchor each load-bearing concept with a **leitwort** — a named, evocative term of art (`connascence`, `behavior-preserving`, `cold-start test`) the host agent will repeat back while acting, rather than a generic instruction it reads once. Name it where the agent narrates its decisions, not only in a heading; model the sentence you want echoed. When the repo defines a leitwörter convention (e.g. `LEITWORTER.md` and `leitworter.json`), follow it and reuse the canonical word over a synonym. See References.
   - Include concrete examples only when they clarify behavior or prevent common mistakes.
   - Add a short gotchas section when the agent is likely to make a non-obvious mistake.
   - Provide defaults, not menus. Pick the recommended path and mention alternatives only as escape hatches.
   - Define fallback paths for missing scripts, optional tools, unavailable services, or non-interactive execution.
   - Define the output contract for any generated artifacts: path, file name pattern, required sections, and validation expectations.

7. Apply progressive disclosure.

   - Keep `SKILL.md` lean; split content as it approaches 100-500 lines or mixes distinct domains.
   - Keep references one level deep from `SKILL.md`, such as `references/schema.md`.
   - Tell the agent exactly when to read each reference.
   - Add a table of contents to any reference longer than 100 lines.
   - Avoid duplicating the same information in `SKILL.md` and a reference file.

8. Validate and package.

   - Run repo-local validation when available. Examples:
     ```bash
     python3 .agents/skills/skill-creator/scripts/quick_validate.py .agents/skills/<skill-name>
     python3 .agents/skills/skill-creator/scripts/package_skill.py .agents/skills/<skill-name> /tmp
     ```
   - If those helpers are unavailable, manually verify frontmatter, name matching, description quality, paths, resource references, and file organization.
   - When the repo guards leitwörter (e.g. `scripts/check_leitworter.py`), run it so an edit does not silently delete a named anchor or drift a canonical word back to a generic phrasing.
   - Run any added scripts at least once with representative inputs.
   - Grep for stale project names, old stack assumptions, or copied-template leftovers before finalizing.

9. Evaluate real behavior when risk justifies it.
   - Test trigger accuracy and output quality against a baseline before trusting the skill.
   - See References below for when to load the detailed eval and description-tuning guides.

## Degrees of Freedom

- Use text instructions when multiple approaches are valid and context should guide execution.
- Use pseudocode, examples, or parameterized commands when there is a preferred pattern with valid variation.
- Use scripts with narrow inputs when the workflow is fragile, error-prone, security-sensitive, or likely to be repeated.

## Script Standards

- Prefer a one-off pinned command when an existing tool with a few flags is enough.
- Move complex or repeatedly generated commands into `scripts/`.
- Reference bundled files with paths relative to the skill root.
- Make scripts non-interactive. Accept inputs through flags, environment variables, files, or stdin.
- Provide `--help` output with usage, flags, and examples.
- Send machine-readable results to stdout and diagnostics to stderr.
- Use clear error messages that say what failed, what was expected, and what to try next.
- Prefer structured output such as JSON, CSV, or TSV for data the agent will consume.
- Add idempotency and `--dry-run` support for stateful or destructive operations.

## Quality Bar

- The skill has one clear purpose and a discoverable description.
- The metadata alone is enough for a host agent to choose the skill correctly.
- The body explains how to execute, not why the skill exists.
- Load-bearing concepts are named with leitwörter the agent will repeat while acting; generic filler verbs ("carefully", "thoroughly", "make sure") are replaced by named anchors, and shared concepts use the canonical word, not a synonym.
- The skill avoids stale, time-sensitive, or repo-foreign assumptions.
- All referenced files exist and are linked from `SKILL.md`.
- Scripts communicate success and failure through clear stdout, stderr, and exit codes.
- The final directory contains only files that directly support the skill.

## Troubleshooting

- If the skill does not activate, make the description more specific with trigger words, file types, operations, and user phrases.
- If multiple skills conflict, narrow each description and add negative triggers where appropriate.
- If the skill activates too often, add near-miss exclusions and move broad background material into a narrower skill.
- If validation fails, fix the first structural problem before polishing prose.
- If the body is long, extract rarely used details into `references/`.
- If the agent would need to guess a path, command, schema, or output shape, add that detail or provide a fallback.
- If instructions are ignored, cut verbosity, move detailed material to references, surface gotchas earlier, and add a validation loop.
- If the body feels generic and unmemorable, find its load-bearing concept and give it a leitwort — a precise, narratable term of art — then make the agent state it as it works.

## Delivery Contract

When creating or updating a skill, finish with:

- `created_files`: new files and important changed files.
- `validation`: commands run and results, or why validation was not available.
- `sources_used`: external specs, docs, project artifacts, or execution traces used to shape the skill.
- `assumptions`: decisions made without asking the user.
- `optional_refinements`: concise ideas that would improve the skill later without blocking current use.

## References

- Read `references/evaluation.md` when the user asks to test, benchmark, compare, or prove a skill is better, when the skill has objectively verifiable outputs, or when you need the detailed eval workspace, grading, benchmark, and human-review loop.
- Read `references/description-optimization.md` when the user asks why a skill does or does not trigger, when improving frontmatter `description` text, or when optimizing a skill description for trigger accuracy.
- Read the repo's `LEITWORTER.md` (with the `leitworter.json` registry) when authoring or improving a skill's body, to apply the leitwörter convention and the canonical cross-skill vocabulary.
