#!/usr/bin/env python3
"""Offline checks for role overrides and the controls attached to a resolved role."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED / "scripts"))

import model_routing as routing


class RouteOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = routing.load_config()

    def resolve(self, route, provider=None, **kwargs):
        return routing.resolve_route(route, provider, config=self.config, **kwargs)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SHARED / "scripts/model_routing.py"), *args],
                              capture_output=True, text=True)

    def test_override_uses_central_effort_and_keeps_other_roles(self):
        before = self.resolve("routine-code")
        after = self.resolve("routine-code", role_overrides={"implementer": {"seat": "grok"}})
        self.assertEqual((after["roles"]["implementer"]["seat"], after["roles"]["implementer"]["effort"]), ("grok", "high"))
        self.assertEqual(after["roles"]["implementer"]["provider"], "grok")
        self.assertEqual(after["roles"]["reviewer"], before["roles"]["reviewer"])

    def test_gateway_seat_carries_the_strict_gateway_policy(self):
        role = self.resolve("review", role_overrides={"reviewer": {"seat": "glm"}})["roles"]["reviewer"]
        self.assertEqual(role["provider_routing"], self.config["gateway_policy"])
        self.assertIsNot(role["provider_routing"], self.config["gateway_policy"])
        for name, selected in self.resolve("routine-code")["roles"].items():
            with self.subTest(role=name):
                self.assertNotIn("provider_routing", selected)
        for seat in ("qwen-flash", "qwen-plus"):
            with self.subTest(seat=seat), self.assertRaisesRegex(ValueError, "strict privacy"):
                self.resolve("review", role_overrides={"reviewer": {"seat": seat}})

    def test_muse_is_an_optional_implementer_with_a_required_receipt(self):
        role = self.resolve("routine-code", "muse")["roles"]
        self.assertEqual(role["implementer"]["model_verification"], "required")
        self.assertEqual(role["implementer"]["privacy_evidence"]["independently_verified"], False)
        self.assertNotEqual(role["reviewer"]["runner"], "muse")
        self.assertNotEqual(self.resolve("analysis", "muse")["roles"]["worker"]["runner"], "muse")
        with self.assertRaisesRegex(ValueError, "not admitted"):
            self.resolve("review", role_overrides={"reviewer": {"seat": "muse-wonder-full"}})

    def test_invalid_override_never_falls_back(self):
        for overrides in ({"extra": {"seat": "grok"}}, {"implementer": {"seat": "missing"}},
                          {"implementer": {"effort": "unknown"}}, {"implementer": {"seat": "astra"}},
                          {"implementer": {"provider_routing": {"zdr": False}}},
                          {"reviewer": {"seat": "sonnet", "effort": "medium"}}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                self.resolve("routine-code", role_overrides=overrides)

    def test_resolution_is_deterministic_and_does_not_mutate_config(self):
        before = copy.deepcopy(self.config)
        first = self.resolve("hard-code", "openai", risk="high")
        self.assertEqual(first, self.resolve("hard-code", "openai", risk="high"))
        self.assertEqual(before, self.config)

    def test_cli_resolves_overrides_runtime_effort_and_lists_routes(self):
        result = self.cli("resolve", "lookup", "--provider", "openai", "--role", "worker=gemini:runtime")
        self.assertEqual(result.returncode, 0, result.stderr)
        worker = json.loads(result.stdout)["roles"]["worker"]
        self.assertEqual((worker["seat"], worker["effort"], worker["effort_control"]), ("gemini", None, "runtime"))
        for args in (("resolve", "lookup", "--provider", "missing"), ("resolve", "lookup", "--role", "worker"),
                     ("resolve", "lookup", "--role", "worker=sonnet:")):
            with self.subTest(args=args):
                self.assertEqual(self.cli(*args).returncode, 2)
        listed = json.loads(self.cli("routes").stdout)
        self.assertEqual(set(listed), set(self.config["routes"]))
        self.assertTrue(all(entry["use_when"] for entry in listed.values()))


if __name__ == "__main__":
    unittest.main()
