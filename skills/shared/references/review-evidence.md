# Review Evidence Contract

Use this contract for reusable task, integration, and PR review evidence. Resolve `shared/scripts/review_evidence.py` from the loaded collection.

The helper checks source identity, record integrity, declared coverage, command results, and readiness. Selecting a complete requirements plan, assessing review quality, resolving findings, and interpreting browser observations still require judgment. Local checksums detect changed records; they are not signatures against a writer who can replace all files.

## Prepare before review

Complete planned simplification first. Write a task contract and a requirements JSON file. Declare every required check and browser flow. Select exclusions before review. Empty lists are valid only when the task and repository require none.

```json
{
  "context": {
    "runtime": "Actual runtime version",
    "dependencies": "Actual installed dependency state",
    "external_state": "Relevant service or browser state, or none"
  },
  "checks": [
    {
      "id": "tests",
      "command": ["npm", "test"],
      "cwd": ".",
      "timeout_seconds": 900
    }
  ],
  "observations": [],
  "exclusions": {}
}
```

Replace these placeholders with actual facts and repository commands. Context is caller supplied. Refresh it before reuse. If runtime, installed dependencies, or external state cannot be confirmed, run fresh verification. A matching context file alone does not prove that a service is unchanged.

```bash
python3 <shared-dir>/scripts/review_evidence.py prepare \
  --root <git-worktree-root> --base <intended-base> \
  --contract <task-or-feature-contract> \
  --requirements <requirements.json> --output <new-evidence-directory>
```

For a recheck, add `--previous-review <prior-review.json>`. The task launcher
requires the latest recorded review for that track. For integration, pass the
latest record from each task; use task-specific finding IDs to avoid collisions.
Prior records are bound by checksum. The new response must retain their finding
IDs, paths, and severity, then state each resolution. Findings cannot disappear
or become less severe without an explicit rejected or fixed result.

Use absolute paths. The helper resolves the base to a commit. It hashes tracked and nonignored untracked files, executable modes, symbolic link targets, and the index. Coverage includes committed, staged, unstaged, deleted, renamed, and new paths. Renames use old and new paths.

Keep evidence outside the source tree. For launcher artifacts inside the worktree, pass `--artifact-dir <launcher-artifact-directory>` to exclude only that generated directory. It cannot contain tracked source. Never put task source files there. Non-Git directories, submodules, unresolved index conflicts, and symbolic links outside the source root return `blocked`.

The task contract is hashed separately. Its standalone status line can change; acceptance cannot. Requirements, context, and exclusions are frozen by hash. Ignored files and remote state are outside the source hash.

Keep other source writers stopped during preparation, checks, and review, or use
an isolated worktree. This is a source hash record, not a copied filesystem.
The helper compares captured and current state; it cannot detect an intermediate
edit that another process made and then reverted during review.

## Capture checks

```bash
python3 <shared-dir>/scripts/review_evidence.py run-check \
  --snapshot <evidence-directory>/snapshot.json --id tests
```

The helper executes the declared argument list without an implicit shell. It records exit code, duration, timeout, source changes, and hashes of stdout and stderr. A command that changes captured source cannot supply passing evidence for that snapshot. Run prerequisites that change source before preparation.

Each check runs once per evidence directory. A retry uses a new directory and preserves the failed result. Reference a prior captured check when its source hash, context hash, and complete command definition match. For identical content after a commit or worktree transfer, use the explicit `transfer-check` protocol below. The validator checks these bindings. A prose claim of a pass is insufficient.

New captures bind the original snapshot path and hash. Validation also checks the
original contract, requirements, command definition, and capture directory. Keep
the original result with its separate `stdout.log` and `stderr.log`; copying a
result into another bundle does not rebind it. Older direct captures remain valid
when their bundle snapshot supplies the same binding. Generic status reports
without these facts cannot become captured command records.

For browser observations, save actual driver output or screenshots and their SHA-256 hashes. The helper checks file integrity and the declared result; it does not execute or interpret browser actions. Missing or skipped required observations prevent readiness.

## Reviewer response

