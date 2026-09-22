#!/usr/bin/env python3
"""Inspect local prerequisites without installing tools or calling model providers."""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
# This file lives at <skills-root>/shared/scripts/check_environment.py in both
# supported layouts (source checkout and flat install), so parents[2] is the
# skills root on either one.
SKILLS_ROOT = SCRIPT_PATH.parents[2]
try:
    from skill_paths import skill_dir
except ImportError:
    sys.path.insert(0, str(SCRIPT_PATH.parent))
    from skill_paths import skill_dir


def _source_root():
    """The rar-skills source checkout, when this script runs inside one."""
    candidate = SKILLS_ROOT.parent
    return candidate if (candidate / 'docs/machine-setup.md').is_file() else None


SOURCE_ROOT = _source_root()
SETUP_GUIDE = (str(SOURCE_ROOT / 'docs/machine-setup.md') if SOURCE_ROOT
               else 'docs/machine-setup.md in the rar-skills source repository')


def install_action(name, minimum=None):
    """Return instructions only; the checker never runs setup commands."""
    if name == 'pi':
        floor = minimum or minimum_pi_version()
        action = 'Run: npm install -g @earendil-works/pi-coding-agent'
        if floor:
            version = '.'.join(map(str, floor))
            action += f'@{version}\nCheck: pi --version\nMinimum version: {version}. Newer stable releases are accepted.'
        else:
            action += '\nCheck: pi --version'
        return action + '\nThe runner checks request hook readiness before sending task content.'
    if name in ('node', 'npm'):
        install = ('Run: brew install node@24\n'
                   'Add this line to your shell startup file (~/.zshrc for zsh), then open a new terminal:\n'
                   'export PATH="$(brew --prefix node@24)/bin:$PATH"'
                   if sys.platform == 'darwin' else
                   'Install Node.js 24.x with npm from https://nodejs.org/en/download')
        return install + '\nCheck: node --version\nCheck: npm --version'
    if name in ('python', 'git', 'bash', 'rg', 'gh', 'jq'):
        package = {'python': 'python3', 'rg': 'ripgrep'}.get(name, name)
        if sys.platform == 'darwin':
            package = 'python' if name == 'python' else package
            install = f'With Homebrew installed (https://brew.sh), run: brew install {package}'
        elif sys.platform.startswith('linux'):
            install = (f'On Debian/Ubuntu, run: sudo apt-get update && sudo apt-get install {package}\n'
                       'On other Linux systems, use the system package manager.')
        else:
            install = f'Install {package} in a supported macOS, Linux or WSL environment.'
        command = 'python3' if name == 'python' else name
        action = f'{install}\nCheck: {command} --version'
        if name == 'python':
            action += '\nPython 3.11 or newer is required. See https://www.python.org/downloads/'
        if name == 'gh':
            action += '\nThen: gh auth login\nCheck: gh auth status'
        return action
    if name == 'agent-browser':
        return ('Run: npm install -g agent-browser@0.36.0\n'
                'Then: agent-browser install\nCheck: agent-browser --version')
    if name == 'playwright-cli':
        return ('Run: npm install -g @playwright/cli\n'
                'Run: playwright-cli --help\nFollow its browser setup instructions.\n'
                'Check: playwright-cli --version')
    return (f'Follow the {name} setup instructions in {SETUP_GUIDE}, section 4.\n'
            f'Check: command -v {name}\nRestart the host after changing PATH.')


def minimum_pi_version():
    """Stable Pi floor from the installed adapter, or None when it is absent."""
    source = skill_dir('pi-runner', root=SKILLS_ROOT) / 'scripts/provider_runtime.py'
    if not source.is_file():
        return None
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MINIMUM_PI_VERSION' for t in node.targets):
            return tuple(ast.literal_eval(node.value))
    raise ValueError('Cannot read the minimum Pi version from the adapter')


class VersionCheckError(RuntimeError):
    pass


