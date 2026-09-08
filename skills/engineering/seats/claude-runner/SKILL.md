---
name: claude-runner
description: Execute an external Claude CLI prompt in headless print mode. Use only for an explicit Claude CLI request, a selected Claude route unavailable as native host delegation, or an approved external fallback.
---

# Claude Runner

Execute the caller's scoped prompt through the local CLI. Shared roles, envelope keys, and result handling live in `shared/references/runner-common.md`. Preserve **seat fidelity**: name the provider that actually answered, and report unavailable or unverified seats honestly.

## Native routing

Read `shared/references/host-model-execution.md` before choosing an external route. If the current host can dispatch the exact selected Claude model with the required effort, isolation, and receipt policy in a native subagent or task thread, use that route. `agents/openai.yaml` is host UI metadata; it does not dispatch a native model.

## Invocation

Set `SKILL_DIR` to this loaded skill directory in the same shell call:

```bash
SKILL_DIR="<absolute path of this skill directory>";
python3 "$SKILL_DIR/scripts/run_claude.py" "<scoped prompt>" --json
```

An approved workflow supplies the exact model, effort, role, tool mode, and receipt policy. Pass those approved options and `--disable-fallback`; this basic example does not authorize a different route.

## Runtime boundaries

- Use the local authenticated `claude` CLI in print mode. Permission checks remain enabled.
- Analysis roles default to read-only planning mode. `--restrict-tools` forces it; `--allow-write` opts out within the caller's authority.
- Prompt and file context may be sent to the configured provider. Bare mode changes authentication behavior; read the runtime reference before using it.
- The wrapper forwards model and effort. Current print output does not prove the serving model; a configured label alone gives an unverified receipt.
- Direct calls can fall back once to codex-runner when the CLI is missing. Approved routes disable fallback; native session continuation must preserve the selected runner.

## Load by need

- [references/command-reference.md](references/command-reference.md): flags, examples, native mappings, and return codes when composing a non-basic invocation.
- [references/runtime-reference.md](references/runtime-reference.md): authentication, fallback conditions, configuration, and extended envelope fields when configuring a route or interpreting its result.
- [references/continuation.md](references/continuation.md): only when resuming a session or managing a background job.

## Result

Read `agent_message` and the wrapper envelope. Check success, serving-model receipt, effective runner/provider, and any fallback or malformed-output status. A completed process alone does not prove the requested task or model was used. Report touched files when the caller authorized edits.