Give the independent reviewer the current snapshot path and file hash,
requirements, prior findings, check paths, and `response-contract` output.
The reviewer reads [reviewer-response.md](reviewer-response.md) for the exact
response fields, coverage and finding rules, packet substitution, scope approval,
rechecks, and prose corrections. Keep its response unchanged when recording it.

## Record and verify

For `implement-and-review`, use the launcher's `record-review`. It reads the completed native receipt or runner response, checks the approved route, validates the result, and records its path and checksum in the task manifest. Do not rewrite the reviewer's result before recording it.

For a standalone or integration review, save the actual execution envelope with `success: true` and the reviewer's complete JSON response in `agent_message`. Preserve host or runner metadata. Then run:

```bash
python3 <shared-dir>/scripts/review_evidence.py record \
  --snapshot <evidence-directory>/snapshot.json --execution <execution.json>
python3 <shared-dir>/scripts/review_evidence.py verify \
  --snapshot <evidence-directory>/snapshot.json --base <current-intended-base>
```

The generic recorder checks response identity and integrity. Model identity and context independence remain the caller's execution protocol; the task launcher checks its own route plan. Never construct a successful envelope from a failed or missing execution.

The verifier returns JSON and an exit code: 0 for `ready`, 1 for `needs-work`, and 2 for `blocked`. Preparation and recording can succeed before readiness is checked. Always verify before a completion decision.

Readiness requires complete coverage, passing required checks and observations, no open or disputed finding, and no deferred P0, P1, or P2. Deferred P3 findings need a reason in their evidence. There is no approval field to override these rules.

A changed source, index, intended base, contract, requirement, or evidence file blocks implicit reuse. An explicit transfer can reuse a captured check on identical content. The bounded carry forward protocol below can release task dependencies; it cannot establish final combined acceptance. The error lists changed source paths where available. Review affected paths and interactions, then create a new snapshot and result. Preserve old records. A reviewer can retain earlier coverage after assessing the effects of later changes; matching individual file hashes cannot prove semantic independence.

Legacy Markdown reports remain context. They cannot establish deterministic readiness without a current structured record. Human reports link to snapshots, review records, captured checks, and verifier output.

## Transfer checks after a commit or worktree change

The snapshot keeps its original source identity, including root, base, and index.
`content_id` separately hashes present file contents, executable modes, and symlink
targets. Deletions are represented by absence, so committing a deletion does not
change that content identity. Older snapshots remain readable.

Prepare a target snapshot. Capture fresh evidence of runtime, installed dependency
state, external state, and changed-base interactions. Save an assessment JSON with
`from_snapshot_sha256`, `to_source_id`, and four objects named `runtime`,
`dependencies`, `external_state`, and `base_interactions`. Each object needs a
nonempty `reason` and `evidence` list of absolute `path` and file `sha256` pairs.
A not-applicable external state still needs a recorded explanation. The reviewer
assesses these facts; a checksum does not prove that an environment is equivalent.

```bash
python3 <shared-dir>/scripts/review_evidence.py transfer-check \
  --from-snapshot <original-snapshot.json> --to-snapshot <target-snapshot.json> \
  --check <original-check/result.json> --assessment <transfer-assessment.json>
```

The helper rejects changed required inputs, contract, environment identity, command definitions,
failed checks, altered logs, and nested transfers. It writes a target check with
links to the original snapshot, result, and assessment. Use that path in the new
review. Transfer directly from the original check, not from a prior transfer.
Keep final combined acceptance and review of changed interactions. Check-specific input subsets require an unchanged explicit `inputs` declaration
from the original check. Otherwise use a fresh check when whole-content equality cannot be established.

## Evidence packet before dispatch

Run `response-contract --snapshot <snapshot.json>` before building the reviewer brief. It
returns the required checks, observations, fresh observation IDs, prior findings, and coverage paths.
Prepare a JSON observation list from actual driver captures. Each entry contains `id`, an observed
`result`, and absolute evidence paths. Existing `{path, sha256}` links are accepted only when correct.
Use `prepare-packet --snapshot <snapshot.json> --observations <observations.json> --output <packet.json>`.
An optional `--checks <checks.json>` maps check IDs to captured result files. Otherwise the helper
uses the snapshot's check directory. Preparation rejects missing entries and invalid hashes.
For sequential validation units, repeat `--id <declared-id>` to prepare a scoped
unit packet with only those checks and observations. It records that explicit
`scope` and validates every included ID. A scoped packet cannot establish review
readiness until the required unit packets are combined into a complete packet.
For the task launcher, pass `review --evidence-packet <packet.json>` to validate the packet before
reserving a review cycle. The launcher adds required response coverage to the bound review brief.

