# Canonical gate result

Use this schema for `design-gate`, its selected lenses, and the task's Gates section. A lens returns its scoped result. The gate merges results without replacing finding IDs. This planning result is separate from the final code review schema.

| Field | Required content |
| --- | --- |
| `verdict` | `proceed` or `revise`; proceed requires no open blocking finding and `decision_required: none` |
| `lenses_run` | Lens names, the decision or risk each checked, and evidence or reused decision references; `[]` when none apply |
| `blocking_findings` | Findings that block approval, including resolved entries with their history |
| `advisory_findings` | Findings that do not block approval; retain their IDs and dispositions |
| `required_changes` | Open amendments linked to finding IDs; `[]` when none remain |
| `decision_required` | Unresolved question, owner, and decision ID, or `none` |
| `review_focus` | Risks, invariants, public contracts, and decision or finding IDs for implementation and final review |

Each finding has `id`, `lens`, `summary`, `evidence` (source or decision locators), `status` (`open`, `resolved`, or `dismissed`), and `resolution` (evidence and reason, or `none` while open). IDs are stable within the feature, for example `T1-architecture-lens-F1`. A recheck updates status and evidence under the same ID. A dismissal requires evidence; an approval label alone cannot close a finding. Lens-specific conclusions, such as fired signals or conceptual integrity, belong in the finding or review focus rather than a competing result schema.

Reference settled shared choices by decision ID and source-index locator. Each slice still classifies its own design surface and security triggers. A changed scope, source revision, or disputed choice requires a focused reassessment.
