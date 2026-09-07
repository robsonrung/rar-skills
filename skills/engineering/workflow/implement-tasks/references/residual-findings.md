# Residual review findings

Read when a review leaves actionable findings unapplied. Record them locally before delivery. A local record is durable without a commit or tracker ticket.

## Record

Write `residual-findings.md` beside the feature report. Each finding needs a stable ID, severity, affected path, evidence, impact, reason it was not applied, and next action. Distinguish accepted risk from work required for acceptance. A blocking finding keeps its task blocked.

Do not store the only copy in the conversation. Reference the record from the final report and an authorized PR when relevant. Keep the PR risk summary brief instead of copying the full list.

## Optional tracker filing

Create or update tickets only when authorized for the named project or tracker. Prepare the exact title and body first. Detect and probe the requested sink once when filing is needed; do not silently use a different tracker after a failure.

Each ticket states the defect, evidence, affected revision, next action, and finding ID. Use the shared prepare/execute/confirm rule to prevent duplicate filings. Record ticket URLs only after success.

If filing fails, keep the local record and report the failure. A tracker failure cannot erase the finding or block otherwise complete local work. Commit or push the record only when authorized.

## Return

Return the local record path, filed URLs, filing failures, and findings that still block acceptance. A ticket does not resolve a defect.