Pass the complete packet reference to the reviewer. Its substitution and
assessment rules are in [reviewer-response.md](reviewer-response.md). The helper
preserves the original response and rechecks every referenced capture.

## Structured context and scoped inputs

New requirements can use `context: {"version": 2, "identity": {"runtime": "...", "dependencies": "...",
"fixtures": "...", "services": "..."}, "notes": "Review explanation"}`. Identity values must represent
observed relevant state. Notes remain bound to their snapshot but do not change environment identity.
Legacy contexts keep their full comparison. An identity change requires fresh observations.

A check definition can include `inputs`, a nonempty list of relative captured file paths.
Declare the complete dependency set, including tests, scripts, lockfiles, configuration, and schema,
before the original check. Directories, symbolic links, and existing ignored files are rejected.
Use explicit captured files; deleted files can be tracked as absent. A transfer requires the same declaration and unchanged file identities,
command, contract, and environment identity, plus the existing transfer assessment. Without inputs,
whole-content equality remains required. A declaration is a scope decision, not an inferred proof
that omitted callers are independent. Unknown dependencies require the full scope.

Optional `observation_inputs` maps observation IDs to relative captured file paths. A change to a
listed file or the declaration requires a fresh observation. The reviewer still assesses semantic
effects on unlisted callers. This does not authorize reuse after a behavior change.

Without a complete observation input declaration, any source content change
requires fresh browser observations. Use the same observation shape in
validation, browser smoke tests, and review: `{id, result, evidence}` with
`pass`, `fail`, or `skipped` and nonempty `{path, sha256}` capture links. Runtime
commands remain declared checks, including when a browser suite runs them.

## Select affected checks

Run the selector before executing or transferring checks:

```bash
python3 <shared-dir>/scripts/review_evidence.py select-checks \
  --snapshot <current-snapshot.json> --from-snapshot <prior-snapshot.json> \
  --checks <original-check-paths.json> --fresh <required-fresh-check-id>
```

`--checks` is a JSON map of IDs to original captured result paths. Omit
`--from-snapshot` and `--checks` for an initial run. Repeat `--fresh` for required
fresh runs. A check definition can set `fresh: true` to enforce that requirement
for every consumer. The selector returns each ID, its declared inputs, changed
paths, and one action:

1. `run`: execute through `run-check`. This includes missing, failed, invalid,
   or changed evidence and required fresh checks.
2. `reuse`: reference the passing capture with matching source, requirements,
   contract, environment, and command.
3. `transfer`: unchanged declared inputs permit a candidate transfer. Capture
   the existing environment and base assessment, then use `transfer-check`.

Unknown dependencies use the whole captured source. The selector does not infer
dependencies from path names or turn an unaffected path into review approval.
Transfer still rejects failed commands, altered output, and changed identities.
Fresh checks cannot transfer. A fresh run uses a new snapshot directory.

## Bridge feature validation to review

New `validate-e2e` plans bind `review_snapshot: {path, sha256}` to the existing
shared requirements and snapshot artifacts. Required units account for every
shared check and observation ID. Reserve each attempt against a current snapshot,
execute commands through `run-check`, and capture browser observations in the
shape above. Finish with a bound evidence packet; declared unit statuses must
equal its captured command and browser outcomes. A unit can use a scoped packet
that covers its declared IDs, so sequential units can finish within the approved
parallel ceiling. The final bridge combines the completed required units into
one complete packet before independent review.

After all required units pass, export checked references:

```bash
python3 <validate-e2e-dir>/scripts/validation_control.py \
  --shared-dir <shared-dir> --state <run-state.json> \
  evidence-packet --output <validation-evidence-packet.json>
```

The bridge returns `snapshot` and `evidence_packet` links. It rechecks current
source, raw logs, scope, and capture hashes. All required units must bind one
current snapshot. A repair may reserve a new snapshot with the same approved
contract, root, base, and required scope; it retains consumed limits. Changed
environment facts belong in the new snapshot context. No extra mutable evidence
ledger or acceptance copy is needed.

