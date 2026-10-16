#!/usr/bin/env python3
"""Offline event, receipt, checkpoint, usage and host proposal contracts."""
import argparse
import copy
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_state
import workflow_controller as controller


class ControllerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.plan = self.root / "plan.json"
        self.brief = self.root / "brief.md"
        self.brief.write_text("Implement the contract.")
        self.route = {"id": "T1-writer", "task_id": "T1", "model": "fixture-model", "effort": "high"}
        self.plan.write_text(json.dumps({"approval": {"status": "approved"}, "routes": [self.route]}))
        self.state = {}
        run_state.initialize(self.state, self.plan, "run-1", {"total_role_calls": 3, "T1-writer": 3})
        run_state.reserve(self.state, "T1-writer", "call-1", self.brief, "implementation")
        self.ledger = self.root / "state.json"
        run_state.atomic_write(self.ledger, self.state)
        self.events = self.root / "events.jsonl"
        self.events.touch()
        self.checkpoint = self.root / "controller.json"
        self.args = argparse.Namespace(root=str(self.root), ledger=str(self.ledger), queue=str(self.root / "queue.json"),
                                      routing_plan=str(self.plan), checkpoint=str(self.checkpoint), events=str(self.events),
                                      limit=100, timeout=0.12, interval=0.05)
        self.schedule = {"ready": [{"id": "T2"}], "active": [{"id": "T1"}], "integrated": [],
                         "blocked": [], "required_integration": []}
        patcher = mock.patch.object(controller.task_queue, "schedule", return_value=self.schedule)
        patcher.start()
        self.addCleanup(patcher.stop)

    def event(self, kind="status", identifier="event-1", **values):
        value = {"id": identifier, "kind": kind, "source": "fixture-host", "cursor": identifier}
        value.update(values or {"call_id": "call-1", "status": "running"})
        return value

    def append(self, event):
        with self.events.open("a") as stream:
            stream.write(json.dumps(event) + "\n")

    def receipt(self, *, success=True, **overrides):
        path = self.root / "receipt.json"
        value = {"success": success, "call_id": "call-1", "input_revision": run_state.sha(self.brief),
                 "configured_model": "fixture-model", "configured_effort": "high", "context_id": "context-1",
                 "usage": {"input_tokens": 100, "output_tokens": 10}, **overrides}
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": run_state.sha(path)}

    def apply(self, acknowledge=True):
        with controller.lock(self.checkpoint), controller.lock(self.ledger):
            result = controller.cycle(self.args, apply=True)
        if acknowledge:
            self.acknowledge(result)
        return result

    def acknowledge(self, result):
        identities = [item["id"] for item in [*result["actions"], *result["sidebar_actions"]]]
        identities.extend(result["superseded_action_ids"])
        return controller.acknowledge(self.checkpoint, identities) if identities else None

    def kinds(self, result):
        return {item["kind"] for item in result["actions"]}

    def test_preview_is_read_only_and_apply_deduplicates_unchanged_status(self):
        self.append(self.event())
        before = self.ledger.read_bytes()
        preview = controller.cycle(self.args)
        self.assertEqual(preview["mode"], "preview")
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse(self.checkpoint.exists())
        first = self.apply()
        self.assertEqual(first["status"], "actionable")
        self.assertTrue(all(len(action["id"]) == 24 for action in first["actions"]))
        self.append(self.event(identifier="same-status"))
        second = self.apply()
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(second["actions"], [])
        self.assertEqual(second["sidebar_actions"], [])
        self.assertEqual(second["cursors"]["fixture-host"], "same-status")

    def test_completed_status_requires_receipt_and_cannot_complete_queue(self):
        self.append(self.event(status="completed", call_id="call-1"))
        result = self.apply()
        self.assertIn("receipt_required", self.kinds(result))
        self.assertNotIn("call_completed", self.kinds(result))
        self.assertNotIn("task_integrated", self.kinds(result))
        self.assertEqual(json.loads(self.ledger.read_text())["call_ledger"]["calls"]["call-1"]["status"], "pending")
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt()))
        preview = controller.cycle(self.args)
        self.assertFalse(preview["dispatch_allowed"])
        self.assertNotIn("ready", self.kinds(preview))
        result = self.apply()
        self.assertIn("call_completed", self.kinds(result))
        self.assertNotIn("task_integrated", self.kinds(result))
        self.assertEqual(len(json.loads(self.ledger.read_text())["steps"]), 1)

    def test_invalid_receipt_stops_cursor_and_can_resume_after_receipt_arrives(self):
        self.append(self.event())
        valid_offset = self.events.stat().st_size
        ref = self.receipt()
        receipt = Path(ref["path"])
        saved = receipt.read_bytes()
        receipt.unlink()
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=ref))
        result = self.apply()
        self.assertEqual(result["cursor"], valid_offset)
        self.assertTrue(result["event_blocked"])
        self.assertIn("receipt_invalid", self.kinds(result))
        unchanged = self.apply()
        self.assertEqual(unchanged["actions"], [])
        receipt.write_bytes(saved)
        resumed = self.apply()
        self.assertFalse(resumed["event_blocked"])
        self.assertIn("call_completed", self.kinds(resumed))
        self.assertEqual(resumed["cursor"], self.events.stat().st_size)

    def test_wrong_receipt_cannot_change_ledger(self):
        before = self.ledger.read_bytes()
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt(input_revision="incorrect")))
        result = self.apply()
        self.assertEqual(result["cursor"], 0)
        self.assertIn("receipt_invalid", self.kinds(result))
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_failed_receipt_is_reconciled_and_reported_once(self):
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt(success=False)))
        result = self.apply()
        self.assertIn("call_failed", self.kinds(result))
        self.assertNotIn("task_integrated", self.kinds(result))
        self.assertEqual(self.apply()["actions"], [])

    def test_ledger_saved_before_checkpoint_crash_replays_without_duplicate_step(self):
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt()))
        original = run_state.atomic_write
        def crash_checkpoint(path, value, **kwargs):
            if Path(path) == self.checkpoint:
                raise OSError("simulated crash")
            original(path, value, **kwargs)
        with mock.patch.object(run_state, "atomic_write", side_effect=crash_checkpoint):
            with self.assertRaisesRegex(OSError, "simulated crash"):
                self.apply()
        self.assertFalse(self.checkpoint.exists())
        result = self.apply()
        self.assertIn("call_completed", self.kinds(result))
        self.assertEqual(len(json.loads(self.ledger.read_text())["steps"]), 1)
        self.assertEqual(self.apply()["actions"], [])

    def test_saved_outbox_recovers_after_checkpoint_publication_before_delivery(self):
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt()))
        original = run_state.atomic_write
        def saved_then_crashed(path, value, **kwargs):
            original(path, value, **kwargs)
            if Path(path) == self.checkpoint:
                raise OSError("crash before delivery")
        with mock.patch.object(run_state, "atomic_write", side_effect=saved_then_crashed):
            with self.assertRaisesRegex(OSError, "crash before delivery"):
                self.apply(acknowledge=False)
        saved = json.loads(self.checkpoint.read_text())
        saved_ids = list(saved["outbox"])
        replay = self.apply(acknowledge=False)
        replay_ids = [item["id"] for item in [*replay["actions"], *replay["sidebar_actions"]]]
        self.assertEqual(set(replay_ids), set(saved_ids))
        self.assertIn("call_completed", self.kinds(replay))
        self.assertEqual(len(json.loads(self.ledger.read_text())["steps"]), 1)
        self.assertTrue(all(item["persisted"] for item in replay["actions"]))
        first_ack = self.acknowledge(replay)
        second_ack = self.acknowledge(replay)
        self.assertEqual(first_ack["new_acknowledgements"], len(saved_ids))
        self.assertEqual(second_ack["new_acknowledgements"], 0)
        self.assertEqual(self.apply(acknowledge=False)["actions"], [])

    def test_ready_return_after_block_has_new_occurrence_and_stale_ready_is_withheld(self):
        first = self.apply(acknowledge=False)
        first_ready = next(item for item in first["actions"] if item["kind"] == "ready")
        self.schedule["ready"] = []
        self.schedule["blocked"] = [{"id": "T2", "reasons": ["dependency changed"]}]
        blocked = self.apply(acknowledge=False)
        self.assertNotIn("ready", self.kinds(blocked))
        self.assertIn(first_ready["id"], blocked["superseded_action_ids"])
        self.assertTrue(json.loads(self.checkpoint.read_text())["outbox"][first_ready["id"]]["superseded"])
        self.schedule["ready"] = [{"id": "T2"}]
        self.schedule["blocked"] = []
        resumed = self.apply(acknowledge=False)
        next_ready = next(item for item in resumed["actions"] if item["kind"] == "ready")
        self.assertNotEqual(first_ready["id"], next_ready["id"])
        self.assertIn(first_ready["id"], resumed["superseded_action_ids"])
        self.acknowledge(resumed)
        self.assertEqual(self.apply(acknowledge=False)["actions"], [])

    def test_preview_action_ids_are_unpersisted_and_match_apply(self):
        preview = controller.cycle(self.args)
        self.assertTrue(preview["actions"])
        self.assertTrue(all(not item["persisted"] for item in preview["actions"]))
        with self.assertRaisesRegex(ValueError, "checkpoint is missing"):
            controller.acknowledge(self.checkpoint, [preview["actions"][0]["id"]])
        applied = self.apply(acknowledge=False)
        self.assertEqual([item["id"] for item in preview["actions"]], [item["id"] for item in applied["actions"]])
        self.assertTrue(all(item["persisted"] for item in applied["actions"]))
        self.acknowledge(applied)
        self.append(self.event("decision", "waiting-1", task_id="T1", status="waiting"))
        preview = controller.cycle(self.args)
        proposed = next(item for item in preview["actions"] if item["kind"] == "user_decision")
        before = self.checkpoint.read_bytes()
        with self.assertRaisesRegex(ValueError, "unknown action"):
            controller.acknowledge(self.checkpoint, [proposed["id"]])
        self.assertEqual(self.checkpoint.read_bytes(), before)

    def test_cli_acknowledges_only_explicit_saved_ids(self):
        result = self.apply(acknowledge=False)
        identity = result["actions"][0]["id"]
        command = [sys.executable, controller.__file__, "ack", "--checkpoint", str(self.checkpoint), "--id", identity]
        for expected_new in (1, 0):
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)["new_acknowledgements"], expected_new)
        saved = json.loads(self.checkpoint.read_text())
        self.assertNotIn(identity, saved["outbox"])
        self.assertTrue(saved["outbox"])

    def test_event_identity_uses_source_and_id_without_separator_collisions(self):
        one = self.event(identifier="b:c")
        one["source"] = "a"
        two = self.event(identifier="c")
        two["source"] = "a:b"
        self.append(one)
        self.append(two)
        result = self.apply()
        self.assertEqual(result["cursor"], self.events.stat().st_size)
        self.assertEqual(len(json.loads(self.checkpoint.read_text())["seen"]), 2)

    def test_wait_reports_time_based_budget_change_at_bound(self):
        self.apply()
        allowed = {"decision": "allow", "dispatch_allowed": True, "reasons": [], "resume_at": None}
        blocked = {"decision": "block", "dispatch_allowed": False,
                   "reasons": [{"code": "subscription_snapshot_stale"}], "resume_at": None}
        with mock.patch.object(controller.usage_accounting, "evaluate_budget", side_effect=[allowed, blocked, blocked]):
            result = controller.wait(self.args)
        self.assertEqual(result["status"], "actionable")
        self.assertEqual(result["budget"]["decision"], "block")
        self.assertNotIn("ready", self.kinds(result))

    def test_event_id_reuse_and_event_source_replacement_fail_closed(self):
        self.append(self.event())
        self.apply()
        self.append(self.event(status="completed", call_id="call-1"))
        with self.assertRaisesRegex(ValueError, "reused"):
            self.apply()
        replacement = self.root / "replacement"
        replacement.write_bytes(self.events.read_bytes())
        replacement.replace(self.events)
        with self.assertRaisesRegex(ValueError, "replaced"):
            self.apply()

    def test_partial_tail_timeout_and_event_arrival(self):
        self.apply()
        with self.events.open("a") as stream:
            stream.write('{"id":')
        before = time.monotonic()
        result = controller.wait(self.args)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["actions"], [])
        self.assertLess(time.monotonic() - before, 0.7)
        self.events.write_text("")
        event = self.event(status="completed", call_id="call-1")
        writer = threading.Timer(0.03, lambda: self.append(event))
        writer.start()
        self.addCleanup(writer.join)
        result = controller.wait(self.args)
        self.assertIn("receipt_required", self.kinds(result))

    def test_wait_does_not_repeat_queue_projection_while_source_is_unchanged(self):
        self.apply()
        with mock.patch.object(controller.task_queue, "schedule", return_value=self.schedule) as schedule:
            result = controller.wait(self.args)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(schedule.call_count, 1)

    def test_usage_ceiling_blocks_new_ready_work_but_allows_completion(self):
        state = json.loads(self.ledger.read_text())
        policy_file = self.root / "usage-policy.json"
        policy_file.write_text(json.dumps({"usage_policy": {"limits": {"input_tokens": 50}}}))
        plan = json.loads(self.plan.read_text())
        inputs = [{"path": str(policy_file), "content_sha256": controller.task_queue.canonical_text_sha256(policy_file.read_text())}]
        plan["scope"] = {"inputs": inputs}
        plan["approval"]["scope_digest"] = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.plan.write_text(json.dumps(plan))
        state["call_ledger"]["plan"]["sha256"] = run_state.sha(self.plan)
        state["call_ledger"].update(controller.usage_accounting.bind_policy(plan, policy_file))
        state["workflow_measurement"]["coverage"] = ["coordinator"]
        run_state.atomic_write(self.ledger, state)
        self.append(self.event("receipt", "receipt-1", call_id="call-1", receipt=self.receipt()))
        result = self.apply()
        self.assertIn("call_completed", self.kinds(result))
        self.assertFalse(result["dispatch_allowed"])
        self.assertNotIn("ready", self.kinds(result))
        self.assertEqual(result["budget"]["decision"], "block")
        self.assertIn("budget_exhausted", {reason["code"] for reason in result["budget"]["reasons"]})

    def test_tampered_usage_policy_blocks_new_ready_work(self):
        state = json.loads(self.ledger.read_text())
        state["call_ledger"]["usage_policy"] = {"limits": {"input_tokens": 50}}
        run_state.atomic_write(self.ledger, state)
        result = self.apply()
        self.assertNotIn("ready", self.kinds(result))
        self.assertFalse(result["dispatch_allowed"])
        self.assertEqual(result["budget"]["reasons"][0]["code"], "invalid_usage_binding")

    def test_sidebar_changes_order_by_waiting_active_complete_then_number(self):
        self.schedule.update(ready=[{"id": "T10"}], active=[{"id": "T2"}], integrated=["T1"])
        self.append(self.event("decision", "decision-1", task_id="T10", status="waiting"))
        result = self.apply()
        order = next(item for item in result["sidebar_actions"] if item["kind"] == "reorder_tasks")
        self.assertEqual(order["task_ids"], ["T10", "T2", "T1"])
        self.assertIn("user_decision", self.kinds(result))
        self.assertNotIn("ready", self.kinds(result))
        self.assertEqual(self.apply()["sidebar_actions"], [])

    def test_legacy_state_preserves_unknown_fields_and_does_not_create_authority(self):
        self.ledger.write_text(json.dumps({"status": "running", "steps": [{"old": True}], "custom": {"keep": 1}}))
        before = self.ledger.read_bytes()
        with mock.patch.object(controller.task_queue, "schedule", side_effect=ValueError("ledger has no call_ledger")):
            result = self.apply()
        self.assertIn("queue_error", self.kinds(result))
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse(any(item["kind"] == "ready" for item in result["actions"]))

    def test_shell_or_tool_fields_are_rejected_as_data(self):
        self.append({**self.event(), "command": "echo unsafe"})
        with self.assertRaisesRegex(ValueError, "fields differ"):
            self.apply()
        self.assertFalse(self.checkpoint.exists())

    def test_cli_help_and_json_error_envelope(self):
        help_result = subprocess.run([sys.executable, controller.__file__, "--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("preview", help_result.stdout)
        flags = [flag for name in ("root", "queue", "routing_plan", "ledger", "checkpoint", "events")
                 for flag in ("--" + name.replace("_", "-"), getattr(self.args, name))]
        result = subprocess.run([sys.executable, controller.__file__, "wait", *flags, "--timeout", "61"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertEqual(result.stderr, "")


    def test_provisional_tasks_remain_active_until_final_feature_review(self):
        schedule = {"implemented": ["T1", "T2"], "integrated": [], "ready": [], "active": [], "blocked": [],
                    "feature_review": {"status": "review_required", "reasons": ["independent review required"]}}
        projection = controller.sidebar_projection(schedule, set())
        self.assertEqual(projection["tasks"]["T1"]["icon"], "🧑‍💻")
        self.assertEqual(projection["tasks"]["T2"]["acceptance"], "pending_feature_review")
        checkpoint = {}
        result = controller.project(self.state, checkpoint, schedule)
        self.assertIn("feature_review_required", self.kinds(result))
        self.assertIn("task_implemented", self.kinds(result))
        self.assertNotIn("task_integrated", self.kinds(result))
        schedule["integrated"] = ["T1", "T2"]
        schedule["feature_review"] = {"status": "ready", "reasons": []}
        projection = controller.sidebar_projection(schedule, set())
        self.assertEqual(projection["tasks"]["T1"]["icon"], "✅")
        accepted = controller.project(self.state, checkpoint, schedule)
        self.assertIn("task_integrated", self.kinds(accepted))
        self.assertNotIn("task_implemented", self.kinds(accepted))
        self.assertNotIn("feature_review_required", self.kinds(accepted))
        self.assertFalse(any(action.get("acceptance") == "pending_feature_review" for action in accepted["actions"]))
        self.assertTrue(accepted["superseded_action_ids"])
        self.assertTrue(all(value.get("acceptance") != "pending_feature_review"
                            for value in checkpoint["projection"].values()))



class QueueIntegrationTests(unittest.TestCase):
    def test_real_queue_acceptance_is_preserved_and_cli_resolves_paths_from_root(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_task_queue import TaskQueueTests
        fixture = TaskQueueTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.queue_config(["T1", "T2"], dependencies={"T2": ["T1"]})
        plan = fixture.routing_plan(["T1", "T2"])
        ledger = fixture.ledger(plan)
        flags = ["--root", str(fixture.root), "--queue", "queue.json", "--routing-plan", "routing-plan.json",
                 "--ledger", str(ledger.relative_to(fixture.root)), "--checkpoint", "controller.json", "--events", "events.jsonl"]
        before = ledger.read_bytes()
        process = subprocess.run([sys.executable, controller.__file__, "preview", *flags], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = json.loads(process.stdout)
        self.assertIn({"kind": "ready", "task_id": "T1"}, [{k: v for k, v in item.items() if k not in {"id", "persisted"}} for item in result["actions"]])
        self.assertNotIn("T2", [item.get("task_id") for item in result["actions"] if item["kind"] == "ready"])
        self.assertEqual(ledger.read_bytes(), before)
        self.assertFalse((fixture.root / "controller.json").exists())



if __name__ == "__main__":
    unittest.main()
