#!/usr/bin/env python3
"""Offline council recovery, approval, receipt and budget checks."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import council_state as council


def preview_document(transport="runner"):
    seats, roles, efforts, executions = [], [], [], []
    for index in range(3):
        seat = f"seat-{index}"
        call = f"opening-{index}"
        model = f"fixture-{index}"
        seats.append({"id": seat, "provider": "fixture", "requested_model": model,
                      "model_receipt": {"status": "unverified", "source": "not_observed", "observed_model": None}})
        roles.append({"call": call, "role": "opening", "seat": seat, "requested_model": model,
                      "effort": "high", "effort_control": "configured", "continuity_key": call, "depends_on": []})
        efforts.append({"call": call, "effort": "high", "effort_control": "configured"})
        executions.append({"call": call, "host": "local", "execution_path": "fixture", "transport": transport,
                           "continuity_key": call, "session_policy": "persistent_same_role", "resume_policy": "recorded_context_only",
                           "runner": "fixture", "runner_role": "researcher"})
    return {"session_id": "fixture-council", "question": "Which option has the strongest evidence?", "mode": "poll",
            "preview": {"seats": seats, "roles": roles, "effort": efforts, "execution": executions,
                        "transport": "per_call", "serving_receipt": "explicitly_allowed_unverified", "tool_profile": "no_tools",
                        "base_calls": 3, "conditional_calls": 0, "validation_retry_ceiling": 3, "maximum_calls": 6,
                        "output_cap_tokens": 2000}}


def answer():
    return {"answer": "Hold until checked.", "key_points": ["Evidence is incomplete."], "assumptions": [], "confidence": 30}


class CouncilStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "state.json"
        self.approval = self.root / "approval.json"
        self.brief = self.root / "brief.txt"
        self.brief.write_text("Which option has the strongest evidence?")
        self.document = preview_document()
        self.initialize()

    def approve(self):
        scope_digest = council.fingerprint(self.document)
        self.document["preview"]["scope_fingerprint"] = scope_digest
        self.document["approval"] = {"status": "approved", "scope_fingerprint": scope_digest}
        self.approval.write_text(json.dumps(self.document))

    def initialize(self):
        self.approve()
        with council.ledger.locked(self.path) as state:
            council.initialize(state, self.path, self.approval)

    def reset(self):
        self.path.unlink()
        shutil.rmtree(str(self.path) + ".artifacts")
        self.initialize()

    def read(self):
        return json.loads(self.path.read_text())

    def reserve(self, call="call-1", step="opening-0"):
        with council.ledger.locked(self.path) as state:
            return council.reserve(state, step, call, self.brief)

    def receipt(self, call="call-1", context="context-0", message=None, **overrides):
        state = self.read()
        dispatch = json.loads(Path(state["call_ledger"]["calls"][call]["council"]["dispatch"]["path"]).read_text())
        receipt = {"dispatch_metadata": dispatch, "context_id": context, "success": True,
                   "configured_model": dispatch["configured_model"], "effort": dispatch["configured_effort"],
                   "effective_runner": "fixture", "tool_profile": "no_tools", "role": "researcher",
                   "tool_profile_receipt": {"profile": "no_tools", "status": "verified", "observed_tools": [],
                                            "observed_mcp_servers": [], "errors": []},
                   "agent_message": json.dumps(answer()) if message is None else message,
                   "usage": {"input_tokens": 20, "output_tokens": 10}, "duration_ms": 300, "total_cost_usd": 0.2}
        receipt.update(overrides)
        path = self.root / (call + ".receipt.json")
        path.write_text(json.dumps(receipt))
        return path

    def reconcile(self, path, call="call-1"):
        with council.ledger.locked(self.path) as state:
            return council.reconcile(state, call, path)

    def test_interrupted_reservation_and_duplicate_never_dispatch_again(self):
        result = self.reserve()
        self.assertTrue(result["dispatch_allowed"])
        before = self.read()["attempts"]
        result = self.reserve()
        self.assertFalse(result["dispatch_allowed"])
        self.assertEqual(self.read()["attempts"], before)
        with self.assertRaisesRegex(ValueError, "completed or pending"):
            self.reserve("second")
        self.reconcile(self.receipt())
        self.assertFalse(self.reserve()["dispatch_allowed"])
        with self.assertRaisesRegex(ValueError, "completed or pending"):
            self.reserve("second")

    def test_concurrent_duplicate_reservations_have_one_dispatch_winner(self):
        command = [sys.executable, council.__file__, "--state", str(self.path), "reserve", "--step", "opening-0", "--call", "same", "--brief", str(self.brief)]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
        results = [json.loads(p.communicate()[0]) for p in processes]
        self.assertEqual(sum(r["dispatch_allowed"] for r in results), 1)
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 1)

    def test_plan_mutations_fail_and_completed_state_survives_upgrade(self):
        self.reserve()
        self.reconcile(self.receipt())
        saved = self.read()
        with patch.object(council, "plan_from", side_effect=AssertionError("do not regenerate")), patch.object(council, "SCHEMAS", {"poll": {}}):
            self.initialize()
        self.assertEqual(saved["call_ledger"], self.read()["call_ledger"])
        self.assertEqual(saved["attempts"], self.read()["attempts"])
        self.document["question"] = "Changed question"
        with self.assertRaisesRegex(ValueError, "different approval"):
            self.initialize()

    def test_every_approval_control_is_fingerprinted(self):
        initial = council.fingerprint(self.document)
        for key, value in (("output_cap_tokens", 1), ("tool_profile", "repo_read_only"), ("maximum_calls", 10), ("reported_limits", {"output_tokens": 1})):
            changed = copy.deepcopy(self.document)
            changed["preview"][key] = value
            self.assertNotEqual(initial, council.fingerprint(changed))
        changed = copy.deepcopy(self.document)
        changed["preview"]["roles"][0]["effort"] = "low"
        self.assertNotEqual(initial, council.fingerprint(changed))

    def test_absent_or_stale_approval_cannot_initialize(self):
        for approval in ({}, {"status": "approved", "scope_fingerprint": "wrong"}):
            document = copy.deepcopy(self.document)
            document["approval"] = approval
            with self.assertRaises(ValueError):
                council.plan_from(document)

    def test_raw_and_normalized_receipt_digests_are_saved(self):
        self.reserve()
        path = self.receipt(message="Result follows.\n```json\n" + json.dumps(answer()) + "\n```\nEnd.")
        raw = path.read_bytes()
        result = self.reconcile(path)
        self.assertEqual(result["status"], "valid")
        artifact = json.loads(Path(result["artifact"]["path"]).read_text())
        self.assertEqual(artifact["response"], answer())
        self.assertEqual(Path(artifact["raw_receipt"]["path"]).read_bytes(), raw)
        self.assertEqual(self.reconcile(path)["reconciled"], "existing")
        Path(result["artifact"]["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.reconcile(path)

    def test_wrong_call_input_model_tool_and_context_do_not_complete(self):
        self.reserve()
        for key, value in (("call_id", "other"), ("input_revision", "other"), ("configured_model", "other"), ("tool_policy", "write"), ("host", "elsewhere"), ("configured_effort", "low")):
            before = self.path.read_bytes()
            with self.assertRaisesRegex(ValueError, "binding differs"):
                self.reconcile(self.receipt(**{key: value}))
            self.assertEqual(before, self.path.read_bytes())

    def test_failed_execution_preserves_context_and_retry_resumes_same_role(self):
        self.reserve()
        self.reconcile(self.receipt(success=False, error="interrupted"))
        state = self.read()
        self.assertEqual(state["call_ledger"]["contexts"]["opening-0"], "context-0")
        result = self.reserve("retry")
        self.assertEqual(result["context_id"], "context-0")
        with self.assertRaisesRegex(ValueError, "recorded role context"):
            self.reconcile(self.receipt("retry", context="new-context"), "retry")
        self.reconcile(self.receipt("retry"), "retry")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 2)
        self.assertEqual(self.read()["call_ledger"]["calls"]["call-1"]["status"], "failed")

    def test_failure_without_context_does_not_authorize_new_context(self):
        self.reserve()
        self.reconcile(self.receipt(success=False, context=None, error="unknown setup"))
        with self.assertRaisesRegex(ValueError, "context is unavailable"):
            self.reserve("retry")

    def test_roles_cannot_share_a_context_even_after_failure(self):
        self.reserve()
        self.reconcile(self.receipt(success=False))
        self.reserve("other", "opening-1")
        with self.assertRaisesRegex(ValueError, "another role"):
            self.reconcile(self.receipt("other", success=False), "other")

    def test_schema_failure_is_saved_and_only_one_retry_is_allowed(self):
        self.reserve()
        result = self.reconcile(self.receipt(message=json.dumps({**answer(), "confidence": 101})))
        self.assertEqual(result["status"], "malformed")
        self.reserve("retry")
        self.reconcile(self.receipt("retry", message="{} {}"), "retry")
        with self.assertRaisesRegex(ValueError, "retry ceiling"):
            self.reserve("third")

    def test_schema_and_prompt_snapshots_are_intact(self):
        self.reserve()
        original = self.read()["call_ledger"]["calls"]["call-1"]["intent"]["input"]
        self.brief.write_text("changed source")
        self.reconcile(self.receipt())
        self.assertEqual(Path(original["path"]).read_text(), "Which option has the strongest evidence?")
        with self.assertRaisesRegex(ValueError, "different inputs"):
            self.reserve()

    def test_changed_plan_snapshot_is_rejected(self):
        path = Path(self.read()["call_ledger"]["plan"]["path"])
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "plan changed"):
            self.reserve()

    def test_exhausted_and_unknown_reported_budgets_block_dispatch(self):
        self.document["preview"]["reported_limits"] = {"output_tokens": 10}
        self.reset()
        self.reserve()
        with self.assertRaisesRegex(ValueError, "unknown usage"):
            self.reserve("next", "opening-1")
        self.reconcile(self.receipt())
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.reserve("next", "opening-1")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 1)

    def test_missing_usage_is_not_zero(self):
        self.reserve()
        self.reconcile(self.receipt(usage={}))
        summary = council.status(self.read())
        self.assertEqual(summary["budget"]["measurements"]["output_tokens"]["unknown_calls"], 1)
        self.assertEqual(summary["budget"]["response_cap"]["enforcement"], "advisory")

    def test_elapsed_and_call_limits_are_not_reset_on_resume(self):
        self.document["preview"]["elapsed_seconds"] = 30
        self.reset()
        with council.ledger.locked(self.path) as state:
            state["started_at"] = "2000-01-01T00:00:00+00:00"
        self.initialize()
        with self.assertRaisesRegex(ValueError, "elapsed time budget"):
            self.reserve()

    def test_native_wait_capture_is_reused_and_remains_unverified(self):
        self.document = preview_document("native")
        self.reset()
        reservation = self.reserve()
        text = json.dumps(answer())
        raw = self.root / "wait.json"
        raw.write_text(json.dumps({"polls": [{"thread": {"id": "context-0", "hostId": "local"},
            "latestTurn": {"id": "turn-1", "status": "completed", "durationMs": 45},
            "latestAssistantMessage": {"turnId": "turn-1", "phase": "final_answer", "text": text}}]}))
        path = self.root / "captured.json"
        council.native_completion.capture(raw, reservation["dispatch"]["path"], "context-0", "local", "turn-1", 1, path)
        self.assertEqual(self.reconcile(path)["status"], "valid")
        self.assertEqual(self.read()["call_ledger"]["calls"]["call-1"]["council"]["model_receipt"]["status"], "unverified")

    def test_runner_tool_violation_and_serving_mismatch_block_acceptance(self):
        for overrides in ({"tool_profile_receipt": {"status": "violated"}},
                          {"model_receipt": {"status": "verified", "source": "provider_event", "observed_model": "wrong-model"}}):
            self.reset()
            self.reserve()
            self.assertEqual(self.reconcile(self.receipt(**overrides))["status"], "blocked_receipt")
            with self.assertRaisesRegex(ValueError, "completed or pending"):
                self.reserve("retry")

    def add_synthesis(self, conditional=False):
        preview = self.document["preview"]
        role = {**preview["roles"][0], "call": "synthesis", "role": "synthesis", "continuity_key": "synthesis",
                "depends_on": ["opening-0", "opening-1", "opening-2"], "conditional": conditional}
        preview["roles"].append(role)
        preview["effort"].append({**preview["effort"][0], "call": "synthesis"})
        preview["execution"].append({**preview["execution"][0], "call": "synthesis", "continuity_key": "synthesis"})
        preview["base_calls" if not conditional else "conditional_calls"] += 1
        preview["maximum_calls"] += 1

    def test_dependency_gate_conditional_skip_and_terminal_status(self):
        self.add_synthesis(conditional=True)
        self.reset()
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            self.reserve("synthesis", "synthesis")
        for index in range(3):
            call = f"call-{index}"
            self.reserve(call, f"opening-{index}")
            self.reconcile(self.receipt(call, context=f"context-{index}"), call)
        with council.ledger.locked(self.path) as state:
            council.skip(state, "synthesis", "Approved conditional synthesis is unnecessary.")
        self.assertEqual(self.read()["status"], "completed")
        with self.assertRaisesRegex(ValueError, "skipped"):
            self.reserve("synthesis", "synthesis")
        with self.assertRaisesRegex(ValueError, "only an approved conditional"):
            council.skip(self.read(), "opening-0", "No")

    def test_invalid_dependency_and_shared_judge_context_are_rejected(self):
        self.add_synthesis()
        self.document["preview"]["roles"][-1]["depends_on"] = ["missing"]
        self.approve()
        with self.assertRaisesRegex(ValueError, "dependencies"):
            council.plan_from(self.document)
        self.document["preview"]["roles"][-1]["depends_on"] = ["opening-0"]
        self.document["preview"]["roles"][-1]["continuity_key"] = "opening-0"
        self.document["preview"]["execution"][-1]["continuity_key"] = "opening-0"
        self.approve()
        with self.assertRaisesRegex(ValueError, "independent roles"):
            council.plan_from(self.document)

    def test_observe_uses_shared_batch_observer_without_dispatch(self):
        self.reserve()
        with council.ledger.locked(self.path) as state:
            state["call_ledger"]["calls"]["call-1"]["council"]["job"] = {"working_dir": str(self.root), "job_id": "job-1"}
        with patch.object(council.runner_jobs, "observe_many", return_value={(str(self.root), "job-1"): {"status": "running"}}) as observe:
            result = council.observe(self.read())
        observe.assert_called_once_with([(str(self.root), "job-1")])
        self.assertFalse(result["call-1"]["dispatch_allowed"])

    def no_dispatch_receipt(self, **overrides):
        values = {"success": False, "context": None, "message": "", "terminal_status": "preflight_blocked",
                  "print_invocation_started": False, "return_code": -3, "stdout": "", "preflight": {"blocked": True, "evidence": {"provider_calls": 0}},
                  "usage": {"input_tokens": 0, "output_tokens": 0}, "total_cost_usd": 0,
                  "tool_profile_receipt": {"profile": "no_tools", "status": "unverified", "observed_tools": None, "observed_mcp_servers": None, "errors": []}}
        values.update(overrides)
        return self.receipt(**values)

    def test_proven_prelaunch_failure_allows_bounded_first_context_recovery(self):
        self.document["preview"]["reported_limits"] = {"reported_cost_usd": 1}
        self.document["preview"]["serving_receipt"] = "required"
        for seat in self.document["preview"]["seats"]:
            seat["model_receipt"] = {"status": "verified", "source": "provider_event", "observed_model": seat["requested_model"]}
        self.reset()
        self.reserve()
        path = self.no_dispatch_receipt()
        self.assertEqual(self.reconcile(path)["status"], "execution_failed")
        before = self.read()
        self.assertEqual(before["status"], "running")
        self.initialize()
        result = self.reserve("retry")
        self.assertIsNone(result["context_id"])
        self.assertTrue(result["dispatch_allowed"])
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 2)
        self.assertEqual(before["call_ledger"]["plan"], self.read()["call_ledger"]["plan"])
        self.assertEqual(before["call_ledger"]["calls"]["call-1"], self.read()["call_ledger"]["calls"]["call-1"])
        self.assertEqual(council.status(self.read())["budget"]["measurements"]["reported_cost_usd"]["measured_sum"], 0)
        result = self.reconcile(self.receipt("retry", model_receipt={"status": "verified", "source": "provider_event", "observed_model": "fixture-0"}), "retry")
        self.assertEqual(result["status"], "valid")
        self.assertEqual(self.read()["call_ledger"]["contexts"]["opening-0"], "context-0")
        self.assertEqual(self.read()["council"]["retries"], 1)
        with self.assertRaisesRegex(ValueError, "completed or pending"):
            self.reserve("third")

    def test_ambiguous_or_contradictory_prelaunch_receipts_never_allow_first_context(self):
        for overrides in ({"print_invocation_started": None}, {"print_invocation_started": True}, {"return_code": 0},
                          {"terminal_status": "failed"}, {"preflight": {"blocked": True, "evidence": {}}},
                          {"stdout": "A result"}, {"message": "A result"}, {"effective_runner": "other"},
                          {"effort": "low"}, {"tool_profile": "repo_read_only"},
                          {"total_cost_usd": 0.1}, {"usage": {"output_tokens": 1}},
                          {"model_receipt": {"status": "verified", "source": "provider_event", "observed_model": "fixture-0"}},
                          {"tool_profile_receipt": {"profile": "no_tools", "status": "verified", "observed_tools": [], "observed_mcp_servers": [], "errors": []}}):
            with self.subTest(overrides=overrides):
                self.reset()
                self.reserve()
                self.reconcile(self.no_dispatch_receipt(**overrides))
                with self.assertRaisesRegex(ValueError, "context is unavailable"):
                    self.reserve("retry")
                self.assertEqual(self.read()["attempts"]["total_role_calls"], 1)

    def test_proven_prelaunch_failure_cannot_refund_or_extend_retry_budget(self):
        self.reserve()
        self.reconcile(self.no_dispatch_receipt())
        self.reserve("retry")
        self.reconcile(self.no_dispatch_receipt(call="retry"), "retry")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 2)
        self.assertEqual(self.read()["status"], "failed")
        with self.assertRaisesRegex(ValueError, "retry ceiling"):
            self.reserve("third")
        self.document["preview"].update(validation_retry_ceiling=0, maximum_calls=3)
        self.reset()
        self.reserve()
        self.reconcile(self.no_dispatch_receipt())
        with self.assertRaisesRegex(ValueError, "retry ceiling"):
            self.reserve("retry")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 1)

    def test_required_serving_proof_still_blocks_uncertain_failure(self):
        self.document["preview"]["serving_receipt"] = "required"
        for seat in self.document["preview"]["seats"]:
            seat["model_receipt"] = {"status": "verified", "source": "provider_event", "observed_model": seat["requested_model"]}
        self.reset()
        self.reserve()
        self.assertEqual(self.reconcile(self.no_dispatch_receipt(print_invocation_started=True))["status"], "blocked_receipt")

    def test_actual_runner_session_wins_over_stale_dispatch_context(self):
        self.reserve()
        self.reconcile(self.receipt(success=False))
        self.reserve("retry")
        path = self.receipt("retry")
        receipt = json.loads(path.read_text())
        receipt.pop("context_id")
        receipt["session_id"] = "new-unapproved-session"
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "recorded role context"):
            self.reconcile(path, "retry")
        receipt["session_id"] = "context-0"
        path.write_text(json.dumps(receipt))
        self.assertEqual(self.reconcile(path, "retry")["status"], "valid")

    def test_tool_proof_and_observed_inventory_must_match_profile(self):
        for proof in ({"profile": "repo_read_only", "status": "verified", "observed_tools": ["Read", "Glob", "Grep"], "observed_mcp_servers": [], "errors": []},
                      {"profile": "no_tools", "status": "verified", "observed_tools": ["Read"], "observed_mcp_servers": [], "errors": []},
                      {"profile": "no_tools", "status": "verified", "observed_tools": [], "observed_mcp_servers": ["extra"], "errors": []},
                      {"profile": "no_tools", "status": "unverified", "observed_tools": None, "observed_mcp_servers": None, "errors": []}):
            self.reset()
            self.reserve()
            self.assertEqual(self.reconcile(self.receipt(tool_profile_receipt=proof))["status"], "blocked_receipt")

    def test_dispatch_context_without_actual_session_is_not_completion_evidence(self):
        self.reserve()
        self.reconcile(self.receipt(success=False))
        self.reserve("retry")
        path = self.receipt("retry")
        receipt = json.loads(path.read_text())
        receipt.pop("context_id")
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "recorded role context"):
            self.reconcile(path, "retry")

    def test_actual_runner_controls_cannot_be_replaced_by_metadata(self):
        self.reserve()
        for key, value in (("effort", "low"), ("effective_runner", "different"), ("tool_profile", "write"), ("role", "implementer")):
            with self.subTest(field=key):
                with self.assertRaisesRegex(ValueError, "actual"):
                    self.reconcile(self.receipt(**{key: value}))
        self.assertEqual(self.read()["call_ledger"]["calls"]["call-1"]["status"], "pending")

    def test_native_turn_replay_is_not_a_new_call(self):
        self.document = preview_document("native")
        self.reset()
        first = self.reserve()
        raw = self.root / "wait.json"
        raw.write_text(json.dumps({"polls": [{"thread": {"id": "context-0", "hostId": "local"},
            "latestTurn": {"id": "turn-1", "status": "completed", "durationMs": 45},
            "latestAssistantMessage": {"turnId": "turn-1", "phase": "final_answer", "text": "{}"}}]}))
        receipt = self.root / "native-first.json"
        council.native_completion.capture(raw, first["dispatch"]["path"], "context-0", "local", "turn-1", 1, receipt)
        self.assertEqual(self.reconcile(receipt)["status"], "malformed")
        second = self.reserve("retry")
        replay = self.root / "native-replay.json"
        council.native_completion.capture(raw, second["dispatch"]["path"], "context-0", "local", "turn-1", 2, replay)
        with self.assertRaisesRegex(ValueError, "already consumed"):
            self.reconcile(replay, "retry")

    def test_native_final_message_must_match_raw_completion(self):
        self.document = preview_document("native")
        self.reset()
        first = self.reserve()
        raw = self.root / "wait.json"
        raw.write_text(json.dumps({"polls": [{"thread": {"id": "context-0", "hostId": "local"},
            "latestTurn": {"id": "turn-1", "status": "completed", "durationMs": 45},
            "latestAssistantMessage": {"turnId": "turn-1", "phase": "final_answer", "text": "{}"}}]}))
        captured = self.root / "captured.json"
        council.native_completion.capture(raw, first["dispatch"]["path"], "context-0", "local", "turn-1", 1, captured)
        receipt = council.load_record(captured)
        receipt["agent_message"] = json.dumps(answer())
        altered = self.root / "altered.json"
        altered.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "exact host completion"):
            self.reconcile(altered)

    def test_interrupted_initialization_reuses_published_plan(self):
        state = self.read()
        self.path.unlink()
        with patch.object(council, "plan_from", side_effect=AssertionError("must reuse published plan")):
            self.initialize()
        self.assertEqual(self.read()["call_ledger"]["plan"], state["call_ledger"]["plan"])
        self.assertEqual(self.read()["attempts"], {})

    def test_context_event_binds_exact_call_and_job(self):
        self.reserve()
        raw = self.root / "event.raw.json"
        raw.write_text('{"context_id":"context-0"}')
        state = self.read()
        event = {"setup_reference": "council:call-1", "call_id": "call-1", "context_id": "context-0",
                 "input_revision": state["call_ledger"]["calls"]["call-1"]["intent"]["input"]["sha256"],
                 "host": "local", "transport": "runner", "job_id": "job-1", "working_dir": str(self.root),
                 "evidence": {"path": str(raw), "sha256": council.ledger.sha(raw)}}
        path = self.root / "event.json"
        path.write_text(json.dumps(event))
        with council.ledger.locked(self.path) as state:
            council.bind(state, "call-1", path)
        event["job_id"] = "different"
        path.write_text(json.dumps(event))
        before = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "job differs"):
            with council.ledger.locked(self.path) as state:
                council.bind(state, "call-1", path)
        self.assertEqual(before, self.path.read_bytes())

    def test_required_proof_missing_and_fallback_keep_usage(self):
        self.document["preview"]["serving_receipt"] = "required"
        for seat in self.document["preview"]["seats"]:
            seat["model_receipt"] = {"status": "verified", "source": "provider_event", "observed_model": seat["requested_model"]}
        self.reset()
        self.reserve()
        self.assertEqual(self.reconcile(self.receipt(fallback_reason="fallback"))["status"], "blocked_receipt")
        self.assertEqual(council.status(self.read())["budget"]["measurements"]["output_tokens"]["measured_sum"], 10)

    def test_cost_duration_and_total_call_limits_stop_new_reservations(self):
        for metric, limit in (("reported_cost_usd", 0.2), ("duration_ms", 300)):
            self.document["preview"]["reported_limits"] = {metric: limit}
            self.reset()
            self.reserve()
            self.reconcile(self.receipt())
            with self.assertRaisesRegex(ValueError, "budget exhausted"):
                self.reserve("second", "opening-1")
        self.document["preview"].pop("reported_limits")
        self.reset()
        with council.ledger.locked(self.path) as state:
            state["attempts"]["total_role_calls"] = 6
        with self.assertRaisesRegex(ValueError, "call ceiling"):
            self.reserve()

    def test_personas_and_debate_stage_schemas_and_cycles(self):
        document = preview_document()
        document["mode"] = "personas"
        preview = document["preview"]
        preview["seats"] = preview["seats"][:1]
        for index, stage in enumerate(("advisor", "reviewer", "chairman")):
            role = preview["roles"][index]
            role.update(role=stage, seat="seat-0", requested_model="fixture-0", depends_on=[] if index == 0 else [preview["roles"][index - 1]["call"]])
        value = council.fingerprint(document)
        preview["scope_fingerprint"] = value
        document["approval"] = {"status": "approved", "scope_fingerprint": value}
        plan = council.plan_from(document)
        self.assertIn("shared_omissions", plan["steps"]["opening-1"]["schema"]["required"])
        preview["roles"][1]["depends_on"] = ["opening-2"]
        value = council.fingerprint(document)
        preview["scope_fingerprint"] = value
        document["approval"]["scope_fingerprint"] = value
        with self.assertRaisesRegex(ValueError, "cycle"):
            council.plan_from(document)
        document = preview_document()
        document["mode"] = "debate"
        value = council.fingerprint(document)
        document["preview"]["scope_fingerprint"] = value
        document["approval"] = {"status": "approved", "scope_fingerprint": value}
        self.assertIn("stance", council.plan_from(document)["steps"]["opening-0"]["schema"]["required"])

    def test_flat_install_help_and_initialization(self):
        flat = self.root / "flat"
        shutil.copytree(SKILL, flat / "models-consensus")
        shutil.copytree(Path(council.ledger.__file__).parent, flat / "shared" / "scripts")
        script = flat / "models-consensus" / "scripts" / "council_state.py"
        for arguments in (["--help"], ["--state", str(self.root / "flat-state.json"), "init", "--approval-state", str(self.approval)]):
            process = subprocess.run([sys.executable, str(script), *arguments], capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
