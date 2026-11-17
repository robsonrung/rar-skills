# Report data contract

Use `schema_version: 1` and `kind: "plan"` or `"implementation"`. The bundled Python renderer produces a complete offline HTML report and a complete Markdown report from one JSON input. It does not inspect the repository or establish the truth of claims. Gather evidence before creating the input.

## Required report identity

Supply nonempty strings for `report_id`, `title`, `generated_at`, and `revision`. Use an ISO timestamp for `generated_at`. Supply `subtitle` as a string when useful. Set `snapshot` to an object with nonempty string fields `repository`, `base`, `head`, `worktree`, and `scope`, plus `limitations` as a list of strings. Record an explicit unknown for unavailable values. Do not invent a commit, clean working tree, observation or date.

Supply `summary` with nonempty strings `problem`, `impact`, `solution`, `why`, `scope`, and `out_of_scope`. Supply top level `risks` and `questions` as lists of strings. Material risks and every check that has not passed appear in the overview.

For demonstration data, start `snapshot.repository` with `Illustrative`. This renders a conspicuous example badge. Demonstrations must not be presented as findings from an actual repository.

## Linked entities

Every entity in `decisions`, `areas`, `checks`, `evidence`, `execution`, `deviations`, and `requirements` has a unique `id`. Start with a letter and use only letters, numbers and underscores. Prefer stable IDs such as `D001`, `A001`, `C001`, `E001`, `S001`, `V001`, and `R001`. IDs must also be unique ignoring letter case, to preserve Markdown links. Preserve these IDs across report revisions so feedback remains understandable. Section names such as `overview` and `checks` are reserved.

All fields listed below are strings unless marked otherwise. Include the field with an explicit explanation of uncertainty when the information is unavailable. Empty strings are acceptable for inapplicable entity fields, but do not omit material limits.

1. `decisions`: `id`, `title`, `status`, `context`, `choice`, `rationale`, `revisit_when`, `tradeoffs` as string list, `areas` as area ID list, `evidence` as evidence ID list. `alternatives` is a list of objects with `option`, `benefit`, `cost`, `rejected_because`. `precedents` is a list of objects with `path`, `symbol`, `reason`, `difference`, `evidence` as evidence ID list. Include a real baseline alternative when relevant.
2. `areas`: `id`, `name`, `path`, `symbol`, `change_type`, `why`, `before`, `after`, `risk`, `decisions` as decision ID list, `evidence` as evidence ID list. Optional fields are `details` as a string list, `diff`, and `diff_status`. State whether a diff is an actual excerpt, illustrative pseudocode, or a complete change. An area can represent a symbol, file or tightly related set, but coverage accounting uses exact `path` values.
3. `checks`: `id`, `criterion`, `method`, `status`, `command`, `environment`, `result`, `limitations`, and `evidence` as evidence ID list. `method` is one of `test`, `static`, `manual`, `review`, `formal`. `status` is one of `planned`, `passed`, `failed`, `blocked`, `not_run`. A passed check must record an actual result and at least one observed evidence item. A test passing is not a formal proof. For planned checks, put the expected result in `result` and say that execution has not occurred in `limitations`. Optional `exit_code` is an integer or null, `executed_at` is a timestamp string, and `revision` is a string. A passed check cannot have a nonzero exit code. The renderer warns when a check or its observed evidence records a different revision from the report head. Baseline comparisons are allowed, but explain why the different revision is relevant.
4. `evidence`: `id`, `label`, `type`, `status`, `location`, `revision`, `excerpt`, `limitations`. `status` is one of `observed`, `inferred`, `proposed`, `unknown`. Optional `url` must be an absolute HTTPS URL. Record exact repository paths and symbols or command log identifiers in `location`. Pin source observations to the inspected revision.
5. `execution`: `id`, `title`, `detail`, `depends_on` as execution ID list, and `checks` as check ID list. Use this only when sequencing helps explain delivery.
6. `deviations`: `id`, `decision`, `planned`, `actual`, `reason`, `consequence`, and `evidence` as evidence ID list. `decision` is an existing decision ID or an empty string when no decision links. The implementation report presents these separately from design decisions.
7. `requirements`: `id`, `text`, `status`, `areas` as area ID list, `checks` as check ID list, and `evidence` as evidence ID list. `status` is one of `proposed`, `met`, `unmet`, `unknown`. Unmet and unknown requirements remain visible in the overview. A status is supplied by the report author; the renderer does not infer that a requirement is met from a test count. Record the criteria and evidence needed to justify that conclusion.

Entity collections can be empty. Missing optional collections become empty collections. Unknown extra fields do not prevent rendering, but are not displayed automatically. Do not put material information only in an unknown field.

## Architecture

Optionally supply `architecture.before` and `architecture.after`. Each contains `title`, `nodes` and `edges`. Each node has `id`, `label`, `detail`, and `target`. Node IDs are unique inside their graph. `target` identifies an existing report entity or section, optionally prefixed by `#`. Each edge has `from`, `to`, and `label`, referencing nodes within that graph. The renderer draws the actual directed relationships, links nodes to their explanations, and provides a textual relationship list. Keep graphs small and split concepts by responsibility. Long labels and every detail remain available in the component list and text export.

## Delivery and completeness

For an implementation report with a plan baseline, supply optional `plan` with string fields `report_id`, `revision`, `sha256`, and `status`. This identity appears in the header and overview, above the plan reconciliation. Record the exact plan content hash when available and an explicit unknown otherwise. State whether the baseline was approved, proposed, or unavailable only when the source evidence establishes that state. Reader notes do not constitute approval.

Optionally supply `rollout` with `strategy`, `rollback`, `observability`, and `data_compatibility` strings. Record actual operational limits, including migrations that cannot be undone merely by reverting application code.

Supply `coverage` for implementation reports: `changed_paths` as a list of exact paths, `excluded` as a list of objects with `path` and nonempty `reason`, and `unexplained` as a list of paths. Every changed path must either match an area `path`, have a justified exclusion, or remain visibly unexplained. The renderer derives coverage from these records; a path omitted from explanations is never silently counted as explained. An absent manifest is shown as an inability to assess completeness.

Optionally supply `sources` as a list of objects with `title`, `url`, and `note`. Only absolute HTTPS links are accepted, as the shared page guard requires. External documentation is background, not proof of local implementation.

## Run

```bash
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/render_report.py" report.json --validate-only
SHARED_DIR="<absolute path of the shared skill directory>"; python3 "$SHARED_DIR/explain-report/scripts/render_report.py" report.json --html report.html --markdown report.md
```

`validate_report(data)` returns a list of errors without reading files. An empty list indicates schema and reference validity only. The command exits with status 2 on invalid input. HTML content, code excerpts, labels and metadata are escaped, and the report has no external runtime dependencies or network calls.

## Reader interaction

The HTML report supports deep links, details, search, theme switching, full report printing and local decision notes. Notes can be copied or downloaded as text with report identity and snapshot. A note is never an approval or an instruction that executes itself. Local browser storage may be unavailable in a preview; export notes before closing. All main report text and diagrams exist in the HTML before JavaScript runs, and Markdown contains the same substantive content. Browser print behavior depends on the viewer. Inspect generated print output before treating a PDF as a final deliverable.
