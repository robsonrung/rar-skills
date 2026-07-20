---
name: approval-gate
description: Merge-time approval gate for a pull request — deterministic safety gates first (deny-list categories, size ceiling, PR prerequisites), then a showstopper-only agent pass hunting production breakage, security holes, and undisclosed behavior; returns APPROVE, REFUSE, ESCALATE, or WAIT with an evidence bundle. Use when the user asks whether a PR can be auto-approved or stamped, to run the approval gate on a PR, or as pr-shepherd's final step. Do not use for spec-time threat modeling (security-gate) or for a findings-oriented review (full-review, review-swarm).
---

# Approval Gate

Decide whether a PR is safe to approve without a human — and refuse to decide when it is not automation's call. Determinism first, judgment last: file paths and PR state settle most PRs before any model reads the diff.

Two rules carry the skill; say them as you apply them:

- The **deny-list** names the categories automation must never approve — auth, crypto and secrets, migrations, infra and CI, billing, public API contracts, dependency manifests. Membership is decided by paths, not by reading the code. *"`billing/webhooks.py` is a deny-list hit — T2, escalating no matter how clean the diff looks."*
- The agent pass is **showstopper-only**: it hunts reasons the merge must not happen and stays silent about everything else. *"The naming is ugly, but this pass is showstopper-only — not my call to block on style."*

## Verdicts

| Verdict | Meaning | Next actor |
|---|---|---|
| `APPROVE` | Every gate passed; no showstopper found | Merge queue / author |
| `REFUSE` | A fixable problem blocks approval (red CI, conflict, showstopper in the diff) | Author fixes, re-run |
| `ESCALATE` | Not automation's call: deny-list hit, oversize, or a judgment-shaped showstopper | Human reviewer |
| `WAIT` | Someone or something is mid-flight (pending checks, a reviewer's 👀, an in-flight bot review) | Re-run later |
| `ERROR` | The gate itself failed (API error, missing tooling) | Re-run; report the failure |

## Phase 1 — Prerequisites

`gh pr view <n> --json isDraft,mergeable,reviewDecision,reviews,statusCheckRollup,labels,reactionGroups`, then, in order:

1. Draft PR → `REFUSE` (not submitted for approval).
2. Merge conflicts → `REFUSE`.
3. Any `CHANGES_REQUESTED` review state → `REFUSE` (a human already objected; automation never overrules them).
4. Required checks pending → `WAIT`; required checks failed → `REFUSE`.
5. A human 👀 reaction on the PR, or a known review bot still running → `WAIT` (someone is mid-review; polling again later is cheaper than a collision).

## Phase 2 — Hard gates

```bash
python3 .agents/skills/approval-gate/scripts/gate_check.py --git origin/<base> HEAD
```

When reviewing a PR without a local checkout, the same numbers come from the patch: `gh pr diff <n> | git apply --numstat | python3 .../gate_check.py --numstat-file -`. The script is the executable source of truth for patterns and ceilings; `references/deny-list.md` explains each category and how to extend them per repo with `--extra-deny`.

| Script result | Verdict |
|---|---|
| `tier: T2` (any deny-list hit) | `ESCALATE` — name every hit category and file |
| `tier: T1` with a `size:` blocker (>800 substantive lines or >30 substantive files) | `ESCALATE` — too large for a trustworthy automated pass |
| `tier: T0` (only excluded kinds changed — docs, tests, snapshots, assets) | `APPROVE` deterministically — no agent pass |
| `tier: T1` within size | Continue to Phase 3 |

The deny-list is evaluated on every changed path, including size-excluded ones — an auth test is still an auth change. Never argue a hit down: "the diff looks safe" does not override the deny-list.

## Phase 3 — Showstopper-only agent pass (T1 only)

Read-only pass (Read, Grep, Glob — no writes, no network) over the diff plus surrounding code. Check exactly:

1. **Production breakage** — changed signatures, routes, schemas, or configs whose callers/dependents were not updated; grep for the call sites.
2. **Security showstoppers in the diff** — injection, authz bypass, secret material, unsafe deserialization introduced by these hunks.
3. **Undisclosed behavior** — the diff does something sensitive the PR description does not mention (data writes, permission changes, network calls, telemetry). Mismatch between story and diff is itself a showstopper.
4. **Reviewer signals** — unresolved threads where a human raised a blocking concern that the diff does not address.
5. **Untested risky behavior** — changed behavior that is both consequential and entirely uncovered by tests.

Anything found: `REFUSE` when the author can fix it in this PR; `ESCALATE` when it needs human judgment. Nothing found: `APPROVE`. Style, refactors, nits: out of scope — showstopper-only.

## Evidence bundle

Always emit, whatever the verdict:

```json
{"pr": 0, "head_sha": "...", "verdict": "APPROVE|REFUSE|ESCALATE|WAIT|ERROR",
 "reason": "one sentence",
 "prerequisites": {"draft": false, "conflicts": false, "changes_requested": false,
                    "checks": "passing|pending|failing", "in_flight_review": false},
 "gate": {"tier": "T0|T1|T2", "blockers": [], "substantive_lines": 0,
           "substantive_files": 0, "denylist_hits": []},
 "showstoppers": [{"path": "...", "line": 0, "kind": "breakage|security|undisclosed|reviewer-signal|untested", "detail": "..."}]}
```

## Posting

Default is **report-only**: print the verdict and evidence bundle; post nothing.

With explicit caller opt-in (`post=true`):

- `APPROVE` → submit a real approving review (`gh pr review --approve --body`), body carrying the bot header and the evidence summary. Only when the repo's policy allows agent approvals. This skill never merges.
- `REFUSE` / `ESCALATE` / `WAIT` → upsert one sticky status comment marked `<!-- approval-gate-status -->` (same upsert mechanics as review-swarm's summary; include a run counter). Never post these as blocking review states — humans hold that channel.

Every posted body starts with:

```markdown
> [!NOTE]
> 🤖 Automated comment by **approval-gate** — not written by a human
```

## Gotchas

1. `WAIT` is retryable, `REFUSE` needs a new push, `ESCALATE` needs a human — never loop a `REFUSE` hoping for a different answer on the same sha.
2. T0 requires zero substantive files — one source line makes it T1. Lockfile churn does not count toward size but does trip the dependencies deny-list.
3. Deny-list false positives (a file merely named like billing) still escalate — over-escalation is the designed failure mode; tune with `--extra-deny` or repo policy, never by skipping the gate.
4. The Phase 3 pass inherits none of full-review's output ambitions: no findings list, no severity ladder, no suggestions. One question only — is there a reason this must not merge?
5. Without `gh` (local diff only), Phases 1 and 3's reviewer signals are unavailable: run Phase 2 + the diff-only showstopper checks and mark the verdict advisory (`ESCALATE` at best, never `APPROVE`).
6. Do not run this gate on your own uncommitted work to self-certify — it gates PRs, and the evidence bundle should name a real head sha.
