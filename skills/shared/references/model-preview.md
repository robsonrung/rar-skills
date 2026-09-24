# Model preview

Use this contract once for every directly invoked executable skill. Resolve
`shared/` from the loaded shared library as [its entry](../SKILL.md) describes.
Nested skills reuse the parent's selected snapshot without another prompt or
unlisted workers. Preserve manual invocation rules and the separate explicit
council gate in `models-consensus`.

## Resolve the selection

1. Identify the actual current coordinator model and exposed effort. A preview
   cannot change it. Report unavailable identity or usage fields as unknown.
2. Select only the roles needed by the requested scope. Run existing tests,
   builds, checks, hashes, and status commands directly. For a skill with no
   worker, say **No additional model worker**; name the coordinator and the
   tools that will run. Do not create a worker merely to fill a preview row.
3. Before selection, apply explicit user instructions, then
   [local preview preferences](local-config.md), then central defaults.
   [`model-routing.json`](../model-routing.json) is the only maintained source
   of exact model and effort defaults. Updated workflow callers select the
   `saver` profile unless the user or local preference selects another.
   `economy` and `balanced` are selectable; existing explicit family routes
   remain valid.
   Resolve applicable routes with `model_routing.py resolve <route> --profile
   default`. Add `--local-profile <name>` for a validated local preference.
   An explicit `--profile saver`, `--profile economy`, or `--profile balanced`
   wins over that preference. Use `--role ROLE=SEAT[:EFFORT]` for explicit
   role changes;
   `runtime` selects null effort when supported. Without profile options,
   the CLI retains legacy family behavior, not the workflow default.
   A validated local `route_overrides` entry applies its per-route seat and
   effort changes here, at preview time only; it never changes an approved
   route.
4. Apply the route's risk conditions. Preserve strong planning, invariant,
   integration design, and risk review roles. A routine author implements
   settled cases; it cannot decide unresolved product policy. Resolve exact
   overrides before dispatch, without changing central defaults.
5. Keep profile preferences separate from role overrides. Use `--profile
   default` with the validated local preference when present; do not let a
   hardcoded Economy example override a selected local profile.
   Check [host capabilities](host-model-execution.md) and the selected runner
   without a paid model call. Record actual tool access, image support when
   needed, supported effort controls, role isolation, and receipt limits. For
   external Pi browser work, save `browser: {mechanism, preflight: {path, sha256}}` with
   captured readiness evidence.
   A candidate or installed command is not proof of a working route.

## Show one concrete preview

Show the actual coordinator separately, then one row per required worker:

| Scope and role | Exact model and effort | Execution and tools | Privacy and receipt | Fallback and limits |
| --- | --- | --- | --- | --- |
| Task or unit IDs and role | Resolved ID; selected level and control, or runtime controlled | Native host or runner, gateway, browser driver when needed, allowed tools and session isolation | Source sharing scope, request controls, provider restrictions, receipt policy and unverified limits | Exact approved alternate and trigger, or block; calls, attempts, time and concurrency |

State the selected profile, direct command work, total run ceilings, and any
missing capabilities. Separate model author, gateway, and observed inference
provider. For OpenRouter routes, show the selected `provider_routing` policy:
`gateway: openrouter`, `zdr: true`, `data_collection: deny`, and
`require_parameters: true`, plus `only` and `allow_fallbacks` when selected.
An inference provider preference is not an allowlist. Unknown account guardrails
stay unknown. These controls do not establish a browser service's privacy policy.

Show only the routes needed for the current request, including on the first
invocation. If the user names exact models and efforts, resolve those choices
and show their roles, transports, controls, and limits in this one preview.
Do not add unrelated task categories or a second model selection step.

Show the full routing table only when the user asks to inspect or change the
profile across task kinds. Persist requested per-route changes to
`.rar-skills/config.local.yaml` as `route_overrides` (see
[local-config.md](local-config.md)) only when the user asks to save them for
future work. A selection for the current task is not a request to change
future defaults. Saved changes never alter approved routes.

Offer **Keep defaults**, **Change selected roles**, or **Use another profile**.
A direct request to “use defaults and run” permits the unchanged resolved setup
within existing source sharing authority and accepted receipt limits. Show the
concrete setup and proceed. Reuse actual prior approval only when scope and all
selected controls still match. Preserve invocation authority that a skill
explicitly grants, such as `interview-me --auto`; do not add another gate.
Otherwise obtain one concrete selection before workers start, using the caller's
model plan decision when it has one. Silence is not approval. A skill with only
the current coordinator and direct commands can continue work already authorized
by its invocation; the preview does not create another approval gate.

An override received before dispatch wins. Save a replacement selection for
unresolved work and keep completed evidence intact. Keep the required separate
approval for a council, even when another skill used the same model.

## Execute the selected snapshot

Save exact routes, source sharing, provider controls, capabilities, tool policy,
effort control, fallback triggers, limits, and the decision reference in the
caller's existing plan. Bind them to its route digest where supported. Keep
**seat fidelity**: “This child uses the selected route and adds no worker.”
Dispatch, repair, fallback, and resume use that immutable snapshot. Do not reread
local preferences or regenerate an approved route from central defaults.

A missing model, unsupported effort, absent driver, receipt mismatch, or failed
privacy check blocks its affected route. Do not relax controls to continue.
Models without selectable effort must say runtime controlled and retain the
observed setting; never invent a shared effort level. Verify model specific
reasoning in the serialized request before using a new adapter path.

Use one initial attempt and one repair with changed input or new evidence before
considering a reasoning escalation. Only an exact selected fallback can run
without another decision. Preserve the workflow's total call and time ceilings;
recovery never resets them. Missing services, credentials, driver access, or
requirements need preparation or a decision, not a stronger model.

Show dated rates only when the selected endpoint supplies them. Distinguish
rates, estimates, and enforced spending caps. Record coordinator, worker,
reviewer, and failed attempt usage when available. Static checks and lower rates
do not prove equal quality or savings per accepted result.
