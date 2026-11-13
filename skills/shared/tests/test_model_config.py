#!/usr/bin/env python3
"""Offline checks for the single routing configuration and its consumers."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / "shared" / "scripts"))

import model_routing as routing
from skill_paths import runner_script, skill_dir


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(value)
    finally:
        sys.path.pop(0)
    return value


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = routing.load_config()

    def test_all_routes_resolve_with_supported_effort_and_distinct_reviewers(self):
        for name in self.config["routes"]:
            for provider in self.config["providers"]:
                with self.subTest(route=name, provider=provider):
                    roles = routing.resolve_route(name, provider, config=self.config)["roles"]
                    for role in roles.values():
                        routing.validate_selection(role["runner"], role["model"], role["effort"], self.config)
                    if "implementer" in roles and "reviewer" in roles:
                        self.assertNotEqual(roles["implementer"]["model"], roles["reviewer"]["model"])
                        escalated = routing.resolve_route(name, provider, risk="high", config=self.config)["roles"]
                        self.assertIn("implementer", escalated)
                        self.assertIn("reviewer", escalated)

    def test_bounded_work_uses_small_workers_and_cross_provider_review(self):
        lookup = routing.resolve_route("lookup", "openai")["roles"]["worker"]
        self.assertEqual((lookup["seat"], lookup["effort"]), ("terra", "medium"))
        claude = routing.resolve_route("routine-code", "claude")["roles"]
        self.assertEqual((claude["implementer"]["seat"], claude["implementer"]["provider"]), ("sonnet", "claude"))
        self.assertEqual((claude["reviewer"]["seat"], claude["reviewer"]["provider"]), ("sol", "openai"))
        self.assertEqual(routing.resolve_route("routine-code")["provider"], self.config["default_provider"])

    def test_sensitive_work_cannot_resolve_to_small_implementation(self):
        result = routing.resolve_route("routine-code", "openai", risk="high")
        self.assertEqual(result["route"], "hard-code")
        self.assertEqual(result["roles"]["implementer"]["seat"], "astra")
        self.assertEqual(result["requested_route"], "routine-code")

    def test_config_change_updates_resolution_without_editing_consumers(self):
        changed = copy.deepcopy(self.config)
        changed["models"]["terra"]["model"] = "test-model-revision"
        changed["routes"]["lookup"]["roles"]["worker"]["openai"] = "terra:high"
        routing.validate_config(changed)
        result = routing.resolve_route("lookup", "openai", config=changed)
        self.assertEqual(result["roles"]["worker"]["model"], "test-model-revision")
        self.assertEqual(result["roles"]["worker"]["effort"], "high")
        self.assertNotEqual(result["config_digest"], routing.resolve_route("lookup", "openai")["config_digest"])

    def test_invalid_config_fails_instead_of_using_hidden_defaults(self):
        for mutate in (
            lambda c: c["routes"]["lookup"]["roles"]["worker"].update(openai="missing:low"),
            lambda c: c["routes"]["lookup"]["roles"]["worker"].update(openai="terra:unknown"),
            lambda c: c["routes"]["lookup"]["roles"]["worker"].update(openai="terra"),
            lambda c: c["routes"]["lookup"]["roles"]["worker"].update(openai="sonnet:low"),
            lambda c: c["routes"]["lookup"]["roles"]["worker"].pop("claude"),
            lambda c: c["routes"]["lookup"].update(risk_route="missing"),
            lambda c: c["routes"]["lookup"].pop("use_when"),
            lambda c: c["providers"]["grok"].update(cross="grok"),
            lambda c: c.update(default_provider="missing"),
            lambda c: c["gateway_policy"].update(zdr=False),
            lambda c: c["runners"]["codex"].update(default_seat="missing"),
            lambda c: c["runners"]["codex"].update(fallback_runner="missing"),
            lambda c: c["runners"]["codex"].update(default_seat="sonnet"),
            lambda c: c["runners"]["gemini"]["fallbacks"][0].update(seat="sonnet"),
            lambda c: c["runners"]["pi"]["effort_aliases"].update(none="invalid"),
            lambda c: c["discovery_presets"].update(light=["missing"]),
        ):
            changed = copy.deepcopy(self.config)
            mutate(changed)
            with self.assertRaises(ValueError):
                routing.validate_config(changed)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                routing.load_config(Path(directory) / "missing.json")

    def test_duplicate_config_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version": 1, "schema_version": 1}')
            with self.assertRaisesRegex(ValueError, "Duplicate configuration key"):
                routing.load_config(path)

    def test_unknown_route_provider_and_risk_fail_closed(self):
        for args, kwargs in ((["missing", "openai"], {}), (["lookup", "missing"], {}), (["lookup", "openai"], {"risk": "unknown"})):
            with self.assertRaises(ValueError):
                routing.resolve_route(*args, **kwargs)

    def test_runners_share_capabilities_with_the_routing_config(self):
        for name, constant in (("pi", "PI_SEATS"),):
            runner = module(runner_script(name, root=SKILLS), f"config_{name}")
            self.assertEqual(getattr(runner, constant), routing.seat_models(name))

    def test_maintained_model_pins_are_not_copied_into_other_skill_files(self):
        pins = {entry["model"] for entry in self.config["models"].values()}
        violations = []
        for path in SKILLS.rglob("*"):
            if path.suffix not in {".py", ".md", ".json", ".toml", ".yaml"} or path == routing.CONFIG_PATH:
                continue
            if "tests" in path.parts or path.name.startswith("test"):
                continue
            text = path.read_text()
            for pin in pins:
                if pin in text:
                    violations.append(f"{path.relative_to(SKILLS)}: {pin}")
            if path.suffix == ".py" and re.search(r"^(?:MODEL_EFFORT_LEVELS|CODEX_MODEL_EFFORTS|EFFORT_LEVELS|PI_SEATS)\s*=\s*[({\[]", text, re.M):
                violations.append(f"{path.relative_to(SKILLS)}: duplicated capability table")
        self.assertEqual(violations, [])

    def test_flat_install_and_arbitrary_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "installed"
            shutil.copytree(SKILLS / "shared", root / "shared", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(skill_dir("pi-runner", root=SKILLS), root / "pi-runner", ignore=shutil.ignore_patterns("__pycache__"))
            result = subprocess.run([sys.executable, str(root / "shared" / "scripts" / "model_routing.py"), "resolve", "routine-code", "--provider", "openai"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["roles"]["implementer"]["seat"], "terra")
            result = subprocess.run([sys.executable, str(root / "pi-runner" / "scripts" / "run_pi.py"), "--help"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            changed = copy.deepcopy(self.config)
            changed["models"]["kimi"]["model"] = "routingtest"
            (root / "shared/model-routing.json").write_text(json.dumps(changed))
            result = subprocess.run([sys.executable, str(root / "pi-runner/scripts/run_pi.py"), "--help"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("routingtest", result.stdout)


if __name__ == "__main__":
    unittest.main()
