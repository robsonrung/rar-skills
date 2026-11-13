# rar-skills

`rar-skills` is a library of engineering skills for coding agents. Each skill is
a `SKILL.md` with its own references and scripts. The skills plan a feature,
implement it task by task with independent review, and deliver it. Shared
contracts, model routing, and runner scripts live in
[`skills/shared/`](skills/shared/SKILL.md), which installs beside the skills.

Each skill owns its rules. This README only points to them.

## Install

```bash
npx skills@latest add robsonrung/rar-skills --skill '*'
```

From a local checkout, run
[`scripts/install-skills.sh`](scripts/install-skills.sh) `/path/to/project`. It
installs to `.agents/skills/` and `.claude/skills/` (`--layout` picks one, and
`--copy` copies instead of symlinking). If a host hides a skill, tell the agent
to read `.agents/skills/<name>/SKILL.md` and follow it.

[docs/machine-setup.md](docs/machine-setup.md) lists the tools, CLIs,
credentials, and environment variables. `bash scripts/check-environment.sh`
checks them.

## Workflow

1. [`brainstorm`](skills/engineering/workflow/brainstorm/SKILL.md): decide whether an idea is worth building.
2. [`interview-me`](skills/engineering/workflow/interview-me/SKILL.md): settle the decisions.
3. [`to-prd`](skills/engineering/workflow/to-prd/SKILL.md): write the PRD for approval.
4. [`to-tasks`](skills/engineering/workflow/to-tasks/SKILL.md): split the PRD into an approved task queue.
5. [`implement-tasks`](skills/engineering/workflow/implement-tasks/SKILL.md): run the queue, one [`implement-and-review`](skills/engineering/engine/implement-and-review/SKILL.md) per task.
6. [`pre-pr-review`](skills/engineering/workflow/pre-pr-review/SKILL.md) and [`validate-e2e`](skills/engineering/workflow/validate-e2e/SKILL.md): check the finished change.
7. [`open-pr`](skills/engineering/deliver/open-pr/SKILL.md): commit, push, and open the pull request when asked.

[`models-consensus`](skills/engineering/workflow/models-consensus/SKILL.md) is
optional: a council of model opinions, only on request. A single bounded change
can go straight to `implement-and-review`.

The feature files (decision record, PRD, tasks, reports, evidence) live under
`.ai-workflow/work/<feature>/`, as
[work-state.md](skills/shared/references/work-state.md) describes. Models and
effort come from [`model-routing.json`](skills/shared/model-routing.json).

## Skills

| Domain | Skills |
| --- | --- |
| Workflow | `brainstorm`, `interview-me`, `to-prd`, `to-tasks`, `implement-tasks`, `to-prototype`, `models-consensus`, `pre-pr-review`, `validate-e2e` |
| Engine | `coding-design-plan`, `implement-and-review`, `worktree` |
| Gates | `design-gate`, `security-gate` |
| Lenses | `advanced-react`, `agent-architecture-lens`, `architecture-lens`, `data-systems-coding-lens`, `distributed-systems-patterns`, `domain-driven-design`, `software-design-philosophy` |
| Practice | `clean-code`, `diagnose`, `frontend-design`, `safe-incremental-coding`, `tdd`, `test-lens` |
| Review | `architecture-review`, `coding-review-simplify`, `full-review` |
| Delivery | `capture-learning`, `open-pr`, `resolve-pr-feedback`, `session-handoff` |
| Model seats | `cli-runner`, `pi-runner`, `muse-runner` |
| Extras | `browser-smoke`, `claude-models-router`, `diverse-plan`, `environment-check`, `knowledge-graph`, `openai-models-router`, `peer-sessions`, `response-unslop`, `skill-expert`, `verify-changes` |
| Visualization | `consensus-summary-html`, `html-explainer` |

Skills live under `skills/<domain>/`. Engineering skills sit one level deeper,
in `skills/engineering/<group>/<name>/`.

## Other docs

- [CONCEPTS.md](CONCEPTS.md): the shared vocabulary.
- [docs/solutions/](docs/solutions/README.md): learnings recorded by `capture-learning`.

## Contributing

Write and change skills with
[`skill-expert`](skills/extras/skill-expert/SKILL.md). It owns the authoring
guidance and the leitwörter convention
([leitworter.md](skills/extras/skill-expert/references/leitworter.md)). Run
`python3 scripts/check_leitworter.py` and
`python3 skills/shared/scripts/validate_skill_frontmatter.py` before committing.

## License

See [LICENSE](LICENSE).
