---
name: gemini-runner
description: Execute an external Antigravity CLI (`agy`) prompt for a Gemini route. Use only for an explicit Gemini or Antigravity CLI request, a selected external route, or an approved fallback when native delegation cannot meet the route.
---

# Gemini Runner

Use `shared/references/model-preview.md` to choose the branch first. Deterministic checks need no model selection. Actual dispatch uses one concrete approved snapshot; nested calls consume it without re-resolution or extra workers.

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected Gemini model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_gemini.py" "<scoped prompt>" \
  --model <approved-model-id> --disable-fallback --json
```

Copy the selected model label, role, tool mode, receipt policy, and supported limits
from the snapshot. This runner has no effort flag or native effort control. A route
requiring unsupported control stays blocked. Nested calls use the saved options
without resolving defaults again. The example does not grant source sharing or
tool authority.

## Runtime boundaries

- Use the local authenticated Antigravity CLI, `agy`, in print mode.
- The user configures the model in agy. `--model` and output-format flags are request labels or prompt hints, not native model or format controls.
- Permission checks follow local configuration. Prompt and file context may be sent to the configured provider.
- Analysis roles use a read-only prompt overlay, not an enforced sandbox. Isolate the workspace for untrusted input; `--restrict-tools` alone is not a security boundary.
- Missing-CLI fallback is labelled and described in the runtime reference. Approved routes use `--disable-fallback`; an unverified model requires the caller's explicit receipt policy.
- Native output has no session ID. `--agy-continue` resumes the latest shared conversation and must not run concurrently against the same home.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
