# Observed usage and dispatch budgets

Use this contract when a new plan has a usage budget, or when importing observed
usage into its existing run state. The budget gates the next dispatch. It does
not stop a running call. A running call can exceed the limit before its next
observation. Reconcile pending calls before evaluating the next dispatch.

## Bind an optional policy

A policy file contains one `usage_policy` object. Add that file to the new plan's
existing `scope.inputs` before approval. Its canonical content hash and the scope
digest bind the policy through the existing approval contract. No route digest
format changes. Legacy plans without this opt-in keep their existing call limits.

Example policy, with illustrative limits chosen by the plan owner:

```json
{
  "usage_policy": {
    "limits": {"input_tokens": 100000},
    "require_known": ["output_tokens"]
  }
}
```

Run initialization from the same repository root used to resolve relative scope
paths:

```bash
python3 <shared-dir>/scripts/run_state.py --state <state.json> init --plan <plan.json> --run-id <id> --limits <calls.json> --usage-policy <policy.json>
```

Initialization validates the approved scope digest and policy content. The ledger
stores the policy and its file hash. New reservations and budget queries validate
that binding again. Changing policy requires the owning approval process and a
new run. Keep bound files available. An existing ledger cannot acquire a policy
by retrying initialization.

`limits` accepts positive finite ceilings for `response_count`, `input_tokens`,
`cached_input_tokens`, `cache_write_input_tokens`, `output_tokens`,
`reasoning_output_tokens`, `duration_ms`, and `reported_cost_usd`. Each configured
ceiling requires known observations for that metric. `require_known` adds metrics
that must be known even without a ceiling. Reaching a ceiling blocks future
reservations. Recorded failed attempts consume the same measured usage as
successful attempts.

Choose a metric that the selected observation source reports. No fixed budget is
supplied. Token logs do not report provider cost or response count. A limit on
those fields blocks until a source reports them. Token counts are not converted
to currency. Subscription percentages are not converted to tokens or currency.

## Capture startup observations

A cold run has unknown coordinator usage. An empty ledger does not prove zero
usage. Capture an actual startup baseline before the run and import an observation
before the first budgeted reservation. A resumed context needs its actual
cumulative baseline. Zero is valid only when evidence establishes a fresh context
with no prior usage.

The saved token log adapter reads JSONL `event_msg` records with payload type
`token_count` and `info.total_token_usage`. It checks any `session_meta` context
ID. It reads cumulative input, cached input, output, reasoning output, and an
explicit response count when present. It does not copy message content. Repeated
totals count once. It uses total usage, never `last_token_usage`, because the
latter can repeat a response subtotal.

The baseline JSON binds these counters to the same source, context, and epoch:

```json
{
  "source_id": "local-account",
  "context_id": "actual-context-id",
  "epoch_id": "run-start-observation",
  "metrics": {
    "input_tokens": 12000,
    "cached_input_tokens": 8000,
    "output_tokens": 3000,
    "reasoning_output_tokens": 1800
  }
}
```

Snapshot metadata identifies the observation and its covered receipt records:

```json
{
  "source_id": "local-account",
  "context_id": "actual-context-id",
  "epoch_id": "run-start-observation",
  "scope": "coordinator",
  "sequence": 1,
  "covers": []
}
```

Import the saved log with the explicit baseline:

```bash
python3 <shared-dir>/scripts/run_state.py --state <state.json> usage-token-log --log <saved.jsonl> --metadata <metadata.json> --baseline <baseline.json>
```

Each measured value is the latest cumulative counter minus its baseline. Missing
baseline or counter fields remain unknown. The baseline hash stays fixed for an
epoch. A counter decrease, context mismatch, changed baseline, or malformed log
fails without changing state. A source reset requires a distinct observed epoch
with a valid new baseline and disjoint covered records. Use increasing sequences
for later observations in that epoch. Repeated imports at the same sequence must
have identical facts. This adapter reads saved data; the host still supplies the
correct log and baseline at each observation boundary.

## Import normalized snapshots

