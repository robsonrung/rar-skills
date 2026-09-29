# Research: removing AI slop from code

Research snapshot: **September 28, 2026**. This is a synthesis of public primary sources, not a comparative performance study. Repository links on moving branches describe the reviewed material, not a pinned dependency version. No third-party scanner was installed or benchmarked while building this package.

## Working definition

For this skill, slop is **unnecessary or misleading code that adds maintenance or review cost without justified functional, domain or operational value**. This is an operational synthesis, not a standardized community definition. Authorship is irrelevant to the cleanup decision.

The discussion spans three concerns: superficial noise, structural debt and missing trustworthy intent. A removal policy must handle all three. It must not confuse style with a defect, duplicated syntax with duplicated knowledge, or an analyzer's incomplete graph with proof of dead code.

Developer discussion supports combining deterministic signals with contextual judgment and behavioral checks. It also highlights the cost shifted to reviewers. These observations motivate the design; they do not establish that any one remover is the best.

## What was adopted

| Source family | Useful idea | Adaptation in this skill |
| --- | --- | --- |
| Code-simplifier skills | Preserve behavior; prefer clarity over terseness; start with changed code. | Explicit mode/scope, verification evidence and no-op outcomes. |
| Scoped deslop skills | Read complete files; keep edits local; parallelize only worthwhile independent work. | Exclusive write ownership, serial integration and honest review provenance. |
| Structural analyzers | Find unreachable code, duplicate structures, type escapes and coupling. | Findings are candidates; entry-point and counterevidence checks precede deletion. |
| Broad cleanup harnesses | Combine mechanical and contextual review; triage related findings; rescan. | Bounded batches and repair attempts, not a high-score mandate. |
| Testing and refactoring practice | Check actual contracts; distinguish real shared knowledge from accidental similarity. | Characterization, equivalence/failure tests and hard negatives. |
| Developer feedback | Cleanup must improve future work, not just the current diff. | Propose a targeted local invariant for recurrent issues; do not create an expanding instruction dump. |

## What was rejected

No AI-authorship classifier. No universal zero-comment, zero-duplication, 20-line-function or one-component-per-file rule. No automatic removal of catches, wrappers, validation, memoization or one-promise combinators. No ranking by lines deleted. No unsafe autofix campaign. No treating tool-output instructions as authority. No automatic installation, cloud upload or branch-wide rewrite. No claim that tests or a report validator prove all behavior is preserved.

One concrete warning came from the `dabit3/deslop` README: its proposed replacement of explicit null/undefined/empty-string checks with truthiness changes the accepted values. The fixture tests protect `0`, `false`, `NaN` and `0n`. This is a counterexample to that rewrite, not a benchmark of the entire tool.

## Source register

### Community discussion and research