Give the packet to the independent reviewer. Record its actual coverage,
findings, and response, then run `verify`. `pre-pr-review` reuses that structured
review only when the same verifier accepts current source and evidence. A unit
pass alone supplies no reviewer judgment. Historical generic validation data
remains context only; the bridge rejects it instead of adding missing identities
after the run.

## Carry forward task dependency release

Use this optional protocol only when the original reviewer can approve exact
prospective changes before its review. It keeps the **scope contract** explicit:
"The scope contract permits these exact notes because their content has no
runtime, build, configuration, schema, or public interface effect."
Path or hash equality alone does not prove semantic independence. Unknown
or incomplete dependencies keep whole source review. Legacy requirements remain
strict by default.

Before the original `prepare`, add `review_scope` to requirements:

```json
{
  "inputs": ["src/task.py", "tests/task_test.py", "requirements.lock"],
  "complete": true,
  "reason": "Complete dependency closure, including callers, configuration, schemas, runtime inputs, and shared boundaries; evidence and rationale for independence.",
  "changes": [
    {
      "path": "notes/session.txt",
      "content": {"path": "/absolute/prospective-session.txt", "sha256": "file hash"},
      "reason": "Why these exact bytes cannot affect the reviewed task or its acceptance."
    }
  ]
}
```

The example is the value of `review_scope`. Resolve actual dependency facts;
do not copy its claim of completeness. List the complete file dependency
closure, including declared check and observation inputs. Changes must be
outside that closure. The helper accepts 1 to 32 exact file changes with captured
prospective content. It accepts no globs, directories, symlinks, ignored source,
executable outputs, deletions, or evidence artifacts as changed paths. This is
not an exclusion list: the reviewer inspects each proposed content file and its
semantic effects. Relevant dependency, configuration, schema, runtime, public
or shared boundary changes require review, even if their paths differ.

`response-contract` returns the scope and its digest. The original reviewer
must supply `scope_approval` with that digest in its actual response. An
unsupported scope blocks carry forward. The requirements hash, snapshot hash,
review hash, and approved dispatch bind this decision before later changes.
No retrospective scope may be attached to an existing review.

After an approved change occurs:

1. Prepare a new target snapshot with the same contract, requirements file,
   artifact directory, source root, base commit, and index. Bind only the original
   review with `--previous-review`. Preserve original records and findings.
2. Capture current environment and base evidence in the same assessment shape
   used by `transfer-check`: original `from_snapshot_sha256`, target `to_source_id`,
   and evidence for runtime, dependencies, external state, and base interactions.
3. Run required fresh and affected checks. Existing check transfer rules still
   apply; unknown check dependencies require a fresh run after content changes.
   Prepare a complete target evidence packet. Capture fresh observations when
   their declared inputs or environment change, or when inputs are unknown.
4. Run `carry-forward` and store its returned `carry_forward` link in the
   task's existing integration evidence entry. Keep that entry's original
   `snapshot`, `base`, and `launch_manifest` bindings.

```bash
python3 <shared-dir>/scripts/review_evidence.py carry-forward \
  --from-snapshot <original-snapshot.json> --to-snapshot <current-snapshot.json> \
  --assessment <current-environment-assessment.json> --packet <current-packet.json> \
  --output <new-checkpoint.json>
```

The queue rechecks the checkpoint and all linked evidence on each projection.
Every source change must match one of the original exact prospective contents.
All other files, the full declared dependency closure, contract, requirements,
root, base, index, and environment identity remain bound. Missing or changed
capture files, failed checks or observations, unresolved original findings,
missing original reviewer dispatch, and pending calls still block release.
Budgets and ownership remain under the existing queue and ledger rules.

A checkpoint proves task dependency release only. It creates no reviewer
response and cannot pass normal `verify` for the target. Final feature completion
still needs an independent current combined review and acceptance evidence.
New changes outside the approved scope need ordinary integration review; never
widen an existing checkpoint or chain it as a new original review.

## Current batch integration review

