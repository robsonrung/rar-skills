# Incremental review coordination

Use after an initial structured review. Give the reviewer
[reviewer-response.md](reviewer-response.md) for the complete response contract,
including recheck, addendum, evidence packet, and conditional scope approval fields.
The coordinator uses [review-evidence.md](review-evidence.md) for capture and
verification commands.

Prepare a new snapshot with the latest review bound by `--previous-review`.
The reviewer must inspect the actual change and assess retained coverage and
evidence. File equality alone cannot establish semantic independence. A changed
acceptance contract requires a full review under the updated approved plan.

Before executing checks, use `select-checks` with the current snapshot in
`--snapshot`, the original capture snapshot in `--from-snapshot`, and original
result paths in `--checks`. For unchanged source and context, both snapshot
arguments refer to the same file. Execute `run` entries, keep validated
`reuse` references, and complete the assessment and `transfer-check` protocol for
transfer candidates. Unknown dependencies use whole source scope. Required fresh
checks always run. Retain raw failures and required failing regression evidence.
Unscoped observations require new captures after any source content change;
changed environment identity or declared observation inputs also require fresh
observations.

Use `response-contract` for current coverage, findings, observations, and any scope
approval. Prepare a complete evidence packet before dispatch. A complete packet
replaces prior checks and observations; inline updates merge with prior evidence.
Neither removes unresolved findings. Exported validation packets use the same
capture contract and still require independent coverage and findings. Generic
status files and historical prose cannot become captured evidence.

Confirmed persistent native rechecks use a compact continuation input after the
launcher validates context and accepted contract identity. Initial or reconstructed
reviewer contexts receive the full contract. Response format and input size are
separate: every expanded review must still cover the whole current snapshot.
A factual prose correction uses `addendum` only on unchanged source and requirements
and cannot change findings or evidence. It consumes a normal approved reviewer call.

The helper preserves the actual response and re-expands it against immutable prior
records. Never edit reviewer words to pass validation. For a common defect reported
by multiple reviewers, group finding IDs in one repair brief while retaining each
reviewer's independent resolution. Run the verifier before reporting completion.
