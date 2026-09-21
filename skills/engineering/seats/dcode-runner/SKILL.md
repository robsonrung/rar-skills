---
name: dcode-runner
description: Execute an external DeepAgents CLI (`dcode`) prompt with the user's configured model and credentials. Use only for an explicit dcode or DeepAgents CLI request. It is not an approved implementation or review route.
disable-model-invocation: true
---

# Dcode Runner

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_dcode.py" "<scoped prompt>" --json
```

An approved workflow supplies the exact model, effort, role, tool mode, and receipt policy. Pass those approved options and `--disable-fallback`; this basic example does not authorize a different route.

## Runtime boundaries

- Use only for an explicitly requested manual dcode run. This wrapper cannot bind an exact model and cannot be an approved implementation or review route.
- The user's existing model and credentials stay configured in dcode. `--model` is a metadata label and is not forwarded.
- Permission checks stay enabled unless an authorized call passes `--auto-approve`. Prompt and file context may be sent to the configured provider.
- Analysis roles use a read-only prompt overlay, not an enforced sandbox. Isolate the workspace for untrusted input; do not treat `--restrict-tools` as a security boundary.
- Direct calls have a labelled fallback chain when the CLI is missing. Do not attribute a fallback answer to dcode. Use `--disable-fallback` when the caller requires that seat.
- Native output has no session ID. Resuming the latest session uses shared state and must not run concurrently against the same home.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
