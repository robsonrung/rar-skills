#!/usr/bin/env python3
"""Inspect local prerequisites without installing tools or calling model providers."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def supported_pi_versions():
    source = ROOT / 'skills/engineering/seats/pi-runner/scripts/provider_runtime.py'
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SUPPORTED_PI_VERSIONS' for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise ValueError('Cannot read supported Pi versions from the adapter')


def version_of(path, timeout):
    try:
        result = subprocess.run([path, '--version'], capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    # Never return raw output: a misconfigured executable could print a secret.
    match = re.search(r'(?<![\d.])(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)(?![\d.])', result.stdout or result.stderr)
    return match.group(1) if match else None


def numeric(version):
    return tuple(int(part) for part in re.split(r'[-+]', version, maxsplit=1)[0].split('.'))


class Checker:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.checks = []

    def add(self, name, status, required, detail, action=''):
        row = dict(name=name, status=status, required=required, detail=detail, action=action)
        self.checks.append(row)
        return row

    def command(self, name, required=True, minimum=None, exact=None, probe=True):
        path = shutil.which(name)
        if not path:
            return self.add(name, 'MISSING', required, 'Command not found on PATH.',
                            f'Install {name} or expose it to the host process.')
        if not probe:
            return self.add(name, 'OK', required, 'Command found; authentication and execution were not tested.')
        version = version_of(path, self.timeout)
        if version is None:
            return self.add(name, 'WARN', required, 'Command found; version check failed or timed out.',
                            f'Check {name} --version in this host environment.')
        if exact and version not in exact:
            return self.add(name, 'MISSING', required, f'Unsupported version {version}.',
                            'Install a verified version: ' + ', '.join(sorted(exact)))
        if minimum and numeric(version) < minimum:
            return self.add(name, 'MISSING', required, f'Version {version} is too old.',
                            'Use version ' + '.'.join(map(str, minimum)) + ' or newer.')
        return self.add(name, 'OK', required, f'Version {version}; runtime access still depends on host permissions.')

    def report(self):
        missing = sum(c['required'] and c['status'] == 'MISSING' for c in self.checks)
        warnings = sum(c['required'] and c['status'] == 'WARN' for c in self.checks)
        return {'schema_version': 1, 'checks': self.checks,
                'summary': {'missing_required': missing, 'required_warnings': warnings,
                            'status': 'missing_requirements' if missing else 'needs_verification' if warnings else 'local_checks_passed'},
                'limits': ['No provider request, installation, browser launch or login was performed.',
                           'Presence of a credential does not prove validity, credit or model access.',
                           'Version commands may use their own local caches; raw command output is not reported.']}


def check_environment(project=None, browser='auto', native_models=False, timeout=5):
    check = Checker(timeout)
    py = sys.version_info[:3]
    check.add('python', 'OK' if py >= (3, 11, 0) else 'MISSING', True,
              'Running interpreter: ' + '.'.join(map(str, py)),
              '' if py >= (3, 11, 0) else 'Run this script with Python 3.11 or newer.')
    for name in ('git', 'bash', 'rg'):
        check.command(name)
    check.command('node', minimum=(22, 19, 0))
    check.command('npm')
    check.command('pi', exact=supported_pi_versions())
    if native_models:
        check.add('review and planning models', 'WARN', True,
                  'Native model access declared by the caller; not observable from this script.',
                  'Confirm each selected model and effort in the host preview.')
    else:
        check.command('codex')
        check.add('review and planning authentication', 'WARN', True,
                  'CLI authentication and exact model access were not tested.',
                  'Authenticate the selected runner and verify the model preview.')

    key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    placeholders = {'your-key', 'your_api_key', 'replace-me', '<your-key>', '<key>'}
    state = Path(os.environ.get('PI_CODING_AGENT_DIR') or str(Path.home() / '.pi/agent')).expanduser()
    auth = state / 'auth.json'
    if key and key.lower() not in placeholders:
        check.add('gateway credential', 'OK', True, 'OPENROUTER_API_KEY is present; its value was not displayed or validated.')
    elif auth.is_file():
        check.add('gateway credential', 'WARN', True, 'Pi credential store exists; gateway login was not inspected.',
                  'Configure OPENROUTER_API_KEY or confirm the gateway login in Pi.')
    else:
        check.add('gateway credential', 'MISSING', True, 'No environment key or Pi credential store found.',
                  'Export OPENROUTER_API_KEY to the host process or use Pi /login.')
    parent = state
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    writable = parent.is_dir() and os.access(parent, os.W_OK | os.X_OK)
    check.add('Pi state permissions', 'WARN' if writable else 'MISSING', True,
              'Filesystem permission check passed; sandbox and credential locks remain untested.' if writable
              else 'Pi state directory or nearest parent is not writable.',
              'Allow the host to write Pi state and credential locks; do not change permissions on unrelated files.')

    if browser == 'none':
        check.add('browser', 'WARN', False, 'Browser checks skipped by request.')
    else:
        candidates = ('playwright-cli', 'agent-browser') if browser == 'auto' else (browser,)
        rows = [check.command(name, required=False) for name in candidates]
        available = [row for row in rows if row['status'] != 'MISSING']
        if not available:
            check.add('browser driver', 'MISSING', True, 'No selected interactive browser driver found.',
                      'Install playwright-cli or agent-browser; use --browser none for command-only work.')
        else:
            good = any(r['status'] == 'OK' for r in rows)
            check.add('browser driver', 'OK' if good else 'WARN', True,
                      'At least one selected driver passes its version check.' if good else 'Driver commands exist but version checks failed.')
            check.add('browser readiness', 'WARN', True,
                      'Browser binary, application access, test account and evidence capture were not exercised.',
                      'Run the selected driver preflight from the worker environment.')

    for name in ('gh', 'jq', 'claude', 'agy', 'cline', 'grok', 'dcode', 'opencode', 'cmux'):
        check.command(name, required=False, probe=False)
    for name in ('AGY_CLI_PATH', 'DCODE_CLI_PATH'):
        value = os.environ.get(name)
        if value:
            check.add(name, 'OK' if shutil.which(value) else 'MISSING', False,
                      'Configured override resolves to an executable.' if shutil.which(value) else 'Configured override does not resolve to an executable.')

    if project is not None:
        project = Path(project).expanduser().resolve()
        if not project.is_dir():
            raise ValueError('Project directory does not exist')
        layouts = [project / '.agents/skills', project / '.claude/skills']
        required = ['shared/model-routing.json', 'shared/scripts/model_routing.py',
                    'pi-runner/SKILL.md', 'implement-and-review/SKILL.md', 'validate-e2e/SKILL.md']
        installed = any(all((layout / name).is_file() for name in required) for layout in layouts)
        check.add('project skills', 'OK' if installed else 'WARN', True,
                  'A project layout contains the core skills and shared files.' if installed
                  else 'No complete project layout found; global host skills were not inspected.',
                  '' if installed else 'Install the collection in the project or confirm the global host installation.')
        config = project / '.rar-skills/config.local.yaml'
        check.add('model preferences', 'OK', False,
                  'Local preference file exists; values were not read or validated.' if config.is_file()
                  else 'No local preferences; central workflow defaults apply.')
        check.add('application setup', 'WARN', True,
                  'Project dependencies, services, tests and application credentials require project-specific checks.',
                  'Follow the project setup instructions and run its documented checks.')
    return check.report()


def main():
    parser = argparse.ArgumentParser(prog="check-environment.sh", description=__doc__)
    parser.add_argument('--project', type=Path, help='Optional target repository to inspect')
    parser.add_argument('--browser', choices=('auto', 'playwright-cli', 'agent-browser', 'none'), default='auto')
    parser.add_argument('--native-models', action='store_true', help='Use host model access instead of requiring the external review/planning CLI')
    parser.add_argument('--timeout', type=float, default=5, help='Seconds allowed per version command')
    parser.add_argument('--json', action='store_true', help='Print a structured report')
    args = parser.parse_args()
    if not 0 < args.timeout <= 60:
        parser.error('--timeout must be greater than zero and at most 60')
    try:
        result = check_environment(args.project, args.browser, args.native_models, args.timeout)
    except (OSError, ValueError, SyntaxError) as error:
        # Do not include exception contents: they can contain environment values.
        print(json.dumps({'error': 'Cannot inspect the project or adapter configuration', 'type': type(error).__name__}))
        return 2
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for row in result['checks']:
            level = 'required' if row['required'] else 'optional'
            print(f"{row['status']:7} {row['name']} ({level}): {row['detail']}")
            if row['action']:
                print(f"        Action: {row['action']}")
        summary = result['summary']
        print(f"\nResult: {summary['status']}. Missing required: {summary['missing_required']}. Required warnings: {summary['required_warnings']}.")
        for limit in result['limits']:
            print(limit)
    return 1 if result['summary']['missing_required'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
