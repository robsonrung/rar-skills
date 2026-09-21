#!/usr/bin/env bash
# Shell entry point for the environment checker.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "${BASH_SOURCE[0]%/*}" && pwd)"
JSON_OUTPUT=false
for argument in "$@"; do
  if [[ "$argument" == "--json" ]]; then
    JSON_OUTPUT=true
  fi
done

if ! command -v python3 >/dev/null 2>&1 ||
   ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
  if [[ "$JSON_OUTPUT" == true ]]; then
    printf '%s\n' '{"schema_version":1,"checks":[{"name":"python","status":"MISSING","required":true,"detail":"Python 3.11 or newer is unavailable.","action":"On macOS with Homebrew (https://brew.sh), run: brew install python. On Debian/Ubuntu, run: sudo apt-get update && sudo apt-get install python3. Check: python3 --version. If it is below 3.11, use https://www.python.org/downloads/ for a supported release. Restart the host after updating PATH, then rerun this checker with the same options. See docs/machine-setup.md, section 1."}],"summary":{"missing_required":1,"required_warnings":0,"status":"missing_requirements"},"limits":["Remaining checks were not run because the checker requires Python."]}'
  else
    printf '%s\n' 'MISSING python (required): Python 3.11 or newer is unavailable.'
    printf '\n%s\n' 'Complete these steps first:'
    printf '%s\n' '  1. Install Python using the instructions for your system.'
    printf '%s\n' '     macOS with Homebrew (https://brew.sh): brew install python'
    printf '%s\n' '     Debian/Ubuntu: sudo apt-get update && sudo apt-get install python3'
    printf '%s\n' '     Other systems or older packages: https://www.python.org/downloads/'
    printf '%s\n' '  2. Run: python3 --version'
    printf '%s\n' '     The result must be 3.11 or newer. If an older version appears, put the new installation first on PATH.'
    printf '%s\n' '  3. Restart the host after changing PATH. Run this command from its terminal:'
    printf '     bash %q' "$SCRIPT_DIR/check-environment.sh"
    if [[ $# -gt 0 ]]; then
      printf ' %q' "$@"
    fi
    printf '\n\nSetup guide: %s/../docs/machine-setup.md\n' "$SCRIPT_DIR"
    printf '%s\n' 'Remaining checks were not run. Run the checker again after installing Python.'
  fi
  exit 1
fi

exec python3 "$SCRIPT_DIR/check-environment.py" "$@"