def version_of(path, timeout):
    try:
        result = subprocess.run([path, '--version'], capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL, check=False)
    except subprocess.TimeoutExpired:
        raise VersionCheckError(f'Version check timed out after {timeout:g} seconds.') from None
    except OSError:
        raise VersionCheckError('Version command could not start.') from None
    if result.returncode != 0:
        raise VersionCheckError(f'Version command exited with code {result.returncode}.')
    # Never return raw output: a misconfigured executable could print a secret.
    match = re.search(r'(?<![\d.])(\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?)(?![\d.])', result.stdout or result.stderr)
    return match.group(1) if match else None


def numeric(version):
    return tuple(int(part) for part in re.split(r'[-+]', version, maxsplit=1)[0].split('.'))


class Checker:
    def __init__(self, timeout=5):
        self.timeout = timeout
        self.checks = []

    def add(self, name, status, required, detail, action='', manual=False):
        row = dict(name=name, status=status, required=required, detail=detail, action=action)
        if manual:
            row['manual'] = True
        self.checks.append(row)
        return row

    def command(self, name, required=True, minimum=None, probe=True):
        path = shutil.which(name)
        if not path:
            return self.add(name, 'MISSING', required, 'Command not found on PATH.',
                            install_action(name, minimum))
        if not probe:
            return self.add(name, 'OK', required, 'Command found; authentication and execution were not tested.')
        failure = 'Version output did not contain a recognizable version.'
        try:
            version = version_of(path, self.timeout)
        except VersionCheckError as error:
            version = None
            failure = str(error)
        if version is None:
            return self.add(name, 'WARN', required, 'Command found. ' + failure,
                            f'In the terminal used to start the host, run:\n{name} --version\n'
                            'If this works, rerun the checker with --timeout 30.\n'
                            'If it fails, resolve the reported error. Do not reinstall solely because this probe failed.')
        if minimum and ('-' in version.split('+', 1)[0] or numeric(version) < minimum):
            return self.add(name, 'MISSING', required, f'Version {version} does not meet the stable minimum ' + '.'.join(map(str, minimum)) + '.',
                            install_action(name, minimum))
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
              '' if py >= (3, 11, 0) else install_action('python'))
    for name in ('git', 'bash'):
        check.command(name)
    check.command('node', minimum=(22, 19, 0))
    check.command('npm')
    check.command('pi', minimum=minimum_pi_version())
    if native_models:
        check.add('review and planning models', 'WARN', True,
                  'Native model access declared by the caller; not observable from this script.',
                  'Open the host model selector. Confirm access to each selected review and planning model.\n'
                  'Check the model and effort in the workflow preview before starting work.', manual=True)
    else:
        check.command('codex')
        check.add('review and planning authentication', 'WARN', True,
                  'CLI authentication and exact model access were not tested.',
                  f'Follow the selected runner login instructions in {SETUP_GUIDE}, section 4.\n'
                  'Confirm access to the selected model. If the host supplies these models, rerun with --native-models.', manual=True)

    key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    placeholders = {'your-key', 'your_api_key', 'replace-me', '<your-key>', '<key>'}
    state = Path(os.environ.get('PI_CODING_AGENT_DIR') or str(Path.home() / '.pi/agent')).expanduser()
    auth = state / 'auth.json'
    if key and key.lower() not in placeholders:
        check.add('gateway credential', 'OK', True, 'OPENROUTER_API_KEY is present; its value was not displayed or validated.')
    elif auth.is_file():
        check.add('gateway credential', 'WARN', True, 'Pi credential store exists; gateway login was not inspected.',
                  'Run pi, enter /login, and select OpenRouter. Complete the login instructions.\n'
                  'Alternatively, supply OPENROUTER_API_KEY through the launcher or secret manager that starts the host.\n'
                  'Restart the host so its workers receive the credential. Store presence alone does not confirm login.', manual=True)
    else:
        check.add('gateway credential', 'MISSING', True, 'No environment key or Pi credential store found.',
                  'Run pi, enter /login, and select OpenRouter. Complete the login instructions.\n'
                  'Alternatively, supply OPENROUTER_API_KEY through the launcher or secret manager that starts the host.\n'
                  'Restart the host so its workers receive the credential. Do not put the key in project files.')
    parent = state
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    writable = parent.is_dir() and os.access(parent, os.W_OK | os.X_OK)
    state_exists = state.is_dir()
    check.add('Pi state permissions', 'OK' if writable and state_exists else 'WARN' if writable else 'MISSING', True,
              'Pi state directory is writable and searchable; credential locking was not tested.' if writable and state_exists
              else 'Pi state directory does not exist; its parent is writable.' if writable
              else 'Pi state directory or nearest parent is not writable.',
              '' if writable and state_exists else
              'In the host terminal, run: mkdir -p "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"\n'
              'Check: test -w "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}" && test -x "${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"\n'
              'If this fails, grant the host access to that directory or set PI_CODING_AGENT_DIR to a writable directory.')

    if browser == 'none':
        check.add('browser', 'WARN', False, 'Browser checks skipped by request.')
    else:
        candidates = ('playwright-cli', 'agent-browser') if browser == 'auto' else (browser,)
        rows = [check.command(name, required=False) for name in candidates]
        available = [row for row in rows if row['status'] != 'MISSING']
        if not available:
            check.add('browser driver', 'MISSING', True, 'No selected interactive browser driver found.',
                      (('Choose one driver. For agent-browser:\n' + install_action('agent-browser') +
                        '\nFor Playwright CLI:\n' + install_action('playwright-cli'))
                       if browser == 'auto' else install_action(browser)) +
                      '\nIf this task needs no browser, rerun with --browser none.')
        else:
            good = any(r['status'] == 'OK' for r in rows)
            selected = next((row['name'] for row in rows if row['status'] == 'OK'), available[0]['name'])
            if browser == 'auto' and good:
                check.checks = [row for row in check.checks if row not in rows or row['name'] == selected]
            check.add('browser driver', 'OK' if good else 'WARN', True,
                      f'Using {selected}; one working driver is enough.' if good else 'Driver commands exist but version checks failed.',
                      '' if good else 'Run the selected driver with --version. Resolve its error, then rerun this checker.')
            browser_setup = ('If the browser binary is missing, run: agent-browser install\n'
                             if selected == 'agent-browser' else
                             'If the browser binary is missing, run: playwright-cli install-browser\n')
            check.add('browser readiness', 'WARN', True,
                      'Browser binary, application access, test account and evidence capture were not exercised.',
                      f'Use {selected}. Start the application and open its URL from the worker environment.\n' + browser_setup +
                      'If the browser is already installed, proceed to the application checks.\n'
                      'Use a test account. Verify navigation, page state, an interaction and a screenshot.\n'
                      f'See {SETUP_GUIDE}, section 3, for session setup and evidence requirements.', manual=True)

    check.command('rg', required=False)
    for name in ('gh', 'jq', 'claude', 'agy', 'grok', 'cmux'):
        check.command(name, required=False, probe=False)
    for name in ('AGY_CLI_PATH',):
        value = os.environ.get(name)
        if value:
            check.add(name, 'OK' if shutil.which(value) else 'MISSING', False,
                      'Configured override resolves to an executable.' if shutil.which(value) else 'Configured override does not resolve to an executable.',
                      '' if shutil.which(value) else f'Set {name} to the installed executable path, or unset {name} to use PATH.\n'
                      'Restart the host and rerun this checker.')

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
                  '' if installed else 'Preserve local changes to existing skill entries; the installer replaces matching names.\n'
                  + _install_action(project) +
                  '\nUse --layout claude or --layout both if your host needs those layouts.\n'
                  'Keep this source checkout in place for the installed links. If using global skills, confirm them in the host.')
        config = project / '.rar-skills/config.local.yaml'
        check.add('model preferences', 'OK', False,
                  'Local preference file exists; values were not read or validated.' if config.is_file()
                  else 'No local preferences; central workflow defaults apply.')
        check.add('application setup', 'WARN', True,
                  'Project dependencies, services, tests and application credentials require project-specific checks.',
                  f'Open the README and setup guide in {project}.\n'
                  'Install locked dependencies, configure local settings and start required services as documented.\n'
                  'Run the documented build and tests. Set up test accounts before browser checks.', manual=True)
    return check.report()


