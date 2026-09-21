# Model execution update proposal

Status: implemented in the repository on 20 September 2026. The sections below
retain the approved design and research context. See
[implementation validation](model-execution-validation.md) for completed checks
and remaining live validation. Installed skill copies outside this repository
were not updated.

Use GLM 5.3 Flash for implementation from an agreed plan, test authorship, and interactive browser checks. Run existing tests directly. Keep stronger models for unresolved design, independent review, and difficult failures.

This recommendation combines current repository inspection with public model and browser documentation. It is not a measured claim about local quality or savings.

## Proposed default setup

| Work | Proposed model or executor | Alternative and trigger |
| --- | --- | --- |
| Requirements, architecture, security invariants | Existing strong planning route | Preserve the selected planner; do not repeat completed planning |
| Bounded implementation and routine repairs | GLM 5.3 Flash High | DeepSeek V4.1 Flash as a selectable implementation alternative |
| Unit, integration, and E2E test authorship from agreed cases | GLM 5.3 Flash High | Luna High for unresolved test design or causal reasoning |
| Interactive browser exploration | GLM 5.3 Flash High with an explicitly available browser driver | MiMo V2.5 as a comparison candidate; Qwen 3.8 Flash only when the required privacy route becomes available |
| Existing tests, build, lint, type checks, evidence hashes | Repository commands | No separate model worker |
| Independent routine review | Luna High | Sol High for changes across components, transactions, or difficult findings |
| Security, money, concurrency, migrations, or ambiguous acceptance | Existing strong risk route | Settle the invariant first; delegate only the bounded routine work |
| Difficult repair after evidence shows a reasoning gap | Luna High, then the existing strong route if needed | Use only a fallback included in the selected plan |

MiMo V2.5 is a browser comparison candidate. Qwen 3.6 Plus and Kimi K2.7 Code are proposed selectable implementation alternatives that need new seats and preflight. The current public ZDR endpoint list has no entries for either Qwen candidate. A strict privacy profile must block those routes until an eligible endpoint is verified. Do not invoke all candidates for each task. A candidate list is not a sequence of mandatory calls.