**R01. Baltes, Cheong and Treude, “An Endless Stream of AI Slop.”** [Paper record, v4 revised August 28, 2026](https://arxiv.org/abs/2603.27249). The abstract reports qualitative analysis of 1,154 Reddit/Hacker News posts, with themes around review friction, quality degradation and systemic forces. This is evidence about expressed concerns, not a representative prevalence estimate or cleanup-tool benchmark. Reviewed the current record and abstract.

**R02. Baltes, Cheong and Treude, “AI Slop and the Software Commons.”** [April 17, 2026 position paper](https://arxiv.org/html/2604.16754v1). Argues that cheap generation shifts costs onto reviewers and shared artifacts. Examples include type escapes, fictional integrations and tests changed to accept broken behavior. Used to broaden the target beyond cosmetics, not to endorse all proposed governance measures.

**R03. r/reactjs, “AI code janitors.”** [Developer discussion](https://www.reddit.com/r/reactjs/comments/1r76c4s/ai_code_janitors_deslop_ai_slop/). Participants discuss static analysis, explicit dependency rules, feedback to the coding workflow and the gap between cleaner source and working application behavior. Anecdotal and partly promotional; not consensus or validated vendor statistics.

**R04. Addy Osmani, “Agentic Code Review.”** [Engineering essay](https://addyosmani.com/blog/agentic-code-review/). Supports reviewing intent, requirements and decisions rather than relying on plausible code. Used for review design, not for numerical claims about tool accuracy or productivity.

**R05. Sandi Metz, “The Wrong Abstraction.”** [Original essay](https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction). Explains why removing duplication can create worse coupling and why undoing a mistaken abstraction can be appropriate. Used to distinguish duplicated knowledge from coincidentally similar code.

### Existing skills and cleanup tools

**R06. Anthropic code-simplifier.** [Official agent definition](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md). Behavior preservation, limited scope and clarity over compactness are useful. Its JavaScript style preferences are not universal defaults. This package adds explicit evidence and execution boundaries rather than copying the agent verbatim.

**R07. Sentry code-simplifier.** [Current skill](https://github.com/getsentry/skills/blob/main/skills/code-simplifier/SKILL.md). Explicitly based on Anthropic's agent; not independent validation of that approach. Older `deslop` listings were not treated as verified current documentation when the corresponding path could not be retrieved.

**R08. Mike Cann deslop.** [Skill](https://github.com/mikecann/agent-skills/blob/main/skills/deslop/SKILL.md) and [style companion](https://github.com/mikecann/agent-skills/blob/main/skills/deslop/style.md). Useful scoped second pass, selective subagents, preservation of public signatures and permission to make no change. Personal style limits are left to repository policy; supporting tests are not categorically excluded.

**R09. Desloppify.** [Repository and README](https://github.com/peteromallet/desloppify). Combines mechanical and subjective review with a persistent prioritized queue. Its documented scan model is coherent-project/full-codebase, not true diff-only. Borrowed triage and evidence integration; rejected adopting broad refactor/score instructions as this skill's default authority. License and installed-version behavior need separate inspection before use.

**R10. deslop-js.** [Repository and README](https://github.com/millionco/deslop-js). JS/TS structural candidate detection with confidence tiers and explicit analyzer-error reporting. Its library is `deslop-js`; its CLI package is `deslop-cli`. Confidence, defaults and actual installed behavior require inspection; a “high” tier is not proof of equivalence.

**R11. dabit3/deslop.** [Repository and examples](https://github.com/dabit3/deslop). Diff-oriented pattern detection illustrates common cosmetic complaints. Its truthiness example is not generally behavior-preserving. Useful as a source of hypotheses and a hard-negative regression example, not an automatic rewrite policy. Its package name must not be confused with other tools called deslop.

**R12. React Doctor.** [Repository](https://github.com/millionco/react-doctor). Optional React-specific diagnostic input for state/effects, component structure and related issues. No adoption or accuracy claim was inferred from its own marketing. Inspect the installed version's network, telemetry, licensing and configuration behavior before execution.

### Deterministic analysis and verification

**R13. Knip, resolving reported issues.** [Official guide](https://knip.dev/guides/handling-issues). An unreachable-file report describes the configured graph. Dynamic imports, missing generated inputs, aliases and framework entry points can explain apparent unused code. Used for the deletion gate; silencing findings is not equivalent to resolving them.

**R14. Ruff, linter and fix safety.** [Official documentation](https://docs.astral.sh/ruff/linter/). Distinguishes safe from unsafe fixes; unsafe transformations may change runtime behavior or remove comments. Used to prefer check mode and reviewed targeted fixes over broad autofix.

**R15. Vulture.** [Maintainer repository](https://github.com/jendrikseipp/vulture). Python unused-code candidates, confidence and handling of dynamic usage. Treated as supporting evidence rather than a universal reachability oracle.

**R16. Staticcheck.** [Official documentation](https://staticcheck.dev/docs/). Go static analysis complements the compiler and existing tests. Listed as an optional installed tool, not a new mandatory dependency.

**R17. dependency-cruiser.** [Maintainer repository](https://github.com/sverweij/dependency-cruiser). Dependency analysis and rule enforcement. Used to enforce actual agreed boundaries rather than invent a new architecture during cleanup.

**R18. jscpd.** [Maintainer repository](https://github.com/kucherenko/jscpd). Clone detection is a useful lead for inspection, not proof that matching blocks should share a business abstraction.

**R19. Stryker.** [Official documentation](https://stryker-mutator.io/docs/). Mutation testing can reveal tests that fail to detect broken behavior. Recommended only as a bounded, authorized check; surviving equivalent mutants require judgment.

**R20. React, “You Might Not Need an Effect.”** [Official guide](https://react.dev/learn/you-might-not-need-an-effect). Distinguishes unnecessary derived state/effects from synchronization with external systems. Used for a contextual rule rather than a blanket effect-removal policy.

**R21. Semgrep.** [Official quickstart](https://semgrep.dev/docs/getting-started/quickstart). Optional pattern/security analysis within reviewed local configuration and execution permissions. No assumption that source uploads or telemetry are acceptable.

### Skill format and Git scope

**R22. Agent Skills specification.** [Specification](https://agentskills.io/specification). Portable `SKILL.md` metadata and progressive disclosure through references, scripts and assets. Used to keep core instructions small and helper execution optional.

**R23. OpenAI skills documentation.** [Official documentation](https://developers.openai.com/codex/skills). Repository `.agents/skills` and personal skill locations. Used for installation guidance only; host permissions still apply.

**R24. Claude Code skills documentation.** [Official documentation](https://code.claude.com/docs/en/skills). Repository and personal `.claude/skills` locations and slash invocation. The same portable folder can be placed in the host's supported location.

**R25. Git diff documentation.** [Official documentation](https://git-scm.com/docs/git-diff). Distinguishes working-tree, staged and revision comparisons. Scope collection also received local tests for dirty-state handling, merge-base selection, literal filenames and execution safeguards; those tests are described in `VALIDATION.md`.

## Limits and provenance

All source-derived material above is summarized rather than copied wholesale. The package is not an endorsement, redistribution or installation of the listed tools. Source claims about performance and scoring were not adopted without comparative evidence. Forum comments and issue reports were treated as reports, not established product defects or broad prevalence estimates.

No live multi-model tournament, production cleanup, architecture rewrite or real-user repository inspection was performed. [evaluation.md](evaluation.md) defines how to test usefulness, safety and cost under matched conditions. The included validation covers only the package helpers and small synthetic oracles.
