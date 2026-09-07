# Council Role Routing

Resolve current model ids, providers, and transports through `shared/references/model-roster.md`. This file selects seat aliases and effort only. Its result is a recommendation for the user approval preview, never a dispatch instruction.

Use `high` effort where the selected transport supports it. It is sufficient for bounded read-only work. Gemini uses `effort_control: runtime` and `effort: null`; state both values in every affected call. Do not raise to `xhigh` unless the user requests it or a completed, approved run shows that `high` was inadequate. A higher effort requires a revised preview.

When a headless wrapper supplies only a configured model label, set `serving_receipt: explicitly_allowed_unverified` in the preview and record `model_receipt: {status: unverified, source: configured_model, observed_model: null}` for that seat. This is the normal starting state for Astra and Fable through their wrappers. Use `status: verified` only after a native or provider event. An echoed `effective_model` value is not that receipt.

## Poll and debate

Choose the task shape before building the preview.

| Task shape | Opening seats | Organizer and synthesizer | Judges |
| --- | --- | --- | --- |
| Coding, systems, security, or tools | `astra`, `fable`, `grok`, all `high` | `astra`, `high` | `fable`, `high`; `grok`, `high` |
| Long-horizon coding or agent workflow | `astra`, `fable`, `qwen`, all `high` | `astra`, `high` | `fable`, `high`; `qwen`, `high` |
| Product, design, or large codebase | `fable`, `high`; `astra`, `high`; `gemini`, `effort: null`, `effort_control: runtime` | `fable`, `high` | `astra`, `high`; `gemini`, `effort: null`, `effort_control: runtime` |

The third opening seat and second judge provide a distinct-provider specialist view. Use `grok` for execution-path, tool, and system scrutiny. Use `qwen` for long-horizon coding and agent workflow scrutiny. Use `gemini` for wide cross-file, product, design, and large-codebase scrutiny. Its runner cannot enforce an effort setting, so its effort remains `null` with runtime control.

For a poll, the base plan is three openings, one organizer, two judges, and one synthesizer: seven calls. The organizer can open one gap-repair round: up to three additional calls, using the approved opening seats at their previewed efforts. Each actual call has one same-route validation retry. State `base: 7`, `conditional gap repair: 3`, and `hard maximum: 20` in the preview.

For a debate, use the approved opening seats in each approved round. The preview must list the fixed round ceiling, the moderator seat, every stance assignment from [stance-rotation-schedule.md](stance-rotation-schedule.md), the base call count, and the hard maximum after one same-route validation retry per planned call.

## Personas

Use one model for all five advisors, five reviewers, and the chairman. For a coding or systems question, recommend `astra`; for product, design, or large-codebase judgment, recommend `fable`. Advisors and chairman use `high`; reviewers use `medium`. The preview states whether peer review is included and lists the resulting base call count.

## Boundaries

An unavailable route is a blocker, not a selection rule. Report it and, if useful, recommend an alternate plan for the user to approve. Do not switch to another seat, change effort, or change mode after approval.

Record `requested_model`, `configured_model`, `effective_model`, and `model_receipt` in the run envelope. A verified observed model that differs from the approved requested model blocks the route, even when unverified serving receipts were allowed. A missing or unverified receipt cannot increase diversity confidence.