Set GLM reasoning to `high` explicitly and verify the serialized setting through the selected adapter. The [publisher model card](https://huggingface.co/zai-org/GLM-5.3-Flash) accepts `low`, `high`, and `max`; an omitted or unrecognized value defaults to `max`. Thus a generic `medium` route can defeat the intended cost control. Benchmark Low later for simple browser work. High is a proposed balance, not a locally measured equivalent to published Max scores. For models without selectable effort, record runtime reasoning accurately instead of inventing a common effort level.

Use one initial attempt and one repair with new evidence before a reasoning escalation. An unavailable server, missing credential, broken browser driver, or unsettled product requirement is not a reason to spend more on a model. Preserve the existing total call and time ceilings across all attempts and fallbacks.

## One visible selection per invocation

Every directly invoked skill should show the models it will use. Resolve worker choices before dispatch. Nested skills reuse the selected setup. A skill that runs only repository commands should name the current coordinator and say that it starts no additional model worker.

Example preview:

```text
Profile: Economy
Coordinator: actual current host model
Implementation and test authoring: GLM 5.3 Flash High through Pi and OpenRouter
Browser exploration: GLM 5.3 Flash High with the selected browser driver
Independent review: Luna High
Difficult repair: Luna High within the same run budget
Existing tests: repository commands
OpenRouter privacy: ZDR required; data collection denied
Limits: resolved call, attempt, time, and concurrency ceilings

Use defaults | Change selected roles | Use another profile
```

Show exact model IDs, effort control, transport, browser capability, approved fallback triggers, and any receipt limit in the expanded plan. Show a dated token rate or cost estimate only when the selected endpoint supplies it. Distinguish a token rate, a forecast, and an enforced spending cap.

A direct request to use defaults and run permits the unchanged resolved setup. This intentionally aligns `implement-tasks` with the existing `validate-e2e` behavior; its current rule treats a default selection as insufficient. The updated rule must still show the concrete setup and respect source sharing and receipt limits already authorized by the user. Otherwise use the existing model plan decision. Reuse that decision for matching scope on resume and inside child skills. Never treat silence as a decision. New model choices apply only to unresolved work.

A saved preference selects a profile name. Keep maintained model IDs in the central catalogue. Before selection, precedence is explicit user instructions, then local preview preferences, then central defaults. After selection, the immutable run snapshot controls. A later explicit user change creates a replacement snapshot for unresolved rows; it cannot rewrite completed evidence.

A preview cannot change the current host model. Show its actual identity and cost separately. Foreign models need an executable runner route with their tools available in that process.

## Repository changes

| File or consumer | Required change |
| --- | --- |
| `skills/shared/model-routing.json` | Add an Economy selection and distinct candidate seats. Set GLM for bounded implementation and test work. Keep stronger risk routes. Maintain capabilities, source date, and provider policy here; copy the resolved policy into each approved route digest. |
| `skills/shared/scripts/model_routing.py` | Validate the Economy normal and risk routes, model specific effort, and image/tool requirements. Keep the legacy CLI default; updated workflow callers explicitly select Economy. |
| `skills/shared/references/task-shaped-model-routing.md` | Define one preview and override procedure, evidence based fallback triggers, and inherited selections for child skills. |
| `skills/shared/references/local-config.md` and its example | Permit a profile preference for previews. Keep credentials and duplicate model mappings out. |
| `skills/engineering/workflow/implement-tasks/references/model-plan.md` | Replace the strongest suitable model preference with the selected cost and risk policy. Keep scope, exact route, source sharing, independent review, and receipt checks. |
| `skills/engineering/engine/implement-and-review` | Carry provider controls and required tools into dispatch and resume. Include them in the approved route digest. |
| `skills/shared/references/implementation-routing-plan.schema.json` | Represent provider policy, model capabilities, runtime effort where applicable, and exact fallback controls. Preserve existing saved plans. |
| `skills/engineering/seats/pi-runner` | Enforce the approved request fields, tool policy, and per role session. Separate model author, gateway, and inference provider in reported evidence. |
| `skills/engineering/workflow/validate-e2e` | Select Economy routes; separate test authorship, direct execution, interactive exploration, and independent assessment. |
| `skills/extras/browser-smoke` | Select the browser mechanism by required capabilities and worker access. Preserve observed state, console/network evidence, save and reload checks, and failure artifacts. |
| Other directly invoked skills | Show the models they use through the same preview contract. A child invocation must not prompt again or add unlisted workers. |

The current catalogue already contains GLM 5.3 Flash. The current Qwen seat points to Qwen 3.8 Max, and Kimi points to Kimi K3. Add separate seats for the supplied alternatives instead of changing the meaning of an existing seat. Implementation and validation already have model previews; consolidate their behavior instead of adding another approval system.

The resolver currently defaults to the `gpt` family. Each normal route must have a matching family in its risk route. Adding an Economy entry to only the normal routes would leave high risk resolution incomplete. Reuse the present resolver structure where possible; a new routing engine is unnecessary.

Apply Economy to `routine-function`, `isolated-implementation`, `routine-implementation`, and `test-implementation` with GLM and an independent Luna reviewer. Add matching Economy mappings to `sensitive-implementation`. For validation, add explicit mappings for `validation-scope`, `validation-unit`, `validation-integration`, `validation-browser`, `validation-diagnosis`, and `validation-review`, with complete `validation-risk` and `validation-review-risk` targets. Preserve strong scope and integration design roles when they decide expected behavior. GLM authors integration tests only after those cases are settled. Keep strong risk mappings. Deterministic `test-execution` work bypasses model dispatch; use a diagnosis route only when a specific failure requires reasoning.

Keep independent review of the requirement, assertions, and changed code. Reuse valid earlier evidence and review only the missing scope. Preserve the existing source snapshot and readiness checks. A successful worker exit does not prove acceptance.

## Current candidate evidence

All six exact IDs below exist in the current [OpenRouter catalogue](https://openrouter.ai/api/v1/models). All list image input and tool support. Catalogue rates are USD per million tokens, before route specific differences.

| Exact model ID | Input | Output | Use in this proposal |
| --- | ---: | ---: | --- |
| `z-ai/glm-5.3-flash` | 0.09 | 0.30 | Default executor |
| `deepseek/deepseek-v4.1-flash` | 0.15 | 0.60 | Implementation alternative |
| `qwen/qwen3.8-flash` | 0.15 | 0.47 | Browser alternative awaiting a verified strict privacy route |
| `xiaomi/mimo-v2.5` | 0.14 | 0.28 | Browser comparison candidate |
| `qwen/qwen3.6-plus` | 0.325 | 1.95 | Optional implementation candidate; higher context tiers cost more |
| `moonshotai/kimi-k2.7-code` | 0.7062 | 3.21 | Optional implementation candidate |

The [public ZDR endpoint catalogue](https://openrouter.ai/api/v1/endpoints/zdr) lists GLM through DeepInfra at 0.075 input and 0.25 output, and Relace at 0.09 and 0.30. It also lists DeepSeek, MiMo, and Kimi routes. Neither Qwen candidate has an entry at inspection. These are dated endpoint observations, not proof that a particular account can execute the combined privacy and capability policy. The [GLM page](https://openrouter.ai/z-ai/glm-5.3-flash) identifies the lowest listed rates as promotional. Do not use a temporary discount as a permanent cost assumption.

## Provider policy and runner support

The request must carry at least:

```json
{
  "provider": {
    "zdr": true,
    "data_collection": "deny",
    "require_parameters": true
  }
}
```

Add `only` when the selected plan names exact inference providers. A provider preference order alone is not a provider allowlist. Provider fallback within an approved set and fallback to another model are separate decisions. Do not remove privacy constraints to recover availability. OpenRouter documents these controls in [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

Use account or key guardrails as a second enforcement point. Do not claim those settings exist without readback. ZDR applies to inference routing and does not establish the policy of browser services or other tools. OpenRouter also permits some in memory prompt caching under its ZDR definition. See [ZDR documentation](https://openrouter.ai/docs/guides/features/zdr).

The current Pi wrapper does not pass this policy. The implementation route schema also rejects additional fields, and the launcher does not forward provider policy. Source sharing metadata is not a request control. Add a typed provider policy field, include it in the route digest, and carry it through initial calls, repairs, and resume.

The wrapper's reported effective provider can be inferred from the model vendor prefix, which does not identify the inference host. The installed Pi 0.85.1 documentation supports `compat.openRouterRouting` and a `before_provider_request` hook. Use a run scoped configuration or explicit packaged extension while keeping unrelated extension discovery disabled. Do not depend on a mutable global model configuration to enforce an approved run.

Prove the serialized request locally before sending repository content: exact model, privacy fields, provider constraints, reasoning control, tool schemas, and image payloads. Record the request policy digest and provider evidence without logging source text or secrets. A client reported model label must not be described as independent proof of the inference host.

## Browser mechanism

| Mechanism | Recommended use | Reason and limit |
| --- | --- | --- |
| Playwright Test | Default for repeatable E2E acceptance, regression tests, and CI | Assertions, fixtures, isolated contexts, reports, and traces. Execute the suite without a model worker. |
| Raw Playwright library | Small scripts and integration with an existing harness | Useful building block. For a maintained test suite, prefer the test runner instead of rebuilding its fixtures and reporting. |
| Playwright CLI with its skill | First candidate for GLM controlled exploration, locator inspection, and test creation or repair | Official tooling with shell access and concise output. Distinct from the Playwright Test CLI command. |
| agent-browser | Supported alternative for model controlled exploration | Compact element references, snapshots, sessions, and diagnostic commands. Compare it with Playwright CLI on the same flows before claiming a cost advantage. |
| Playwright MCP | A workflow that needs its structured tool interface or rich page inspection | Official guidance identifies higher context cost than CLI use. Do not load it by default into every coding worker. |
| Native host browser tools | A flow that requires an existing authenticated session, a native dialog, or a host specific capability | Use only when the selected worker can access those tools. An external Pi process does not inherit them. |

Playwright documents its [test practices](https://playwright.dev/docs/best-practices), including isolated tests, resilient locators, web assertions, and trace based debugging. Its [CLI repository](https://github.com/microsoft/playwright-cli) and [MCP comparison](https://playwright.dev/mcp/introduction) explain the shell interface and context cost tradeoff. The [agent-browser repository](https://github.com/vercel-labs/agent-browser) documents the alternative interface. These sources establish features and design intent; they do not prove which wrapper gives the lowest cost per accepted task here.

Keep one driver per journey. Reuse the project stack when it meets the required evidence contract. Playwright Test is the default when a working suite exists or the task includes its setup. Browser smoke retains its no install rule; missing CLI support is a preparation gap, not permission to add a stack. If a different driver is needed, state the missing capability and select it before execution. Record the mechanism and readiness in the validation plan. Pin versions and give each parallel worker its own session and fixtures. Promote stable, important discovered flows into the existing test suite.

Use role, label, and stable test ID locators with automatic waits and observable assertions. Inspect the current accessibility state before choosing targets. Use screenshots for visual questions and failures. Verify state after save and reload. Retain console errors, relevant network failures, and traces according to the project test policy. A retry that passes does not erase the original failure or flakiness.

Give an external browser worker the selected driver's instructions and actual command access. The current Pi analysis mode enables file reads only, while its action mode grants broader tools. A browser route needs an explicit tool policy; changing only its model name cannot provide a browser. Browser test authority must not silently become product repair authority.

The proposed GLM browser route stays unavailable until this bridge passes preflight. For visual checks, the driver writes the screenshot to an artifact file; Pi's image capable reader must load it and send typed image content through the provider adapter. Validate that payload using a synthetic image and confirm the selected model registry permits image input. Sending a file path or screenshot description as plain text is insufficient. Keep screenshot artifacts and provider receipt limits in the evidence record.

## Validation before adoption

1. Test profile resolution, explicit overrides, high risk routing, missing models, unsupported effort, and compatibility with saved plans.
2. Test preview inheritance and ensure a child skill cannot add a hidden model or change its transport.
3. Capture synthetic local requests to verify Pi preserves privacy fields, tool calls, image content, usage, and model identity through initial calls and resume.
4. Check browser readiness from the external worker environment. Prove navigation, current state inspection, interaction, assertions, and evidence capture before a business test attempt.
5. Check that provider or driver failure never weakens privacy or marks a skipped test as passed.
6. Run a bounded comparison with three implementation tasks and three browser flows from the same revisions and acceptance cases. Include a form save and reload, an authorization denial, and an async failure. Compare GLM with the existing route. Compare another candidate only if a specific result needs it.
7. Record accepted outcomes, missed defects, review findings, repairs, total calls, input/cache/output tokens, elapsed time, and total cost. Include coordinator and reviewer work. No local comparison was run for this proposal.

The current machine has Pi installed. The `agent-browser` command exists, but its version command failed while attempting to change executable permissions. `playwright-cli` was not found on PATH. No browser setup was changed. These findings do not establish whether each target application already has a working Playwright Test suite.
