#!/usr/bin/env python3
"""Offline validation ledger tests with disposable inputs and no model calls."""

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SHARED = next((p / "shared" for p in SKILL.parents if (p / "shared/scripts/run_state.py").exists()), None)
if SHARED is None:
    raise RuntimeError("shared library missing")
sys.path.insert(0, str(SHARED / "scripts"))
import run_state as ledger
import model_routing
import review_evidence as evidence

spec = importlib.util.spec_from_file_location("validation_control", SKILL / "scripts/validation_control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class ModelPreviewTests(unittest.TestCase):
    def preview(self, *args):
        return subprocess.run([sys.executable, str(SKILL / "scripts/validation_control.py"),
                               "--shared-dir", str(SHARED), "preview-models", *args],
                              capture_output=True, text=True)

    def test_default_preview_shows_central_routes_without_state_or_runner_probe(self):
        config = model_routing.load_config(SHARED / "model-routing.json")
        names = ("validation-unit", "validation-browser")
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            argv = [str(SKILL / "scripts/validation_control.py"), "--shared-dir", str(SHARED),
                    "--state", str(state_path), "preview-models"]
            for name in names:
                argv.extend(["--route", name])
            output = io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stdout(output), \
                 patch.object(subprocess, "run", side_effect=AssertionError("Preview must not probe runners")) as run, \
                 patch.object(subprocess, "Popen", side_effect=AssertionError("Preview must not launch processes")) as popen, \
                 patch.object(ledger, "locked", side_effect=AssertionError("Preview must not open state")) as locked:
                self.assertEqual(control.main(), 0)
            run.assert_not_called()
            popen.assert_not_called()
            locked.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])
        preview = json.loads(output.getvalue())
        profile_name = config["default_profile"]
        profile = config["profiles"][profile_name]
        self.assertEqual(preview["profile"], profile_name)
        self.assertEqual(preview["config_path"], str((SHARED / "model-routing.json").resolve()))
        self.assertEqual(preview["config_digest"], model_routing.config_digest(config))
        self.assertEqual([route["route"] for route in preview["routes"]], list(names))
        for route in preview["routes"]:
            family = profile.get("route_families", {}).get(route["route"], profile["family"])
            expected_roles = config["routes"][route["route"]]["families"][family]
            self.assertEqual(route["family"], family)
            self.assertEqual(route["selection_source"], "central")
            self.assertEqual(set(route["roles"]), set(expected_roles))
            for role, selection in expected_roles.items():
                expected_model = config["models"][selection["seat"]]
                actual = route["roles"][role]
                self.assertEqual((actual["seat"], actual["model"], actual["runner"], actual["effort"]),
                                 (selection["seat"], expected_model["model"], expected_model["runner"], selection["effort"]))
        self.assertFalse(preview["availability_checked"])

    def test_explicit_profile_overrides_local_preference(self):
        result = self.preview("--route", "validation-browser", "--profile", "economy", "--local-profile", "balanced")
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["profile"], "economy")
        self.assertEqual(preview["routes"][0]["selection_source"], "explicit")

    def test_existing_test_execution_adds_no_worker(self):
        result = self.preview("--route", "test-execution")
        self.assertEqual(result.returncode, 0, result.stderr)
        route = json.loads(result.stdout)["routes"][0]
        self.assertEqual(route["roles"], {})
        self.assertEqual(route["execution"], "repository-commands")

    def test_unrelated_route_is_rejected(self):
        result = self.preview("--route", "routine-implementation")
        self.assertEqual(result.returncode, 2)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "requirement.md"
        self.source.write_text("Save and reload preserves the selected value.\n")
        self.input = self.root / "snapshot.json"
        self.input.write_text('{"revision":"one"}')
        self.raw = self.root / "raw.json"
        self.raw.write_text('{"exit_code":0}')
        self.plan = {"version": 1, "run_id": "test", "mode": "assess",
                     "approval": {"status": "approved", "reference": "test user decision"},
                     "scope": {"requirements": ["R1"], "discovery_closed": True},
                     "inputs": [{"path": str(self.source), "sha256": control.digest(self.source)}],
                     "units": [{"id": "U1", "required": True, "requirements": ["R1"],
                                "checks": ["behavior", "runtime"], "max_attempts": 2}],
                     "routes": [], "call_limits": {"total_role_calls": 2},
                     "budgets": {"total_attempts": 2, "max_parallel": 1,
                                 "deadline": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}}
        self.path = self.root / "plan.json"
        self.state_path = self.root / "state.json"
        self.state = {}
        self.init()

    def init(self):
        self.path.write_text(json.dumps(self.plan))
        self.state = {}
        control.initialize(self.state, self.path, ledger)

    def reserve(self, attempt="A1", reason=""):
        return control.reserve(self.state, "U1", attempt, self.input, reason)

    def finish(self, runtime="passed", attempt="A1"):
        path = self.root / (attempt + "-result.json")
        result = {"attempt_id": attempt, "input_sha256": control.digest(self.input),
                  "checks": {"behavior": "passed", "runtime": runtime}, "reason": "captured gate result",
                  "evidence": [{"path": str(self.raw), "sha256": control.digest(self.raw)}]}
        path.write_text(json.dumps(result))
        control.finish(self.state, attempt, path)
        return path

    def test_crash_before_execution_keeps_reservation_and_counter(self):
        self.reserve()
        ledger.atomic_write(self.state_path, self.state)
        self.state = control.read(self.state_path)
        self.assertEqual(self.reserve()["reservation"], "existing")
        self.assertEqual(self.state["attempts"]["validation_attempts"], 1)
        with self.assertRaisesRegex(ValueError, "pending"):
            self.reserve("A2", "new probe")

    def test_crash_after_execution_reconciles_without_replay(self):
        self.reserve()
        ledger.atomic_write(self.state_path, self.state)
        self.state = control.read(self.state_path)
        path = self.finish()
        control.finish(self.state, "A1", path)
        self.assertEqual(len(self.state["steps"]), 1)
        self.assertEqual(control.summarize(self.state)["status"], "blocked")
        self.assertEqual(control.summarize(self.state)["evidence_kind"], "context-only")
        with self.assertRaisesRegex(ValueError, "reuse"):
            self.reserve("A2", "repeat")

    def test_business_pass_cannot_hide_failed_runtime_gate(self):
        self.reserve(); self.finish("failed")
        self.assertEqual(control.summarize(self.state)["status"], "failed")

    def test_required_skip_and_unknown_inventory_cannot_pass(self):
        self.reserve(); self.finish("skipped")
        self.assertNotEqual(control.summarize(self.state)["status"], "passed")
        self.plan["scope"]["discovery_closed"] = False
        self.init(); self.reserve(); self.finish()
        self.assertEqual(control.summarize(self.state)["status"], "blocked")

    def test_browser_preflight_and_result_must_use_selected_mechanism(self):
        self.plan["working_dir"] = str(self.root.resolve())
        self.plan["units"][0].update(browser_mechanism="playwright-test", preflight_required=True)
        self.init()
        preflight = self.root / "browser-preflight.json"
        observation = {"status": "ready", "reason": "fixture driver exercised", "mechanism": "agent-browser",
                       "working_dir": str(self.root.resolve()), "evidence": [{"path": str(self.raw), "sha256": control.digest(self.raw)}]}
        preflight.write_text(json.dumps(observation))
        with self.assertRaisesRegex(ValueError, "mechanism"):
            control.record_preflight(self.state, "U1", "P1", self.input, preflight)
        self.assertFalse(self.state["validation"]["attempts"])
        observation["mechanism"] = "playwright-test"
        preflight.write_text(json.dumps(observation))
        control.record_preflight(self.state, "U1", "P1", self.input, preflight)
        self.reserve()
        with self.assertRaisesRegex(ValueError, "mechanism"):
            self.finish()
        path = self.root / "A1-result.json"
        result = control.read(path)
        result["browser_mechanism"] = "playwright-test"
        path.write_text(json.dumps(result))
        control.finish(self.state, "A1", path)
        self.assertEqual(control.summarize(self.state)["status"], "blocked")

    def test_browser_units_cannot_omit_driver_preflight(self):
        self.plan["units"][0]["browser_mechanism"] = "playwright-test"
        with self.assertRaisesRegex(ValueError, "preflight"):
            control.validate_plan(self.plan)

    def test_provider_policy_is_checked_before_any_role_reservation(self):
        selection = model_routing.resolve_profile("validation-unit")["roles"]["implementer"]
        self.plan["routes"] = [{"id": "author", "task_id": "U1", **selection}]
        self.plan["call_limits"]["author"] = 1
        self.plan["routes"][0]["provider_routing"]["zdr"] = False
        with self.assertRaises(ValueError):
            self.init()

    def test_retry_limit_and_init_do_not_reset_consumption(self):
        self.reserve(); self.finish("failed")
        self.reserve("A2", "different discriminating probe"); self.finish("failed", "A2")
        control.initialize(self.state, self.path, ledger)
        with self.assertRaisesRegex(ValueError, "ceiling"):
            self.reserve("A3", "another probe")

    def test_deadline_rejects_new_work_but_allows_result_reconciliation(self):
        self.plan["budgets"]["deadline"] = "2000-01-01T00:00:00Z"
        self.init()
        with self.assertRaisesRegex(ValueError, "deadline"):
            self.reserve()
        self.assertEqual(control.summarize(self.state)["status"], "ceiling_hit")

    def test_modified_plan_and_acceptance_source_are_rejected(self):
        self.path.write_text(self.path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "plan changed"):
            self.reserve()
        self.init()
        self.source.write_text("different requirement")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.reserve()

    def test_missing_check_and_changed_raw_evidence_are_rejected(self):
        self.reserve()
        path = self.finish()
        self.raw.write_text("tampered")
        with self.assertRaisesRegex(ValueError, "changed"):
            control.summarize(self.state)
        self.init(); self.reserve()
        result = control.read(path); result["checks"].pop("runtime")
        path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "every planned check"):
            control.finish(self.state, "A1", path)

    def test_unapproved_empty_duplicate_or_unmapped_scope_is_rejected(self):
        for change in (lambda p: p["approval"].update(status="draft"),
                       lambda p: p.update(units=[]),
                       lambda p: p["units"].append(copy.deepcopy(p["units"][0])),
                       lambda p: p["scope"]["requirements"].append("R2")):
            candidate = copy.deepcopy(self.plan); change(candidate)
            with self.assertRaises(ValueError):
                control.validate_plan(candidate)

    def test_role_reservation_uses_shared_ceiling_and_blocks_pending_pass(self):
        route = model_routing.resolve_route("validation-scope", "balanced")["roles"]["worker"]
        self.plan["routes"] = [{"id": "scope", "task_id": "U1", **route}]
        self.plan["call_limits"]["scope"] = 1
        self.init()
        control.reserve_role(self.state, ledger, "scope", "C1", self.source, "scope")
        self.assertEqual(control.reserve_role(self.state, ledger, "scope", "C1", self.source, "scope")["reservation"], "existing")
        self.reserve(); self.finish()
        self.assertNotEqual(control.summarize(self.state)["status"], "passed")
        self.assertEqual(self.state["attempts"]["total_role_calls"], 1)

    def test_all_validation_routes_resolve_and_custom_runner_effort_is_checked(self):
        config = model_routing.load_config()
        names = [n for n in config["routes"] if n.startswith("validation-")]
        self.assertGreaterEqual(len(names), 7)
        for name in names:
            model_routing.resolve_route(name, "balanced")
            model_routing.resolve_route(name, "balanced", risk="high")
        for seat in ("grok", "sonnet", "kimi", "qwen"):
            model_routing.resolve_role({"seat": seat, "effort": "medium"}, config)
        with self.assertRaises(ValueError):
            model_routing.resolve_role({"seat": "gemini", "effort": "high"}, config)
        for seat in ("muse", "minimax", "mistral-small"):
            # Former cline seats now route through pi with runtime-controlled effort.
            with self.assertRaises(ValueError):
                model_routing.resolve_role({"seat": seat, "effort": "medium"}, config)
            resolved = model_routing.resolve_role({"seat": seat, "effort": None}, config)
            self.assertIsNone(resolved["effort"])
            self.assertEqual(resolved["runner"], "pi")

    def test_approved_recovery_categories_preserve_total_limit(self):
        self.plan["units"][0].update(max_attempts=1, recovery_attempts={"test_repair": 2})
        self.init()
        self.reserve(); self.finish("failed")
        with self.assertRaisesRegex(ValueError, "unit attempt ceiling"):
            self.reserve("A2", "fix fixture")
        control.reserve(self.state, "U1", "A2", self.input, "fix fixture", "test_repair")
        self.finish("failed", "A2")
        with self.assertRaisesRegex(ValueError, "total attempt ceiling"):
            control.reserve(self.state, "U1", "A3", self.input, "another fixture fix", "test_repair")
        self.assertEqual(len(self.state["validation"]["attempts"]), 2)

    def test_preflight_block_does_not_consume_business_attempt(self):
        self.plan["units"][0]["preflight_required"] = True
        self.init()
        with self.assertRaisesRegex(ValueError, "preflight"):
            self.reserve()
        blocked = self.root / "blocked.json"
        blocked.write_text(json.dumps({"status": "blocked", "reason": "driver unavailable", "evidence": [{"path": str(self.raw), "sha256": control.digest(self.raw)}]}))
        control.record_preflight(self.state, "U1", "P1", self.input, blocked)
        self.assertEqual(control.record_preflight(self.state, "U1", "P1", self.input, blocked)["reservation"], "existing")
        with self.assertRaisesRegex(ValueError, "preflight is blocked"):
            self.reserve()
        self.assertEqual(self.state["validation"]["attempts"], {})
        self.assertEqual(control.summarize(self.state)["status"], "blocked")
        ready = self.root / "ready.json"
        data = json.loads(blocked.read_text()); data.update(status="ready", reason="driver available")
        ready.write_text(json.dumps(data))
        control.record_preflight(self.state, "U1", "P2", self.input, ready)
        self.reserve()
        self.assertEqual(len(self.state["validation"]["attempts"]), 1)
        with self.assertRaisesRegex(ValueError, "preflight ceiling"):
            control.record_preflight(self.state, "U1", "P3", self.input, ready)

    def test_recovery_does_not_add_product_repair_authority(self):
        self.plan["units"][0]["recovery_attempts"] = {"product_repair": 1}
        with self.assertRaisesRegex(ValueError, "repair authority"):
            self.init()


