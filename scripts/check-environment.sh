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
    printf '%s\n' '{"schema_version":1,"checks":[{"name":"python","status":"MISSING","required":true,"detail":"Python 3.11 or newer is unavailable.","action":"Install Python 3.11 or newer and expose python3 on PATH."}],"summary":{"missing_required":1,"required_warnings":0,"status":"missing_requirements"},"limits":["Remaining checks were not run because the checker requires Python."]}'
  else
    printf '%s\n' 'MISSING python (required): Python 3.11 or newer is unavailable.'
    printf '%s\n' 'Action: Install Python 3.11 or newer and expose python3 on PATH.'
    printf '%s\n' 'Remaining checks were not run.'
  fi
  exit 1
fi

exec python3 "$SCRIPT_DIR/check-environment.py" "$@"
