import copy
import json
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import run_pi
from provider_routing import provider_policy_digest, provider_receipt_error, validate_provider_policy_receipt, validate_provider_routing

POLICY = {"gateway": "openrouter", "zdr": True, "data_collection": "deny", "require_parameters": True}


class ProviderRoutingTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for the hook fixture")
    def test_resolved_auth_cannot_redirect_the_gateway(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config, receipt = root / "config.json", root / "receipt.json"
            config.write_text(json.dumps({"model": "fixture/model", "gateway": "openrouter",
                                          "base_url": "https://openrouter.ai/api/v1", "policy": POLICY}))
            script = root / "probe.mjs"
            script.write_text("import hook from " + json.dumps((SCRIPTS / "provider_policy.mjs").as_uri()) + ";\n" + """
const handlers = {};
hook({on: (name, handler) => {handlers[name] = handler;}});
await handlers.session_start({}, {
  model: {id: 'fixture/model', provider: 'openrouter', api: 'openai-completions', baseUrl: 'https://openrouter.ai/api/v1'},
  modelRegistry: {getApiKeyAndHeaders: async () => ({ok: true, baseUrl: 'https://fixture.invalid/v1'})}
});
""")
            result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=10,
                                    env=dict(os.environ, RAR_PI_RUN_CONFIG=str(config), RAR_PI_RUN_RECEIPT=str(receipt)))
            self.assertEqual(result.returncode, 78, result.stderr)
            self.assertFalse(receipt.exists())

    def test_validation_rejects_weak_and_ambiguous_policy(self):
        invalid = [None, [], {}, {**POLICY, "zdr": 1}, {**POLICY, "zdr": False},
                   {**POLICY, "gateway": "other"}, {**POLICY, "data_collection": "allow"},
                   {**POLICY, "require_parameters": False}, {**POLICY, "only": []},
                   {**POLICY, "only": [" "]}, {**POLICY, "only": ["a", "a"]},
                   {**POLICY, "only": [1]}, {**POLICY, "allow_fallbacks": 1},
                   {**POLICY, "order": ["a"]}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_provider_routing(value)

    def test_digest_is_order_independent_but_binds_all_policy_fields(self):
        self.assertEqual(provider_policy_digest(POLICY), provider_policy_digest(dict(reversed(list(POLICY.items())))))
        self.assertNotEqual(provider_policy_digest(POLICY), provider_policy_digest({**POLICY, "allow_fallbacks": False}))

    def test_missing_or_tampered_receipt_is_rejected(self):
        receipt = {"status": "enforced", "gateway": "openrouter", "policy_sha256": provider_policy_digest(POLICY), "request_count": 1}
        validate_provider_policy_receipt(receipt, POLICY)
        for invalid in [None, {}, {**receipt, "policy_sha256": "0" * 64}, {**receipt, "request_count": 0},
                        {**receipt, "request_count": True}, {**receipt, "status": "ready"}, {**receipt, "gateway": "other"}]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                validate_provider_policy_receipt(invalid, POLICY)
        with self.assertRaises(ValueError):
            validate_provider_policy_receipt(receipt, {**POLICY, "only": ["provider-a"]})

    def test_invalid_policy_never_starts_process(self):
        with patch.object(run_pi.subprocess, "run") as process:
            result = run_pi.run_pi("private task", model="vendor/model", provider="other", provider_routing=POLICY)
        self.assertFalse(result["success"])
        process.assert_not_called()

    def test_duplicate_policy_key_is_rejected(self):
        policy = json.dumps(POLICY)[:-1] + ', "zdr": false}'
        self.assertFalse(run_pi.run_pi("task", model="vendor/model", provider_routing=policy)["success"])

    def test_missing_hook_receipt_fails_the_wrapper(self):
        with patch.object(run_pi.shutil, "which", return_value="/fixture/pi"), \
                patch.object(run_pi, "run_controlled", side_effect=ValueError("Missing or mismatched provider policy receipt")):
            result = run_pi.run_pi("private task", model="vendor/model", provider_routing=POLICY)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "provider_policy_error")
        self.assertNotIn("private task", result["command"])

    def test_verified_privacy_seat_defaults_to_central_strict_policy(self):
        captured = {}

        def fake_run_controlled(command, **kwargs):
            captured.update(kwargs.get("config") or {})
            raise ValueError("Missing or mismatched provider policy receipt")

        with patch.object(run_pi.shutil, "which", return_value="/fixture/pi"), \
                patch.object(run_pi, "run_controlled", side_effect=fake_run_controlled):
            result = run_pi.run_pi("private task", model="z-ai/glm-5.3-flash")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "provider_policy_error")
        self.assertEqual(captured.get("policy"), POLICY)
        self.assertNotIn("private task", result["command"])

    def test_seat_without_privacy_block_keeps_legacy_path(self):
        with patch.object(run_pi.shutil, "which", return_value="/fixture/pi"), \
                patch.object(run_pi, "run_controlled") as controlled, \
                patch.object(run_pi.subprocess, "run") as process:
            process.return_value.returncode = 0
            process.return_value.stdout = ""
            process.return_value.stderr = ""
            run_pi.run_pi("task", model="moonshotai/kimi-k3")
        controlled.assert_not_called()
        process.assert_called_once()

    def test_model_author_is_not_inference_host(self):
        result = run_pi.normalize_envelope({"model": "vendor/model", "provider": "openrouter", "return_code": -3}, "pi")
        self.assertEqual(result["effective_provider"], "vendor")
        self.assertEqual(result["model_author"], "vendor")
        self.assertEqual(result["gateway"], "openrouter")
        self.assertIsNone(result["inference_provider"])

    def test_ledger_helper_rejects_success_without_receipt(self):
        self.assertIsNotNone(provider_receipt_error(POLICY, {"success": True}))
        self.assertIsNone(provider_receipt_error(None, {"success": True}))
        self.assertIsNone(provider_receipt_error(POLICY, {"success": True, "provider_policy_receipt": {
            "status": "enforced", "gateway": "openrouter", "request_count": 1, "policy_sha256": provider_policy_digest(POLICY)}}))

    def test_browser_evidence_and_driver_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            driver, artifact, record = root / "driver", root / "capture", root / "preflight.json"
            driver.write_text("fixture command")
            artifact.write_text("fixture capture")
            evidence = {"mechanism": "agent-browser", "working_dir": str(root.resolve()), "ready": True, "status": "ready",
                "checks": {name: True for name in ("navigation", "state_inspection", "interaction", "assertions", "evidence_capture")},
                "driver": {"path": str(driver), "sha256": hashlib.sha256(driver.read_bytes()).hexdigest(), "version": "fixture"},
                "evidence": [{"path": str(artifact), "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}]}
            record.write_text(json.dumps(evidence))
            with patch.object(run_pi.shutil, "which", return_value=str(driver)):
                self.assertTrue(run_pi.browser_preflight("agent-browser", str(record), temp)["ready"])
                artifact.write_text("changed")
                with self.assertRaises(ValueError):
                    run_pi.browser_preflight("agent-browser", str(record), temp)
                artifact.write_text("fixture capture")
                driver.write_text("changed")
                with self.assertRaises(ValueError):
                    run_pi.browser_preflight("agent-browser", str(record), temp)

    def test_model_specific_effort_is_checked_before_process(self):
        config = copy.deepcopy(run_pi.ROUTING_CONFIG)
        config["effort_profiles"]["fixture"] = ["low", "high", "max"]
        config["models"]["fixture"] = {"runner": "pi", "model": "fixture/model", "effort_profile": "fixture", "default_effort": "high"}
        with patch.object(run_pi, "ROUTING_CONFIG", config), patch.object(run_pi.subprocess, "run") as process:
            for effort in ("medium", "xhigh", "off"):
                result = run_pi.run_pi("fixture", model="fixture/model", thinking=effort)
                self.assertFalse(result["success"])
            process.assert_not_called()

    def test_known_model_default_effort_uses_request_controls(self):
        config = copy.deepcopy(run_pi.ROUTING_CONFIG)
        config["models"]["fixture"] = {"runner": "pi", "model": "fixture/model", "effort_profile": "pi", "default_effort": "high"}
        with patch.object(run_pi, "ROUTING_CONFIG", config), patch.object(run_pi.shutil, "which", return_value="/fixture/pi"), \
                patch.object(run_pi, "run_controlled", side_effect=ValueError("fixture stop")) as controlled:
            run_pi.run_pi("fixture", model="fixture/model")
        self.assertEqual(controlled.call_args.kwargs["config"]["effort"], "high")


if __name__ == "__main__":
    unittest.main()
