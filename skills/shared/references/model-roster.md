# Model roster

This is the canonical seat to model mapping. Select roles from
[task-shaped-model-routing.md](task-shaped-model-routing.md), then resolve the
execution path from [host-model-execution.md](host-model-execution.md). A runner
is an external transport option, not the default for a model native to the host.

## Policy and evidence

The task choices use the user's quality-first policy supplied on 2026-09-08.
They are routing defaults, not a benchmark ranking verified by this repository.
Do not copy benchmark scores into run evidence. Local acceptance results can
justify a proposed change; they cannot change an already approved route.

`shared/scripts/discover_runners.py` checks external CLI presence. Native host
capabilities need a separate check. Neither check proves model account access.
An envelope separates `requested_model`, `configured_model`, and an observed
`effective_model`. Only `model_receipt.status: verified` with a native or provider
event identifies the serving model. A configured label is not a serving receipt.

A route with `model_verification: required` blocks without a matching receipt.
`allow_unverified` needs the authority defined by the calling workflow and must
be visible in its preview and report. Never turn a requested label, a wrapper
echo, or a model's self-description into a verified receipt.

## Seats

| Seat | External transport | Model | Task fit |
| --- | --- | --- | --- |
| astra | `codex-runner` | `gpt-6-astra` | General repository work, difficult implementation, TDD, diagnosis, parallel exploration, migration, and broad defect review. |
| fable | `claude-runner` | `claude-fable-5-1` | Deep research and synthesis, ambiguous user problems, one deep reasoning chain, architecture, and trade-off analysis. |
| opus | `claude-runner` | `claude-opus-5` | Independent precision review, subtle semantics, hard-code second opinion, documentation, and explanation. |
| sol | `codex-runner` | `gpt-5.6-sol` | Broad independent review and host-only fallback for normal or hard technical work. |
| terra | `codex-runner` | `gpt-5.6-terra` | Routine, well-specified functions at medium effort. |
| luna | `codex-runner` | `gpt-5.6-luna` | Trivial, isolated, pure functions with explicit acceptance at low effort. |
| sonnet | `claude-runner` | `claude-sonnet-5` | Routine function alternative at supported low or medium effort. |
| grok | `grok-runner` | `grok-4.6` | Optional independent execution-path and tool-flow perspective. |
| gemini | `gemini-runner` | `gemini-3.8-flash` | Optional wide cross-file perspective. This is not the restricted Cyber model. |
| kimi | `pi-runner --seat kimi` | `moonshotai/kimi-k3` | Optional long-context feasibility perspective. |
| glm | `pi-runner --seat glm` | `z-ai/glm-5.3-flash` | Optional boundary and failure-case perspective. |
| qwen | `pi-runner --seat qwen` | `qwen/qwen3.8-max` | Optional additional engineering perspective. |
| muse | `cline-runner --seat muse` | `meta/muse-spark-1.3` | Optional agent and tool-use perspective. |
| gemma | `pi-runner --seat gemma` | `google/gemma-4-31b-it` | Optional document-grounded perspective. |
| minimax | `cline-runner --seat minimax` | `minimax/minimax-m2.7` | Optional additional perspective. |

`codex` and `codex-code` remain legacy runner aliases. New plans name the
selected seat. A host may also expose Haiku or other models; discover its exact
identifier and controls before proposing a route. Family membership alone does
not make a model a default or prove access.

## Conditional security route

Gemini 3.8 Flash Cyber at `high` is the preferred specialized defensive-security
candidate from the supplied policy. This repository has no verified callable
identifier or account entitlement for it. Do not invent an ID, register ordinary
Gemini Flash as Cyber, or claim the Gemini runner selects it: that wrapper uses
the model configured in its host and cannot set effort.

Before proposing Cyber as available, obtain its exact identifier, access, model
selection, effort control, and tool limits from the active host or adapter. If
these cannot be established, propose Astra `max` or `ultra`, or Sol `ultra` under
the host-only constraint. Approval rules still apply to a changed route. Pair
defensive review with applicable static analysis, dependency and secret scans,
fuzzing or property tests, and manual reproduction of each claimed defect.

## Effort support

Task defaults are in the routing table. Quality comes first; do not reduce effort
just because the current host or a runner has a cheaper default. Effort labels
are provider-specific. `max`, `xhigh`, and `ultra` are not interchangeable, and
an effort label alone does not create or prove parallel workers.

Validate the exact model and transport before dispatch. Native APIs, installed
CLIs, and wrappers can expose different controls. A wrapper forwarding a flag
does not prove that the selected model supports it. Record runtime-controlled
effort as null; it cannot satisfy a promised exact effort.

1. The current native catalog lists Astra, Sol, and Terra through `ultra`, and
   Luna through `max`. Recheck the active host when making a run plan.
2. The Claude wrapper forwards `low`, `medium`, `high`, `xhigh`, and `max`.
   Verify the installed CLI and exact model accept the selected setting. If a
   host cannot set Opus `xhigh`, expose that limit and propose a supported
   alternative such as `max` before approval; do not silently translate it.
3. Grok's wrapper accepts at most `high`; approved routes must not rely on its
   direct-call effort clamp. Pi and Cline forward their selected controls, which
   still need validation against the actual provider model.
4. Gemini's current wrapper uses `effort_control: runtime` with null effort.
   Dcode cannot enforce an exact model and is not an approved implementation or
   review route.
