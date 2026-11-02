# Review lenses

A lens is the question one seat answers. Give each seat one lens; when two seats see the same change, give them different lenses. A lens narrows attention, never reading: open callers, guards, and tests whenever they could confirm or refute a finding.

For every candidate, trace **trigger → mechanism → impact**, then look for the guard, caller, or test that would refute it. A finding that survives names its path, line range, smallest useful fix, and the check that proves it. A hardening wish is not a bug.

## Concerns

| Concern | Question |
| --- | --- |
| Specification | Does the change meet its acceptance contract, and only that? |
| Input boundary | Can untrusted input reach parsing, commands, paths, queries, or output unescaped? |
| Access boundary | Are authentication, authorization, tenancy, sessions, and credentials enforced before data access? |
| Logic and state | Do branches, invariants, transitions, concurrency, retries, and partial failures hold? |
| Data and resources | Are transactions, bounds, cleanup, and ownership safe against loss or exposure? |
| Contract and integration | Do callers, public shapes, config, generated artifacts, and rollout order still agree? |
| Performance | Does the change add unbounded work, repeated remote calls, or an invalid cache path? |
| Structure | Does it add complexity, unclear ownership, or a fragile boundary? See [structural.md](structural.md). |
| Tests | Do the tests prove the changed behavior and its important failure and boundary cases? |

## Seat lenses

### `logic_state`

Control-flow and state bugs a focused test would catch: swapped or inverted conditions, missing default cases and unhandled variants, transitions that skip a state or break an invariant, shared mutable state and lost wakeups, a failed step whose earlier side effects stay applied, swallowed errors and silent retries.

### `cross_file_consistency`

Ripples beyond the diff: signature changes with stale callers, removed exports still referenced, changed defaults, nil semantics, or ordering that callers depend on, type contract drift, tests that pass without covering the new path, generated files (schemas, stubs, fixtures) left stale. Read every touched file and its callers and callees.

### `security_runtime`

What an attacker, malformed input, or a flaky dependency can do: validation gaps on an untrusted boundary, weakened auth or tenancy, crypto misuse and secrets in logs or config, missing timeouts, idempotency, or limits, crash paths reachable from input. Each finding tells the story: who triggers it, how, and what they get.

### `precision_root_cause`

Challenge the plausible. Trace each symptom through mechanism to cause, which may sit in a caller, callee, or transition. Drop a finding that a guard, framework contract, test, or recovery path contradicts, and flag a fix that treats the symptom or reaches beyond the task. Every finding names its artifact of proof; an empty list beats an open chain.

### `structural_maintainability`

Apply [structural.md](structural.md). Every finding names a concrete simpler structure and the smallest safe refactor path.

### `broad_sweep`

Sweep the whole diff for an assigned category band (for example input and authorization, edge cases and resource bounds, regression and performance, execution and integration paths). Include boundary values the change forgets: empty, nil, maximum, negative, unicode. Return only the strongest findings in the band.

## Skeptic

For a CRITICAL or HIGH finding that one seat raised and execution could neither confirm nor refute, a deep review may send it to a skeptic: a different seat that did not raise it. Give the finding, its diff slice, and the surrounding source, without the originator's rationale:

```text
Try to refute this finding. Check whether the cited evidence is really there; whether a guard, middleware, flag, or framework behavior already handles it; whether the fix is worse than the code; whether the path is reachable.
Return {"refuted": true|false, "rationale": "...", "counter_evidence": ["..."]}.
```

`refuted: true` drops the finding. `refuted: false` keeps it, noting that an independent seat could not refute it. A skeptic that could not run leaves the original confidence and records the coverage limit. A skeptic adds evidence; a runnable reproduction outranks it.
