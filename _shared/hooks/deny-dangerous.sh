#!/bin/bash
# Runner-fleet command guard.
# Blocks catastrophic shell commands before an agent CLI runs them.
# Denylist: dangerous-patterns.txt next to this script (one ERE regex per line);
# override the location with RAR_GUARD_PATTERNS.
#
# Wiring (see _shared/references/runner-common.md, "Guardrails"):
#   Claude Code  ~/.claude/settings.json  PreToolUse (matcher Bash) -> this script
#   Codex        ~/.codex/hooks.json      PreToolUse (matcher Bash) -> this script
#
# stdin:  hook JSON. The command lives at .tool_input.command (Claude/Codex),
#         .toolInput.command (Claude-compat hosts), or .command.
# Block:  exit 2 + reason on stderr (the PreToolUse contract).
# Allow:  exit 0, silent.
#
# This is a seatbelt against accidents, NOT a sandbox against a malicious
# agent — obfuscated equivalents (python -c "shutil.rmtree(...)") slip past
# regex. Keep sandboxing and permission modes on regardless.

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_FILE="${RAR_GUARD_PATTERNS:-$SCRIPT_DIR/dangerous-patterns.txt}"

# Without jq we cannot inspect the command: fail open rather than break agents.
command -v jq >/dev/null 2>&1 || exit 0

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .toolInput.command // .command // empty' 2>/dev/null)

[ -z "$CMD" ] && exit 0
[ -f "$PATTERNS_FILE" ] || exit 0

while IFS= read -r pattern; do
  case "$pattern" in ''|\#*) continue ;; esac
  if printf '%s\n' "$CMD" | grep -qE -- "$pattern" 2>/dev/null; then
    echo "Blocked by the runner-fleet command guard ($PATTERNS_FILE). Matched pattern: $pattern. Do not retry it or work around the guard; explain the block to the user instead." >&2
    exit 2
  fi
done < "$PATTERNS_FILE"

exit 0
