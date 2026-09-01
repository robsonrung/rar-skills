# Station Dispatch

Loaded by `ship` before phase 3. One row per delegated station: what the worker invokes, what it may read, what its report must carry forward, and what its envelope's `verdict` may say.

The brief/report/envelope shapes are **not** restated here — they live in `shared/references/handoff-contract.md`. This file is only the per-station binding.

Run directory for a ship run: `.ai-workflow/ship/<run-id>/<slice-id>/`. Phase-1 and phase-2 artifacts are run-level (no `<slice-id>`), since they precede the slice split.

## Two seats rules that apply to every station

1. **A station worker does not spawn host-native subagents.** Nesting the `Agent` tool is not guaranteed inside a worker, so a station whose skill fans out to seats routes them through the runner CLIs instead — the existing switch is `python3 shared/scripts/discover_runners.py probe --native-agent no`, which reports the opus/sonnet seats as `claude-runner`-backed rather than expecting a host subagent. State `--native-agent no` in the brief for every station that fans out (3, 4, 5, 6). Seat fidelity is unchanged: a missing CLI is `seat_unavailable`, never a substitution.
2. **Entry-point skills are invoked by file path.** A skill carrying `disable-model-invocation: true` never appears in a worker's skill list, so naming it finds nothing. In this pipeline that is `resolve-pr-feedback` — its brief says *read `resolve-pr-feedback/SKILL.md` and follow it*. Every other station skill is model-invocable and is named normally.

## Phase 1 — delegated grounding (the one exception in the interactive half)

Phases 0–2 run in the conductor's own context because only it can ask the user. One piece of phase 1 is not conversation and is delegated anyway:

| | |
|---|---|
| Worker invokes | nothing — a read-only exploration pass |
| Reads | `CONCEPTS.md`, `docs/adr/`, `docs/solutions/`, and the code paths the request touches |
| Writes | `01-grounding.report.md` |
| Verdict vocabulary | `grounded` \| `thin` (thin = the repo does not answer enough to skip questions) |
| Carries forward | The glossary terms the feature reuses, the ADRs that constrain it, the existing code that already does part of it, and — the payload `interview` actually wants — **the questions the repo already answers**, so they are never put to the user |

The conductor then runs `interview` inline against that report. This is the whole reason the pass exists: *the user's time is the bottleneck*, and the reading that protects it is the most delegable work in the interactive half.

## Phases 3–6 — fully delegated stations

### Phase 3 — design gate

| | |
|---|---|
| Worker invokes | `coding-design-plan`, then `design-gate` with the slice's `gates` flags |
| Reads | the slice contract (tracker issue or `TASKS.md` section), `01-grounding.report.md` |
| Writes | `03-design-gate.report.md` |
| Verdict | `proceed` \| `revise` |
| Carries forward | The shaped plan, the named test scenarios, and the lens findings the implementer must honor. A `revise` carries the concrete load-bearing finding — cosmetic notes are listed under *Findings not applied*, not returned as blockers. |

`design-gate` runs its lenses as parallel read-only reviewers *inside* this worker. Lens count is capped at three by its own table; the worker does not widen it.

### Phase 4 — implement

| | |
|---|---|
| Worker invokes | `implement-and-review` (alternatives per ship's phase table: `collaborative-delivery`, or direct `tdd` for a trivial single-track slice) |
| Reads | the slice contract, `03-design-gate.report.md` |
| Writes | `04-implement.report.md` |
| Verdict | `built` \| `blocked` |
| Carries forward | The branch/worktree, the diff range, which acceptance commands are now expected to pass, and the verification evidence the evidence gate reads — which existing tests were inspected, which were added, which ran, what they proved |

`implement-and-review` keeps its own `.ai-workflow/impl-review/<id>/report.md`; the station report **cites that path**, and does not copy it. The evidence gate is evaluated by the conductor from the envelope plus the *Evidence* section — one recovery re-invocation, counted in the run state, never decided by the model.

### Phase 5 — verify

| | |
|---|---|
| Worker invokes | in order, fail-fast: the slice's acceptance commands → `coding-review-simplify` → `full-review` → `browser-smoke` (pipeline mode) or the harness run check |
| Reads | the slice contract, `04-implement.report.md` |
| Writes | `05-verify.report.md` |
| Verdict | `pass` \| `fail` |
| Carries forward | Command output, the review summary, the applied fixes, and **every finding not applied** — that list is the input to phase 6's residual durability step |

One worker owns the whole chain, because the ordering is the point: `full-review` gates **final** code, so a mutating pass must not follow it. Splitting the chain across workers puts a barrier where the contract needs a sequence. A `fail` returns to phase 4 through `diagnose`, with the failure's report path in the new brief.

### Phase 6 — deliver

| | |
|---|---|
| Worker invokes | commit → `references/residual-findings.md` → `open-pr` (skipped in local-only mode) → `session-handoff` → `capture-learning` in headless mode when the run solved a non-obvious problem |
| Reads | `03-design-gate.report.md`, `04-implement.report.md`, `05-verify.report.md` — this is the one station that reads several, because the PR body is assembled from all of them |
| Writes | `06-deliver.report.md` |
| Verdict | `delivered` \| `local-only` \| `blocked` |
| Carries forward | The PR URL (or the local commits), the filed residual tickets, and the handoff note path |

Every side effect here gets its `side_effects` key written *before* the effect (`commit:<slice-id>`, `pr:<branch>`, `ticket:<finding-id>`), so a re-dispatched phase-6 worker skips what already landed instead of filing every residual twice.

### Phase 6b — resolve PR feedback

Dispatched only when review comments arrive, usually in a later session.

| | |
|---|---|
| Worker invokes | read `resolve-pr-feedback/SKILL.md` and follow it (entry-point skill — see rule 2 above) |
| Reads | `06-deliver.report.md` for the PR URL and the decision log |
| Writes | `06b-resolve-feedback.report.md` |
| Verdict | `resolved` \| `partial` |
| Carries forward | Which threads were fixed, which were answered with evidence, which need the human |

`resolve-pr-feedback` judges every thread centrally inside this worker and fans out only the approved fixes — do not split its judgment across workers, which is exactly what its own contract forbids.

## What the conductor keeps

After a full slice, the conductor's context holds five envelopes and nothing else from the stations. It opens a report body only to route a `revise` or `fail`, to assemble the final report, or to resolve a conflict between two stations' findings. Everything else is a path it can name without having read.
