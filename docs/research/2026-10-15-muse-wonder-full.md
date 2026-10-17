# Muse Wonder Full research and workflow proposal

Updated: 16 October 2026. External sources checked: 15 October 2026. Status: optional implementation worker with one completed pilot. No default route change.

Select Muse Wonder Full explicitly for bounded implementation with an approved contract, executable checks, and independent review. The pilot confirms that the native runner can implement, test, and repair a small task. It also shows why passing tests cannot replace independent review. Larger features, complex repairs, legacy refactors, and scientific code remain candidates for controlled comparisons. Neither the pilot nor the benchmarks establish a local quality, speed, or cost advantage.

A small live check on 15 October succeeded at `high` effort. The provider completion record identified `muse-wonder-full-1.0`, and the returned function passed five local behavior checks. The runner now reads that receipt. This confirms access and serving identity for that request; it does not establish subscription privacy or repository task quality. Subscription coverage was later confirmed by the user as recorded below. [Live evidence](2026-10-15-muse-wonder-full-live-test.json).

## Model and access

Meta released Wonder and Wonder Full on 12 October 2026. Full is a separate model, not Wonder with more reasoning. Full is available through Muse Code subscriptions. Standard Wonder is also available through the Model API. [Release announcement](https://about.fb.com/news/2026/10/introducing-muse-wonder-models/), [model documentation](https://dev.meta.ai/docs/models).

The published Full identifier is `muse-wonder-full-1.0`. Its context window is 1M tokens. Power Usage costs USD 50 per month and Maximum Usage costs USD 200 per month. Both include Full. Standard Wonder rates of USD 4 input and USD 20 output per million tokens do not price Full. [Meta model page](https://dev.meta.ai/models/muse-wonder).

## Benchmark observations, 15 October 2026

These are dated observations. Keep benchmark versions, reasoning effort, and execution tools with each result.

| Evaluation | Full | Standard Wonder | Interpretation and source |
| --- | ---: | ---: | --- |
| Intelligence Index v4.3.2 | 56, max | 52, max | Full's current model page lists rank 4 of 693. Rounded scores can hide ordering. [Full model page](https://artificialanalysis.ai/models/muse-wonder-full), [release analysis](https://artificialanalysis.ai/articles/muse-wonder) |
| Coding Agents Index | 68, max | 63, max | Evaluated in Muse Code. Sonnet 5.5 in its coding tool also scores 68; Opus 5.5 scores 66. This compares complete coding systems. [Evaluator analysis](https://artificialanalysis.ai/articles/muse-wonder) |
| SWE-Marathon v1.1, current owner board | 53.1%, max | 52.5%, max | Full ranks first, Wonder second, Sonnet 5.5 third at 51.3%. Eight trials per task across 20 tasks. [Owner leaderboard](https://www.swe-marathon.org/#leaderboard) |
| DeepSWE 1.1, Meta launch table | 79.0, max | 78.8, max | Opus 5.5 is 74.2. Meta attributes these three results to Datacurve. [Launch table](https://dev.meta.ai/models/muse-wonder), [model card, page 6](https://research.meta.ai/static/muse-wonder-model-card) |
| Terminal-Bench 4.0, Vals | 58.08% | 49.49% | Full is listed fifth, numerically tied with Fable 5.1. Opus 5.5 leads at 65.15%. Uses Mini-SWE-agent. [Evaluator leaderboard, updated 13 October](https://www.vals.ai/benchmarks/terminal-bench-4) |
| Terminal-Bench 4.0, Meta table using another evaluator | 57.1, max | 52.0, max | Opus 5.5 is 59.6; Astra is 59.1. Keep this separate from Vals. [Launch table](https://dev.meta.ai/models/muse-wonder) |
| ProgramBench, Meta launch table | 59.0, max | 50.0, max | Opus 5.5 leads the comparison at 70.5. [Launch table](https://dev.meta.ai/models/muse-wonder) |

Full also places first on CritPt at 33% and GDP.pdf at 33%, second on GDPval at 1857 Elo, and third on SciCode at 63%, Briefcase at 1729 Elo, and AutomationBench at 71%. The first place margins are small. The GDPval result overlaps the confidence intervals of Opus and Sonnet. Knowledge is weaker: Omniscience scores 30, versus Opus at 46. These are evaluator results, not proof of domain expertise on our tasks. [Evaluator analysis](https://artificialanalysis.ai/articles/muse-wonder).

## Evidence limits that change the recommendation

1. **The current Marathon result differs from the launch claim.** Meta reports Full at 57.5 with `xhigh`, versus Wonder at 53.1. The owner currently displays 53.1 and 52.5, both at `max`. Use the current owner board for the ranking. The reason for the difference is unconfirmed. Full's current advantage over Wonder is about 0.6 percentage points, or one additional successful trial out of 160. [Meta table](https://dev.meta.ai/models/muse-wonder), [owner board](https://www.swe-marathon.org/#leaderboard).
2. **Marathon compares different execution tools.** Meta explicitly states that its row is not a controlled comparison using one harness. The current board also identifies the tool for each model. A first place result supports the Muse Code plus Full combination. It does not isolate the model's contribution. [Model card, page 6](https://research.meta.ai/static/muse-wonder-model-card), [owner board](https://www.swe-marathon.org/#leaderboard).
3. **DeepSWE owner confirmation is incomplete.** Datacurve's public board is dated 22 September and contains no Wonder entries when checked. Its published common harness is Mini-SWE-agent. Describe 79.0 as a Datacurve result reported by Meta, not a directly confirmed current public leaderboard result. [Datacurve board](https://deepswe.datacurve.ai/), [model card, page 6](https://research.meta.ai/static/muse-wonder-model-card).
4. **Terminal scores are not interchangeable.** Vals and the evaluator used by Meta publish different results. Vals also displays a token cost for Full that cannot establish public subscription pricing. Meta and the Full model page confirm that Full lacks a public API price. [Vals board](https://www.vals.ai/benchmarks/terminal-bench-4), [Full model page](https://artificialanalysis.ai/models/muse-wonder-full).
5. **Memory and focus claims need local tests.** MemoryBench and FocusBench are internal Meta evaluations. They cannot prove persistence, recovery, or exact requirement recall in this runner. ProgramBench uses Mini-SWE-agent and tests program reconstruction against hidden behavioral tests. Its result does not support making Full our default for new programs. [Model card](https://research.meta.ai/static/muse-wonder-model-card).

## Pilot results, 16 October 2026

The pilot used one synthetic Python task: implement `unique(values)` for iterable inputs, preserve the first equal value and input order, and reject every unhashable entry. Eight fixed test methods failed against the initial stub. Full ran at `high` effort, using native file tools and sandboxed shell tests.

| Stage | Result |
| --- | --- |
| Initial implementation | Passed all eight original test methods. |
| Independent review | Astra found P2 R1: Python set lookup can accept a mutable set as equal to a stored frozenset. `unique([frozenset({1}), {1}])` did not raise the required `TypeError`. |
| Regression and repair | A separate check reproduced R1 without changing the original tests. Full added `hash(value)` before duplicate lookup. |
| Recheck and final gate | The same reviewer session accepted the repair. Fresh runs passed the eight original tests and the added regression. The review gate returned `ready`, with no open findings or failed checks. |

Both Full calls verified the serving identifier `muse-wonder-full-1.0`. Receipt coverage was complete for all 8 implementation steps and 10 repair steps. Astra was configured at `high` effort; its serving identity was unverified under explicit user approval for this pilot. That exception does not change the normal receipt requirements. [Pilot report](../../.ai-workflow/pilots/muse-full-20261016/report.json), [per-call receipts](../../.ai-workflow/pilots/muse-full-20261016/model-receipts.json), [final gate](../../.ai-workflow/pilots/muse-full-20261016/verify-review-after-final.stdout.json).

The four worker calls took 269.821 seconds in total. Execution wall time was 1126.101 seconds, including coordination and evidence capture, but excluding earlier preparation and approval wait. Full token usage and cost were unavailable. Reviewer usage records do not establish a combined or billed total. There was no comparison with the default implementer, so these figures show no speed or cost advantage.

The pilot changed no existing tracked source files. Full's repair used explicit context reconstruction because native sessions are not retained. This result confirms the implementation, review, regression, repair, and verification path for one small function. It does not validate sustained context retention, work across several modules, or domain expertise.

## When to select Full

Keep the current profile as the normal choice. Select Full only as an explicit implementer override when all these conditions hold:

1. The task has a bounded scope, an approved contract, and executable acceptance checks.
2. Design decisions and any required diagnosis are complete. Full can implement the agreed result without taking over those roles.
3. A different model remains responsible for review. Review findings require a repair and a reviewer recheck before acceptance.
4. The current account has the recorded subscription coverage, and every completed root model task supplies the required serving receipt. A missing receipt blocks the call without substitution.
5. Follow-up work can use explicit context reconstruction with a recorded recovery reason. The task does not require native persistent resume.

Use `high` for this optional route because it is the only effort tested locally. The pilot gives no local basis to prefer `xhigh` or `max`.

| Task | Selection guidance | Required boundary |
| --- | --- | --- |
| Bounded implementation or repair | Optional use when the conditions above hold | Keep the approved design, fixed checks, attempt budget, and independent reviewer. A repair starts from a proved cause. |
| Feature or API change across several files | Controlled comparison before wider use | Resolve compatibility, errors, authentication, and versioning first. The small pilot did not test this task class. |
| Legacy refactor and characterization tests | Controlled comparison | Review expected behavior independently and run existing tests. New tests alone cannot prove behavior is preserved. |
| Integration tests or scientific code | Controlled comparison with agreed expected results | Check numerical tolerances, parity, runtime, and integration behavior as applicable. No local result covers these tasks yet. |
| Migration code | Controlled comparison limited to implementation after design approval | Keep separate review of data invariants, concurrency, rollback, and recovery. |
| Diagnosis, architecture, security review, or visual design | Keep the current route | The optional Full seat is admitted only as an implementer. It does not replace a lead or reviewer. |

Keep simple lookups, mechanical edits, routine shell commands, and small test edits on the current route. The pilot shows that Full can complete a small task; it does not show a reason to replace the current route for those tasks.

## Runner and admission

`muse-runner` is the native CLI adapter. The optional `muse-wonder-full` implementation seat selects the exact Full model and requires a verified serving receipt. The existing `muse` seat still selects Spark 1.3 through Pi. Unavailable Full calls block without substitution. Profile defaults and the selected independent reviewer stay unchanged. [Current roster](../../skills/shared/model-routing.json), [execution and selection rules](../../skills/shared/references/task-shaped-model-routing.md).

**Account scoped admission was authorized on 16 October 2026.** The user confirmed that ZDR covers the current Muse Code subscription and requested Full as an optional implementation worker. The record is `user_confirmed`, not independent vendor verification or universal coverage. The repository requires a verified zero data retention provider before adding a seat. Standard mode prevents training use, but that alone does not prove zero retention. Muse Code subscriptions default to Contributor mode; turning it off applies to future content. Meta says Contributor mode is unavailable for accounts with ZDR, which indicates that such account arrangements exist. [Roster admission rule](../../skills/shared/references/model-roster.md#seat-admission), [Contributor mode policy](https://dev.meta.ai/help/subscriptions/muse-code-contributor-mode).

Meta's dedicated ZDR policy requires separate organization enablement, says support can vary by model, and describes coverage for direct API calls with an eligible organization key. It excludes personal account requests. Full's subscription route therefore needs explicit account and model coverage evidence. Do not infer coverage from a subscription, Standard mode, or local log settings. This is a verification gap, not proof that Full cannot support ZDR. [ZDR policy](https://dev.meta.ai/help/policies-and-privacy/zero-data-retention).

### Subscription privacy check, 15 October 2026

The local settings have `contributor_mode_enabled: false`. No ZDR approval or organization coverage field was found in the inspected settings and authentication metadata. The CLI reports no managed configuration, which describes local administration rather than provider retention. The browser reached an account chooser; authenticated subscription and organization settings were not verified. These observations do not establish whether Meta has enabled ZDR for this account.

Meta's terms dated 9 October apply Standard Services rules to subscriptions with Contributor mode disabled. Section 5.1 excludes training use, while section 4.4 still permits retention for service operation, compliance, and safety purposes. Subscription payment alone therefore does not establish ZDR. The subscription uses a dedicated harness credential; an organization's separate API arrangement cannot be assumed to cover that credential. [Terms, sections 3.2, 3.3, 4.4, and 5.1](https://dev.meta.ai/legal/terms-of-service), [subscription credential](https://dev.meta.ai/help/subscriptions/what-is-a-muse-code-subscription).

Decision on 15 October: admission was pending subscription coverage confirmation. This was superseded on 16 October by the user confirmation and explicit admission request. No support request was sent. The live test establishes model access and identity only. Public documentation has not independently confirmed this account arrangement. Other accounts require their own coverage evidence.

Select the optional worker with `python3 skills/shared/scripts/model_routing.py resolve routine-implementation --profile default --role implementer=muse-wonder-full:high`. The override changes only the implementer. Background execution supports sandboxed tests; Contributor mode stays off. Every completed root model task needs a matching serving receipt. Persistent resume is unsupported, so follow-up reconstruction requires an explicit recorded recovery reason.

## Next controlled comparisons

The six representative tasks remain proposed: two features across several files, two difficult repairs, one legacy refactor with characterization tests, and one scientific or integration test task. The completed function pilot does not count as this comparison. Compare the current approved implementer with Full on the same starting revision and acceptance cases. Use isolated copies and independent review. Reuse the same checks and total attempt limits.

Start with `high` to measure the locally tested route. A comparison at `max` can test the effort used by the cited independent benchmarks, but must be a separate experiment. Treat `xhigh` separately too. Record exact model and effort receipts, accepted tests, review findings, repair count, total wall time, and subscription usage where available. A missing usage figure stays unknown.

Expand Full's use only for task classes where it improves acceptance or reduces total correction work. Keep the current route when it provides the same accepted result with less time or usage. Six tasks can identify a promising use; they cannot prove general superiority. Defaults and independent review stay unchanged.
