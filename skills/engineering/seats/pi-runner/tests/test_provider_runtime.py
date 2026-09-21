"""Check runtime version requirements without sending task content."""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'shared/scripts'))
import provider_runtime as runtime


class RuntimeVersionTests(unittest.TestCase):
    def test_stable_minimum_and_newer_versions(self):
        for version in ('0.85.1', '0.86.1', '0.100.0', '1.0.0', '0.85.1+build.1'):
            with self.subTest(version=version):
                self.assertTrue(runtime.supports_pi_version(version))

    def test_old_prerelease_and_malformed_versions(self):
        for version in ('0.85.0', '0.9.9', '0.85.1-beta', '1.0.0-rc.1', '', 'unknown', '0.86.1 extra'):
            with self.subTest(version=version):
                self.assertFalse(runtime.supports_pi_version(version))

    def test_newer_runtime_still_requires_packaged_hook(self):
        process = subprocess.CompletedProcess([], 0, '0.86.1\n', '')
        with patch.object(runtime.subprocess, 'run', return_value=process), \
             patch.object(runtime, 'EXTENSION_PATH', Mock(is_file=Mock(return_value=False))), \
             patch.object(runtime.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'Packaged request hook is missing'):
                runtime.run_controlled(['pi'], prompt='private task', cwd='.', timeout=10,
                                       config={}, image_files=[])
        launch.assert_not_called()

    def test_old_runtime_is_rejected_before_launch(self):
        process = subprocess.CompletedProcess([], 0, '0.85.0\n', '')
        with patch.object(runtime.subprocess, 'run', return_value=process), \
             patch.object(runtime.subprocess, 'Popen') as launch:
            with self.assertRaisesRegex(ValueError, 'stable version at or above'):
                runtime.run_controlled(['pi'], prompt='private task', cwd='.', timeout=10,
                                       config={}, image_files=[])
        launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
