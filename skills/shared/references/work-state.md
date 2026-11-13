# Work state

The one contract for a feature's files. `interview-me`, `to-prd`, `to-tasks`, `implement-tasks`, `implement-and-review`, `validate-e2e`, and `pre-pr-review` read and write them; each skill keeps only its own steps. Progress lives in **the ledger, not the transcript**: `tasks.md` plus the task reports are the ledger. What only the conversation holds is lost at a compaction or a restart.

## Layout

```
.ai-workflow/work/<feature>/
  decision-record.md     interview-me (an --auto run adds interview-auto/<run-id>/)
  prd.md                 to-prd
  tasks.md               to-tasks writes the queue; implement-tasks adds the model plan and keeps status
  T<N>-<slug>/
    brief.md             the task contract (to-tasks)
    report.md            the worker's report (implement-and-review)
    evidence/            captured command output
  validation/            validate-e2e: plan.md, report.md, evidence/
```

A standalone `implement-and-review` run uses the same layout under a slug of its own, with a one-row `tasks.md`.

## tasks.md

Top: `# Tasks: <feature>`, the PRD path, and the queue approval. Then, once approved, `## Model plan`:

- review mode, `task` or `feature`;
- for each task and role: model, effort, and host route;
- the integration or final reviewer, whose model differs from every author's;
- the concurrency cap, review-cycle limit, and call ceiling;
- the approval: the user's actual words or the host's message locator, and the time.

Then the queue:

| ID | Depends on | Files owned | Route and models | Status | Verdict |
| --- | --- | --- | --- | --- | --- |
| T1 | none | `src/auth/**` | routine-code, critical; implementer sonnet, reviewer sol | accepted | ready |

IDs are stable: a split gets a new ID, a deletion leaves a gap. Mark a feature-mode task `critical` in its route cell; every other task is deferred.

## Task folder

`brief.md` is the task contract: what to build, the acceptance contract (verified commands and observable behavior), gates (design verdict, open decision or none, security level and trigger, review focus), rollback, and owned paths. It changes only before approval; afterwards a scope change gets a new ID.

`report.md` follows the report sections in [handoff-contract.md](handoff-contract.md), leads with the task status, and lists every model call (role, requested model, and the model the host or CLI reported, or `not reported`) and the review cycle count.

`evidence/` holds captured output only.

## Rules

**Status** moves `draft` → `pending` (on queue approval) → `active` → `implemented` → `accepted`. Either exit, `blocked` (with the reason: failed checks, an unavailable route, or a decision only the user can make) or `ceiling_hit` (with the ceiling named), can follow `active` or `implemented`. These are the **three exits**: accepted, blocked, ceiling_hit. Update the row before dispatch and after each result. A worker's success label is a claim, not a status; you set the status from evidence.

**Release.** A dependent starts only when its dependency is `accepted`. In feature mode, `implemented` also releases it once the dependency's checks pass on the combined source. A blocked task blocks its descendants, not unrelated work.

**Evidence.** Only captured command output counts. Capture each check with `shared/scripts/capture_check.py run --out <task>/evidence/<check>.json -- <command>`. It records the command, cwd, git HEAD, a hash of the working tree, the exit code, and the output, and it never overwrites a file. Evidence is stale once the tree changes: `capture_check.py stale <files>` says which. Reuse it only while it is current and the contract and check definition are unchanged. Rerun a stale check; never edit evidence to make it current. A prose pass is not evidence.

**Ceilings.** Write the cycle or attempt count to the report before the attempt starts. At the ceiling, stop and record `ceiling_hit`: **the model never decides the retry**. A crash mid-attempt still counts.

**The approved plan is fixed.** Dispatch, repair, retry, and resume use it as written. Changing a model, effort, role, host route, or limit needs a new approval of the affected rows. An unavailable route blocks its tasks; never substitute another model.

**Approvals.** Record the user's actual words or the host's message locator, never a generated approval sentence. Silence, `--auto`, a saved preference, or task approval is not model approval. On resume a recorded approval is **already decided** while its scope still matches; do not ask again.

**Side effects.** Before an authorized commit, push, merge, or pull request, write it to `tasks.md` as pending; after it, record the result. On resume, inspect the repository before retrying a pending one.

## Feature mode

Under `review_mode: feature`, a `critical` task gets its own task review; its result stays `implemented`. A deferred task gets its focused checks only. Once every task is `implemented`, one combined cleanup pass, every required check on the final source, and one `full-review` by a reviewer independent of every author decide the feature. Only that review accepts the feature and moves its tasks to `accepted`. In task mode, each task's own review accepts it, and one `full-review` of the combined change still runs before delivery.

## Resume

Resume from these files, never from the transcript. Apply the **crash-resume test**: a fresh session that reads only these files must be able to continue without asking what happened. Read `tasks.md`, then the reports of active and implemented tasks. Restart each task at its recorded status with its counts intact. Check stale evidence before relying on it. Rebuild a lost role context only from that task's brief, report, and evidence, under the unchanged route.
