---
name: opencode-runner
description: Guide OpenCode CLI runs through the host agent approval flow. Use when users explicitly request OpenCode, want to compare OpenCode output with another model, or need an OpenCode perspective without a bundled runner script.
---

# OpenCode Runner

Use this skill as a safe OpenCode handoff guide. This package intentionally does not ship an executable OpenCode wrapper.

## Safety Model

OpenCode can read project files and send prompt context to the configured model provider. Treat every run as an external model call.

Before running OpenCode:

1. Confirm the user asked for OpenCode or that the active workflow explicitly selected it.
2. Confirm the working directory and prompt scope.
3. Prefer read only review or planning prompts.
4. Avoid attaching secrets, credentials, private keys, tokens, or unrelated files.
5. Use the host agent's normal shell approval, sandbox, and logging flow for the command.

If the user asks for unattended editing, explain that this skill does not provide an unattended wrapper. Use a normal host approved command instead.

## Manual Invocation Pattern

After the checklist above passes, run the local OpenCode CLI directly from the target repository. Keep the command narrow and pass a concise prompt. Capture stdout and stderr in the normal host tool output.

```bash
opencode run "<concise prompt>"
opencode run -m <provider/model> "<concise prompt>"
opencode run --agent plan "<concise review prompt>"
```

For review tasks, ask OpenCode for analysis only; the `plan` agent variant above keeps the run read only. For implementation tasks, ask OpenCode for a patch plan first, then apply changes through the primary host agent.

## Output Contract

Return a short summary with:

1. OpenCode command scope
2. Main result
3. Files or areas discussed
4. Any uncertainty, failure, or missing prerequisite

When acting as a seat in a cross-runner workflow (for example models-consensus or council), return this same summary to the orchestrating skill verbatim.

## Missing Prerequisite

If OpenCode is not installed or authenticated, report the missing prerequisite and stop. Do not provide install commands from this skill.