Use `usage-snapshot --snapshot <snapshot.json>` for another source that reports
cumulative metrics. The JSON has the same metadata above plus `metrics`, with
known fields from the metric list. An optional `observed_at` has an ISO 8601
timestamp with timezone. Null and absent metrics remain unknown. `response_count`
is an observed count of model responses within the invocation, including tool
turns. A role reservation alone does not establish that count.

Each snapshot identity is `(source_id, context_id, epoch_id)`. A later sequence
replaces its cumulative totals. It does not add them to the old totals. Known
counters must remain known and must not decrease. Receipt records in `covers`
are replaced by the snapshot, which prevents counting both the receipt and its
cumulative source total. Covered record IDs use these forms:

1. `worker:<call_id>` for a local reserved call.
2. `coordinator:<event_id>` for a captured coordinator receipt.
3. `stage:<stage>:<call_id>` for an imported worker call.
4. `stage:<stage>:coordinator:<event_id>` for an imported coordinator receipt.

Worker snapshots must cover recorded calls. The context must match every covered
record; a reported receipt source must also match. Coverage can grow but cannot
shrink. Overlapping snapshots and omitted receipts with the same source or
unbound source and matching context block admission. Each snapshot must cover
all receipt records included in its cumulative source total. Distinct epochs
must represent disjoint usage. A snapshot can cover a pending call after its
actual context is recorded. Its later receipt remains available for reconciliation.

Receipt reconciliation and coordinator capture store normalized usage and any
explicit `usage_identity: {source_id, context_id}`. Known execution context IDs
must agree. Stage imports retain worker receipts, coordinator receipts, nested
stage records, and cumulative snapshots. Equal receipt hashes count once.

Input totals include reported cache reads and writes. Cached and cache write
counts are subsets of input. Reasoning output is a subset of output; adding it
again would duplicate usage. `duration_ms` is the sum of reported invocation
durations. Parallel invocation durations are not workflow wall time. Only
provider reported currency cost belongs in `reported_cost_usd`.

## Keep subscription observations separate

An account snapshot describes shared account usage. It is not usage attributable
to this feature. Capture a saved account observation with:

```bash
python3 <shared-dir>/scripts/run_state.py --state <state.json> usage-subscription --snapshot <account-snapshot.json>
```

The file contains `source_id`, `window_id`, nonnegative integer `sequence`,
`used_percent`, `observed_at`, and `resets_at`. Percentage is in `[0, 100]` or
null. Timestamps need a timezone. The reset follows the observation. Identity
includes the source, window name, and reset time. Counters cannot decrease within
that window. A later reset is accepted only after the preceding window ends;
old window observations remain available.

To enforce a shared account ceiling, add this policy field:

```json
{
  "subscription_limits": [
    {
      "source_id": "shared-account",
      "window_id": "five-hour",
      "max_used_percent": 90,
      "max_age_seconds": 300
    }
  ]
}
```

These are illustrative thresholds. Admission requires a matching observation
within the configured maximum age and before its reset. Unknown, future, expired,
or stale observations block dispatch. A reached quota returns its observed reset
time as `resume_at`; obtain a fresh observation before resuming. Reset time alone
does not prove renewed capacity.

## Read results

```bash
python3 <shared-dir>/scripts/run_state.py --state <state.json> usage-status
```

`--dry-run` before an import validates it without writing. Normal imports use the
existing lock and atomic write. Usage queries do not write.

Python consumers use `summarize_usage(state)` and
`evaluate_budget(state, policy=None, now=None)`. Summary is pure. Evaluation with
an explicit policy is pure; the default validates the ledger's bound files.
`now` accepts a timezone aware datetime or ISO timestamp for deterministic quota
checks. Evaluation returns `decision`, `dispatch_allowed`, `reasons`, and
`resume_at`. Each reason has a stable `code` and relevant metric or window fields.

Summary reports each metric's `measured_sum`, `measured_records`,
`unknown_records`, and `total`. Total is null when any counted record is unknown.
It also reports worker and coordinator scopes, identity anomalies, and separate
subscription observations. Partial measured sums establish a lower bound only.
An exhausted measured sum blocks even when some records remain unknown. This
checks observed admission limits; it does not predict the next invocation's cost.
