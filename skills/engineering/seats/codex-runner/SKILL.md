---
name: codex-runner
description: Execute an external Codex CLI prompt in non-interactive exec mode. Use only for an explicit Codex CLI request, a selected Astra, Sol, Terra, or Luna route unavailable as native host delegation, or an approved external fallback.
---

# Codex Runner

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected Astra, Sol, Terra, or Luna model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_codex.py" "<scoped prompt>" --json
```

An approved workflow supplies the exact model, effort, role, tool mode, and receipt policy. Pass those approved options and `--disable-fallback`; this basic example does not authorize a different route.

## Runtime boundaries

- Use the local authenticated `codex` CLI in exec mode. Analysis roles default to a read-only sandbox.
- `--allow-write`, an explicit sandbox, or `--full-auto` can change that boundary only within the caller's authority. Full auto requires approval for an unattended run.
- Prompt and file context may be sent to the configured provider. Set `--working-dir` to the task's repository or package.
- The wrapper forwards model and effort. Current headless output does not prove the serving model; a configured label alone gives an unverified receipt.
- Direct calls can fall back once to claude-runner when the CLI is missing. Approved routes disable fallback. Native resume cannot fall back to another runner.
- Read [references/prompting.md](references/prompting.md) only when a prompt needs clarification or an output contract needs design. It is optional guidance, not a required recipe.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
