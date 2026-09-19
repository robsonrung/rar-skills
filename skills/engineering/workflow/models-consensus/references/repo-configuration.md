# Repository Configuration

The single source for seat IDs, model IDs, effort support, and role defaults is `shared/model-routing.json`. The task routing reference explains how to select and verify a route. `shared/references/host-model-execution.md` selects native delegation before an external runner. This skill never pins a model id in its prose or command examples.

Check the active host for exact native model selection, effort, isolation, read-only controls, result collection, and per-role resume before probing an external runner. Probe a runner with `shared/scripts/discover_runners.py probe` only when the native route cannot meet the approved plan. Record the host or CLI path, version when applicable, execution path, availability, session-resume support, and blocker. A check only establishes route availability. A post-call label is a serving-model receipt only when it is native or provider-observed.

Use `.ai-workflow/consensus/` for persisted state, reports, and response artifacts. If it is not writable, use inline state and make the lack of a durable report visible in the preview.

Optional local configuration may exclude a seat or set a preference. It can narrow the recommended route before the preview, but a poll or debate still needs three distinct requested-model opening seats. It cannot select an unapproved route or replace a failed approved seat.

For `cmux`, verify socket access with `cmux ping` before the preview. Do not modify socket configuration. If `cmux` is unavailable, show a headless plan only when the user approves that changed transport.
