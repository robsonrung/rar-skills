#!/usr/bin/env python3
"""Offline checks for runner discovery and Claude CLI compatibility."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import discover_runners
import model_routing


class DiscoverRunnersTests(unittest.TestCase):
    def test_discovery_checks_model_minimum_without_provider_call(self):
        spec = next(s for s in discover_runners.SEAT_SPECS if s.seat == "opus")
        with patch.object(discover_runners.shutil, "which", return_value="/mock/claude"), patch.object(discover_runners.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "2.1.275", "")) as run:
            result = discover_runners.probe_seat(spec, "no", 1)
        self.assertFalse(result.available)
        self.assertEqual(result.checks["transport"]["status"], "true")
        self.assertEqual(result.checks["compatibility"]["status"], "false")
        self.assertEqual(run.call_count, 1)

    def test_native_transport_does_not_imply_compatibility(self):
        spec = next(s for s in discover_runners.SEAT_SPECS if s.seat == "opus")
        with patch.object(discover_runners.subprocess, "run") as run:
            result = discover_runners.probe_seat(spec, "yes", 1).to_dict()
        self.assertTrue(result["available"])
        self.assertEqual(result["checks"]["compatibility"]["status"], "unknown")
        run.assert_not_called()

    def test_each_runner_seat_names_one_runner_skill(self):
        skills_root = Path(__file__).resolve().parents[2]
        expected = {"opus": "cli-runner", "astra": "cli-runner", "gemini": "cli-runner", "grok": "cli-runner",
                    "kimi": "pi-runner", "muse-wonder-full": "muse-runner"}
        with patch.object(discover_runners.shutil, "which", return_value=None):
            for spec in discover_runners.SEAT_SPECS:
                with self.subTest(seat=spec.seat):
                    skill = discover_runners.probe_seat(spec, "no", 1).skill
                    self.assertEqual(skill, expected.get(spec.seat, skill))
                    self.assertEqual(len(list(skills_root.glob(f"**/{skill}/SKILL.md"))), 1)
        opus = next(s for s in discover_runners.SEAT_SPECS if s.seat == "opus")
        self.assertIsNone(discover_runners.probe_seat(opus, "yes", 1).skill)

    def test_unknown_version_is_not_compatible(self):
        model = model_routing.load_config()["models"]["opus"]["model"]
        result = discover_runners.claude_compatibility(model, "unrecognized version")
        self.assertEqual(result["status"], "unknown")

    def test_compatibility_resolves_exact_model_from_central_seat(self):
        config = copy.deepcopy(model_routing.load_config())
        original = config["models"]["opus"]["model"]
        config["models"]["opus"]["model"] = "fixture-model-revision"
        updated = discover_runners.claude_compatibility("fixture-model-revision", "2.1.275", config=config)
        self.assertEqual(updated["status"], "false")
        self.assertEqual(updated["requirement_seat"], "opus")
        self.assertEqual(discover_runners.claude_compatibility(original, "2.1.275", config=config)["status"], "unknown")
        sibling = config["models"]["sonnet"]["model"]
        self.assertEqual(discover_runners.claude_compatibility(sibling, "2.1.275", config=config)["status"], "unknown")

    def test_compatibility_rejects_missing_or_wrong_runner_seat(self):
        config = model_routing.load_config()
        for seat in ("missing-seat", "sol"):
            policy = {"schema_version": 1, "claude": {seat: {
                "minimum_version": "2.1.280", "evidence": "fixture"}}}
            with self.subTest(seat=seat), patch.object(discover_runners, "COMPATIBILITY_PATH") as path:
                path.read_text.return_value = json.dumps(policy)
                with self.assertRaisesRegex(ValueError, "not a registered Claude seat"):
                    discover_runners.claude_compatibility("fixture-model", "2.1.280", config=config)


if __name__ == "__main__":
    unittest.main()
