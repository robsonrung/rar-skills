# Skill Authoring Contract

Read this before writing or editing skill prose, before referencing any bundled file or script from a skill, and before applying review, peer, or eval feedback to a skill. These are the mechanical rules; the reasoning layer lives in `references/portable-skill-authoring.md`.

## Contents

1. [Skill prose admission rules](#skill-prose-admission-rules)
2. [Reference context, not instruction filenames](#reference-context-not-instruction-filenames)
3. [Bundled-file path resolution (three tiers)](#bundled-file-path-resolution-three-tiers)
4. [No load-time pre-resolution](#no-load-time-pre-resolution)
5. [Skill self-containment](#skill-self-containment)
6. [Applying feedback: Change / Verify / Consider](#applying-feedback-change--verify--consider)

## Skill prose admission rules

- Keep a line only when it states a falsifiable constraint, counters a known default tendency or observed shortcut, or supplies domain knowledge that materially changes a decision.
- Do not keep vague effort or quality language such as "be thorough" or "produce high-quality work" as a standalone instruction. Replace it with an observable rule, or retain a targeted effort cue only when it counters a documented runtime tendency and has been evaluated there.
- Do not append motivational rationale to a directive that already stands on its own.
- Repeat an instruction only at a demonstrated drift point where placement changes whether it fires. Protect genuinely required always-loaded duplicates with a parity test.

## Reference context, not instruction filenames

When a skill needs a project convention at runtime — issue tracker, coding standards, commit format, lint command, scope constraints — describe **what to look for in the agent's existing context**, not **which file to open**.

On the read path, do not name instruction files (`AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.cursor/rules`). Phrase it as "the project's active instructions and conventions already in your context." Three reasons:

- **Redundant.** Every major harness auto-injects the project's root instruction file at session start; "read `AGENTS.md`" asks the agent to re-open content it already has.
- **Brittle.** The filename differs per harness; a hardcoded name silently finds nothing on a harness that uses a different one.
- **Security smell.** Instructing an agent to go read named instruction dotfiles is the exact shape some prompt-injection defenses flag.

Name a concrete file only where a context reference cannot express the job:

- **Writing a convention back** needs a target — name it minimally and as an example ("the project's root agent-instructions file, e.g., `AGENTS.md`").
- **Reading content genuinely not auto-loaded** — a subdirectory-scoped instruction file, an optional project doc, or any file a fresh subagent (which does not inherit the parent's loaded instructions) must open. Auditing tools that enumerate every standards file are a legitimate exception: they review the files, they don't re-read them for context.

Pair this with naming the *category* of thing rather than a closed set ("the project's issue tracker, e.g., GitHub Issues, Linear, Jira" and "whatever interface it exposes — connector/MCP, documented API, or documented CLI"). Never treat a missing binary, env var, or MCP server as proof the capability is unavailable.

## Bundled-file path resolution (three tiers)

How a bundled-file reference resolves depends on who resolves it and whether a shell is involved. Do not assume a bare `scripts/…` path behaves the same in all three tiers.

**Tier 1 — read-time file references (relative, no anchor).** When skill content points the agent at a co-located file to read ("read `references/schema.yaml`"), use a relative path from the skill root. The skill loader resolves these against the skill's own directory on all major platforms.

**Tier 2 — prose pointers to a bundled file the agent acts on (relative + cue).** When prose names a bundled file the agent will use but does not put it in an executed shell command ("drive the loop with `scripts/hitl-loop.template.sh`"), use a relative path plus an explicit "from this skill's directory" phrase.

**Tier 3 — executed shell commands (the `SKILL_DIR` anchor).** When skill content puts a bundled script into a command the agent runs through the shell tool — a fenced bash block or an inline `bash …` / `python …` — anchor it to the skill directory. The shell tool's working directory is the user's **project**, not the skill directory, so a bare `bash scripts/my-script.sh` resolves to `<project>/scripts/…`. A capable agent often translates relative paths correctly, but the failure mode is a fenced block copied verbatim into a shell call, which runs literally and misses (`exit 127`). Anchoring bakes resolution into the command, making it deterministic:

```
# set inline in the SAME command (shell state does not persist between shell tool calls):
SKILL_DIR="<absolute path of the directory containing the SKILL.md you just read>";
bash "$SKILL_DIR/scripts/my-script.sh" ARG
```

Key properties of the anchor:

- `SKILL_DIR` is a **model-filled** value, not a harness variable. Every harness loads SKILL.md from a real absolute path the agent knows; the skill instructs the agent to set `SKILL_DIR` to that directory. It works identically across harnesses precisely because it depends on no host-specific variable.
- **Keep the trailing `;` on the assignment line.** Some hosts flatten a fenced multi-line block into one line by replacing the newline with a space; without the `;` the assignment collapses into an env-var-prefix form where `$SKILL_DIR` expands before the assignment takes effect, so the script path becomes `/scripts/my-script.sh`. The `;` is load-bearing, not style.
- Shell state does not persist between separate shell tool calls, so `SKILL_DIR` cannot be set once and reused — each invocation carries the path inline.
- A script that needs its **own** directory (to read a sibling file) derives it from `BASH_SOURCE`, not `SKILL_DIR` — `SKILL_DIR` is the orchestrator's shell variable and is not exported to the child process.

Do not use platform-specific variables or substitutions (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, `CODEX_SESSION_ID`, …) in skill content without a graceful fallback that works when the variable is unavailable or unresolved: such substitutions are typically single-host and expand to empty everywhere else, turning a guarded call into a genuine silent skip. When a platform variable is unavoidable, resolve it at runtime with a single shell call and state explicitly what to do when the value is empty, a literal command string, or an error.

## No load-time pre-resolution

Do not use the `` !`cmd` `` SKILL.md syntax that runs a command at skill load and inlines its stdout. It is single-host (inert literal text on other harnesses), and on the host that supports it a non-zero exit **aborts skill load** with a user-facing error — while the typical uses (git or PR context probes) have non-zero exits as *normal* states (no PR yet, detached HEAD, not a repo). Guards that force exit 0 with POSIX idioms then fail to parse under Windows PowerShell. No single command string is safe under all of these, so the construct cannot be fixed.

Gather context at runtime instead: have the agent run one argv-style command per shell tool call (`git …`, `gh …`) — no `;`, `&&`, `||`, pipes, `$(…)`, or redirects — and interpret each exit status as control flow. A single external-program invocation parses identically under POSIX sh and PowerShell, and a non-zero exit becomes data the agent reads rather than a load-time abort.

## Skill self-containment

Each skill directory is a self-contained unit. A SKILL.md must only reference files within its own directory tree (`references/`, `assets/`, `scripts/`) using relative paths from the skill root — never a sibling skill by relative traversal (`../other-skill/…`), an absolute path to another skill, or an installed-plugin cache path.

Why: skills execute from the user's working directory, not the skill directory; installed copies land at unpredictable versioned paths; and packaging or conversion tools copy each skill directory as an isolated unit, so cross-directory references break in the copy.

If two skills need the same small supporting file, **duplicate it into each skill's directory** and prefer small, self-contained reference files over shared dependencies. **Repo exception:** this repository's `_shared/` convention (shared references, scripts, schemas, and tests under `_shared/`) is a sanctioned shared root for skills that live and run inside this repo — keep using it here. The self-containment rule applies in full to any skill meant to be packaged, distributed, or installed standalone: at that point, inline or duplicate whatever it needs from `_shared/`.

## Applying feedback: Change / Verify / Consider

Applying review, peer, or eval feedback to a skill is a material revision. An item is not addressed because a sentence landed; it is addressed when a demonstrated gap is closed at its owning layer by the smallest mechanism. Before editing:

1. **Evidence** — classify each item:
   - **Change:** demonstrated gap with a supported smallest fix — a reproduced failure or the exact implementation path that necessarily fails; for additions, an observable consequence, unmet consumer contract, or material risk.
   - **Verify:** concrete risk that still needs reproduction or implementation tracing.
   - **Consider:** plausible enhancement whose value has not been demonstrated.
   Do not edit the skill for Verify or Consider items.
2. **Owning layer** — for each Change, identify the layer that owns it: activation contract, outcome spine or skill boundary, runtime protocol, loading or placement, deterministic enforcement, or shared authoring rule.
3. **Mechanism** — fix the gap at its owning layer. Add prose only when it is the smallest mechanism that closes the gap, and then only the smallest falsifiable unit per the prose admission rules.
4. **Reconcile** — reread the affected block; remove or rewrite text the change makes conflicting, duplicated, or obsolete. Resolve conflicting feedback items rather than stacking both.

When evidence shows the same cause across skills, fix the shared rule or mechanism unless the skills' contracts materially differ. For a multi-item round, record one line per item: `item -> Change|Verify|Consider | owning layer | mechanism - why`. Reviewer wording is a hypothesis about mechanism, not authority over it. Do not solve a non-problem with a rewrite: prefer an additive guard or explicit definition over replacing an implementation that already works.

---

*Adapted from [compound-engineering-plugin](https://github.com/EveryInc/compound-engineering-plugin) (MIT). See NOTICE.*
