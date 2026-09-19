#!/usr/bin/env python3
"""Offline crash, receipt, context and usage tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import context_packet
import execution_metrics
import run_state as ledger


class RunStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "state.json"
        self.plan = self.root / "plan.json"
        self.route = {"id": "T1-writer", "task_id": "T1", "model": "fixture-model", "effort": "high"}
        self.plan.write_text(json.dumps({"approval": {"status": "approved"}, "routes": [self.route, {**self.route, "id": "T1-reviewer"}]}))
        self.brief = self.root / "brief.md"
        self.brief.write_text("Build the bounded change.")
        self.limits = {"total_role_calls": 3, "T1-writer": 2, "T1-reviewer": 2}
        with ledger.locked(self.path) as state:
            ledger.initialize(state, self.plan, "run-1", self.limits)

    def reserve(self, call="call-1", route="T1-writer", setup=None):
        with ledger.locked(self.path) as state:
            return ledger.reserve(state, route, call, self.brief, "implementation", setup)

    def receipt(self, call="call-1", context="context-1"):
        path = self.root / (call + ".json")
        path.write_text(json.dumps({"success": True, "call_id": call, "input_revision": ledger.sha(self.brief),
                                    "configured_model": "fixture-model", "configured_effort": "high", "context_id": context,
                                    "usage": {"input_tokens": 100, "cached_input_tokens": 90, "output_tokens": 10},
                                    "agent_message": "Completed."}))
        return path

    def test_crash_after_reservation_does_not_reset_or_duplicate_attempt(self):
        self.reserve()
        self.reserve()
        state = json.loads(self.path.read_text())
        self.assertEqual(state["attempts"]["total_role_calls"], 1)
        with self.assertRaisesRegex(ValueError, "pending call"):
            self.reserve("call-2")
        receipt = self.receipt()
        with ledger.locked(self.path) as state:
            ledger.reconcile(state, "call-1", receipt)
        with ledger.locked(self.path) as state:
            ledger.reconcile(state, "call-1", receipt)
        state = json.loads(self.path.read_text())
        self.assertEqual(len(state["steps"]), 1)
        self.assertEqual(ledger.status(state)["calls"]["call-1"]["status"], "completed")
        self.reserve("call-2")

    def test_wrong_receipt_and_reused_call_id_fail_without_state_write(self):
        self.reserve()
        before = self.path.read_bytes()
        receipt = self.receipt("another-call")
        with self.assertRaisesRegex(ValueError, "another call"):
            with ledger.locked(self.path) as state:
                ledger.reconcile(state, "call-1", receipt)
        self.assertEqual(self.path.read_bytes(), before)
        self.brief.write_text("different input")
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.reserve()

    def test_context_resolves_only_matching_setup_and_receipt(self):
        self.reserve(setup="queued-1")
        event = self.root / "event.json"
        event.write_text(json.dumps({"setup_reference": "queued-2", "call_id": "call-1", "context_id": "real-task"}))
        with self.assertRaisesRegex(ValueError, "queued setup"):
            with ledger.locked(self.path) as state:
                ledger.resolve_context(state, "call-1", event)
        raw = self.root / "raw-host-event.json"
        raw.write_text(json.dumps({"context_id": "real-task"}))
        event.write_text(json.dumps({"setup_reference": "queued-1", "call_id": "call-1", "context_id": "real-task",
                                     "evidence": {"path": str(raw), "sha256": ledger.sha(raw)}}))
        with ledger.locked(self.path) as state:
            self.assertEqual(ledger.resolve_context(state, "call-1", event), "real-task")
        with self.assertRaisesRegex(ValueError, "recorded role"):
            with ledger.locked(self.path) as state:
                ledger.reconcile(state, "call-1", self.receipt())
        with ledger.locked(self.path) as state:
            ledger.reconcile(state, "call-1", self.receipt(context="real-task"))

    def test_ceiling_and_independent_contexts_survive_resume(self):
        for n in (1, 2):
            call = f"call-{n}"
            self.reserve(call)
            with ledger.locked(self.path) as state:
                ledger.reconcile(state, call, self.receipt(call))
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.reserve("call-3")
        self.reserve("review-1", "T1-reviewer")
        with self.assertRaisesRegex(ValueError, "another role"):
            with ledger.locked(self.path) as state:
                ledger.reconcile(state, "review-1", self.receipt("review-1"))

    def test_existing_counters_are_preserved_and_unapproved_plan_rejected(self):
        state = {"run_id": "run-1", "attempts": {"total_role_calls": 3}, "steps": [{"step": "earlier"}]}
        ledger.initialize(state, self.plan, "run-1", self.limits)
        with self.assertRaisesRegex(ValueError, "ceiling"):
            ledger.reserve(state, "T1-writer", "call", self.brief, "implementation")
        self.assertEqual(state["steps"], [{"step": "earlier"}])
        self.plan.write_text(json.dumps({"approval": {"status": "draft"}}))
        with self.assertRaisesRegex(ValueError, "approved"):
            ledger.initialize({}, self.plan, "new", self.limits)

    def test_cli_dry_run_does_not_create_ledger(self):
        target = self.root / "absent.json"
        limits = self.root / "limits.json"
        limits.write_text(json.dumps(self.limits))
        proc = subprocess.run([sys.executable, ledger.__file__, "--state", str(target), "--dry-run", "init",
                               "--plan", str(self.plan), "--run-id", "new", "--limits", str(limits)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertFalse(target.exists())

    def test_failed_call_without_session_is_counted_without_binding_context(self):
        self.reserve()
        receipt = self.receipt()
        data = json.loads(receipt.read_text())
        data.update(success=False, context_id=None)
        receipt.write_text(json.dumps(data))
        with ledger.locked(self.path) as state:
            ledger.reconcile(state, "call-1", receipt)
        state = json.loads(self.path.read_text())
        self.assertEqual(state["call_ledger"]["calls"]["call-1"]["status"], "failed")
        self.assertEqual(state["call_ledger"]["contexts"], {})
        self.assertEqual(ledger.status(state)["metrics_by_task"]["T1"]["input_tokens"]["measured_sum"], 100)
        self.reserve("call-2")

    def test_runner_dispatch_metadata_can_be_reconciled(self):
        self.reserve()
        receipt = self.receipt()
        data = json.loads(receipt.read_text())
        data["dispatch_metadata"] = {key: data.pop(key) for key in ("call_id", "input_revision")}
        data["session_id"] = data.pop("context_id")
        receipt.write_text(json.dumps(data))
        with ledger.locked(self.path) as state:
            ledger.reconcile(state, "call-1", receipt)

    def test_invalid_terminal_runner_output_is_failed(self):
        import runner_jobs
        result = self.root / "result.json"
        for output in ("partial json", "[]", '{"success":"yes"}'):
            result.write_text(output)
            self.assertEqual(runner_jobs.job_status(self.root, {"result_file": str(result)}), "failed")

    def test_native_capture_preserves_exact_text_and_binds_turn(self):
        import native_completion
        raw = self.root / "wait.json"
        dispatch = self.root / "dispatch.json"
        output = self.root / "captured.json"
        poll = {"thread": {"id": "task-1", "hostId": "local"},
                "latestTurn": {"id": "turn-1", "status": "completed", "error": None, "durationMs": 25},
                "latestAssistantMessage": {"turnId": "turn-1", "phase": "final_answer", "text": 'Exact text: ```json\n{}\n```'}}
        raw.write_text(json.dumps({"content": [{"type": "text", "text": json.dumps({"polls": [poll]})}], "isError": False}))
        dispatch.write_text(json.dumps({"host": "desktop-local", "transport": "thread", "role": "reviewer", "task_id": "T1",
                        "configured_model": "fixture-model", "configured_effort": "high", "tool_policy": "read-only",
                        "call_id": "call-1", "input_revision": "sha"}))
        native_completion.capture(raw, dispatch, "task-1", "local", "turn-1", 1, output)
        captured = native_completion.load_record(output)
        self.assertEqual(captured["agent_message"], poll["latestAssistantMessage"]["text"])
        self.assertEqual(captured["metrics"]["duration_ms"], 25)
        self.assertIsNone(captured["metrics"]["input_tokens"])
        self.assertEqual(captured["model_verification"], "unverified")
        for context, host, turn in (("other", "local", "turn-1"), ("task-1", "remote", "turn-1"), ("task-1", "local", "turn-2")):
            with self.assertRaises(ValueError):
                native_completion.capture(raw, dispatch, context, host, turn, 1, self.root / "wrong.json")
        poll["latestAssistantMessage"]["phase"] = "commentary"
        raw.write_text(json.dumps({"polls": [poll]}))
        with self.assertRaisesRegex(ValueError, "final message"):
            native_completion.capture(raw, dispatch, "task-1", "local", "turn-1", 1, self.root / "wrong.json")

    def test_metrics_preserve_unknown_and_do_not_double_count_reasoning(self):
        normalized = execution_metrics.normalize_metrics({"usage": {"input_tokens": 5, "cache_read_input_tokens": 80,
                    "cache_creation_input_tokens": 15, "output_tokens": 20, "output_tokens_details": {"thinking_tokens": 10}}})
        self.assertEqual(normalized["input_tokens"], 100)
        self.assertEqual(normalized["output_tokens"], 20)
        totals = execution_metrics.aggregate_metrics([{"receipt": {"metrics": normalized}}, {"receipt": {}}])
        self.assertEqual(totals["input_tokens"], {"measured_sum": 100, "measured_calls": 1, "unknown_calls": 1})
        self.assertEqual(totals["reported_cost_usd"]["unknown_calls"], 2)

    def test_decision_packet_detects_stale_decisions_and_oversized_briefs(self):
        sources = [{"path": str(self.brief), "authority": "decision", "locator": "Acceptance"}]
        notes = self.root / "notes.md"
        notes.write_text("Use the current acceptance and listed evidence.")
        packet = context_packet.prepare(notes, sources, self.root / "packet.json")
        context_packet.verify(packet, notes)
        self.brief.write_text("Changed access rules.")
        with self.assertRaisesRegex(ValueError, "decision source changed"):
            context_packet.verify(packet)
        with self.assertRaisesRegex(ValueError, "limit"):
            context_packet.prepare(notes, sources, self.root / "large.json", max_bytes=5)

    def test_packet_status_changes_do_not_change_acceptance(self):
        self.brief.write_text("Acceptance\n**Status:** ready-for-agent\n")
        notes = self.root / "notes.md"
        notes.write_text("Bounded notes")
        packet = context_packet.prepare(notes, [{"path": str(self.brief), "authority": "decision", "locator": "Acceptance"}], self.root / "packet.json")
        self.brief.write_text("Acceptance\n**Status:** done\n")
        context_packet.verify(packet)
        notes.write_text("Stale replacement notes")
        with self.assertRaisesRegex(ValueError, "brief changed"):
            context_packet.verify(packet)


if __name__ == "__main__":
    unittest.main()
