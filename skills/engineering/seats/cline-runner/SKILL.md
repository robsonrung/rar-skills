---
name: cline-runner
description: Execute an external Cline CLI prompt with structured output. Use only for an explicit Cline CLI request, a selected Cline provider route unavailable as native host delegation, or an approved external fallback, including Muse and Minimax seats.
---

# Cline Runner

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected provider model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_cline.py" "<scoped prompt>" --json
```

An approved workflow supplies the exact model, effort, role, tool mode, and receipt policy. Pass those approved options and `--disable-fallback`; this basic example does not authorize a different route.

## Runtime boundaries

- Use the local authenticated `cline` CLI. Select provider and model together; catalog IDs can differ across providers.
- Analysis roles default to enforced read-only plan mode with read tools enabled. `--no-tools` instead rejects all tool calls. Act mode permits writes and auto-approves tools within the caller's authority.
- Prompt and file context may be sent to the selected provider. `--model` mutates persisted provider configuration unless state is isolated with `--data-dir` or an authenticated lane.
- Concurrent calls require separate authenticated state directories and bounded credential-pool slots. A missing lane must not fall back to shared state.
- Named Muse and Minimax seats are selected with `--seat`. The runtime reference records their mappings and the files that must stay in sync.
- No provider fallback is allowed. The stream's serving-model receipt and terminal result determine the observed model and success.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
