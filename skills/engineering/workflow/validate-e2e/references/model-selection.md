# Model selection and execution

Load `shared/references/host-model-execution.md` when selecting transport and `shared/references/task-shaped-model-routing.md` when resolving roles. Keep exact choices in the approved snapshot; do not place duplicate defaults in this file.

| Work | Central route | Dispatch rule |
| --- | --- | --- |
| Scope, requirement mapping, final evidence assessment | `validation-scope` | One bounded coordinator step; reuse valid planning |
| Unit, component, property tests; a deterministic browser test from agreed cases | `validation-unit` | Author only when tests are missing; review new assertions independently |
| API, database, queue, migration, integration; performance diagnosis | `validation-integration` | A strong role settles cases and invariants. Use the routine test author only after expected behavior is settled; execute with real required dependencies |
| Interactive browser journeys, visual state, accessibility interpretation | `validation-browser` | Worker must have the real browser tools; a text answer cannot prove navigation |
| Authorization, money, concurrency, data loss, complex root cause | `validation-risk` | Strong lead settles invariants before lower risk work is delegated |
| Bounded failure diagnosis and defect correction from a proven cause | `validation-diagnosis` | Escalate only an unresolved causal or safety question |
| Independent assessment of evidence and missing cases | `validation-review` | Distinct context; use a different configured model if it authored the assertions |
| Build, lint, types, existing unit/integration/load tests | No model route | Run the repository command directly; use a model only for a decision or failure |

Resolve the selected route without dispatch:

```bash
python3 "$SHARED_DIR/scripts/model_routing.py" resolve validation-unit --profile default
```

Add `--local-profile <name>` for the validated local preference or name an explicit
user profile. The central default is `economy`; `balanced` and explicit
legacy families remain selectable. Use `--risk high` for a risk trigger. The normal configuration is a recommendation, not evidence that a route is available on this host. Do not instantiate every role merely because it appears in the table. Reuse completed independent review. If a role is absent from a requested family, offer an exact custom route; do not infer an alternate.

Use `shared/references/model-preview.md` once. The preview has one row per required role: unit IDs, route ID, role, exact model, effort and control, runner/gateway, execution mode, host/transport, model and driver capabilities, tool access, provider privacy controls, receipt policy, exact fallback triggers, and per role call ceiling. Show total calls, command timeout, deadline, and maximum concurrency. Users can keep defaults, change selected rows, require one provider, select a CLI, or supply exact model IDs. These overrides belong to this run, not the global defaults.

A saved route includes `id`, `task_id`, `role`, `seat` if known, `model`, `effort`, `runner`, `provider`, `mode`, `transport`, `capability_source`, `model_verification`, and `unavailable: block`. Include observed supported efforts or runtime effort, `provider_routing`, capabilities, tool policy, exact fallback triggers, limits, relevant runner version, configuration digest, and actual user decision reference. An external Pi browser route also binds `browser: {mechanism, preflight: {path, sha256}}` with actual readiness evidence. Bind selected controls in the route digest. Do not reread local preferences after selection. Validate known selections with the central resolver. For a custom model, inspect the actual host or adapter catalog; unknown support is a blocker, not permission to clamp effort. Effort labels across providers are not equivalent.

Prefer exact native delegation when it supplies the required model, effort, tool access, isolated context, and receipt. If the host cannot dispatch a selected route, use its runner. An explicit user request for a runner takes precedence. A current coordinator can handle a role only if its exact route matches; otherwise record coordinator overhead separately. A preview cannot change the current host model by itself.

Load only the selected runner's skill and command reference:

| Runner | Control to verify |
| --- | --- |
| `claude-runner` | Explicit model and effort; persist the role session. Current print receipts do not prove serving identity. Disclose this and obtain `allow_unverified` if required. |
| `codex-runner` | Exact model/effort, session ID, scoped tools, provider receipt policy. Use only when the exact native path is unavailable or the CLI was requested. |
| `grok-runner` | Model receipt and effective effort. The adapter can clamp unsupported efforts; reject a changed effort in an approved run. |
| `pi-runner` | Pin gateway, model, serialized reasoning and provider privacy controls per call; use a unique persistent session file per role. Preflight browser commands, tool schemas, and typed image input in that external process. Host tools are not inherited. |
| `cline-runner` | Isolate provider state in a data directory or authenticated lane before selecting a model. |
| `gemini-runner` | Current runtime does not enforce exact model or effort. Accept only an explicitly approved runtime controlled route, or select another verified transport. Do not claim exact control. |
| Other installed runners | Inspect their actual skill and adapter. Availability alone does not prove exact routing, persistence, tools, or receipts. |

Pass `--disable-fallback` where supported for approved runner calls. Keep approval checks and permission enforcement enabled. Use the shared receipt contract and metrics normalizer. Match configured model, effective effort, actual context, and serving identity when required. A mismatch blocks acceptance even when useful output exists. Reconcile a lost or ambiguous completion before another dispatch.

For browser mechanism selection, use `browser-smoke`: reuse an established
Playwright Test suite directly, consider Playwright CLI with its skill for
exploration, and preflight agent-browser as an alternative. Select MCP only for
its required interface or page inspection; use native tools for authenticated
or native capabilities. Driver access and images must work in the selected
worker process before a business attempt.

A route change affects only unresolved work. Preserve completed receipts and counters. One user decision can approve an exact fallback and its trigger in advance; the fallback still consumes the original run budget. Do not silently map provider maximum effort to another provider's maximum.
