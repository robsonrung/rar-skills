#!/usr/bin/env python3
"""Offline regression checks for runner context and model compatibility."""
import json
import copy
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discover_runners
import runner_preflight as preflight


class RunnerPreflightTests(unittest.TestCase):
    def probe(self, version="2.1.280 (Claude Code)", logged_in=False, context=None, effort="high", model="claude-opus-5-5"):
        def command(argv, **kwargs):
            self.assertIn(argv[1:], (["--version"], ["auth", "status", "--json"]))
            output = version if argv[1:] == ["--version"] else json.dumps({"loggedIn": logged_in, "email": "private@example.test"})
            return subprocess.CompletedProcess(argv, 0, output, "")
        with patch.object(preflight.shutil, "which", return_value="/mock/claude"), patch.object(preflight.subprocess, "run", side_effect=command) as run:
            result = preflight.check_claude(model, effort, launch_context=context)
        return result, run

    def test_old_cli_blocks_exact_model_without_auth_or_inference(self):
        result, run = self.probe(version="2.1.275 (Claude Code)")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["checks"]["compatibility"]["status"], "false")
        self.assertIn("2.1.280", " ".join(result["reasons"]))
        self.assertEqual(run.call_count, 1)

    def test_sandbox_logout_is_unknown_and_does_not_block(self):
        result, run = self.probe(context={"auth_visibility": "restricted"})
        self.assertFalse(result["blocked"])
        self.assertEqual(result["checks"]["auth_visibility"]["status"], "unknown")
        self.assertEqual(result["checks"]["model_entitlement"]["status"], "unknown")
        self.assertEqual(result["checks"]["tools"]["status"], "unknown")
        self.assertEqual(run.call_count, 2)
        self.assertNotIn("private@example.test", json.dumps(result))

    def test_known_full_visibility_logout_blocks(self):
        result, _ = self.probe(context={"auth_visibility": "full"})
        self.assertTrue(result["blocked"])
        self.assertEqual(result["checks"]["auth_visibility"]["status"], "false")

    def test_visible_login_is_not_entitlement(self):
        result, _ = self.probe(logged_in=True)
        self.assertFalse(result["blocked"])
        self.assertEqual(result["checks"]["auth_visibility"]["status"], "true")
        self.assertEqual(result["checks"]["model_entitlement"]["status"], "unknown")

    def test_unsupported_effort_blocks(self):
        result, _ = self.probe(effort="ultra")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["checks"]["effort"]["status"], "false")

    def test_missing_cli_and_config_evidence(self):
        with patch.object(preflight.shutil, "which", return_value=None), patch.object(preflight.subprocess, "run") as run:
            result = preflight.check_claude("claude-opus-5-5", "high")
        self.assertTrue(result["blocked"])
        self.assertEqual(result["checks"]["transport"]["status"], "false")
        self.assertEqual(result["evidence"]["config"]["path"], str(preflight.CONFIG_PATH))
        self.assertEqual(len(result["evidence"]["config"]["sha256"]), 64)
        run.assert_not_called()

    def test_auth_failures_remain_unknown(self):
        responses = [subprocess.CompletedProcess([], 0, "2.1.280", ""), subprocess.TimeoutExpired([], 10)]
        with patch.object(preflight.shutil, "which", return_value="/mock/claude"), patch.object(preflight.subprocess, "run", side_effect=responses):
            result = preflight.check_claude("claude-opus-5-5", "high")
        self.assertFalse(result["blocked"])
        self.assertEqual(result["checks"]["auth_visibility"]["status"], "unknown")

    def test_unknown_version_is_not_compatible(self):
        result, _ = self.probe(version="unrecognized version")
        self.assertEqual(result["checks"]["compatibility"]["status"], "unknown")
        self.assertTrue(result["blocked"])

    def test_discovery_checks_model_minimum_without_provider_call(self):
        spec = next(s for s in discover_runners.SEAT_SPECS if s.seat == "opus-5-5")
        with patch.object(discover_runners.shutil, "which", return_value="/mock/claude"), patch.object(discover_runners.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "2.1.275", "")) as run:
            result = discover_runners.probe_seat(spec, "no", 1)
        self.assertFalse(result.available)
        self.assertEqual(result.checks["transport"]["status"], "true")
        self.assertEqual(result.checks["compatibility"]["status"], "false")
        self.assertEqual(run.call_count, 1)

    def test_native_transport_does_not_imply_compatibility(self):
        spec = next(s for s in discover_runners.SEAT_SPECS if s.seat == "opus-5-5")
        with patch.object(discover_runners.subprocess, "run") as run:
            result = discover_runners.probe_seat(spec, "yes", 1).to_dict()
        self.assertTrue(result["available"])
        self.assertEqual(result["checks"]["compatibility"]["status"], "unknown")
        run.assert_not_called()

    def test_supplied_launch_context_reaches_both_probes(self):
        env = {"PATH": "/actual/bin", "HOME": "/actual/home", "CLAUDE_CODE_OAUTH_TOKEN": "never-print-this"}
        with patch.object(preflight.shutil, "which", return_value="/actual/bin/claude") as which, patch.object(preflight.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], 0, "2.1.280", ""),
            subprocess.CompletedProcess([], 0, '{"loggedIn": true}', ""),
        ]) as run:
            report = preflight.check_claude("claude-opus-5-5", "high", working_dir="/actual/work", env=env)
        which.assert_called_once_with("claude", path="/actual/bin")
        for call in run.call_args_list:
            self.assertEqual(call.kwargs["cwd"], "/actual/work")
            self.assertEqual(call.kwargs["env"], env)
        self.assertNotIn("never-print-this", json.dumps(report))
        self.assertEqual(report["evidence"]["launch_context"]["cwd"], "/actual/work")

    def test_omitted_model_and_effort_preserve_runtime_defaults(self):
        result, run = self.probe(model=None, effort=None)
        self.assertFalse(result["blocked"], result["reasons"])
        self.assertIsNone(result["model"])
        self.assertIsNone(result["effort"])
        self.assertEqual(result["checks"]["compatibility"]["status"], "unknown")
        self.assertEqual(result["checks"]["effort"]["status"], "unknown")
        self.assertEqual(run.call_count, 2)

    def test_explicit_model_with_omitted_effort_checks_version_only(self):
        result, _ = self.probe(effort=None)
        self.assertFalse(result["blocked"], result["reasons"])
        self.assertEqual(result["model"], "claude-opus-5-5")
        self.assertIsNone(result["effort"])
        self.assertEqual(result["checks"]["effort"]["status"], "unknown")
        self.assertEqual(result["checks"]["compatibility"]["status"], "true")
        old, _ = self.probe(effort=None, version="2.1.275")
        self.assertTrue(old["blocked"])
        self.assertEqual(old["checks"]["compatibility"]["status"], "false")

    def test_omitted_model_does_not_claim_effort_support(self):
        result, _ = self.probe(model=None, effort="high")
        self.assertFalse(result["blocked"])
        self.assertEqual(result["checks"]["effort"]["status"], "unknown")
        invalid, _ = self.probe(model=None, effort="ultra")
        self.assertTrue(invalid["blocked"])

    def test_compatibility_resolves_exact_model_from_central_seat(self):
        config = copy.deepcopy(preflight.load_config())
        original = config["models"]["opus-5-5"]["model"]
        config["models"]["opus-5-5"]["model"] = "fixture-model-revision"
        updated = preflight.claude_compatibility("fixture-model-revision", "2.1.275", config=config)
        self.assertEqual(updated["status"], "false")
        self.assertEqual(updated["requirement_seat"], "opus-5-5")
        self.assertEqual(preflight.claude_compatibility(original, "2.1.275", config=config)["status"], "unknown")
        sibling = config["models"]["opus"]["model"]
        self.assertEqual(preflight.claude_compatibility(sibling, "2.1.275", config=config)["status"], "unknown")

    def test_compatibility_rejects_missing_or_wrong_runner_seat(self):
        config = preflight.load_config()
        for seat in ("missing-seat", "sol"):
            policy = {"schema_version": 1, "claude": {seat: {
                "minimum_version": "2.1.280", "evidence": "fixture"}}}
            with self.subTest(seat=seat), patch.object(preflight, "COMPATIBILITY_PATH") as path:
                path.read_text.return_value = json.dumps(policy)
                with self.assertRaisesRegex(ValueError, "not a registered Claude seat"):
                    preflight.claude_compatibility("fixture-model", "2.1.280", config=config)


if __name__ == "__main__":
    unittest.main()
