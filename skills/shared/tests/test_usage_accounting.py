#!/usr/bin/env python3
"""Offline usage observation, identity, and admission checks."""

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_state
import usage_accounting as usage


class UsageAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = {"call_ledger": {"calls": {}, "contexts": {}}}

    def metrics(self, **overrides):
        return {**dict.fromkeys(usage.METRICS, 0), **overrides}

    def snapshot(self, **overrides):
        return {"source_id": "host", "context_id": "coordinator", "epoch_id": "run-1",
                "scope": "coordinator", "sequence": 1, "covers": [], "metrics": self.metrics(), **overrides}

    def call(self, call_id="C1", context="worker", **metrics):
        self.state["call_ledger"]["calls"][call_id] = {
            "status": "failed", "intent": {"route": {"id": "writer", "task_id": "T1"}},
            "observed_usage": {"source_id": "host", "context_id": context, "metrics": self.metrics(**metrics)}}

    def initialize(self, policy):
        policy_path = self.root / "consumo.json"
        policy_path.write_text(json.dumps({"usage_policy": policy}))
        inputs = [{"path": str(policy_path), "content_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest()}]
        digest = hashlib.sha256(json.dumps(inputs, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        plan_path = self.root / "plan.json"
        plan_path.write_text(json.dumps({"approval": {"status": "approved", "scope_digest": digest},
                                       "scope": {"inputs": inputs},
                                       "routes": [{"id": "writer", "task_id": "T1", "model": "fixture", "effort": "high"}]}))
        self.state = {}
        run_state.initialize(self.state, plan_path, "run-1", {"total_role_calls": 4, "writer": 4}, policy_path)
        self.brief = self.root / "brief.md"
        self.brief.write_text("Implement the acceptance contract.")
        return policy_path, plan_path

    def test_legacy_without_policy_allows_unknown_usage(self):
        self.assertTrue(usage.evaluate_budget(self.state)["dispatch_allowed"])
        summary = usage.summarize_usage(self.state)
        self.assertIsNone(summary["metrics"]["input_tokens"]["total"])
        self.assertEqual(summary["scopes"]["coordinator"]["input_tokens"]["unknown_records"], 1)

    def test_cold_start_with_metric_limit_blocks_unknown_coordinator(self):
        result = usage.evaluate_budget(self.state, {"limits": {"input_tokens": 10}})
        self.assertFalse(result["dispatch_allowed"])
        self.assertEqual(result["reasons"][0]["code"], "usage_unknown")

    def test_success_failure_and_coordinator_usage_are_all_counted(self):
        self.call("failure", response_count=3, input_tokens=30, output_tokens=9, reasoning_output_tokens=4,
                  reported_cost_usd=0.1, duration_ms=7)
        self.call("success", response_count=2, input_tokens=20, output_tokens=6, reported_cost_usd=0.2, duration_ms=8)
        self.state["call_ledger"]["calls"]["success"]["status"] = "completed"
        usage.ingest_snapshot(self.state, self.snapshot(metrics=self.metrics(response_count=4, input_tokens=40)))
        result = usage.summarize_usage(self.state)
        self.assertEqual(result["metrics"]["response_count"]["total"], 9)
        self.assertEqual(result["metrics"]["input_tokens"]["total"], 90)
        self.assertEqual(result["metrics"]["output_tokens"]["total"], 15)
        self.assertEqual(result["metrics"]["reasoning_output_tokens"]["total"], 4)
        self.assertEqual(result["metrics"]["duration_ms"]["total"], 15)
        self.assertAlmostEqual(result["metrics"]["reported_cost_usd"]["total"], 0.3)

    def test_receipt_normalization_includes_cache_and_keeps_reasoning_subset(self):
        result = usage.normalize_usage({"response_count": 3, "usage": {
            "input_tokens": 10, "cache_read_input_tokens": 20, "cache_creation_input_tokens": 5,
            "output_tokens": 12, "output_tokens_details": {"thinking_tokens": 7}}})
        self.assertEqual(result["input_tokens"], 35)
        self.assertEqual(result["output_tokens"], 12)
        self.assertEqual(result["response_count"], 3)
        self.assertIsNone(result["reported_cost_usd"])
        self.assertIsNone(usage.normalize_usage({"success": True})["response_count"])

    def test_partial_usage_is_visible_and_blocks_only_required_metrics(self):
        self.call(input_tokens=None, output_tokens=5)
        usage.ingest_snapshot(self.state, self.snapshot())
        total = usage.summarize_usage(self.state)["metrics"]["input_tokens"]
        self.assertEqual(total["measured_sum"], 0)
        self.assertIsNone(total["total"])
        self.assertFalse(usage.evaluate_budget(self.state, {"require_known": ["input_tokens"]})["dispatch_allowed"])
        self.assertTrue(usage.evaluate_budget(self.state, {"limits": {"output_tokens": 10}})["dispatch_allowed"])

    def test_snapshot_replay_and_growth_replace_totals(self):
        first = self.snapshot(metrics=self.metrics(response_count=3, input_tokens=10))
        self.assertEqual(usage.ingest_snapshot(self.state, first)["ingestion"], "new")
        self.assertEqual(usage.ingest_snapshot(self.state, first)["ingestion"], "existing")
        later = {**first, "sequence": 2, "metrics": self.metrics(response_count=5, input_tokens=20)}
        usage.ingest_snapshot(self.state, later)
        self.assertEqual(usage.summarize_usage(self.state)["metrics"]["input_tokens"]["total"], 20)
        self.assertEqual(usage.summarize_usage(self.state)["metrics"]["response_count"]["total"], 5)

    def test_snapshot_conflict_reset_and_stale_sequence_fail_without_mutation(self):
        first = self.snapshot(metrics=self.metrics(input_tokens=10))
        usage.ingest_snapshot(self.state, first)
        before = copy.deepcopy(self.state)
        for bad in ({**first, "metrics": self.metrics(input_tokens=11)},
                    {**first, "sequence": 0},
                    {**first, "sequence": 2, "metrics": self.metrics(input_tokens=9)},
                    {**first, "sequence": 2, "metrics": self.metrics(input_tokens=None)}):
            with self.assertRaises(ValueError):
                usage.ingest_snapshot(self.state, bad)
            self.assertEqual(self.state, before)

    def test_worker_snapshot_replaces_covered_receipts(self):
        self.call(input_tokens=20)
        usage.ingest_snapshot(self.state, self.snapshot())
        row = self.snapshot(context_id="worker", scope="worker", covers=["worker:C1"], metrics=self.metrics(input_tokens=30))
        usage.ingest_snapshot(self.state, row)
        self.assertEqual(usage.summarize_usage(self.state)["metrics"]["input_tokens"]["total"], 30)
        self.call("C2", input_tokens=5)
        self.assertEqual(usage.evaluate_budget(self.state, {"limits": {"input_tokens": 100}})["reasons"][0]["code"],
                         "snapshot_coverage_mismatch")
        usage.ingest_snapshot(self.state, {**row, "sequence": 2, "covers": ["worker:C1", "worker:C2"],
                                          "metrics": self.metrics(input_tokens=35)})
        self.assertEqual(usage.summarize_usage(self.state)["metrics"]["input_tokens"]["total"], 35)

    def test_snapshot_context_source_overlap_and_unknown_record_rejected(self):
        self.call(input_tokens=20)
        base = self.snapshot(context_id="worker", scope="worker", covers=["worker:C1"])
        for bad in ({**base, "context_id": "other"}, {**base, "source_id": "other"},
                    {**base, "covers": ["worker:missing"]}):
            with self.assertRaisesRegex(ValueError, "identity or coverage mismatch"):
                usage.ingest_snapshot(self.state, bad)
        usage.ingest_snapshot(self.state, base)
        with self.assertRaisesRegex(ValueError, "identity or coverage mismatch"):
            usage.ingest_snapshot(self.state, {**base, "epoch_id": "reset"})

    def test_approved_policy_binding_rejects_file_and_state_changes(self):
        path, _ = self.initialize({"limits": {"input_tokens": 50}})
        usage.ingest_snapshot(self.state, self.snapshot())
        self.assertTrue(usage.evaluate_budget(self.state)["dispatch_allowed"])
        self.state["call_ledger"]["usage_policy"]["limits"]["input_tokens"] = 100
        self.assertEqual(usage.evaluate_budget(self.state)["reasons"][0]["code"], "invalid_usage_binding")
        self.state["call_ledger"]["usage_policy"]["limits"]["input_tokens"] = 50
        path.write_text(json.dumps({"usage_policy": {"limits": {"input_tokens": 100}}}))
        self.assertFalse(usage.evaluate_budget(self.state)["dispatch_allowed"])

    def test_scope_digest_supports_unicode_paths_and_rejects_unapproved_input(self):
        path, plan = self.initialize({"require_known": ["output_tokens"]})
        payload = json.loads(plan.read_text())
        unicode_path = path.with_name("consumo_ação.json")
        path.rename(unicode_path)
        payload["scope"]["inputs"][0]["path"] = str(unicode_path)
        payload["approval"]["scope_digest"] = hashlib.sha256(json.dumps(payload["scope"]["inputs"],
            ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertIn("usage_policy", usage.bind_policy(payload, unicode_path))
        payload["approval"]["scope_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "scope digest"):
            usage.bind_policy(payload, unicode_path)

    def test_future_reservation_blocks_but_pending_receipt_and_replay_remain_available(self):
        self.initialize({"limits": {"input_tokens": 10}})
        usage.ingest_snapshot(self.state, self.snapshot())
        run_state.reserve(self.state, "writer", "C1", self.brief, "implementation")
        usage.ingest_snapshot(self.state, self.snapshot(sequence=2, metrics=self.metrics(input_tokens=10)))
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps({"success": False, "call_id": "C1", "input_revision": run_state.sha(self.brief),
            "configured_model": "fixture", "configured_effort": "high", "response_count": 2,
            "usage": {"input_tokens": 5, "output_tokens": 3}}))
        run_state.reconcile(self.state, "C1", receipt)
        self.assertEqual(self.state["call_ledger"]["calls"]["C1"]["observed_usage"]["metrics"]["response_count"], 2)
        self.assertEqual(run_state.reserve(self.state, "writer", "C1", self.brief, "implementation")["status"], "failed")
        with self.assertRaisesRegex(ValueError, "usage budget"):
            run_state.reserve(self.state, "writer", "C2", self.brief, "implementation")
        self.assertEqual(self.state["attempts"]["total_role_calls"], 1)

    def test_subscription_is_account_wide_separate_stale_and_reset_aware(self):
        snapshot = {"source_id": "account", "window_id": "5h", "sequence": 1, "used_percent": 95,
                    "observed_at": "2026-10-16T10:00:00Z", "resets_at": "2026-10-16T15:00:00Z"}
        policy = {"subscription_limits": [{"source_id": "account", "window_id": "5h", "max_used_percent": 90,
                                          "max_age_seconds": 300}]}
        usage.ingest_subscription(self.state, snapshot)
        self.assertEqual(usage.ingest_subscription(self.state, snapshot)["ingestion"], "existing")
        verdict = usage.evaluate_budget(self.state, policy, "2026-10-16T10:00:05Z")
        self.assertEqual(verdict["reasons"][0]["code"], "subscription_budget_exhausted")
        self.assertEqual(verdict["resume_at"], snapshot["resets_at"])
        self.assertEqual(usage.evaluate_budget(self.state, policy, "2026-10-16T10:10:00Z")["reasons"][0]["code"],
                         "subscription_snapshot_stale")
        self.assertEqual(usage.evaluate_budget(self.state, policy, "2026-10-16T15:00:01Z")["reasons"][0]["code"],
                         "subscription_window_expired")
        self.assertIsNone(usage.summarize_usage(self.state)["metrics"]["reported_cost_usd"]["total"])
        fresh = {**snapshot, "used_percent": 2, "sequence": 1, "observed_at": "2026-10-16T15:01:00Z",
                 "resets_at": "2026-10-16T20:00:00Z"}
        usage.ingest_subscription(self.state, fresh)
        self.assertEqual(usage.ingest_subscription(self.state, snapshot)["ingestion"], "existing")
        self.assertTrue(usage.evaluate_budget(self.state, policy, "2026-10-16T15:01:02Z")["dispatch_allowed"])
        self.assertEqual(len(self.state["usage_accounting"]["subscriptions"]), 2)

    def test_subscription_rejects_reset_mismatch_and_unknown(self):
        first = {"source_id": "account", "window_id": "5h", "sequence": 1, "used_percent": 40,
                 "observed_at": "2026-10-16T10:00:00Z", "resets_at": "2026-10-16T15:00:00Z"}
        usage.ingest_subscription(self.state, first)
        for bad in ({**first, "sequence": 2, "used_percent": 30},
                    {**first, "sequence": 2, "resets_at": "2026-10-16T16:00:00Z"}):
            with self.assertRaises(ValueError):
                usage.ingest_subscription(self.state, bad)
        policy = {"subscription_limits": [{"source_id": "missing", "window_id": "5h", "max_used_percent": 90,
                                          "max_age_seconds": 300}]}
        self.assertEqual(usage.evaluate_budget(self.state, policy, "2026-10-16T10:01:00Z")["reasons"][0]["code"],
                         "subscription_usage_unknown")

    def token_log(self, rows):
        path = self.root / "session.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        return path

    def test_raw_token_events_use_baseline_and_repeated_totals_once(self):
        meta = {key: value for key, value in self.snapshot().items() if key != "metrics"}
        baseline = {key: meta[key] for key in ("source_id", "context_id", "epoch_id")}
        baseline["metrics"] = {"input_tokens": 100, "cached_input_tokens": 50,
                               "cache_write_input_tokens": 0, "output_tokens": 20, "reasoning_output_tokens": 10}
        event = {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {
            "input_tokens": 130, "cached_input_tokens": 60, "cache_write_input_tokens": 0,
            "output_tokens": 30, "reasoning_output_tokens": 15}}}}
        path = self.token_log([{"type": "session_meta", "payload": {"id": "coordinator"}},
                               {"type": "message", "payload": {"content": "private text"}}, event, event])
        snapshot = usage.token_log_snapshot(path, meta, baseline)
        usage.ingest_snapshot(self.state, snapshot)
        usage.ingest_snapshot(self.state, snapshot)
        result = usage.summarize_usage(self.state)["metrics"]
        self.assertEqual(result["input_tokens"]["total"], 30)
        self.assertEqual(result["cached_input_tokens"]["total"], 10)
        self.assertEqual(result["cache_write_input_tokens"]["total"], 0)
        self.assertEqual(result["output_tokens"]["total"], 10)
        self.assertEqual(result["reasoning_output_tokens"]["total"], 5)
        self.assertIsNone(result["response_count"]["total"])
        self.assertIsNone(result["reported_cost_usd"]["total"])
        self.assertNotIn("private text", json.dumps(self.state))
        with self.assertRaisesRegex(ValueError, "baseline identity"):
            usage.token_log_snapshot(path, meta, {**baseline, "context_id": "other"})
        with self.assertRaisesRegex(ValueError, "baseline exceeds"):
            usage.token_log_snapshot(path, meta, {**baseline, "metrics": {"input_tokens": 999}})

    def test_impossible_cache_and_reasoning_subsets_are_rejected(self):
        for metrics in (self.metrics(input_tokens=10, cached_input_tokens=8, cache_write_input_tokens=3),
                        self.metrics(output_tokens=4, reasoning_output_tokens=5)):
            with self.assertRaisesRegex(ValueError, "subset"):
                usage.ingest_snapshot(self.state, self.snapshot(metrics=metrics))
        with self.assertRaisesRegex(ValueError, "subset"):
            usage.receipt_usage({"metrics": self.metrics(output_tokens=1, reasoning_output_tokens=2)})

    def test_token_log_detects_context_mismatch_reset_and_baseline_change(self):
        meta = {key: value for key, value in self.snapshot().items() if key != "metrics"}
        baseline = {key: meta[key] for key in ("source_id", "context_id", "epoch_id")}
        baseline["metrics"] = {"input_tokens": 0}
        def event(tokens):
            return {"type": "event_msg", "payload": {"type": "token_count", "info": {"total_token_usage": {
                "input_tokens": tokens}}}}
        with self.assertRaisesRegex(ValueError, "counter reset"):
            usage.token_log_snapshot(self.token_log([event(10), event(9)]), meta, baseline)
        with self.assertRaisesRegex(ValueError, "context differs"):
            usage.token_log_snapshot(self.token_log([{"type": "session_meta", "payload": {"id": "wrong"}}, event(10)]), meta, baseline)
        snapshot = usage.token_log_snapshot(self.token_log([event(10)]), meta, baseline)
        usage.ingest_snapshot(self.state, snapshot)
        changed = {**baseline, "metrics": {"input_tokens": 1}}
        with self.assertRaisesRegex(ValueError, "baseline differs"):
            usage.ingest_snapshot(self.state, usage.token_log_snapshot(self.token_log([event(20)]), {**meta, "sequence": 2}, changed))

    def test_imported_stage_workers_coordinators_and_cumulative_snapshots(self):
        self.call(input_tokens=10)
        worker = self.state["call_ledger"]["calls"].pop("C1")
        coordinator = {"observed_usage": {"source_id": "host", "context_id": "stage-owner", "metrics": self.metrics(input_tokens=5)}}
        stage = {"calls": {"C1": worker}, "coordinator_calls": {"owner": coordinator}, "coverage": ["coordinator"]}
        source = {"call_ledger": {"calls": {"C1": worker}}}
        usage.ingest_snapshot(source, self.snapshot(context_id="worker", scope="worker", covers=["worker:C1"],
                                                    metrics=self.metrics(input_tokens=15)))
        stage["usage_accounting"] = source["usage_accounting"]
        self.state["workflow_measurement"] = {"stage_ledgers": {"planning": stage}}
        usage.ingest_snapshot(self.state, self.snapshot(metrics=self.metrics(input_tokens=2)))
        result = usage.summarize_usage(self.state)
        self.assertEqual(result["anomalies"], [])
        self.assertEqual(result["metrics"]["input_tokens"]["total"], 22)
        self.assertEqual(result["scopes"]["coordinator"]["input_tokens"]["total"], 7)

    def test_cli_snapshot_dry_run_and_query_do_not_write(self):
        state_path = self.root / "state.json"
        state_path.write_text(json.dumps(self.state))
        snapshot_path = self.root / "snapshot.json"
        snapshot_path.write_text(json.dumps(self.snapshot()))
        before = state_path.read_bytes()
        command = [sys.executable, run_state.__file__, "--state", str(state_path)]
        for args in (["--dry-run", "usage-snapshot", "--snapshot", str(snapshot_path)], ["usage-status"]):
            result = subprocess.run(command + args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(state_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
