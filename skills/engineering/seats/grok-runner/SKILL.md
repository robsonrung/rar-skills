---
name: grok-runner
description: Execute an external Grok CLI prompt in headless print mode. Use only for an explicit Grok CLI request, a selected Grok route unavailable as native host delegation, or an approved external fallback.
---

# Grok Runner

For a direct invocation, first use `shared/references/model-preview.md`. Nested calls reuse the parent's selected snapshot without another prompt or unlisted workers.

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected Grok model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_grok.py" "<scoped prompt>" --json
```

An approved workflow supplies the exact model, effort, role, tool mode, and receipt policy. Pass those approved options and `--disable-fallback`; this basic example does not authorize a different route.

## Runtime boundaries

- Use the local authenticated `grok` CLI in print mode. Analysis roles default to enforced read-only plan mode.
- `--restrict-tools` forces plan mode; `--allow-write` opts out within the caller's authority. Prompt and file context may be sent to the configured provider.
- Sessions persist under `~/.grok`; the native CLI has no persistence opt-out.
- The native `modelUsage` receipt identifies the serving model. Effort values unsupported by a direct call are clamped and reported; approved routes must satisfy their exact plan.
- No fallback is allowed. A missing CLI is an unavailable seat, never another model's answer.
- Structured output is checked locally after the native schema constraint. A zero exit code does not make malformed output successful.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
