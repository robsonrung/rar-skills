# Validation results

Edition: 2.0.0, English. Verification date: September 26, 2026.

## Executed checks

| Check | Result | Evidence and scope |
| :--- | :--- | :--- |
| Python selftests | 64 passed, 0 failed | `selftest.log`, Python 3.13.5. Includes schema validation, reference integrity, evidence rules, safe rendering, output handling, terminology, and decision checkpoints. |
| Demo validation | Passed | `scripts/validate_report.py examples/demo-audit.json`. The fictional report satisfies the version 2.0 structural contract. |
| Browser checks | 27 passed, 0 failed | `browser-results.json`, system Chromium 144.0.7559.96 controlled through Playwright. |
| Visual inspection | Completed | English desktop, mobile, layer diagram, proposed diagram, and concept checkpoint screenshots are included in `screenshots/`. |
| Language review | Completed | Instructions, reference documents, catalogs, schema messages, renderer text, demo data, evaluation cases, and generated records were reviewed in English. Portuguese words occur only as deliberately forbidden strings in the language regression test. |
| Python compatibility syntax check | Passed | All four scripts parsed with the Python 3.10 grammar. Actual execution used Python 3.13.5, not a Python 3.10 runtime. |

The browser checks covered document language, the fictional banner, all 20 dimensions, findings, concept checkpoints, SVG diagrams, internal navigation, unique IDs, search, priority filters, keyboard disclosure, evidence expansion, print state, desktop and mobile overflow, local diagram scrolling, absence of runtime errors or external requests, and content availability with JavaScript disabled.

## Browser method and limits

The exact generated HTML bytes were supplied through Playwright's `page.set_content` API in an offline browser context. The bundled Playwright browser was unavailable, so system Chromium was used. Direct `file://` navigation was blocked by the environment's browser policy. No policy was changed. These checks verify rendering of the generated document, not direct local file navigation in this environment.

Print styles and print lifecycle handlers were checked through media emulation and events. A physical printer or an exported PDF was not tested. Source links were checked structurally, not all revisited in the browser test.

## Not executed

The 26 scenarios in `cases.json` are proposed behavioral evaluations. Their fixture repositories, agent runs, independent grading, repeated trials, and performance comparisons have not been performed. They are not evidence of improved agent reliability.

No user repository was audited. No product tests, workload benchmarks, production operations, or agent acceptance tasks were run. The skill was not installed or certified in Codex or Claude Code.

Schema checks can require a canonical term to recur in a decision and a resulting action or check. They cannot prove the diagnosis is sound or the repetition is meaningful. That remains an evidence and review requirement.

## Reproduction

Run `python3 scripts/selftest.py` and `python3 scripts/validate_report.py examples/demo-audit.json` from the extracted skill directory. These checks require only Python's standard library. Browser verification additionally requires an available browser and automation environment; the recorded results describe the actual environment used for this edition.
