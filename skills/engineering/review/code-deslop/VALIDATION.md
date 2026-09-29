# Release validation

**Date:** September 28, 2026. **Package:** code-deslop 1.0.0.

This file records checks actually executed while building the package. It is not a claim that a coding agent completed the 32 scenarios or that this skill outperformed another remover.

## Environment

Linux working container; Python 3.13.5; Git 2.47.3; Node.js v22.16.0. The helper scripts also passed a Python 3.10 syntax parse. Other Python/runtime/operating-system combinations were not executed in this validation.

## Results

| Check | Actual result |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | 46 tests passed: 41 helper tests and 5 package-integrity checks. |
| `python3 -m unittest discover -s evals/fixtures/python -p 'test_*.py' -v` | 6 Python contract tests passed. |
| `node --test evals/fixtures/javascript/test_contracts.mjs` | 9 JavaScript contract tests passed. |
| `python3 scripts/validate_report.py assets/report.example.json` | Example passed structural and consistency validation. It remains a hypothetical example, not real audit evidence. |
| Deliberately unsafe mutations in disposable fixture copies | All 6 were rejected by the unchanged protected tests. |
| Known-safe fixture cleanup demonstrations in disposable copies | JavaScript and Python demonstrations both passed their unchanged contract tests. These were scripted fixture edits, not live agent runs. |

The scope tests exercise clean and unborn repositories; staged/unstaged/untracked unions; cancellation between index and worktree changes; deletion and rename paths; ignored files and exclusions; literal unusual filenames; explicit filters and branch bases; diverged merge-base selection; dirty work inclusion; symlink exclusions; conflicts; non-Git errors; JSON output; and preservation of index bytes/mtime.

Sentinel tests verified that configured external diff, fsmonitor, clean/smudge and process filters were not executed by the helper in the tested fixtures. These tests do not establish a general sandbox or defend against a compromised Git executable or operating system.

The report tests check mode consistency, required evidence fields, actual outcome labels, check references, risk restrictions, review provenance labels, duplicate identifiers/JSON keys, relative paths, malformed types and non-execution of command strings. Structural consistency cannot prove that evidence is truthful.

## Deliberately unsafe mutations

Each mutation was applied only in a new temporary copy; protected tests were not changed. Each command exited nonzero because the altered behavior failed those tests.

| Mutation | Protected behavior |
| --- | --- |
| JavaScript explicit absence check changed to `Boolean(value)` | Zero, false, NaN and zero bigint remain present values. |
| JavaScript `Promise.all([load()])` changed to `load()` | The result remains an array. |
| JavaScript `resource.release()` removed | Cleanup occurs after work, on success and failure. |
| JavaScript tenant filter removed | Other tenants' rows are not returned. |
| Python runtime registration decorator removed | Registry dispatch still reaches the handler. |
| Python explicit absence check changed to `bool(value)` | Falsy-but-present inputs remain accepted. |

The positive demonstrations removed a narrating comment, a redundant temporary alias and a proven private unused fixture helper. They passed the same tests. Passing these small oracles neither proves all possible edits safe nor measures useful-cleanup recall in real code.

## Not performed

No cleanup of the user's codebase. No installation or execution of third-party cleanup scanners. No production/service access. No live model/agent execution of the scenario suite. No independent maintainer review or multi-model comparison. No measured performance, precision, recall, time or token-cost advantage over competing skills.

The package contains 32 labeled evaluation scenarios and a matched-comparison protocol to make those future claims testable. Scenario availability is not a passing benchmark result.
