---
name: dcode-runner
description: Execute prompts using DeepAgents CLI (`dcode`) non-interactive mode with the user's already-configured model and credentials. Use only when the user explicitly requests dcode or DeepAgents execution. It is not an approved implementation or review route.
disable-model-invocation: true
---

# Dcode Runner

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

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

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
