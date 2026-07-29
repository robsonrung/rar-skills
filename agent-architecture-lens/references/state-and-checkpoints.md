# State and checkpoints

Read this when the design has cleared rung 1 or 2 of the escalation ladder and the question is what the state actually looks like.

## Designing the state

State replaces the hope that the model will remember what happened six steps ago. It is a declared structure, not an accumulating conversation.

Per field, decide four things:

1. **Type** — including whether the empty case is `null` or absent, since resume logic reads both.
2. **Default** — what a fresh run starts with, so the first step never branches on "has this been initialized".
3. **Writer** — which steps may write it. A field written by everything is a field nobody owns.
4. **Write rule** — what happens when two steps write it. Replace, append, merge, or max. Parallel branches make this mandatory rather than academic.

Prefer values the run computed and will need later (an id, an amount, a status, a count) over prose the model would have to re-read. A field whose only consumer is a prompt is usually still message history in disguise.

### Size

Keep individual fields small — roughly a few thousand tokens each is a workable ceiling. Anything larger belongs in an external store with only its id in state. Large payloads inline make every checkpoint write, every resume read, and every step boundary more expensive, for a value most steps never read.

Message history is the field that grows without anyone deciding to grow it. Bound it with a summarization step that fires on a token threshold, compacts the history, and replaces it. Without one, reasoning quality degrades slowly and the cost climbs the whole time.

## Checkpoint cadence

A checkpoint is a state snapshot written after a step completes. The cadence is a trade:

- **After every step** — the default. Resume granularity equals step granularity, and no completed work is repeated.
- **After expensive or side-effecting steps only** — acceptable when steps are cheap and idempotent, and repeating a few is cheaper than the writes.
- **Never** — only for runs where losing everything is acceptable, which is the same as saying signal 2 did not fire.

The ordering rule that matters: for a step with an external side effect, the record that the effect is about to happen is written **before** the effect, not after. A crash lands between them either way; writing first means the replay knows to skip, writing second means the replay repeats.

## Storage

- **In memory** — tests and short runs only. It is not a checkpoint if the process owns it.
- **A file on disk** — sufficient for single-machine runs, and readable by a human debugging a stuck run. This is what the skills in this repo use; see `_shared/references/run-state-contract.md`.
- **A database** — when runs are concurrent, distributed, or queried. Slower per write, but the trace is queryable, which is what an audit window actually needs.

## Lifecycle

Checkpoints accumulate. Unbounded checkpoint growth is a slow outage with a delayed fuse.

- Set an expiry on checkpoint keys.
- Purge completed runs past the audit window — decide that window explicitly rather than keeping everything.
- Keep failed and ceiling-hit runs longer than successful ones; they are the ones anybody reads.
- Give every run a unique id at creation. Reusing a fixed path across runs turns concurrent runs into one corrupted run.

## Resume

A resume protocol needs three things, and is incomplete without any of them:

1. **A run identifier** the caller can supply on restart.
2. **A status field with a defined set of values**, so "is this run finished" is a lookup rather than an inference. A protocol that branches on a status whose values are never enumerated has no authority.
3. **A rule for the partially-executed step** — re-run it (safe only if idempotent) or skip it (safe only if the completion was recorded before the crash).

Then prove it with the crash-resume test: kill the run mid-flight, restart it, assert it resumes at the right step with the right counters and does not repeat a side effect.
