---
name: grok-runner
description: Execute prompts using Grok CLI in headless print mode as the xAI seat (Grok 4.6). Use when users explicitly request Grok execution, when a multi-model workflow needs an xAI seat for provider diversity, or when a cross-runner workflow selects Grok as the preferred model.
---

# Grok Runner

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

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

## Integration

`agents/openai.yaml` exposes this skill as a native Codex-app subagent seat; do not remove it.
