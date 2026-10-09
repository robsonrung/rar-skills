"""Check adapter prompt boundaries and retained dispatch receipts offline."""
import hashlib
import importlib.util
import json
import shlex
from pathlib import Path
import sys
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from skill_paths import runner_script


class RunnerPromptTests(unittest.TestCase):
    def runner(self, name):
        spec = importlib.util.spec_from_file_location('prompt_test_' + name, runner_script(name, root=SCRIPTS.parents[1]))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_producers_keep_dispatch_data_outside_prompt_and_measure_adapter_text(self):
        for name in ('codex', 'claude', 'grok', 'gemini', 'pi'):
            with self.subTest(name=name):
                module = self.runner(name)
                metadata = {'prompt_context': {'acceptance': 'Preserve file order'},
                            'execution_provenance': {'resources': ['private-record']},
                            'input_revision': 'bound-input', 'request_receipt': {'id': 'request-1'}}
                with mock.patch.object(module.shutil, 'which', return_value=None):
                    result = getattr(module, 'run_' + name)(
                        'Review the change', role='codereviewer', metadata_json=json.dumps(metadata), disable_fallback=True)
                self.assertEqual(result['dispatch_metadata'], metadata)
                self.assertFalse(result['success'])
                command = result.get('command', '')
                self.assertNotIn('private-record', command)
                self.assertNotIn('bound-input', command)
                self.assertIn('Preserve file order', command)
                measured = result['adapter_input_measurement']
                self.assertEqual(measured['scope'], 'adapter_rendered_input')
                self.assertGreater(measured['utf8_bytes'], len('Review the change'))
                self.assertEqual(len(measured['sha256']), 64)
                parts = shlex.split(command)
                flag = {'claude': '-p', 'grok': '-p', 'gemini': '--print'}.get(name)
                rendered = parts[parts.index(flag) + 1] if flag else parts[-1]
                self.assertEqual(measured['utf8_bytes'], len(rendered.encode('utf-8')))
                self.assertEqual(measured['sha256'], hashlib.sha256(rendered.encode('utf-8')).hexdigest())

    def test_legacy_user_metadata_is_still_role_context(self):
        for name in ('codex', 'claude', 'grok', 'gemini', 'pi'):
            with self.subTest(name=name):
                module = self.runner(name)
                extra = {'output_schema': None, 'tool_mode': module.TOOL_MODE_RESTRICTED} if name == 'pi' else {}
                prompt = module.build_prompt('Task', [], None, None, '{"scope":"User detail"}', **extra)
                self.assertIn('User detail', prompt)
                filtered = module.build_prompt('Task', [], None, None,
                    '{"scope":"User detail","execution_provenance":{"resources":["private-record"]},"request_receipt":{"id":"r1"}}', **extra)
                self.assertIn('User detail', filtered)
                self.assertNotIn('private-record', filtered)
                self.assertNotIn('request_receipt', filtered)
                empty = module.build_prompt('Task', [], None, None, '{"prompt_context":{},"call_id":"bookkeeping"}', **extra)
                self.assertNotIn('bookkeeping', empty)

    def test_adapter_overhead_enforces_launcher_budget_before_provider_start(self):
        for name in ('codex', 'claude', 'grok', 'gemini', 'pi'):
            with self.subTest(name=name):
                module = self.runner(name)
                metadata = {'prompt_context': {}, 'input_measurement': {'max_bytes': 5}}
                with mock.patch.object(module.subprocess, 'run') as run, mock.patch.object(module.shutil, 'which', return_value='/unused'):
                    result = getattr(module, 'run_' + name)(
                        'Task', role='codereviewer', metadata_json=json.dumps(metadata), disable_fallback=True)
                self.assertFalse(result['success'])
                self.assertEqual(result['dispatch_metadata'], metadata)
                self.assertGreater(result['adapter_input_measurement']['utf8_bytes'], 5)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
