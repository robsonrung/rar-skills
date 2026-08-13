#!/usr/bin/env python3
"""Run the pipeline through OpenHands with a CLI as the agent — no API keys.

OpenHands normally calls a provider API directly with LLM_API_KEY. This launcher
uses the SDK's ACPAgent instead, which spawns an existing CLI (Claude Code or
Codex) as a subprocess and speaks the Agent Client Protocol to it. The CLI owns
its own model and auth, so the run bills against your CLI subscription and no
API key is needed anywhere.

The `openhands` CLI cannot do this — its `acp` subcommand is the reverse
direction (OpenHands serving as an ACP agent to Zed/Toad). Hence this script.

Usage:
    scripts/run-pipeline-acp.py <target-repo> -t "Follow the ship skill for: <idea>"
    scripts/run-pipeline-acp.py <target-repo> -f task.txt --agent codex
    scripts/run-pipeline-acp.py <target-repo> --resume <conversation-id> -t "continue"

Skills must be installed in the target repo first:
    scripts/install-skills.sh <target-repo>

The CLI — not OpenHands — discovers the skills, so the layout that matters is
.claude/skills/ for Claude Code and .agents/skills/ for Codex. install-skills.sh
writes both by default.
"""

import argparse
import os
import sys
from pathlib import Path

# Each entry: the command that speaks ACP for that CLI.
AGENTS = {
    "claude": ["npx", "-y", "@agentclientprotocol/claude-agent-acp"],
    "codex": ["npx", "-y", "@zed-industries/codex-acp"],
}

# Stripped before launch so a stray key cannot silently turn this into a
# metered API run — the whole point is that the CLI's own auth is used.
API_KEY_VARS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_API_KEY")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("workspace", help="target repo the agent works in")
    parser.add_argument("-t", "--task", help="task prompt")
    parser.add_argument("-f", "--file", help="file containing the task prompt")
    parser.add_argument("--agent", choices=sorted(AGENTS), default="claude",
                        help="which CLI acts as the agent (default: claude)")
    parser.add_argument("--model", help="model for the CLI to use, e.g. 'sonnet', 'gpt-5.5'")
    parser.add_argument("--resume", metavar="CONVERSATION_ID",
                        help="resume a previous conversation")
    parser.add_argument("--keep-api-keys", action="store_true",
                        help="do not strip API-key env vars (default is to strip them)")
    args = parser.parse_args()

    if not args.task and not args.file and not args.resume:
        parser.error("one of -t/--task or -f/--file is required")

    task = args.task
    if args.file:
        task = Path(args.file).read_text(encoding="utf-8")

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"error: {workspace} is not a directory", file=sys.stderr)
        return 2
    # ACP rejects a relative cwd, so always hand it the resolved path.

    if not args.keep_api_keys:
        for var in API_KEY_VARS:
            os.environ.pop(var, None)

    os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
    from openhands.sdk import Conversation
    from openhands.sdk.agent import ACPAgent

    skills_dir = workspace / (".claude/skills" if args.agent == "claude" else ".agents/skills")
    if not skills_dir.is_dir():
        print(f"warning: {skills_dir} not found — the agent will start with no pipeline "
              f"skills. Run scripts/install-skills.sh {workspace} first.", file=sys.stderr)

    agent_kwargs = {"acp_command": AGENTS[args.agent]}
    if args.model:
        agent_kwargs["acp_model"] = args.model
    agent = ACPAgent(**agent_kwargs)

    # Conversations persist here so a long pipeline run survives a restart, in
    # the same gitignored tree as the pipeline's own run state.
    persistence = workspace / ".ai-workflow" / "openhands"
    persistence.mkdir(parents=True, exist_ok=True)

    conv_kwargs = {"agent": agent, "workspace": str(workspace),
                   "persistence_dir": str(persistence)}
    if args.resume:
        conv_kwargs["conversation_id"] = args.resume

    conversation = None
    try:
        conversation = Conversation(**conv_kwargs)
        print(f"agent: {args.agent} CLI over ACP  |  workspace: {workspace}")
        print(f"conversation: {conversation.state.id}")
        if task:
            conversation.send_message(task)
        conversation.run()
        return 0
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    finally:
        try:
            agent.close()
        except Exception as exc:  # closing must not mask a real failure  # noqa: BLE001
            print(f"note: ACP shutdown: {exc}", file=sys.stderr)
        if conversation is not None:
            print(f"resume with: --resume {conversation.state.id}")


if __name__ == "__main__":
    sys.exit(main())
