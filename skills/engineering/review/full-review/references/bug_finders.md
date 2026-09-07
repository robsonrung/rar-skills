# Bug finding lenses

Use one lens only when the approved review plan assigns the matching concern. This is a prompt guide, not a required panel.

| Concern | Inspect |
| --- | --- |
| Input boundary | Untrusted input, parsing, commands, paths, queries, and output encoding. |
| Access boundary | Authentication, authorization, tenancy, sessions, credentials, and privileged actions. |
| Logic and state | Branches, invariants, transitions, concurrency, retries, and partial failures. |
| Data and resources | Transactions, loss, exposure, bounds, cleanup, and resource ownership. |
| Contract and integration | Callers, public shapes, configuration, generated artifacts, external calls, and rollout order. |
| Performance | Hot paths, query shape, repeated remote work, paging, caching, and bounded memory. |

For each candidate, trace trigger, mechanism, impact, and the guard or caller that could refute it. Report only an evidence-backed finding with a path, line range, smallest useful fix, and verification. Do not report a hardening wish as a bug.
