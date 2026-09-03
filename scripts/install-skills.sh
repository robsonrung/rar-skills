#!/usr/bin/env bash
# Install the rar-skills collection into a target repo.
#
# Usage:
#   scripts/install-skills.sh <target-repo> [--copy] [--layout agents|claude|both]
#
# Layouts (default: both — the two are complementary, not alternatives):
#   agents  → <target>/.agents/skills/   AgentSkills location. Read by OpenHands'
#             own agent and by the Codex CLI.
#   claude  → <target>/.claude/skills/   Read by the Claude Code CLI, which is what
#             actually runs the skills when OpenHands drives it over ACP.
#
# Default is symlinks (edits in this checkout flow through); --copy makes the
# target self-contained. Re-running is idempotent.
#
# NOTE: each skill is linked individually, never by linking the `skills`
# directory itself — Claude Code does not follow a symlinked skills root, so a
# single parent symlink silently yields zero project skills.

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET=""
MODE=link
LAYOUT=both

while [[ $# -gt 0 ]]; do
  case "$1" in
    --copy)   MODE=copy; shift ;;
    --layout) LAYOUT="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,18p' "$0"; exit 0 ;;
    *)        TARGET="$1"; shift ;;
  esac
done

if [[ -z "$TARGET" ]]; then
  echo "usage: $0 <target-repo> [--copy] [--layout agents|claude|both]" >&2
  exit 2
fi
case "$LAYOUT" in
  agents|claude|both) ;;
  *) echo "error: --layout must be agents, claude, or both" >&2; exit 2 ;;
esac
TARGET="$(cd "$TARGET" && pwd)"

dests=()
[[ "$LAYOUT" == "agents" || "$LAYOUT" == "both" ]] && dests+=("$TARGET/.agents/skills")
[[ "$LAYOUT" == "claude" || "$LAYOUT" == "both" ]] && dests+=("$TARGET/.claude/skills")

installed=0
for dest in "${dests[@]}"; do
  mkdir -p "$dest"
  count=0
  # A skill is a directory with SKILL.md; shared ships alongside them as-is,
  # because skills reference .../skills/shared/{references,scripts}/...
  # Skills live nested in the source checkout under skills/ (skills/engineering/<group>/<skill>,
  # skills/visualization/<skill>, skills/extras/<skill>); they install flat, by directory name.
  # skills/shared/ ships as-is.
  while IFS= read -r dir; do
    name="$(basename "$dir")"
    rm -rf "$dest/$name"
    if [[ "$MODE" == "copy" ]]; then
      cp -R "${dir%/}" "$dest/$name"
    else
      ln -s "${dir%/}" "$dest/$name"
    fi
    count=$((count + 1))
  done < <(
    printf '%s\n' "$SOURCE_DIR/skills/shared"
    find "$SOURCE_DIR/skills/engineering" "$SOURCE_DIR/skills/visualization" "$SOURCE_DIR/skills/extras" -name SKILL.md -not -path '*/node_modules/*' -exec dirname {} \; | sort
  )
  echo "  $dest — $count entries"
  installed=$((installed + count))
done

echo "installed $installed entries across ${#dests[@]} layout(s) ($([[ $MODE == copy ]] && echo copies || echo symlinks))"
echo "verify: OpenHands  → openhands, then /skills"
echo "        Claude CLI → claude -p 'list your available skills' from the target repo"
