#!/usr/bin/env python3
"""Offline validation ledger tests with disposable inputs and no model calls."""

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SHARED = next((p / "shared" for p in SKILL.parents if (p / "shared/scripts/run_state.py").exists()), None)
if SHARED is None:
    raise RuntimeError("shared library missing")
sys.path.insert(0, str(SHARED / "scripts"))
import run_state as ledger
import model_routing

spec = importlib.util.spec_from_file_location("validation_control", SKILL / "scripts/validation_control.py")
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class ModelPreviewTests(unittest.TestCase):
    def preview(self, *args):
        return subprocess.run([sys.executable, str(SKILL / "scripts/validation_control.py"),
                               "--shared-dir", str(SHARED), "preview-models", *args],
                              capture_output=True, text=True)

    def test_default_preview_shows_central_routes_without_state_or_runner_probe(self):
        result = self.preview("--route", "validation-unit", "--route", "validation-browser")
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["profile"], "economy")
        self.assertEqual(preview["config_path"], str((SHARED / "model-routing.json").resolve()))
        self.assertEqual(preview["config_digest"], model_routing.config_digest(model_routing.load_config()))
        unit, browser = preview["routes"]
        self.assertEqual((unit["roles"]["implementer"]["seat"], unit["roles"]["implementer"]["effort"]), ("glm", "high"))
        self.assertEqual((unit["roles"]["reviewer"]["seat"], unit["roles"]["reviewer"]["effort"]), ("deepseek-flash", "high"))
        self.assertEqual((browser["roles"]["worker"]["seat"], browser["roles"]["worker"]["effort"]), ("glm", "high"))
        self.assertFalse(preview["availability_checked"])

    def test_explicit_profile_overrides_local_preference(self):
        result = self.preview("--route", "validation-browser", "--profile", "economy", "--local-profile", "balanced")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["routes"][0]["selection_source"], "explicit")

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
        self.assertEqual(control.summarize(self.state)["status"], "passed")
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
        self.assertEqual(control.summarize(self.state)["status"], "passed")

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


if __name__ == "__main__":
    unittest.main()
