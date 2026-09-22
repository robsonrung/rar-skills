import importlib.util
import argparse
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SHARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED / 'scripts'))
REPO_ROOT = SHARED.parents[1]

spec = importlib.util.spec_from_file_location('environment_check', SHARED / 'scripts/check_environment.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)

SHELL_WRAPPER = REPO_ROOT / 'scripts/check-environment.sh'


class EnvironmentTests(unittest.TestCase):
    def test_shell_reports_missing_python_as_json(self):
        shell = SHELL_WRAPPER
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(['/bin/bash', str(shell), '--json'],
                                    env={'PATH': temp}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report['checks'][0]['name'], 'python')
        self.assertEqual(report['summary']['missing_required'], 1)
        self.assertIn('brew install python', report['checks'][0]['action'])
        self.assertIn('python3 --version', report['checks'][0]['action'])

    def test_shell_python_setup_preserves_rerun_arguments(self):
        shell = SHELL_WRAPPER
        for args in ([], ['--project', "/tmp/project's folder", '--browser', 'none', '--native-models']):
            with self.subTest(args=args), tempfile.TemporaryDirectory() as temp:
                result = subprocess.run(['/bin/bash', str(shell), *args],
                                        env={'PATH': temp}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('brew install python', result.stdout)
            self.assertIn('sudo apt-get install python3', result.stdout)
            self.assertIn('python3 --version', result.stdout)
            rerun = next(line.strip() for line in result.stdout.splitlines() if line.startswith('     bash '))
            self.assertEqual(shlex.split(rerun), ['bash', str(shell), *args])

    def test_shell_unsupported_python_also_reports_setup(self):
        shell = SHELL_WRAPPER
        with tempfile.TemporaryDirectory() as temp:
            python = Path(temp) / 'python3'
            python.write_text('#!/bin/sh\nexit 1\n')
            python.chmod(0o755)
            result = subprocess.run(['/bin/bash', str(shell), '--json'],
                                    env={'PATH': temp}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('3.11', json.loads(result.stdout)['checks'][0]['action'])

    def test_shell_forwards_arguments_and_exit_status(self):
        shell = SHELL_WRAPPER
        result = subprocess.run(['/bin/bash', str(shell), '--timeout', '0'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--timeout must be greater than zero', result.stderr)

    def test_raw_command_output_is_not_returned(self):
        process = subprocess.CompletedProcess([], 0, 'tool 2.3.4 secret-value', '')
        with patch.object(check.subprocess, 'run', return_value=process):
            self.assertEqual(check.version_of('fixture', 1), '2.3.4')

    def test_timeout_is_not_reported_as_missing_binary(self):
        with patch.object(check.shutil, 'which', return_value='/fixture/tool'), \
             patch.object(check.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 1)):
            row = check.Checker().command('fixture')
        self.assertEqual(row['status'], 'WARN')
        self.assertIn('timed out after 5 seconds', row['detail'])

    def test_pi_version_must_meet_stable_minimum(self):
        minimum = check.minimum_pi_version()
        baseline = '.'.join(map(str, minimum))
        for version, expected in [(baseline, 'OK'), ('0.86.1', 'OK'), ('1.0.0', 'OK'),
                                  ('0.85.0', 'MISSING'), (baseline + '-beta', 'MISSING')]:
            with self.subTest(version=version), \
                 patch.object(check.shutil, 'which', return_value='/fixture/pi'), \
                 patch.object(check, 'version_of', return_value=version):
                row = check.Checker().command('pi', minimum=minimum)
            self.assertEqual(row['status'], expected)
            if expected == 'MISSING':
                self.assertIn('npm install -g @earendil-works/pi-coding-agent@', row['action'])

    def test_pi_install_action_uses_adapter_minimum(self):
        with patch.object(check.shutil, 'which', return_value=None):
            row = check.Checker().command('pi', minimum=(1, 10, 0))
        self.assertIn('@earendil-works/pi-coding-agent@1.10.0', row['action'])
        self.assertIn('Newer stable releases are accepted', row['action'])

    def test_node_upgrade_has_install_and_path_steps(self):
        with patch.object(check.sys, 'platform', 'darwin'), \
             patch.object(check.shutil, 'which', return_value='/fixture/node'), \
             patch.object(check, 'version_of', return_value='18.0.0'):
            row = check.Checker().command('node', minimum=(22, 19, 0))
        self.assertEqual(row['status'], 'MISSING')
        self.assertIn('brew install node@24', row['action'])
        self.assertIn('shell startup file', row['action'])
        self.assertIn('export PATH=', row['action'])
        self.assertIn('node --version', row['action'])

    def test_optional_missing_tools_do_not_fail_summary(self):
        checker = check.Checker()
        with patch.object(check.shutil, 'which', return_value=None):
            checker.command('optional-tool', required=False)
        self.assertEqual(checker.report()['summary']['missing_required'], 0)

    def run_fixture(self, root, env, browser='none'):
        with patch.dict(os.environ, {'PI_CODING_AGENT_DIR': str(root), **env}, clear=True), \
             patch.object(check.shutil, 'which', return_value=None):
            return check.check_environment(browser=browser, native_models=True)

    def test_credentials_are_presence_only_and_never_printed(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.run_fixture(Path(temp), {'OPENROUTER_API_KEY': 'secret-sentinel'})
        row = next(c for c in report['checks'] if c['name'] == 'gateway credential')
        self.assertEqual(row['status'], 'OK')
        self.assertNotIn('secret-sentinel', json.dumps(report))
        self.assertNotIn('valid credential', row['detail'])

    def test_auth_store_presence_is_not_proof_of_gateway_login(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'auth.json').write_text('{"unrelated":"secret-sentinel"}')
            report = self.run_fixture(root, {})
        row = next(c for c in report['checks'] if c['name'] == 'gateway credential')
        self.assertEqual(row['status'], 'WARN')
        self.assertNotIn('secret-sentinel', json.dumps(report))

    def test_missing_browser_and_missing_credentials_are_required_gaps(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.run_fixture(Path(temp), {}, browser='auto')
        rows = {c['name']: c for c in report['checks']}
        self.assertEqual(rows['gateway credential']['status'], 'MISSING')
        self.assertEqual(rows['browser driver']['status'], 'MISSING')
        self.assertGreater(report['summary']['missing_required'], 0)
        self.assertTrue(all(row['action'] for row in report['checks']
                            if row['required'] and row['status'] != 'OK'))

    def test_selected_browser_guidance_does_not_install_an_alternative(self):
        for browser, package, other in [('agent-browser', 'agent-browser@0.36.0', '@playwright/cli'),
                                        ('playwright-cli', '@playwright/cli', 'agent-browser@0.36.0')]:
            with self.subTest(browser=browser), tempfile.TemporaryDirectory() as temp:
                report = self.run_fixture(Path(temp), {}, browser=browser)
            action = next(row['action'] for row in report['checks'] if row['name'] == 'browser driver')
            self.assertIn('npm install -g ' + package, action)
            self.assertNotIn(other, action)
            self.assertIn('--browser none', action)

    def test_text_report_separates_required_and_optional_steps(self):
        checker = check.Checker()
        checker.add('optional tool', 'MISSING', False, 'Absent.', 'Optional install command.')
        checker.add('required tool', 'MISSING', True, 'Absent.', 'Required install command.\nVerify the version.')
        output = io.StringIO()
        with redirect_stdout(output):
            check.print_report(checker.report(), 'bash /fixture/check-environment.sh')
        text = output.getvalue()
        required = text.split('Required next steps:', 1)[1].split('Optional steps', 1)[0]
        self.assertIn('1. required tool', required)
        self.assertIn('Required install command.', required)
        self.assertIn('Verify the version.', required)
        self.assertNotIn('Optional install command.', required)
        self.assertIn('bash /fixture/check-environment.sh', text)
        self.assertIn('warnings can still require action', text)

    def test_rerun_and_project_install_commands_quote_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project's folder; $(not-a-command)"
            project.mkdir()
            args = argparse.Namespace(project=project, browser='playwright-cli', timeout=10.0, native_models=True)
            command = shlex.split(check.rerun_command(args))
            self.assertEqual(command, ['bash', str(SHELL_WRAPPER),
                                      '--project', str(project.resolve()), '--browser', 'playwright-cli',
                                      '--timeout', '10.0', '--native-models'])
            with patch.object(check.shutil, 'which', return_value=None):
                report = check.check_environment(project=project, browser='none', native_models=True)
            action = next(row['action'] for row in report['checks'] if row['name'] == 'project skills')
            install = next(line.removeprefix('Run: ') for line in action.splitlines() if line.startswith('Run: '))
            self.assertEqual(shlex.split(install), ['bash', str(REPO_ROOT / 'scripts/install-skills.sh'),
                                                   str(project.resolve()), '--layout', 'agents'])

    def test_installed_layout_uses_script_path_and_npx_guidance(self):
        # Outside a source checkout there is no repo wrapper or installer:
        # the rerun command targets the shared script and the install action
        # points at the npx installer.
        with tempfile.TemporaryDirectory() as temp, patch.object(check, 'SOURCE_ROOT', None):
            project = Path(temp) / 'project'
            project.mkdir()
            args = argparse.Namespace(project=project, browser='none', timeout=5.0, native_models=True)
            command = shlex.split(check.rerun_command(args))
            self.assertEqual(command[:2], ['python3', str(check.SCRIPT_PATH)])
            with patch.object(check.shutil, 'which', return_value=None):
                report = check.check_environment(project=project, browser='none', native_models=True)
            action = next(row['action'] for row in report['checks'] if row['name'] == 'project skills')
            self.assertIn('npx skills@latest add robsonrung/rar-skills', action)
            self.assertNotIn('install-skills.sh', action.splitlines()[1])

    def test_required_steps_follow_prerequisite_order(self):
        checker = check.Checker()
        for name in ['gateway credential', 'browser readiness', 'project skills',
                     'application setup', 'Pi state permissions', 'pi', 'node']:
            checker.add(name, 'WARN', True, 'Needs setup.', 'Complete setup.')
        output = io.StringIO()
        with redirect_stdout(output):
            check.print_report(checker.report(), 'bash /fixture/check-environment.sh')
        steps = output.getvalue().split('Required next steps:', 1)[1].split('After setup:', 1)[0]
        self.assertLess(steps.index('Pi state permissions'), steps.index('gateway credential'))
        self.assertLess(steps.index('pi\n'), steps.index('Pi state permissions'))
        self.assertLess(steps.index('node\n'), steps.index('Pi state permissions'))
        self.assertLess(steps.index('project skills'), steps.index('application setup'))
        self.assertLess(steps.index('application setup'), steps.index('browser readiness'))

    def test_json_stays_parseable_and_preserves_warning_exit_status(self):
        checker = check.Checker()
        checker.add('manual check', 'WARN', True, 'Not verified.', 'Complete the manual check.')
        for missing in (False, True):
            with self.subTest(missing=missing):
                if missing:
                    checker.add('required tool', 'MISSING', True, 'Absent.', 'Install the tool.')
                output = io.StringIO()
                with patch.object(check.sys, 'argv', ['check-environment.sh', '--json']), \
                     patch.object(check, 'check_environment', return_value=checker.report()), redirect_stdout(output):
                    exit_code = check.main()
                self.assertEqual(exit_code, int(missing))
                report = json.loads(output.getvalue())
                self.assertEqual(report['schema_version'], 1)
                self.assertEqual(report['summary']['required_warnings'], 1)

    def test_writable_state_does_not_repeat_repairs(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.run_fixture(Path(temp), {})
        row = next(c for c in report['checks'] if c['name'] == 'Pi state permissions')
        self.assertEqual(row['status'], 'OK')
        self.assertEqual(row['action'], '')

    def test_missing_state_still_has_creation_step(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.run_fixture(Path(temp) / 'new-state', {})
        row = next(c for c in report['checks'] if c['name'] == 'Pi state permissions')
        self.assertEqual(row['status'], 'WARN')
        self.assertIn('mkdir -p', row['action'])

    def test_missing_ripgrep_does_not_block_setup(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'PI_CODING_AGENT_DIR': temp, 'OPENROUTER_API_KEY': 'fixture'}, clear=True), \
             patch.object(check.shutil, 'which', side_effect=lambda name: None if name == 'rg' else '/fixture/' + name), \
             patch.object(check, 'version_of', return_value='99.0.0'):
            report = check.check_environment(native_models=True, browser='none')
        row = next(c for c in report['checks'] if c['name'] == 'rg')
        self.assertEqual(row['status'], 'MISSING')
        self.assertFalse(row['required'])
        self.assertEqual(report['summary']['missing_required'], 0)

    def test_manual_checks_are_separate_from_repairs(self):
        checker = check.Checker()
        checker.add('tool', 'MISSING', True, 'Absent.', 'Install tool.')
        checker.add('login', 'WARN', True, 'Not tested.', 'Verify access.', manual=True)
        output = io.StringIO()
        with redirect_stdout(output):
            check.print_report(checker.report(), 'repeat-check')
        required = output.getvalue().split('Required next steps:', 1)[1].split('Manual checks', 1)[0]
        self.assertNotIn('Verify access.', required)
        self.assertIn('Rerunning this script will not clear them.', output.getvalue())
        self.assertIn('Verify access.', output.getvalue())

    def test_version_exit_error_is_specific_without_raw_output(self):
        process = subprocess.CompletedProcess([], 7, '', 'secret-sentinel')
        with patch.object(check.shutil, 'which', return_value='/fixture/node'), \
             patch.object(check.subprocess, 'run', return_value=process):
            row = check.Checker().command('node')
        self.assertEqual(row['status'], 'WARN')
        self.assertIn('exited with code 7', row['detail'])
        self.assertNotIn('secret-sentinel', json.dumps(row))

    def test_auto_browser_accepts_a_working_alternative(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.dict(os.environ, {'PI_CODING_AGENT_DIR': temp}, clear=True), \
             patch.object(check.shutil, 'which', side_effect=lambda name: '/fixture/' + name), \
             patch.object(check, 'version_of', side_effect=lambda path, _: None if path.endswith('playwright-cli') else '99.0.0'):
            report = check.check_environment(native_models=True)
        row = next(c for c in report['checks'] if c['name'] == 'browser driver')
        self.assertEqual(row['status'], 'OK')
        row = next(c for c in report['checks'] if c['name'] == 'browser readiness')
        self.assertEqual(row['status'], 'WARN')
        self.assertTrue(row['manual'])
        self.assertNotIn('playwright-cli', row['action'])
        self.assertIn('agent-browser', row['action'])
        self.assertNotIn('playwright-cli', [item['name'] for item in report['checks']])


if __name__ == '__main__':
    unittest.main()
