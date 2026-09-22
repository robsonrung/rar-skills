#!/usr/bin/env python3
"""Offline checks for profile previews and exact role selection."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SHARED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED / "scripts"))

import model_routing as routing


class ModelProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = routing.load_config()

    def resolve(self, route, profile=None, **kwargs):
        return routing.resolve_profile(route, profile, config=self.config, **kwargs)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SHARED / "scripts/model_routing.py"),
                               "resolve", *args], capture_output=True, text=True)

    def test_profile_precedence_and_legacy_cli_default(self):
        central = self.resolve("routine-function")
        local = self.resolve("routine-function", local_profile="balanced")
        explicit = self.resolve("routine-function", "economy", local_profile="balanced")
        self.assertEqual((central["profile"], central["selection_source"]), ("economy", "central"))
        self.assertEqual((local["profile"], local["selection_source"]), ("balanced", "local"))
        self.assertEqual((explicit["profile"], explicit["selection_source"]), ("economy", "explicit"))
        legacy = self.cli("routine-function")
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        legacy = json.loads(legacy.stdout)
        self.assertEqual(legacy["family"], "gpt")
        self.assertNotIn("profile", legacy)
        self.assertEqual(legacy["roles"]["implementer"]["seat"], "terra")
        default = self.cli("routine-function", "--profile", "default")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(json.loads(default.stdout)["profile"], "economy")

    def test_economy_bounded_roles_and_independent_review(self):
        for route in ("routine-function", "isolated-implementation", "routine-implementation",
                      "test-implementation", "known-cause-fix", "validation-unit", "validation-diagnosis"):
            with self.subTest(route=route):
                roles = self.resolve(route)["roles"]
                self.assertEqual((roles["implementer"]["seat"], roles["implementer"]["effort"]), ("glm", "high"))
                self.assertEqual((roles["reviewer"]["seat"], roles["reviewer"]["effort"]), ("luna", "high"))
                self.assertNotEqual(roles["implementer"]["model"], roles["reviewer"]["model"])

    def test_risk_routes_remain_complete_and_strong(self):
        for name, route in self.config["routes"].items():
            with self.subTest(route=name):
                target = self.config["routes"][route["risk_route"]]
                self.assertIn("economy", target["families"])
                if name == "test-execution":
                    continue
                result = self.resolve(name, risk="high")
                self.assertEqual(result["route"], route["risk_route"])
                expected = target["families"].get("gpt", target["families"].get("balanced"))
                self.assertEqual({role: (value["seat"], value["effort"]) for role, value in result["roles"].items()},
                                 {role: (value["seat"], value["effort"]) for role, value in expected.items()})
                self.assertNotIn("glm", [value["seat"] for value in result["roles"].values()])

    def test_validation_preserves_scope_and_integration_design(self):
        self.assertEqual(self.resolve("validation-scope")["roles"]["worker"]["seat"], "sol")
        integration = self.resolve("validation-integration")["roles"]
        self.assertEqual(integration["implementer"]["seat"], "sol")
        self.assertEqual(integration["reviewer"]["seat"], "astra")
        self.assertEqual(self.resolve("validation-browser")["roles"]["worker"]["seat"], "glm")
        self.assertEqual(self.resolve("validation-review")["roles"]["reviewer"]["seat"], "luna")
        self.assertIn("The cause is proven", " ".join(self.resolve("validation-diagnosis")["conditions"]))

    def test_balanced_uses_existing_family_for_each_route(self):
        for name, route in self.config["routes"].items():
            with self.subTest(route=name):
                actual = self.resolve(name, "balanced")
                if name == "test-execution":
                    self.assertEqual(actual["roles"], {})
                    continue
                family = "balanced" if name.startswith("validation-") else "gpt"
                self.assertEqual(actual["family"], family)
                expected = routing.resolve_route(name, family, config=self.config)["roles"]
                self.assertEqual({role: {key: value[key] for key in ("seat", "model", "runner", "effort")}
                                  for role, value in actual["roles"].items()}, expected)

    def test_profile_policy_attaches_only_to_pi_roles(self):
        result = self.resolve("routine-implementation")
        self.assertEqual(result["roles"]["implementer"]["provider_routing"],
                         {"gateway": "openrouter", "zdr": True, "data_collection": "deny", "require_parameters": True})
        self.assertNotIn("provider_routing", result["roles"]["reviewer"])
        for family in ("gpt", "claude", "economy"):
            legacy = routing.resolve_route("routine-implementation", family, config=self.config)
            for role in legacy["roles"].values():
                self.assertNotIn("provider_routing", role)

    def test_provider_constraints_are_copied_without_weakening(self):
        changed = copy.deepcopy(self.config)
        policy = changed["profile_policy"]["provider_routing"]
        policy.update(only=["approved-provider"], allow_fallbacks=False)
        routing.validate_config(changed)
        resolved = routing.resolve_profile("routine-implementation", config=changed)
        self.assertEqual(resolved["roles"]["implementer"]["provider_routing"], policy)
        self.assertNotIn("provider_routing", resolved["roles"]["reviewer"])

    def test_deterministic_execution_never_resolves_a_model_worker(self):
        with mock.patch.object(routing, "resolve_role", side_effect=AssertionError("Unexpected model selection")):
            for profile in self.config["profiles"]:
                for risk in self.config["policy"]["risk_levels"]:
                    result = self.resolve("test-execution", profile, risk=risk)
                    self.assertEqual(result["execution"], "repository-commands")
                    self.assertEqual(result["roles"], {})
                    self.assertEqual(result["alternatives"], {})
                    self.assertEqual(result["route"], "test-execution")
        with self.assertRaisesRegex(ValueError, "accepts no model overrides"):
            self.resolve("test-execution", role_overrides={"worker": {"seat": "glm"}})

    def test_candidate_identities_capabilities_and_source_dates(self):
        expected = {
            "deepseek-flash": "deepseek/deepseek-v4.1-flash",
            "qwen-flash": "qwen/qwen3.8-flash",
            "mistral-small": "mistralai/mistral-small-3.2",
            "qwen-plus": "qwen/qwen3.6-plus",
            "kimi-code": "moonshotai/kimi-k2.7-code",
        }
        for seat, model in expected.items():
            entry = self.config["models"][seat]
            self.assertEqual(entry["model"], model)
            self.assertEqual(entry["capabilities"], {"tools": True, "images": True})
            self.assertEqual(entry["capability_evidence"]["checked_at"], "2026-09-20")
            self.assertEqual(entry["privacy"]["checked_at"], "2026-09-20")
            self.assertTrue(entry["privacy"]["preflight_required"])
        self.assertEqual(self.config["models"]["qwen"]["model"], "qwen/qwen3.8-max")
        self.assertEqual(self.config["models"]["kimi"]["model"], "moonshotai/kimi-k3")

    def test_glm_and_deepseek_refuse_approximate_effort(self):
        for seat in ("glm", "deepseek-flash"):
            model = self.config["models"][seat]["model"]
            for effort in ("low", "high", "max"):
                routing.validate_selection("pi", model, effort, self.config)
            for effort in (None, "none", "off", "minimal", "medium", "xhigh", "ultra"):
                with self.subTest(seat=seat, effort=effort), self.assertRaises(ValueError):
                    routing.validate_selection("pi", model, effort, self.config)
        self.assertNotIn("max", routing.model_efforts("pi", self.config)[self.config["models"]["qwen"]["model"]])

    def test_runtime_effort_is_explicit_and_only_for_known_models(self):
        for seat in ("qwen-flash", "mistral-small", "qwen-plus", "kimi-code"):
            model = self.config["models"][seat]["model"]
            routing.validate_selection("pi", model, None, self.config)
            for effort in ("off", "high", "max"):
                with self.subTest(seat=seat, effort=effort), self.assertRaises(ValueError):
                    routing.validate_selection("pi", model, effort, self.config)
        with self.assertRaises(ValueError):
            routing.validate_selection("pi", "vendor/custom-model", None, self.config)
        routing.validate_selection("pi", "vendor/custom-model", "high", self.config)
        worker = self.resolve("validation-browser", role_overrides={"worker": {"seat": "mistral-small"}})["roles"]["worker"]
        self.assertIsNone(worker["effort"])
        self.assertEqual(worker["effort_control"], "runtime")

    def test_strict_privacy_refuses_unavailable_overrides(self):
        for seat in ("qwen-flash", "qwen-plus"):
            with self.subTest(seat=seat), self.assertRaisesRegex(ValueError, "strict privacy"):
                self.resolve("routine-implementation", role_overrides={"implementer": {"seat": seat}})
            direct = routing.resolve_role({"seat": seat, "effort": None}, self.config)
            self.assertNotIn("provider_routing", direct)
        implementation = self.resolve("routine-implementation")["alternatives"]["implementer"]
        browser = self.resolve("validation-browser")["alternatives"]["worker"]
        self.assertEqual([entry["seat"] for entry in implementation], ["glm", "deepseek-flash", "kimi-code"])
        self.assertEqual([entry["seat"] for entry in browser], ["glm", "mistral-small"])

    def test_override_uses_central_effort_and_keeps_other_roles(self):
        before = self.resolve("routine-implementation")
        after = self.resolve("routine-implementation", role_overrides={"implementer": {"seat": "deepseek-flash"}})
        self.assertEqual(after["roles"]["implementer"]["effort"], "high")
        self.assertEqual(after["roles"]["reviewer"], before["roles"]["reviewer"])
        self.assertEqual(after["roles"]["implementer"]["provider_routing"], before["roles"]["implementer"]["provider_routing"])
        with self.assertRaisesRegex(ValueError, "distinct models"):
            self.resolve("routine-implementation", role_overrides={"implementer": {"seat": "luna", "effort": "high"}})
        with self.assertRaisesRegex(ValueError, "explicit effort"):
            self.resolve("routine-implementation", role_overrides={"implementer": {"seat": "sol"}})

    def test_missing_tools_or_images_blocks_browser_selection(self):
        for capability in ("tools", "images"):
            changed = copy.deepcopy(self.config)
            changed["models"]["mistral-small"]["capabilities"][capability] = False
            with self.subTest(capability=capability), self.assertRaisesRegex(ValueError, capability):
                routing.resolve_profile("validation-browser", role_overrides={"worker": {"seat": "mistral-small"}}, config=changed)
            alternatives = routing.resolve_profile("validation-browser", config=changed)["alternatives"]["worker"]
            self.assertNotIn("mistral-small", [entry["seat"] for entry in alternatives])

    def test_preview_output_is_deterministic_and_does_not_mutate_config(self):
        before = copy.deepcopy(self.config)
        first = self.resolve("routine-implementation")
        self.assertEqual(first, self.resolve("routine-implementation"))
        first["roles"]["implementer"]["provider_routing"]["zdr"] = False
        first["roles"]["implementer"]["capabilities"]["tools"] = False
        self.assertEqual(self.config, before)
        self.assertTrue(self.resolve("routine-implementation")["roles"]["implementer"]["provider_routing"]["zdr"])

    def test_explicit_saved_panel_snapshot_never_gets_new_policy(self):
        panel = {"providers": {"worker": {"seat": "glm", "model": "saved-model", "runner": "pi", "effort": "medium"}}}
        self.assertEqual(routing.resolve_panel_providers(panel, self.config), panel)
        changed = copy.deepcopy(self.config)
        changed["models"]["glm"]["model"] = "replacement-model"
        changed["default_profile"] = "balanced"
        self.assertEqual(routing.resolve_panel_providers(panel, changed), panel)

    def test_invalid_profile_configuration_fails_before_preview(self):
        mutations = (
            lambda c: c.update(default_profile="missing"),
            lambda c: c["routes"]["validation-risk"]["families"].pop("economy"),
            lambda c: c["profile_policy"]["provider_routing"].update(zdr=False),
            lambda c: c["profile_policy"]["provider_routing"].update(data_collection="allow"),
            lambda c: c["profile_policy"]["provider_routing"].update(allow_fallbacks="yes"),
            lambda c: c["models"]["glm"]["capabilities"].update(images=False),
            lambda c: c["models"]["deepseek-flash"].update(default_effort="medium"),
            lambda c: c["profiles"]["economy"]["role_candidates"]["validation-browser"].update(worker=["missing"]),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.config)
            mutate(changed)
            with self.assertRaises(ValueError):
                routing.validate_config(changed)

    def test_invalid_profile_or_override_never_falls_back(self):
        cases = (
            {"profile": "missing"},
            {"local_profile": "missing"},
            {"role_overrides": {"extra": {"seat": "glm"}}},
            {"role_overrides": {"implementer": {"seat": "missing"}}},
            {"role_overrides": {"implementer": {"effort": "medium"}}},
            {"role_overrides": {"implementer": {"provider_routing": {"zdr": False}}}},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.resolve("routine-implementation", **kwargs)

    def test_cli_overrides_runtime_effort_and_rejects_ambiguous_choices(self):
        result = self.cli("validation-browser", "--profile", "economy", "--role", "worker=mistral-small:runtime")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)["roles"]["worker"]["effort"])
        for args in (
            ("--profile", "economy", "--role", "worker=qwen-flash"),
            ("--profile", "economy", "--role", "worker=glm:medium"),
            ("--profile", "economy", "--role", "worker=glm", "--role", "worker=mistral-small"),
            ("--profile", "economy", "--family", "gpt"),
            ("--local-profile", "economy", "--family", "gpt"),
            ("--role", "worker=glm"),
        ):
            with self.subTest(args=args):
                self.assertNotEqual(self.cli("validation-browser", *args).returncode, 0)


if __name__ == "__main__":
    unittest.main()
