"""Preserve missing usage across all completed request events."""
import importlib.util
import json
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/run_pi.py'
spec = importlib.util.spec_from_file_location('usage_totals_runner', path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class UsageTotalsTests(unittest.TestCase):
    def stream(self, *usages):
        messages = [{'role': 'assistant', 'usage': value} for value in usages]
        return '\n'.join(json.dumps(event) for event in [
            *({'type': 'message_end', 'message': value} for value in messages),
            {'type': 'agent_end', 'messages': messages}])

    def usage(self):
        return {'input': 10, 'output': 2, 'cacheRead': 3, 'cacheWrite': 0, 'totalTokens': 15,
                'cost': {'input': 0.01, 'output': 0.01, 'cacheRead': 0, 'cacheWrite': 0, 'total': 0.02}}

    def test_missing_field_stays_unknown_in_either_request_order(self):
        for group, key in ((None, 'input'), (None, 'output'), (None, 'cacheRead'), (None, 'cacheWrite'),
                           (None, 'totalTokens'), ('cost', 'input'), ('cost', 'output'),
                           ('cost', 'cacheRead'), ('cost', 'cacheWrite'), ('cost', 'total')):
            complete, partial = self.usage(), self.usage()
            del (partial[group] if group else partial)[key]
            for usages in ((complete, partial), (partial, complete)):
                with self.subTest(group=group, key=key, usages=usages):
                    totals = runner.total_native_usage(self.stream(*usages))
                    self.assertIsNone((totals[group] if group else totals)[key])
                    self.assertEqual(totals['output'] if key != 'output' or group else totals['input'],
                                     4 if key != 'output' or group else 20)

    def test_missing_usage_or_cost_is_not_a_partial_total(self):
        for missing in (None, {}):
            totals = runner.total_native_usage(self.stream(self.usage(), missing))
            self.assertIsNone(totals['input'])
            self.assertIsNone(totals['cost']['total'])
        partial = self.usage()
        del partial['cost']
        totals = runner.total_native_usage(self.stream(self.usage(), partial))
        self.assertEqual(totals['input'], 20)
        self.assertTrue(all(value is None for value in totals['cost'].values()))

    def test_known_zero_and_terminal_summary_are_counted_correctly(self):
        totals = runner.total_native_usage(self.stream(self.usage(), self.usage()))
        self.assertEqual(totals['cost']['total'], 0.04)
        self.assertEqual(totals['cacheRead'], 6)
        self.assertEqual(totals['cacheWrite'], 0)
        self.assertEqual(totals['cost']['cacheWrite'], 0)
        self.assertEqual(totals['totalTokens'], 30)
        self.assertEqual(runner.total_native_usage(''), {})


if __name__ == '__main__':
    unittest.main()
