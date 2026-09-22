"""Reject policy drift between preview, dispatch, browser readiness, and receipts."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SHARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED / "scripts"))
import browser_preflight as browser
import model_routing
import run_state
from provider_routing import provider_policy_digest

spec = importlib.util.spec_from_file_location("policy_launcher", SHARED.parent / "engineering/engine/implement-and-review/scripts/launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class ExecutionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.brief = self.root / "brief.md"
        self.brief.write_text("Check a fixture.")
        selection = model_routing.resolve_profile("routine-implementation")["roles"]["implementer"]
        self.route = {**selection, "id": "build", "task_id": "T1", "input_path": "brief.md", "track": "main",
                      "role": "implementer", "mode": "runner", "model_verification": "required",
                      "unavailable": {"action": "block"}}
        self.result = {"success": True, "effective_runner": "pi", "configured_model": self.route["model"],
                       "effective_model": self.route["model"], "effective_effort": self.route["effort"],
                       "model_receipt": {"status": "verified", "source": "native_event", "observed_model": self.route["model"]},
                       "provider_policy_receipt": {"status": "enforced", "gateway": "openrouter", "request_count": 1,
                                                   "policy_sha256": provider_policy_digest(self.route["provider_routing"])}}

    def test_initial_and_resumed_dispatch_forward_the_approved_policy(self):
        launch.validate_route(self.route)
        for context in (None, str(self.root / "session.jsonl")):
            argv = launch.route_arguments(self.route, self.brief, self.root, "implementer", 30, {}, False, context)
            self.assertEqual(json.loads(argv[argv.index("--provider-routing") + 1]), self.route["provider_routing"])
            self.assertEqual(argv[argv.index("--provider") + 1], "openrouter")
            self.assertEqual(argv[argv.index("--thinking") + 1], "high")
            if context:
                self.assertEqual(argv[argv.index("--session") + 1], context)

    def test_policy_is_in_approval_digest(self):
        before = launch.canonical_digest(launch.normalized_routes([self.route]))
        self.route["provider_routing"]["only"] = ["deepinfra"]
        self.assertNotEqual(before, launch.canonical_digest(launch.normalized_routes([self.route])))

    def test_success_requires_an_intact_enforcement_receipt(self):
        self.assertIsNone(launch.receipt_error(self.route, self.result))
        for key, value in (("status", "configured"), ("gateway", "other"), ("policy_sha256", "0" * 64),
                           ("request_count", 0), ("request_count", True)):
            candidate = copy.deepcopy(self.result)
            candidate["provider_policy_receipt"][key] = value
            self.assertIsNotNone(launch.receipt_error(self.route, candidate), key)
        self.result.pop("provider_policy_receipt")
        self.assertIsNotNone(launch.receipt_error(self.route, self.result))

    def test_privacy_controls_cannot_be_bound_to_an_unrelated_runner(self):
        self.route.update(runner="claude", model="fixture")
        with self.assertRaisesRegex(ValueError, "Pi"):
            launch.validate_route(self.route)

    def test_model_with_runtime_reasoning_omits_effort_flag(self):
        candidate = model_routing.resolve_profile("validation-browser", role_overrides={"worker": {"seat": "mistral-small"}})["roles"]["worker"]
        self.route.update(candidate)
        launch.validate_route(self.route)
        argv = launch.route_arguments(self.route, self.brief, self.root, "implementer", 30, {}, False)
        self.assertNotIn("--thinking", argv)
        self.route.update(model="unknown-runtime-model")
        with self.assertRaisesRegex(ValueError, "runtime"):
            launch.validate_route(self.route)

    def test_missing_image_capability_is_rejected(self):
        self.route.update(capabilities={"tools": True, "images": False}, required_capabilities=["images"])
        with self.assertRaisesRegex(ValueError, "capability"):
            launch.validate_route(self.route)

    def test_fallback_to_another_runner_requires_a_separate_policy_decision(self):
        self.route["unavailable"] = {"action": "use", "seat": "luna", "runner": "codex", "model": "gpt-5.6-luna",
                                     "mode": "runner", "effort_control": "runner", "effort": "high", "model_verification": "required"}
        with self.assertRaisesRegex(ValueError, "provider_routing decision"):
            launch.validate_route(self.route)
        self.route["unavailable"]["provider_routing"] = None
        alternate = launch.fallback_route(self.route)
        self.assertNotIn("provider_routing", alternate)
        self.assertIn("provider_routing", self.route)

    def test_pi_fallback_cannot_remove_or_weaken_privacy(self):
        policy = self.route["provider_routing"]
        policy.update(only=["fixture-provider"], allow_fallbacks=False)
        alternate = {"runner": "pi"}
        for replacement in (None, {k: v for k, v in policy.items() if k != "only"},
                            {**policy, "only": ["other-provider"]}, {**policy, "allow_fallbacks": True}):
            with self.assertRaises(ValueError):
                launch.merge_fallback(self.route, {**alternate, "provider_routing": replacement})
        self.assertEqual(launch.merge_fallback(self.route, alternate)["provider_routing"], policy)

    def browser_record(self):
        driver = self.root / "playwright-cli"
        driver.write_text("fixture driver")
        observation = self.root / "observed.json"
        observation.write_text('{"navigation":true,"saved":"after reload"}')
        record = {"mechanism": "playwright-cli", "working_dir": str(self.root), "status": "ready", "ready": True,
                  "checks": {key: True for key in browser.CHECKS}, "evidence": [browser.reference(observation)],
                  "driver": {**browser.reference(driver), "version": "fixture"}}
        path = self.root / "preflight.json"
        path.write_text(json.dumps(record))
        return {"mechanism": "playwright-cli", "preflight": browser.reference(path)}, record, driver

    def test_browser_dispatch_checks_driver_and_artifacts_then_limits_tools(self):
        self.route["browser"], record, driver = self.browser_record()
        with patch.object(browser.shutil, "which", return_value=str(driver)):
            argv = launch.route_arguments(self.route, self.brief, self.root, "implementer", 30, {}, False)
            self.assertEqual(argv[argv.index("--tool-policy") + 1], "browser")
            self.assertNotIn("--allow-write", argv)
            self.assertEqual(argv[argv.index("--browser-mechanism") + 1], "playwright-cli")
            self.assertIsNotNone(launch.receipt_error(self.route, self.result))
            self.result.update(tool_policy="browser", browser_mechanism="playwright-cli")
            self.assertIsNone(launch.receipt_error(self.route, self.result))
            Path(record["evidence"][0]["path"]).write_text("changed")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                launch.route_arguments(self.route, self.brief, self.root, "implementer", 30, {}, False)

    def test_browser_preflight_rejects_changed_driver_workspace_or_checks(self):
        bound, record, driver = self.browser_record()
        with patch.object(browser.shutil, "which", return_value=str(driver)):
            browser.load_bound_preflight(bound, self.root)
            with self.assertRaisesRegex(ValueError, "workspace"):
                browser.load_bound_preflight(bound, self.root / "other")
            record["checks"]["interaction"] = False
            with self.assertRaisesRegex(ValueError, "capability"):
                browser.validate_preflight(record, "playwright-cli", self.root)
            record["checks"]["interaction"] = True
            driver.write_text("new driver")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                browser.load_bound_preflight(bound, self.root)

    def test_direct_ledger_completion_cannot_bypass_policy_verification(self):
        plan = self.root / "plan.json"
        plan.write_text(json.dumps({"approval": {"status": "approved"}, "routes": [self.route]}))
        state = {}
        run_state.initialize(state, plan, "fixture", {"total_role_calls": 2, "build": 2})
        run_state.reserve(state, "build", "C1", self.brief, "implementation")
        receipt = self.root / "receipt.json"
        result = {**self.result, "configured_effort": "high", "call_id": "C1",
                  "input_revision": run_state.sha(self.brief), "session_id": "fixture-session"}
        result.pop("provider_policy_receipt")
        receipt.write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            run_state.complete(state, "C1", receipt)
        self.assertEqual(state["call_ledger"]["calls"]["C1"]["status"], "pending")
        result["provider_policy_receipt"] = self.result["provider_policy_receipt"]
        receipt.write_text(json.dumps(result))
        run_state.complete(state, "C1", receipt)
        self.assertEqual(state["call_ledger"]["calls"]["C1"]["status"], "completed")


if __name__ == "__main__":
    unittest.main()