class SharedEvidenceIntegrationTests(unittest.TestCase):
    """Exercise direct validation capture, shared readiness, and pre-PR reuse."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.artifacts = self.directory / "records"
        self.artifacts.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.test")
        self.git("config", "user.name", "Fixture")
        (self.root / "app.txt").write_text("before")
        self.git("add", ".")
        self.git("commit", "-qm", "Initial fixture")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.root / "app.txt").write_text("after")
        self.contract = self.artifacts / "acceptance.md"
        self.contract.write_text("Save and reload preserves the selected value.")
        self.requirements = self.artifacts / "requirements.json"
        self.requirement_value = {
            "context": {"runtime": sys.version, "dependencies": "standard library only", "external_state": "disposable fixture"},
            "checks": [{"id": key, "command": [sys.executable, "-c", "print('captured " + key + "')"],
                        "cwd": ".", "timeout_seconds": 5, "inputs": ["app.txt"]}
                       for key in ("behavior", "runtime")],
            "observations": ["save"], "observation_inputs": {"save": ["app.txt"]}, "exclusions": {}}
        self.requirements.write_text(json.dumps(self.requirement_value))
        self.capture = self.artifacts / "browser.json"
        self.capture.write_text('{"saved_after_reload":true}')

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def prepare(self, name="initial", previous=()):
        return evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                self.artifacts / name, previous_reviews=previous)

    def initialize(self, snapshot):
        self.plan = {"version": 1, "run_id": "integration", "mode": "repair",
                     "approval": {"status": "approved", "reference": "fixture decision"},
                     "scope": {"requirements": ["R1"], "discovery_closed": True},
                     "inputs": [evidence.evidence_link(self.contract)], "review_snapshot": evidence.evidence_link(snapshot),
                     "units": [{"id": "U1", "required": True, "requirements": ["R1"],
                                "checks": ["behavior", "runtime", "save"], "max_attempts": 2}],
                     "routes": [], "call_limits": {"total_role_calls": 1},
                     "budgets": {"total_attempts": 2, "max_parallel": 1,
                                 "deadline": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()}}
        self.plan_path = self.artifacts / "validation-plan.json"
        self.plan_path.write_text(json.dumps(self.plan))
        self.state = {}
        control.initialize(self.state, self.plan_path, ledger)

    def capture_attempt(self, snapshot, attempt="A1", browser="pass"):
        control.reserve(self.state, "U1", attempt, snapshot, "changed source" if attempt != "A1" else "")
        checks = {key: str(evidence.run_check(snapshot, key)) for key in ("behavior", "runtime")}
        packet = evidence.prepare_packet(snapshot, self.artifacts / (attempt + "-packet.json"), checks,
                    [{"id": "save", "result": browser, "evidence": [str(self.capture)]}])
        statuses = {key: "passed" if evidence.load_record(path)["exit_code"] == 0 else "failed" for key, path in checks.items()}
        statuses["save"] = {"pass": "passed", "fail": "failed", "skipped": "skipped"}[browser]
        result = {"attempt_id": attempt, "input_sha256": evidence.file_hash(snapshot), "checks": statuses,
                  "reason": "Actual captured result", "evidence_packet": evidence.evidence_link(packet)}
        path = self.artifacts / (attempt + "-result.json")
        path.write_text(json.dumps(result))
        control.finish(self.state, attempt, path)
        return path, checks, packet

    def review(self, snapshot, packet):
        captured = evidence.load_record(snapshot)
        response = {"snapshot_sha256": evidence.file_hash(snapshot),
                    "coverage": [{"path": path, "outcome": "reviewed", "reason": "Inspected behavior and callers."}
                                 for path in captured["source"]["changed_paths"]],
                    "findings": [], "evidence_packet": evidence.evidence_link(packet), "summary": "Fixture review result."}
        return evidence.record_review(snapshot, response, {"success": True, "agent_message": json.dumps(response)})

    def test_validation_bridge_readiness_and_pre_pr_reuse_preserve_raw_capture(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        _, checks, packet = self.capture_attempt(snapshot)
        self.assertEqual(control.summarize(self.state)["status"], "passed")
        bridge = control.export_evidence(self.state, self.artifacts / "bridge.json")
        self.assertEqual(bridge["snapshot"], evidence.evidence_link(snapshot))
        state_path = self.artifacts / "run-state.json"
        ledger.atomic_write(state_path, self.state)
        saved_state = state_path.read_bytes()
        command = subprocess.run([sys.executable, control.__file__, "--shared-dir", str(SHARED), "--state", str(state_path),
                                  "evidence-packet", "--output", str(self.artifacts / "bridge-cli.json")], capture_output=True, text=True)
        self.assertEqual(command.returncode, 0, command.stdout + command.stderr)
        self.assertEqual(json.loads(command.stdout)["snapshot"], bridge["snapshot"])
        self.assertEqual(state_path.read_bytes(), saved_state)
        prior = self.review(snapshot, Path(bridge["evidence_packet"]["path"]))
        self.assertEqual(evidence.assess(snapshot, self.base)["status"], "ready")
        original = {path: Path(path).read_bytes() for path in [snapshot, packet, prior, *checks.values()]}

        current = self.prepare("pre-pr", previous=[prior])
        selected = evidence.select_checks(current, snapshot, checks)
        self.assertEqual([row["action"] for row in selected["checks"]], ["reuse", "reuse"])
        packet = evidence.prepare_packet(current, self.artifacts / "pre-pr-packet.json", checks,
                    [{"id": "save", "result": "pass", "evidence": [str(self.capture)]}])
        self.review(current, packet)
        self.assertEqual(evidence.assess(current, self.base)["status"], "ready")
        verify = subprocess.run([sys.executable, evidence.__file__, "verify", "--snapshot", str(current), "--base", self.base],
                                capture_output=True, text=True)
        self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
        self.assertEqual(json.loads(verify.stdout)["status"], "ready")
        self.assertEqual(original, {path: Path(path).read_bytes() for path in original})
        command = evidence.load_record(checks["runtime"])
        self.assertEqual(command["definition"]["command"], self.requirement_value["checks"][1]["command"])
        self.assertEqual(Path(command["logs"][0]["path"]).read_bytes(), b"captured runtime\n")

    def test_failed_runtime_and_browser_fail_or_skip_block_bridge_and_readiness(self):
        for failure in ("runtime", "fail", "skipped"):
            with self.subTest(failure=failure):
                if failure == "runtime":
                    self.requirement_value["checks"][1]["command"] = [sys.executable, "-c", "raise SystemExit(4)"]
                    self.requirements.write_text(json.dumps(self.requirement_value))
                else:
                    self.requirement_value["checks"][1]["command"] = [sys.executable, "-c", "print('captured runtime')"]
                    self.requirements.write_text(json.dumps(self.requirement_value))
                snapshot = self.prepare(failure)
                self.initialize(snapshot)
                _, _, packet = self.capture_attempt(snapshot, attempt=failure, browser="pass" if failure == "runtime" else failure)
                self.assertNotEqual(control.summarize(self.state)["status"], "passed")
                with self.assertRaisesRegex(ValueError, "incomplete|failed"):
                    control.export_evidence(self.state, self.artifacts / (failure + "-bridge.json"))
                self.review(snapshot, packet)
                verdict = evidence.assess(snapshot, self.base)
                self.assertEqual(verdict["status"], "needs-work")
                self.assertEqual(verdict["failed_checks"] if failure == "runtime" else verdict["failed_observations"],
                                 ["runtime"] if failure == "runtime" else ["save"])

    def test_drift_blocks_validation_bridge_and_pre_pr_reuse_then_fresh_repair_recovers(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        _, checks, _ = self.capture_attempt(snapshot)
        (self.root / "app.txt").write_text("repaired behavior")
        with self.assertRaisesRegex(ValueError, "stale"):
            control.export_evidence(self.state, self.artifacts / "stale-bridge.json")
        current = self.prepare("repair")
        selected = evidence.select_checks(current, snapshot, checks)
        self.assertEqual([row["action"] for row in selected["checks"]], ["run", "run"])
        _, _, _ = self.capture_attempt(current, "A2")
        self.assertEqual(control.summarize(self.state)["attempts_used"], 2)
        bridge = control.export_evidence(self.state, self.artifacts / "repair-bridge.json")
        self.assertEqual(bridge["snapshot"], evidence.evidence_link(current))
        self.assertEqual(self.plan_path.read_text(), json.dumps(self.plan))

    def test_declared_pass_cannot_hide_browser_failure(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        path, _, _ = self.capture_attempt(snapshot, browser="fail")
        result = control.read(path)
        result["checks"]["save"] = "passed"
        path.write_text(json.dumps(result))
        self.state["validation"]["attempts"]["A1"].update(status="pending", result=None)
        with self.assertRaisesRegex(ValueError, "statuses differ"):
            control.finish(self.state, "A1", path)

    def test_missing_scope_generic_record_and_packet_from_other_snapshot_are_rejected(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        wrong = copy.deepcopy(self.plan)
        wrong["units"][0]["checks"].remove("runtime")
        with self.assertRaisesRegex(ValueError, "every shared"):
            control.validate_plan(wrong)
        control.reserve(self.state, "U1", "A1", snapshot, "")
        result = {"attempt_id": "A1", "input_sha256": evidence.file_hash(snapshot),
                  "checks": {"behavior": "passed", "runtime": "passed", "save": "passed"},
                  "evidence": [evidence.evidence_link(self.capture)]}
        path = self.artifacts / "generic.json"
        path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "packet is required"):
            control.finish(self.state, "A1", path)
        other = self.prepare("other")
        checks = {key: str(evidence.run_check(other, key)) for key in ("behavior", "runtime")}
        packet = evidence.prepare_packet(other, self.artifacts / "other-packet.json", checks,
                    [{"id": "save", "result": "pass", "evidence": [str(self.capture)]}])
        result["evidence_packet"] = evidence.evidence_link(packet)
        path.write_text(json.dumps(result))
        with self.assertRaisesRegex(ValueError, "another snapshot"):
            control.finish(self.state, "A1", path)

    def test_changed_logs_and_forged_status_are_rejected_at_summary(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        _, checks, _ = self.capture_attempt(snapshot, browser="fail")
        self.state["validation"]["attempts"]["A1"]["status"] = "passed"
        with self.assertRaisesRegex(ValueError, "status differs"):
            control.summarize(self.state)
        self.state["validation"]["attempts"]["A1"]["status"] = "failed"
        log = evidence.load_record(checks["runtime"])["logs"][0]["path"]
        Path(log).write_text("replacement output")
        with self.assertRaisesRegex(ValueError, "log checksum"):
            control.summarize(self.state)

    def test_sequential_scoped_units_finish_inside_one_parallel_slot(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        self.plan["units"] = [{"id": "U" + str(index), "required": True, "requirements": ["R1"],
                               "checks": [key], "max_attempts": 1}
                              for index, key in enumerate(("behavior", "runtime", "save"), 1)]
        self.plan["budgets"]["total_attempts"] = 3
        self.plan_path.write_text(json.dumps(self.plan))
        self.state = {}
        control.initialize(self.state, self.plan_path, ledger)
        for index, key in enumerate(("behavior", "runtime", "save"), 1):
            attempt = "A" + str(index)
            control.reserve(self.state, "U" + str(index), attempt, snapshot, "")
            checks, observations = {}, []
            if key == "save":
                observations = [{"id": key, "result": "pass", "evidence": [str(self.capture)]}]
            else:
                checks[key] = str(evidence.run_check(snapshot, key))
            packet = evidence.prepare_packet(snapshot, self.artifacts / (attempt + "-scoped.json"),
                                             checks, observations, scope=[key])
            result = {"attempt_id": attempt, "input_sha256": evidence.file_hash(snapshot),
                      "checks": {key: "passed"}, "evidence_packet": evidence.evidence_link(packet)}
            path = self.artifacts / (attempt + "-result.json")
            path.write_text(json.dumps(result))
            control.finish(self.state, attempt, path)
            self.assertEqual(control.summarize(self.state)["status"], "passed" if index == 3 else "partial")
            if index == 1:
                with self.assertRaisesRegex(ValueError, "packet is incomplete"):
                    self.review(snapshot, packet)
                with self.assertRaisesRegex(ValueError, "incomplete"):
                    control.export_evidence(self.state, self.artifacts / "early-export.json")
        bridge = control.export_evidence(self.state, self.artifacts / "complete-packet.json")
        final_packet = evidence.load_record(bridge["evidence_packet"]["path"])
        self.assertNotIn("scope", final_packet)
        self.assertEqual(set(final_packet["checks"]), {"behavior", "runtime"})
        self.assertEqual([row["id"] for row in final_packet["observations"]], ["save"])
        self.review(snapshot, Path(bridge["evidence_packet"]["path"]))
        self.assertEqual(evidence.assess(snapshot, self.base)["status"], "ready")
        self.assertEqual(control.summarize(self.state)["attempts_used"], 3)

    def test_historical_success_cannot_export_evidence(self):
        snapshot = self.prepare()
        self.initialize(snapshot)
        del self.plan["review_snapshot"]
        self.plan_path.write_text(json.dumps(self.plan))
        self.state = {}
        control.initialize(self.state, self.plan_path, ledger)
        control.reserve(self.state, "U1", "A1", snapshot, "")
        result = {"attempt_id": "A1", "input_sha256": evidence.file_hash(snapshot),
                  "checks": {"behavior": "passed", "runtime": "passed", "save": "passed"},
                  "evidence": [evidence.evidence_link(self.capture)]}
        path = self.artifacts / "historical.json"
        path.write_text(json.dumps(result))
        control.finish(self.state, "A1", path)
        self.assertEqual(control.summarize(self.state)["evidence_kind"], "context-only")
        with self.assertRaisesRegex(ValueError, "historical generic"):
            control.export_evidence(self.state, self.artifacts / "historical-packet.json")


if __name__ == "__main__":
    unittest.main()
