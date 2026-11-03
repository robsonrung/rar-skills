# Reviewer response contract

What an independent reviewer returns for a task review, a recheck, or a pre-PR review. Where the files live is in [work-state.md](work-state.md); how the reply crosses back is in [handoff-contract.md](handoff-contract.md). `full-review` answers in this contract when a caller supplies it.

## Inputs

The reviewer gets the task's `brief.md` (the acceptance contract), the base revision, the changed paths and diff, the captured files under the task's `evidence/`, the named risk, the conclusions of the methods used, and any earlier findings. It never sees the implementer's transcript. It stays read only: it changes no file and uses only its approved route.

The coordinator passes current evidence, checked with `shared/scripts/capture_check.py stale`. Treat a check that was not captured, or was reported stale, as missing. Read the source and the affected callers, not just the diff, and read the captured output itself. A passing command shows that the command passed; it does not show that the behavior is right or that the scope is complete.

## Response

```json
{
  "verdict": "changes required",
  "reviewed": {"base": "<ref>", "head": "<revision or tree hash>", "paths": ["src/auth/session.ts"]},
  "findings": [
    {"id": "R1", "severity": "P2", "status": "open", "path": "src/auth/session.ts",
     "line": 42, "evidence": "Expiry uses local time; evidence/unit.json shows the UTC case is untested."}
  ],
  "checks_relied_on": ["evidence/unit.json"],
  "summary": "One P2 blocks acceptance."
}
```

- `verdict` is `ready` or `changes required`.
- `reviewed` names the base, the revision reviewed, and every path covered. A path left out is not reviewed.
- Each finding has a stable `id`, a `severity`, a `status`, a `path` with a line where one applies, and `evidence`. Severity follows consequence: P0 to P3. A `full-review` finding maps CRITICAL to P0, HIGH to P1, MEDIUM to P2, and LOW to P3.
- `status` is `open`, `fixed`, `rejected`, `deferred`, or `disputed`.
- `checks_relied_on` lists only captured evidence files. Prose is not evidence.

`ready` requires no `open` or `disputed` finding and no deferred P0, P1, or P2. A deferred P3 needs a reason in its evidence. A P2 whose fix falls outside the scope stays P2 and goes to the user.

## Recheck

A recheck goes to the same reviewer context with the finding IDs and what changed. Return the same shape. Review the changed paths and their callers; say which earlier coverage still holds and why. Keep every earlier finding's ID, path, and severity. List a finding again only when its status changes; an omitted finding keeps its earlier status, open included. A recheck may raise new findings. When two reviewers report one defect, each keeps its own ID and closes its own finding.

## Who decides

The verdict is the reviewer's judgment, not the task status. The coordinator records the reply in the task's `report.md`, checks it against the captured evidence, and sets the status as work-state.md describes. No field in this response overrides those rules.
