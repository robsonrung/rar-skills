# Repository Configuration

The model roster is the source of truth for seat ids, current model ids, providers, and transports: `shared/references/model-roster.md`. The task-shaped routing reference selects recommended seats and effort. This skill never pins a model id in its prose or command examples.

Probe planned seats with `shared/scripts/discover_runners.py probe` before building the approval preview. Record the CLI path, version, availability, and blocker. A probe only establishes transport availability. A post-call label is a serving-model receipt only when it is native or provider-observed.

Use `.ai-workflow/consensus/` for persisted state, reports, and response artifacts. If it is not writable, use inline state and make the lack of a durable report visible in the preview.

Optional local configuration may exclude a seat or set a preference. It can narrow the recommended plan before the preview. It cannot select an unapproved route or replace a failed approved seat.

For `cmux`, verify socket access with `cmux ping` before the preview. Do not modify socket configuration. If `cmux` is unavailable, show a headless plan only when the user approves that changed transport.
