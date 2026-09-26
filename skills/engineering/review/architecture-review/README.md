# Architecture Review

A reusable skill for assessing an existing software architecture and presenting evidence-backed conclusions in a self-contained HTML report.

The central question is: **Is the system fit for purpose, with justified complexity and total cost?** The assessment must identify what to preserve as well as what to change. It does not automatically prefer DDD Tactical Building Blocks, additional layers, an ORM, events, a monolith, or microservices.

## English edition, version 2.0.0

The complete package is in English: instructions, reference guides, catalogs, schema, renderer messages, demo data, HTML, verification records, and behavioral evaluation specifications. Actual identifiers, commands, URLs, and canonical technical spelling are preserved.

The terminology catalog contains 74 entries. It distinguishes DDD from Clean Architecture meanings and includes Component Cohesion/Coupling principles, storage and replication concepts, transaction isolation, legacy seams, and verification patterns. `references/leitwoerter.md` turns selected terms into decision checkpoints, finding statements, actions, and acceptance checks. This is an authoring convention, not a measured agent-performance claim.

Schema 2.0 requires `leitwort` and `decision_statement` on findings and a `concept_applications` register. Earlier report JSON needs explicit migration; the validator will not silently accept or relabel it. Do not merge package versions without review.

## Installation

Extract the archive and install the entire `architecture-review` directory, not just SKILL.md. Keep the directory name, since it is the skill identity. The English archive uses this same root name.

| Environment | Personal skill directory | Project skill directory |
| :--- | :--- | :--- |
| Codex | `~/.agents/skills/architecture-review/` | `.agents/skills/architecture-review/` |
| Claude Code | `~/.claude/skills/architecture-review/` | `.claude/skills/architecture-review/` |

From the directory containing the extracted folder, these commands make a personal copy without overwriting an existing installation:

```sh
# Codex
mkdir -p "$HOME/.agents/skills"
if [ ! -e "$HOME/.agents/skills/architecture-review" ]; then
  cp -R architecture-review "$HOME/.agents/skills/architecture-review"
else
  printf '%s\n' 'An installed version already exists. Compare it before replacing it.'
fi
```

```sh
# Claude Code
mkdir -p "$HOME/.claude/skills"
if [ ! -e "$HOME/.claude/skills/architecture-review" ]; then
  cp -R architecture-review "$HOME/.claude/skills/architecture-review"
else
  printf '%s\n' 'An installed version already exists. Compare it before replacing it.'
fi
```

Installation conventions are carried forward from the official documentation recorded in the original package: Agent Skills specification [W06], Codex skills [W07], and Claude Code skills [W08]. Discovery depends on the installed product version and configuration. This package has not been installed or certified in either application during this revision.

## Use

In Codex, invoke `$architecture-review`. In Claude Code, invoke `/architecture-review`.

After invocation:

> Assess this repository in full. Start in read-only mode. Inspect the code, configuration, and documentation before asking material unanswered questions. Evaluate all 20 dimensions, including cost, maintainability, testability, and agent readiness. Use canonical architecture terminology and evidence-backed decision checkpoints. Compare keeping the design with incremental improvements; propose structural changes only when justified. Generate the HTML and supporting records outside the project. Do not modify product files or execute services or tests without authorization.

Direct instruction also works where the agent can read files: “Read `<path>/architecture-review/SKILL.md` and assess the repository at `<path>`.” Mentioning a local path does not establish access.

Useful context includes purpose, team, criticality, typical and peak workload, data volume, growth horizon, constraints, and budget. Unknowns remain unknown rather than becoming invented requirements.

## Outputs

`report.html` includes context, current architecture, all 20 dimensions, strengths, findings, concept applications, quality scenarios, capacity, alternatives, roadmap, agent readiness, economics, evidence, verification, sources, and glossary. Observed and proposed diagrams remain distinct. Every finding explains its tradeoff, smallest useful action, conditions for not acting, acceptance, and rollback.

`audit.json` is the structured source. `evidence.jsonl` preserves provenance. `verification.md` records procedures and results. Optional inventory records metadata only. None of these files proves correctness on its own.

The HTML includes local search, priority filtering, expandable details, SVG diagrams, accessible tables, narrow-screen layout, and print styles. It loads no external visualization assets, telemetry, or CDN. Source links are optional outbound links activated by the reader.

## Package layout

```text
architecture-review/
  SKILL.md
  README.md
  references/
    workflow.md
    rubric.md
    decisions.md
    agent-readiness.md
    output-contract.md
    terminology.md
    leitwoerter.md
    sources.md
  assets/
    dimensions.json
    terms.json
    sources.json
    report.schema.json
    report.html
  scripts/
    inventory.py
    validate_report.py
    render_report.py
    selftest.py
  examples/
    demo-audit.json
    rendered/
  evals/
    cases.json
    validation-results.md
    screenshots/
```

## Tools and tests

Python 3.10 or later is required. No packages need to be installed for inventory, validation, rendering, or selftests. From the skill directory:

```sh
python3 scripts/selftest.py
python3 scripts/validate_report.py examples/demo-audit.json
```

Render into a new directory:

```sh
OUT="$(mktemp -d)"
python3 scripts/render_report.py examples/demo-audit.json --out "$OUT/report.html"
printf '%s\n' "$OUT/report.html"
```

Inventory a repository using an output path outside it:

```sh
python3 scripts/inventory.py /path/to/repository --out /path/to/audits/inventory.json
```

The inventory does not read code contents or execute the project. Architectural assessment is performed by the agent using this skill; the scripts do not infer architecture or fabricate findings.

## Safety and evaluation

Default: read the system and write only authorized audit artifacts. No commits, deployments, migrations, or automatic corrections. Builds and tests require command inspection, authorization, and isolation. Never load-test production by default.

Selftests and browser checks validate this package. The cases in `evals/cases.json` specify future behavioral evaluations, not completed audits. See `evals/validation-results.md` for actual executed checks and limits.

**The demo is fictional. No user repository was audited, and no agent reliability benchmark was performed when preparing this edition.**

## Technical basis

The translated bibliography spans architecture, DDD, code design, legacy refactoring, data systems, testing, operations, and team learning. Sources are attributed with access limits in `references/sources.md`. They include the OpenAI harness engineering article and primary terminology references. Source concepts are analytical tools, not universal requirements or certification criteria.
