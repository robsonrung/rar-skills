#!/usr/bin/env python3
"""Offline checks for council poll profiles and their central routing contract."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1]
SCRIPT = SHARED / "scripts" / "model_routing.py"
sys.path.insert(0, str(SHARED / "scripts"))

import model_routing as routing  # noqa: E402


class CouncilRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = routing.load_config()

    def resolve_legacy_roles(self, name: str) -> dict:
        council = self.config["councils"][name]
        return {
            key: [routing.resolve_reference(reference, self.config) for reference in value]
            if isinstance(value, list) else routing.resolve_reference(value, self.config)
            for key, value in council.items()
        }

    def council_cli(self, *arguments: str, script: Path = SCRIPT, cwd: str | Path | None = None):
        return subprocess.run(
            [sys.executable, str(script), "council", *arguments],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    def test_standard_default_preserves_existing_routes_and_full_budget(self):
        preview = routing.resolve_council("technical", config=self.config)
        self.assertEqual(
            {key: preview[key] for key in ("openings", "organizer", "judges", "synthesis")},
            self.resolve_legacy_roles("technical"),
        )
        self.assertEqual(preview["council_name"], "technical")
        self.assertEqual(preview["poll_profile"], "standard")
        self.assertEqual(preview["risk_flags"], [])
        self.assertEqual(preview["poll_policy"], routing.council_poll_policy(self.config))
        self.assertEqual(
            preview["poll_budget"],
            {
                "base_calls": 7,
                "conditional_calls": 3,
                "validation_retry_ceiling": 10,
                "maximum_calls": 20,
            },
        )
        self.assertEqual(preview["conditional_stages"], {"gap_repair": 3, "judge": 0})

    def test_lean_keeps_exact_judge_routes_and_declares_conditional_budget(self):
        standard = routing.resolve_council("technical", config=self.config)
        lean = routing.resolve_council("technical", "lean", config=self.config)
        self.assertEqual(lean["openings"], standard["openings"])
        self.assertEqual(lean["organizer"], standard["organizer"])
        self.assertEqual(lean["judges"], standard["judges"])
        self.assertEqual(lean["synthesis"], standard["synthesis"])
        self.assertEqual(len({opening["model"] for opening in lean["openings"]}), 3)
        self.assertEqual(lean["poll_profile"], "lean")
        self.assertEqual(
            lean["poll_budget"],
            {
                "base_calls": 5,
                "conditional_calls": 5,
                "validation_retry_ceiling": 10,
                "maximum_calls": 20,
            },
        )
        self.assertEqual(lean["conditional_stages"], {"gap_repair": 3, "judge": 2})
        self.assertEqual(
            lean["poll_budget"]["base_calls"] + lean["poll_budget"]["conditional_calls"],
            10,
        )

    def test_lean_requires_standard_for_security_or_full_risk(self):
        flags = self.config["council_policy"]["full_required_flags"]
        standard = routing.resolve_council("technical", risk_flags=[flags[1], flags[0]], config=self.config)
        self.assertEqual(standard["risk_flags"], flags[:2])
        for flag in flags:
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "requires standard"):
                routing.resolve_council("technical", "lean", risk_flags=[flag], config=self.config)
        with self.assertRaisesRegex(ValueError, "requires standard"):
            routing.resolve_council("security", "lean", config=self.config)
        with self.assertRaisesRegex(ValueError, "Unknown council risk flag"):
            routing.resolve_council("technical", risk_flags=["unknown"], config=self.config)
        with self.assertRaisesRegex(ValueError, "Duplicate council risk flag"):
            routing.resolve_council("technical", risk_flags=[flags[0], flags[0]], config=self.config)

    def test_resolved_policy_is_a_copy_that_survives_later_configuration_drift(self):
        snapshot = routing.resolve_council("analysis", "lean", config=self.config)
        snapshot["poll_policy"]["full_required_flags"].append("changed")
        snapshot["poll_budget"]["base_calls"] = 99
        self.assertNotIn("changed", self.config["council_policy"]["full_required_flags"])
        self.assertEqual(self.config["council_policy"]["poll_profiles"]["lean"]["budget"]["base_calls"], 5)

        changed = copy.deepcopy(self.config)
        changed["council_policy"]["low_confidence_threshold"] = 69
        routing.validate_config(changed)
        current = routing.resolve_council("analysis", "lean", config=changed)
        self.assertEqual(snapshot["poll_policy"]["low_confidence_threshold"], 70)
        self.assertEqual(current["poll_policy"]["low_confidence_threshold"], 69)

    def test_invalid_council_policy_or_unavailable_judge_route_fails_validation(self):
        mutations = (
            lambda config: config["council_policy"]["poll_profiles"]["lean"]["budget"].update(maximum_calls=19),
            lambda config: config["council_policy"]["poll_profiles"]["lean"]["conditional_stages"].update(judge=1),
            lambda config: config["council_policy"]["full_required_flags"].append("security"),
            lambda config: config["councils"]["technical"]["judges"][0].update(route="missing"),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.config)
            mutate(changed)
            with self.assertRaises(ValueError):
                routing.validate_config(changed)

    def test_cli_resolves_profiles_and_rejects_unsafe_lean_requests(self):
        default = self.council_cli("technical")
        explicit = self.council_cli("technical", "--poll-profile", "standard")
        lean = self.council_cli("technical", "--poll-profile", "lean")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(lean.returncode, 0, lean.stderr)
        self.assertEqual(json.loads(default.stdout), json.loads(explicit.stdout))
        self.assertEqual(json.loads(lean.stdout)["poll_budget"]["conditional_calls"], 5)
        rejected = self.council_cli("technical", "--poll-profile", "lean", "--risk-flag", "security")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("requires standard", rejected.stderr)

    def test_flat_install_resolves_lean_council_from_an_arbitrary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "installed"
            shutil.copytree(SHARED, root / "shared", ignore=shutil.ignore_patterns("__pycache__"))
            result = self.council_cli(
                "routine",
                "--poll-profile",
                "lean",
                script=root / "shared" / "scripts" / "model_routing.py",
                cwd=directory,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["council_name"], "routine")
        self.assertEqual(preview["poll_profile"], "lean")
        self.assertEqual(preview["poll_budget"]["maximum_calls"], 20)


if __name__ == "__main__":
    unittest.main()
