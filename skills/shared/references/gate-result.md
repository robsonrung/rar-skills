# Canonical gate result

Use this contract for `design-gate`, selected lenses, and the task's Gates section. Merge scoped lens results without replacing finding IDs. This planning result is separate from final code review.

## Versioned record

New and revised unstarted task contracts contain exactly one fenced `gate-result` JSON block in `## Gates`. Use `schema_version: 1`. Keep the exact Markdown labels `Verdict:`, `Decision required:`, and `Security:` for the queue reader. The first two labels must match the record; serialize a null decision as `Decision required: none`. Other gate content lives in the JSON, without duplicate prose fields.

```gate-result
{
  "schema_version": 1,
  "verdict": "proceed",
  "lenses_run": [],
  "blocking_findings": [],
  "advisory_findings": [],
  "required_changes": [],
  "decision_required": null,
  "review_focus": []
}
```

| Field | Required content |
| --- | --- |
| `verdict` | `proceed` or `revise`; approval requires proceed, closed blockers and changes, and a null decision |
| `lenses_run` | Objects with `lens`, `risk`, and nonempty `evidence` locator arrays; `[]` when none apply |
| `blocking_findings` | All blocking findings, including closed entries and their evidence |
| `advisory_findings` | All advisory findings with stable IDs and dispositions |
| `required_changes` | Objects with `id`, `finding_id`, `summary`, `status` (`open` or `resolved`), and `resolution`; retain closed amendments |
| `decision_required` | Object with stable `id`, `question`, and `owner`, or `null` |
| `review_focus` | Array of nonempty risk, invariant, public contract, and decision or finding references |

Each finding has exactly `id`, `lens`, `summary`, `evidence` (a nonempty locator array), `status` (`open`, `resolved`, or `dismissed`), and `resolution`. Open entries use `resolution: null`. Resolved or dismissed entries need `resolution: {"reason": "...", "evidence": ["..."]}`. An approval label cannot supply closure evidence. Required changes use the same resolution shape and refer to an existing finding; a resolved change cannot point to an open finding.

IDs start with a letter and contain letters, numbers, dots, underscores, or hyphens. They are unique within the task and stable across rechecks, for example `T1-architecture-lens-F1` and `T1-C1`. Rechecks retain the ID and prior evidence, then add the disposition and its evidence. Lens-specific conclusions belong in findings or review focus.

## Approval readiness

The **acceptance contract** includes deterministic consistency: run `shared/scripts/gate_contract.py <task.md>` before approval. The queue calls `readiness_errors(task_text) -> list[str]` before promotion or dispatch. An empty list means this new-format check passed; the queue still owns task, legacy label, security, and approval checks. The helper rejects missing or unknown fields, duplicate JSON keys or IDs, malformed records, open blockers or changes, missing closure evidence, and inconsistent labels. It does not prove the cited evidence or grant approval.

Legacy tasks without new fields retain their existing reader, including the old `Required changes and resolved findings:` label. New `Blocking findings:`, `Advisory findings:`, `Required changes:`, or `Review focus:` fields require the versioned block. A malformed new record cannot fall back to legacy handling. Do not rewrite a started legacy contract to adopt this format.

Reference settled shared choices by decision ID and source-index locator. Each slice still classifies its design surface and security triggers. Changed scope, source revisions, or disputed choices require focused reassessment.