def _install_action(project):
    """How the user installs the skills: source checkout wrapper or npx."""
    installer = SOURCE_ROOT / 'scripts/install-skills.sh' if SOURCE_ROOT else None
    if installer and installer.is_file():
        return 'Run: ' + shlex.join(['bash', str(installer), str(project), '--layout', 'agents'])
    return ("Run from the project root: npx skills@latest add robsonrung/rar-skills --skill '*'\n"
            'Alternatively, clone the repository and run its scripts/install-skills.sh against the project.')


def rerun_command(args):
    wrapper = SOURCE_ROOT / 'scripts/check-environment.sh' if SOURCE_ROOT else None
    if wrapper and wrapper.is_file():
        command = ['bash', str(wrapper)]
    else:
        command = ['python3', str(SCRIPT_PATH)]
    if args.project is not None:
        command.extend(['--project', str(args.project.expanduser().resolve())])
    command.extend(['--browser', args.browser, '--timeout', str(args.timeout)])
    if args.native_models:
        command.append('--native-models')
    return shlex.join(command)


def print_report(result, rerun):
    print('Environment setup check')
    print('Follow the required steps in order. Run setup commands in the terminal used to start the host.')
    for required, title in ((True, 'Required checks'), (False, 'Optional checks')):
        print(f'\n{title}:')
        for row in result['checks']:
            if row['required'] == required and not row.get('manual'):
                print(f"  {row['status']:7} {row['name']}: {row['detail']}")
    summary = result['summary']
    print(f"\nResult: {summary['status']}. Missing required: {summary['missing_required']}. Required warnings: {summary['required_warnings']}.")
    setup_order = {
        'Pi state permissions': 1,
        'gateway credential': 2,
        'review and planning models': 3,
        'review and planning authentication': 3,
        'project skills': 4,
        'application setup': 5,
        'browser driver': 6,
        'browser readiness': 7,
    }
    for required, title in ((True, 'Required next steps'), (False, 'Optional steps (only for tools your task needs)')):
        rows = [row for row in result['checks']
                if row['required'] == required and row['status'] != 'OK' and row['action'] and not row.get('manual')]
        if required:
            rows.sort(key=lambda row: setup_order.get(row['name'], 0))
        else:
            # The required browser step already covers installation and verification.
            rows = [row for row in rows if row['name'] not in ('agent-browser', 'playwright-cli')]
        if not rows:
            continue
        print(f'\n{title}:')
        for index, row in enumerate(rows, 1):
            print(f"  {index}. {row['name']}")
            for line in row['action'].splitlines():
                print(f'     {line}')
    manual = [row for row in result['checks'] if row.get('manual')]
    manual.sort(key=lambda row: setup_order.get(row['name'], 0))
    if manual:
        print('\nManual checks (not tested by this script):')
        print('  These are not detected installation failures. Rerunning this script will not clear them.')
        for index, row in enumerate(manual, 1):
            print(f"  {index}. {row['name']}: {row['detail']}")
            for line in row['action'].splitlines():
                print(f'     {line}')
    print('\nAfter setup:')
    print('  Restart the host if PATH or credentials changed, then run this command in its environment:')
    print(f'  {rerun}')
    print('  Resolve all required MISSING results. Complete the manual checks for required WARN results.')
    print('  Exit code 0 means no required item is known to be missing; warnings can still require action.')
    print(f'\nSetup guide: {SETUP_GUIDE}')
    for limit in result['limits']:
        print(limit)


def main():
    prog = 'check-environment.sh' if SOURCE_ROOT else 'check_environment.py'
    parser = argparse.ArgumentParser(prog=prog, description=__doc__)
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
        print_report(result, rerun_command(args))
    return 1 if result['summary']['missing_required'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