Use a batch when ordinary later edits make several task reviews stale. This is
one new independent review of the current combined change. It can endorse 1 to
32 explicit task contracts in one call. The **acceptance contract** remains per
task: "This batch retains both acceptance contracts and checks their affected
interactions on the current source." Keep the exact carry forward path above for
its narrower case.

1. Prepare a current snapshot for each retained canonical task. Bind its prior
   task review with `--previous-review`. Keep its contract, all prior command
   definitions, and all observation IDs. Additional requirements are allowed.
   Use one current source root, resolved base, index, artifact directory, and
   observed environment identity for the batch. A new base or index is allowed
   because the new reviewer assesses that state.
2. Use `select-checks` for each current task snapshot. Run affected and explicitly
   fresh checks. Reuse direct captures only when the normal validator accepts
   their source, contract, requirements, environment, and command bindings.
   Transfer other eligible captures through `transfer-check`, with unchanged
   declared inputs and fresh environment and base evidence. A `fresh: true`
   check cannot transfer. Prepare each complete evidence packet.
3. Reuse browser observations only when declared inputs and environment remain
   valid against the latest endorsed task state. Verified review ancestry selects
   that state. Unscoped observations need fresh captures after any source content
   change. Changed inputs, declarations, or environment also need fresh captures.
   A reused result must equal that latest captured observation; an older capture
   cannot replace a later endorsement. `response-contract` reports each task's
   `observation_baseline` and `fresh_observations` reasons.
4. Capture an environment assessment with `to_source_id`, `context_id` from the
   current context identity digest, and the four evidence objects used by check
   transfer. Also include `configuration` and `schema` objects with the same
   `reason` and nonempty evidence list. Capture actual facts, including an
   explanation when a surface is absent. Review changed dependencies, runtime,
   configuration, schema, external state, and base interactions.
5. Add `batch` to the combined requirements. Its exact fields are `tasks`,
   `interactions`, and `environment`. `tasks` maps canonical task IDs to objects
   with `snapshot`, `prior_review`, and `evidence_packet` links. All links use
   absolute `path` and file `sha256`. `interactions` is a nonempty list of named
   affected interactions. `environment` links the assessment JSON. Use a full
   combined coverage scope with no exclusions. Unknown interactions require
   investigation before dispatch; a filename list cannot establish independence.
6. Prepare the batch snapshot against its own approved canonical integration
   contract. Pass every retained prior task review through `--previous-review`.
   Retain prior batch review records when repeating integration. Capture the
   batch contract's own checks and observations, then use `response-contract`
   and [reviewer-response.md](reviewer-response.md) for the full response.
7. Reserve one approved independent integration reviewer call with this batch
   snapshot. Its route must bind the batch contract and a separate scope ID.
   Record the actual response through the existing ledger completion path.
   Add the same `batch_review: {path, sha256}` snapshot link to each endorsed
   task's integration evidence entry. Keep the original task `snapshot`,
   `launch_manifest`, and reviewer bindings. Set `base` to the batch's intended
   current base. Use either `batch_review` or `carry_forward` in an entry.

The queue verifies every member against its canonical queue contract, both the
original task dispatch and the new batch dispatch, complete valid evidence,
prior findings, and the exact task set. It counts the batch as one call under
existing route and total budgets. Pending calls retain every member's ownership.
If a pending snapshot is missing or changed, ownership is unknown and scheduling
blocks until that call is reconciled. Other evidence failures affect only the
batch's tasks and their dependents. Never fabricate separate reviewer opinions
from one response.

A later source, base, index, contract, requirements, environment capture, or log
change invalidates the batch. Preserve every finding ID and severity, including
new findings on retained paths outside the new base diff. A later batch must bind
prior batch reviews. When a reviewed descendant resolves an earlier finding,
verified immutable ancestry selects that resolution while retaining its identity
and complete history. List order and timestamps have no authority. Conflicting
unrelated review branches block until explicitly reconciled, never omitted. This helper validates
captured facts and response identity. The approved execution protocol establishes
reviewer independence; environment equivalence and acceptance remain review judgments.

Batch dependency release alone is not final feature acceptance. A batch can also
serve as the final combined review only when its own approved contract and full
checks, observations, coverage, findings, and current intended base satisfy that
feature gate. Task endorsements cannot override a failed combined check.
