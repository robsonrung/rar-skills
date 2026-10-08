"""Check comparison arithmetic and refusal of unsupported conclusions."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import execution_metrics as metrics
import workflow_comparison as comparison


def fixture():
    receipt = {"metrics": dict(zip(metrics.FIELDS, (100, 80, 0, 20, 5, 8000, 0.25)))}
    return {"status": "complete", "started_at": "2026-10-08T12:00:00Z", "completed_at": "2026-10-08T12:00:10Z",
            "call_ledger": {"calls": {"a": {"status": "failed", "receipt": copy.deepcopy(receipt),
                                            "reserved_at": "2026-10-08T12:00:00Z", "completed_at": "2026-10-08T12:00:08Z"},
                                      "b": {"status": "completed", "receipt": copy.deepcopy(receipt),
                                            "reserved_at": "2026-10-08T12:00:02Z", "completed_at": "2026-10-08T12:00:10Z"}}},
            "workflow_measurement": {
                "identity": {"case_id": "fixture", "case_kind": "bounded-fix", "source_start_revision": "a" * 40,
                             "requirements_sha256": "b" * 64, "checks_sha256": "c" * 64, "environment_sha256": "d" * 64},
                "worker_calls_complete": True, "coordinator_receipts": [copy.deepcopy(receipt)],
                "approval_wait_intervals": [{"started_at": "2026-10-08T12:00:01Z", "completed_at": "2026-10-08T12:00:04Z"},
                                            {"started_at": "2026-10-08T12:00:03Z", "completed_at": "2026-10-08T12:00:05Z"}],
                "repair_call_ids": ["b"], "command_keys": ["tests@root", "build@root", "tests@root"],
                "acceptance": {"passed": True, "evidence": "fixture acceptance record"},
                "missed_defects": {"count": 0, "evidence": "fixture independent check", "observation_window": "acceptance plus fault probes"}}}


class WorkflowComparisonTests(unittest.TestCase):
    def test_elapsed_worker_sum_wait_union_and_usage_are_separate(self):
        report = comparison.summarize(fixture())
        self.assertEqual(report["workflow_elapsed_ms"], 10000)
        self.assertEqual(report["workers"]["duration_ms"]["measured_sum"], 16000)
        self.assertEqual(report["approval_wait_ms"], 4000)
        self.assertEqual(report["coordinator"]["duration_ms"]["measured_sum"], 8000)
        self.assertEqual(report["workers"]["input_tokens"]["measured_sum"], 200)
        self.assertEqual(report["workers"]["cached_input_tokens"]["measured_sum"], 160)
        self.assertEqual(report["workers"]["reported_cost_usd"]["measured_sum"], 0.5)
        self.assertEqual(report["total_reported_cost_usd"], 0.75)
        self.assertEqual((report["failed_calls"], report["repair_calls"], report["repeated_commands"]), (1, 1, 1))

    def test_matched_deltas_are_candidate_minus_baseline(self):
        before, after = fixture(), fixture()
        after["completed_at"] = "2026-10-08T12:00:12Z"
        after["call_ledger"]["calls"]["b"]["receipt"]["metrics"]["reported_cost_usd"] = 0.1
        report = comparison.compare(before, after)
        self.assertEqual(report["status"], "matched")
        self.assertEqual(report["deltas"]["workflow_elapsed_ms"], 2000)
        self.assertAlmostEqual(report["deltas"]["workers"]["reported_cost_usd"], -0.15)
        self.assertTrue(report["observed_acceptance_match"])
        self.assertEqual(report["quality_equivalence"], "not-established")

    def test_missing_measurements_are_not_zero_or_full_deltas(self):
        after = fixture()
        after["call_ledger"]["calls"]["b"]["receipt"] = None
        for key in ("coordinator_receipts", "repair_call_ids", "command_keys", "approval_wait_intervals"):
            del after["workflow_measurement"][key]
        del after["completed_at"]
        report = comparison.compare(fixture(), after)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["candidate"]["workers"]["input_tokens"],
                         {"measured_sum": 100, "measured_calls": 1, "unknown_calls": 1})
        self.assertIsNone(report["deltas"]["workers"]["input_tokens"])
        self.assertIsNone(report["candidate"]["repair_calls"])
        self.assertIsNone(report["deltas"]["workflow_elapsed_ms"])
        self.assertIsNone(report["deltas"]["coordinator"]["reported_cost_usd"])
        self.assertTrue(report["observed_acceptance_match"])
        self.assertIsNone(report["candidate"]["total_reported_cost_usd"])

    def test_missing_ledger_and_unknown_coverage_cannot_imply_zero_cost(self):
        for key in ("ledger", "coverage"):
            after = fixture()
            if key == "ledger":
                del after["call_ledger"]
            else:
                del after["workflow_measurement"]["worker_calls_complete"]
            report = comparison.compare(fixture(), after)
            self.assertEqual(report["status"], "incomplete")
            self.assertIsNone(report["candidate"]["worker_calls"])
            self.assertIsNone(report["deltas"]["workers"]["reported_cost_usd"])
            self.assertIsNone(report["deltas"]["failed_calls"])

    def test_each_identity_mismatch_blocks_comparison(self):
        for key in comparison.IDENTITY_FIELDS:
            after = fixture()
            value = "routine-feature" if key == "case_kind" else "other" if key == "case_id" else "e" * (40 if key == "source_start_revision" else 64)
            after["workflow_measurement"]["identity"][key] = value
            report = comparison.compare(fixture(), after)
            self.assertEqual(report["status"], "mismatched", key)
            self.assertEqual(report["mismatched_fields"], [key])
            self.assertIsNone(report["deltas"])

    def test_missing_identity_blocks_all_deltas(self):
        after = fixture()
        del after["workflow_measurement"]["identity"]["checks_sha256"]
        report = comparison.compare(fixture(), after)
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["deltas"])
        self.assertFalse(report["observed_acceptance_match"])

    def test_all_requested_case_kinds_are_supported(self):
        for kind in comparison.CASE_KINDS:
            state = fixture()
            state["workflow_measurement"]["identity"]["case_kind"] = kind
            self.assertEqual(comparison.compare(state, copy.deepcopy(state))["status"], "matched")

    def test_cheaper_failed_acceptance_or_missed_defects_is_not_quality_match(self):
        for key in ("acceptance", "defects"):
            after = fixture()
            if key == "acceptance":
                after["workflow_measurement"]["acceptance"]["passed"] = False
            else:
                after["workflow_measurement"]["missed_defects"]["count"] = 1
            after["call_ledger"]["calls"]["b"]["receipt"]["metrics"]["reported_cost_usd"] = 0
            report = comparison.compare(fixture(), after)
            self.assertFalse(report["observed_acceptance_match"])
            self.assertEqual(report["status"], "mismatched")
            self.assertIsNone(report["deltas"])
            self.assertEqual(report["quality_equivalence"], "not-established")

    def test_missing_quality_measurement_blocks_cost_comparison(self):
        for key in ("acceptance", "missed_defects"):
            after = fixture()
            del after["workflow_measurement"][key]
            report = comparison.compare(fixture(), after)
            self.assertEqual(report["status"], "incomplete")
            self.assertIsNone(report["deltas"])
            self.assertFalse(report["observed_acceptance_match"])

    def test_observation_window_mismatch_and_pending_calls(self):
        after = fixture()
        after["workflow_measurement"]["missed_defects"]["observation_window"] = "shorter"
        self.assertEqual(comparison.compare(fixture(), after)["status"], "mismatched")
        after = fixture()
        after["call_ledger"]["calls"]["b"]["status"] = "pending"
        report = comparison.compare(fixture(), after)
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["candidate"]["failed_calls"])
        self.assertIsNone(report["deltas"])
        self.assertIsNone(report["candidate"]["total_reported_cost_usd"])
        after = fixture()
        after["status"] = "running"
        report = comparison.compare(fixture(), after)
        self.assertEqual(report["status"], "incomplete")
        self.assertIsNone(report["deltas"])
        self.assertIsNone(report["candidate"]["total_reported_cost_usd"])

    def test_invalid_data_returns_invalid_without_deltas(self):
        mutations = [lambda s: s.update(completed_at="2026-10-08T11:00:00Z"),
                     lambda s: s.update(started_at="2026-10-08T12:00:00"),
                     lambda s: s["workflow_measurement"].update(repair_call_ids=["absent"]),
                     lambda s: s["workflow_measurement"].update(repair_call_ids=["a", "a"]),
                     lambda s: s["workflow_measurement"].update(command_keys="test"),
                     lambda s: s["workflow_measurement"].update(worker_calls_complete=0),
                     lambda s: s["workflow_measurement"]["acceptance"].update(passed=1),
                     lambda s: s["workflow_measurement"]["missed_defects"].update(count=-1),
                     lambda s: s["workflow_measurement"]["approval_wait_intervals"][0].update(completed_at="2026-10-08T12:00:11Z")]
        for mutate in mutations:
            after = fixture()
            mutate(after)
            report = comparison.compare(fixture(), after)
            self.assertEqual(report["status"], "invalid")
            self.assertIsNone(report["deltas"])

    def test_cli_rejects_inconsistent_call_events(self):
        mutations = [lambda s: s.update(completed_at="2026-10-08T12:00:05Z"),
                     lambda s: s["call_ledger"]["calls"]["a"].update(reserved_at="2026-10-08T11:59:59Z"),
                     lambda s: s["call_ledger"]["calls"]["b"].update(reserved_at="2026-10-08T12:00:11Z"),
                     lambda s: s["call_ledger"]["calls"]["b"].update(completed_at="2026-10-08T12:00:01Z"),
                     lambda s: s["call_ledger"]["calls"]["a"].update(completed_at="2026-10-08T12:00:08")]
        with tempfile.TemporaryDirectory() as directory:
            before, after = Path(directory) / "before.json", Path(directory) / "after.json"
            before.write_text(json.dumps(fixture()))
            for mutate in mutations:
                state = fixture()
                mutate(state)
                after.write_text(json.dumps(state))
                result = subprocess.run([sys.executable, str(SCRIPTS / "workflow_comparison.py"), "--baseline", str(before),
                                         "--candidate", str(after)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["status"], "invalid")
                self.assertIsNone(report["deltas"])
                self.assertEqual(result.stderr, "")

    def test_partial_call_timestamps_remain_unknown_and_check_available_bounds(self):
        state = fixture()
        del state["call_ledger"]["calls"]["a"]["reserved_at"]
        state["call_ledger"]["calls"]["b"]["completed_at"] = None
        report = comparison.compare(fixture(), state)
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(report["candidate"]["call_timing"], {"checked_events": 2, "unknown_events": 2})
        self.assertEqual(report["candidate"]["workflow_elapsed_ms"], 10000)
        del state["started_at"]
        state["call_ledger"]["calls"]["a"]["completed_at"] = "2026-10-08T12:00:11Z"
        self.assertEqual(comparison.compare(fixture(), state)["status"], "invalid")
        state = fixture()
        del state["completed_at"]
        state["call_ledger"]["calls"]["a"]["reserved_at"] = "2026-10-08T11:59:59Z"
        self.assertEqual(comparison.compare(fixture(), state)["status"], "invalid")
        state = fixture()
        del state["started_at"]
        del state["completed_at"]
        state["call_ledger"]["calls"]["b"]["completed_at"] = "2026-10-08T12:00:01Z"
        self.assertEqual(comparison.compare(fixture(), state)["status"], "invalid")

    def test_cli_rejects_malformed_status_types_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = Path(directory) / "before.json", Path(directory) / "after.json"
            before.write_text(json.dumps(fixture()))
            for value in ([], {}, 1, True):
                for target in ("workflow", "call"):
                    state = fixture()
                    record = state if target == "workflow" else state["call_ledger"]["calls"]["a"]
                    record["status"] = value
                    after.write_text(json.dumps(state))
                    result = subprocess.run([sys.executable, str(SCRIPTS / "workflow_comparison.py"), "--baseline", str(before),
                                             "--candidate", str(after)], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stderr, "")
                    report = json.loads(result.stdout)
                    self.assertEqual(report["status"], "invalid")
                    self.assertIsNone(report["deltas"])

    def test_cli_accepts_matched_inputs_and_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps(fixture()))
            command = [sys.executable, str(SCRIPTS / "workflow_comparison.py"), "--baseline", str(path), "--candidate", str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "matched")
            path.write_text("invalid json")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("Cannot read comparison inputs", result.stderr)

    def test_cli_is_read_only_and_returns_nonzero_for_incomplete_input(self):
        with tempfile.TemporaryDirectory() as directory:
            before, after = Path(directory) / "before.json", Path(directory) / "after.json"
            before.write_text(json.dumps(fixture()))
            after.write_text("{}")
            original = (before.read_bytes(), after.read_bytes())
            process = subprocess.run([sys.executable, str(SCRIPTS / "workflow_comparison.py"), "--baseline", str(before),
                                      "--candidate", str(after)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 1, process.stderr)
            self.assertEqual(json.loads(process.stdout)["status"], "incomplete")
            self.assertEqual(original, (before.read_bytes(), after.read_bytes()))


class MetricsTests(unittest.TestCase):
    def test_provider_cache_arithmetic_and_nested_details(self):
        row = metrics.normalize_metrics({"usage": {"input_tokens": 10, "cache_read_input_tokens": 70,
                                                     "cache_creation_input_tokens": 20}})
        self.assertEqual(row["input_tokens"], 100)
        row = metrics.normalize_metrics({"usage": {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 70},
                                                     "output_tokens_details": {"reasoning_tokens": 5}}})
        self.assertEqual((row["input_tokens"], row["cached_input_tokens"], row["reasoning_output_tokens"]), (100, 70, 5))
        self.assertIsNone(row["reported_cost_usd"])

    def test_invalid_values_and_partial_cache_remain_unknown(self):
        for value in (None, True, -1, float("nan"), float("inf"), "42"):
            self.assertIsNone(metrics.normalize_metrics({"metrics": {"input_tokens": value}})["input_tokens"])
        self.assertIsNone(metrics.normalize_metrics({"usage": {"input_tokens": 10, "cache_read_input_tokens": 70}})["input_tokens"])
        self.assertTrue(all(value is None for value in metrics.normalize_metrics(None).values()))


if __name__ == "__main__":
    unittest.main()
