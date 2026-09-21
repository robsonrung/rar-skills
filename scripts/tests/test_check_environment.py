import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('environment_check', Path(__file__).resolve().parents[1] / 'check-environment.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class EnvironmentTests(unittest.TestCase):
    def test_shell_reports_missing_python_as_json(self):
        shell = Path(__file__).resolve().parents[1] / 'check-environment.sh'
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(['/bin/bash', str(shell), '--json'],
                                    env={'PATH': temp}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report['checks'][0]['name'], 'python')
        self.assertEqual(report['summary']['missing_required'], 1)

    def test_shell_forwards_arguments_and_exit_status(self):
        shell = Path(__file__).resolve().parents[1] / 'check-environment.sh'
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

    def test_unverified_pi_version_is_rejected(self):
        supported = check.supported_pi_versions()
        for version in ['999.0.0', sorted(supported)[0] + '-beta']:
            with patch.object(check.shutil, 'which', return_value='/fixture/pi'), \
                 patch.object(check, 'version_of', return_value=version):
                row = check.Checker().command('pi', exact=supported)
            self.assertEqual(row['status'], 'MISSING')

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


if __name__ == '__main__':
    unittest.main()
