# Code Deslop

A portable, evidence-driven Agent Skill for removing unnecessary code without deleting useful behavior. Version 1.0.0. Research snapshot: September 28, 2026.

The objective is less unjustified maintenance cost, not code that looks less generated. The skill combines contextual review, selective static analysis, small behavior-preserving edits and verification. It does not identify authorship or promise a universally optimal refactor.

## Install

The only required runtime instruction file is `SKILL.md`. Keep the complete folder so its on-demand references and optional helpers remain available. The format follows the [Agent Skills specification](https://agentskills.io/specification).

For Codex, place this folder at `.agents/skills/code-deslop/` in the repository, or at `~/.agents/skills/code-deslop/` for personal use. See the [official skills documentation](https://developers.openai.com/codex/skills).

For Claude Code, place it at `.claude/skills/code-deslop/`, or at `~/.claude/skills/code-deslop/`. See the [official skills documentation](https://code.claude.com/docs/en/skills). Keep one canonical copy if your host supports linking skill directories. Do not add another copy to the model's context.

Other Agent Skills hosts can use the same folder. There is no provider-specific dependency or mandatory model assignment. Host permissions still apply. The Markdown works without Python; the optional helper scripts require Python 3.10+ and the scope helper also requires Git. The bundled JavaScript fixture tests require a Node.js runtime with the built-in test runner.

## Use

These are messages to the coding agent, not shell commands. In Claude Code, use `/code-deslop` in place of `$code-deslop`.

### Audit only

```text
$code-deslop
Audit the current changed files. Do not edit files or execute repository code.
Identify supported cleanup opportunities, useful code to keep, and verification gaps.
```

### Clean a completed implementation

```text
$code-deslop
Clean up my current changed files. Preserve behavior, public contracts and my existing edits.
You may run relevant, inspected local checks with installed tools. No installs, downloads,
network access, external services, commits or pushes. Use the smallest coherent batches.
```

### Review a branch

```text
$code-deslop
Audit this branch against the existing local origin/main ref, including local changes.
Use its merge base. Do not fetch, edit, or run repository scripts.
```

The example base is explicit, not a default. Substitute the branch's actual known local base.

### Assess a codebase

```text
$code-deslop
Audit the repository one coherent package at a time. Do not edit files or execute code.
Prioritize evidence-backed maintenance cost. State review coverage and exclusions.
Do not turn this into a redesign, formatting campaign or score target.
```

A bare invocation defaults to an audit of current changed files. Explicit cleanup authorizes edits in scope, not command execution. Without authorized checks, executable changes remain proposals; clearly non-executable comment cleanup may proceed after inspection. Broader changes, dependency updates and bug fixes stay separate.

## Package contents

| File | Purpose |
| --- | --- |
| `SKILL.md` | Lean operating contract, workflow and stopping rules. |
| `references/patterns.md` | Evidence, counterevidence and verification for common cleanup candidates. |
| `references/verification.md` | Contract-specific checks, execution permissions and rollback limits. |
| `references/tools.md` | Selective tooling by stack and missing signal. |
| `references/research.md` | Sources, adopted ideas, rejected shortcuts and research limitations. |
| `references/evaluation.md` | Benchmark protocol, hard negatives and scoring without gaming. |
| `scripts/scope.py` | Optional metadata-only Git scope manifest. No source text in its output. |
| `scripts/validate_report.py` | Optional report structure/consistency validation; not truth verification. |
| `assets/report.example.json` | Clearly hypothetical structured audit example. |
| `evals/cases.json` | Review scenarios with expected and forbidden behavior. |
| `evals/fixtures/` | Small JavaScript and Python cleanup targets with protected contract tests. |
| `tests/` | Automated tests for the helper scripts and package integrity. |
| `VALIDATION.md` | Actual validation performed on this release and its limits. |

## Optional helper commands

Run only with appropriate authorization. These examples execute the shipped helpers, not a repository's own scripts.

```bash
python3 /path/to/code-deslop/scripts/scope.py --repo /path/to/repo
python3 /path/to/code-deslop/scripts/scope.py --repo /path/to/repo --scope branch --base origin/main
python3 /path/to/code-deslop/scripts/scope.py --repo /path/to/repo --scope repo --path packages/server
python3 /path/to/code-deslop/scripts/validate_report.py /path/to/report.json
```

`--path` is a literal repository-relative filter, not a glob. The helper supports `changed`, `branch` and `repo` scopes; use `--scope repo --path ...` for explicit paths independent of whether they changed. It respects ignored untracked files, reports tracked exclusions, includes dirty work in branch scope and blocks conflicted repositories. The path manifest is not a backup, a secret scanner, a proof of dead code, or an exhaustive review.

The report validator never executes reported commands. A structurally valid report can still be false. Check the actual artifacts and command evidence.

## Validate this package

From the skill folder:

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s evals/fixtures/python -p 'test_*.py' -v
node --test evals/fixtures/javascript/test_contracts.mjs
python3 scripts/validate_report.py assets/report.example.json
```

The tests use local temporary directories and installed runtimes, not network services. Contract tests protect the fixture behavior but do not measure whether an agent chose a useful cleanup. The scenario suite and benchmark protocol address that separate question.

## Limitations

This package has no universal slop score and no measured claim to be the world's best remover. Its helpers and fixtures can be tested deterministically. Model judgment, repo-specific runtime reachability, meaningful simplification and behavior across real applications require separate evaluation. No live coding-agent benchmark or cleanup of a user's repository is implied by the included validation.

Upstream tools and docs change. The source register records what was reviewed, not a dependency lockfile. Review the installed version before enabling a tool. The package does not bundle third-party tools or copy upstream skill text wholesale.
