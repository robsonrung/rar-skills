---
name: opencode-runner
description: Guide OpenCode CLI runs through the host agent approval flow. Use when users explicitly request OpenCode, want to compare OpenCode output with another model, or need an OpenCode perspective without a bundled runner script.
---

# OpenCode Runner

Use this skill as a safe OpenCode handoff guide. This package intentionally does not ship an executable OpenCode wrapper. The host agent must use its normal shell approval, sandbox, and logging flow for any OpenCode command.

## Safety Model

OpenCode can read project files and send prompt context to the configured model provider. Treat every run as an external model call.

Before running OpenCode:

1. Confirm the user asked for OpenCode or that the active workflow explicitly selected it.
2. Confirm the working directory and prompt scope.
3. Prefer read only review or planning prompts.
4. Avoid attaching secrets, credentials, private keys, tokens, or unrelated files.
5. Use the host agent approval flow for the shell command.

If the user asks for unattended editing, explain that this skill does not provide an unattended wrapper. Use a normal host approved command instead.

## Manual Invocation Pattern

When approved by the user and permitted by the host, run the local OpenCode CLI directly from the target repository. Keep the command narrow and pass a concise prompt. Capture stdout and stderr in the normal host tool output.

For review tasks, ask OpenCode for analysis only. For implementation tasks, ask OpenCode for a patch plan first, then apply changes through the primary host agent.

## Output Contract

Return a short summary with:

1. OpenCode command scope
2. Main result
3. Files or areas discussed
4. Any uncertainty, failure, or missing prerequisite

## Missing Prerequisite

If OpenCode is not installed or authenticated, report the missing prerequisite and stop. Do not provide install commands from this skill.
