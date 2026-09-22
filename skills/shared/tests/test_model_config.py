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
        for name, route in self.config["routes"].items():
            for family in route["families"]:
                with self.subTest(route=name, family=family):
                    resolved = routing.resolve_route(name, family, config=self.config)
                    roles = resolved["roles"]
                    for role in roles.values():
                        routing.validate_selection(role["runner"], role["model"], role["effort"], self.config)
                    if "implementer" in roles and "reviewer" in roles:
                        self.assertNotEqual(roles["implementer"]["model"], roles["reviewer"]["model"])
                        escalated = routing.resolve_route(name, family, risk="high", config=self.config)["roles"]
                        self.assertIn("implementer", escalated)
                        self.assertIn("reviewer", escalated)

    def test_bounded_work_uses_small_workers_and_strong_review(self):
        exploration = routing.resolve_route("code-exploration", "gpt")
        self.assertEqual((exploration["roles"]["worker"]["seat"], exploration["roles"]["worker"]["effort"]), ("luna", "medium"))
        implementation = routing.resolve_route("isolated-implementation", "gpt")
        self.assertEqual((implementation["roles"]["implementer"]["seat"], implementation["roles"]["implementer"]["effort"]), ("luna", "high"))
        self.assertEqual(implementation["roles"]["reviewer"]["seat"], "astra")
        claude = routing.resolve_route("routine-implementation", "claude")
        self.assertEqual(claude["roles"]["implementer"]["seat"], "sonnet")
        self.assertEqual(claude["roles"]["reviewer"]["seat"], "fable")

    def test_sensitive_work_cannot_resolve_to_small_implementation(self):
        result = routing.resolve_route("isolated-implementation", "gpt", risk="high")
        self.assertEqual(result["route"], "sensitive-implementation")
        self.assertEqual(result["roles"]["implementer"]["seat"], "astra")
        self.assertEqual(result["requested_route"], "isolated-implementation")

    def test_config_change_updates_resolution_without_editing_consumers(self):
        changed = copy.deepcopy(self.config)
        changed["models"]["luna"]["model"] = "test-model-revision"
        changed["routes"]["code-exploration"]["families"]["gpt"]["worker"]["effort"] = "high"
        routing.validate_config(changed)
        result = routing.resolve_route("code-exploration", "gpt", config=changed)
        self.assertEqual(result["roles"]["worker"]["model"], "test-model-revision")
        self.assertEqual(result["roles"]["worker"]["effort"], "high")
        self.assertNotEqual(result["config_digest"], routing.resolve_route("code-exploration", "gpt")["config_digest"])

    def test_invalid_config_fails_instead_of_using_hidden_defaults(self):
        for mutate in (
            lambda c: c["routes"]["code-exploration"]["families"]["gpt"]["worker"].update(seat="missing"),
            lambda c: c["routes"]["code-exploration"]["families"]["gpt"]["worker"].update(effort="ultra"),
            lambda c: c["routes"]["isolated-implementation"]["families"]["gpt"]["reviewer"].update(seat="luna"),
            lambda c: c["runners"]["codex"].update(default_seat="missing"),
            lambda c: c["runners"]["codex"].update(fallback_runner="missing"),
            lambda c: c["runners"]["codex"].update(default_seat="luna", default_effort="ultra"),
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

    def test_unknown_route_family_and_risk_fail_closed(self):
        for args, kwargs in ((["missing", "gpt"], {}), (["code-exploration", "missing"], {}), (["code-exploration", "gpt"], {"risk": "unknown"})):
            with self.assertRaises(ValueError):
                routing.resolve_route(*args, **kwargs)

    def test_runners_and_launcher_share_capabilities(self):
        worker = module(runner_script("codex", root=SKILLS), "config_worker")
        launcher = module(skill_dir("implement-and-review", root=SKILLS) / "scripts" / "launch.py", "config_launcher")
        self.assertEqual(worker.DEFAULT_MODEL, routing.default_model("codex"))
        self.assertEqual(worker.MODEL_EFFORT_LEVELS, {k: tuple(v) for k, v in launcher.CODEX_MODEL_EFFORTS.items()})
        for name, constant in (("pi", "PI_SEATS"),):
            runner = module(runner_script(name, root=SKILLS), f"config_{name}")
            self.assertEqual(getattr(runner, constant), routing.seat_models(name))

    def test_panel_references_resolve_without_duplicate_model_flags(self):
        panel = module(SKILLS / "shared" / "scripts" / "panel_round.py", "config_panel")
        path = skill_dir("collaborative-delivery", root=SKILLS) / "assets" / "routing.toml"
        raw = panel.load_toml(path)
        self.assertTrue(all("model" not in provider and "effort" not in provider for provider in raw["providers"].values()))
        resolved = routing.resolve_panel_providers(raw)
        for provider in resolved["providers"].values():
            self.assertTrue(provider["model"])
            self.assertIn(provider["effort"], self.config["effort_levels"])
            self.assertFalse(any(arg in {"--model", "--effort", "--thinking"} for arg in provider.get("runner_args", [])))

    def test_panel_reference_rejects_model_and_effort_overrides(self):
        base = {"providers": {"test": {"route": "precision-review", "family": "claude", "route_role": "reviewer", "kind": "runner"}}}
        for override in ({"effort": "low"}, {"model": "other"}, {"runner_args": ["--effort=low"]}, {"runner_args": ["-elow"]}, {"runner_args": ["-mother"]}, {"runner": "codex"}):
            value = copy.deepcopy(base)
            value["providers"]["test"].update(override)
            with self.assertRaises(ValueError):
                routing.resolve_panel_providers(value)

    def test_panel_command_forwards_resolved_effort(self):
        panel = module(SKILLS / "shared" / "scripts" / "panel_round.py", "config_panel_command")
        provider = routing.resolve_panel_providers({"providers": {"review": {
            "route": "precision-review", "family": "claude", "route_role": "reviewer", "kind": "runner",
        }}})["providers"]["review"]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = panel.run_runner_role(
                provider_cfg=provider, role_cfg={"runner_role": "codereviewer"},
                role="review", phase="review", prompt_path=base / "prompt.md",
                output_file=base / "out.json", stdout_path=base / "stdout", stderr_path=base / "stderr",
                working_dir=base, skill_root=skill_dir("collaborative-delivery", root=SKILLS),
                dry_run=True, role_session=None,
            )
        command = shlex.split(result["command_preview"])
        self.assertEqual(command[command.index("--model") + 1], provider["model"])
        self.assertEqual(command[command.index("--effort") + 1], provider["effort"])
        self.assertEqual(command.count("--effort"), 1)
        self.assertIn("--disable-fallback", command)

    def test_panel_snapshot_blocks_a_changed_selection_before_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = base / "assets" / "routing.toml"
            path.parent.mkdir()
            template = '''[skill]
name = "routing-test"
[providers.reader]
route = "code-exploration"
family = "gpt"
route_role = "worker"
kind = "native"
[roles.reader]
provider = "reader"
[phases.review]
roles = ["reader"]
'''
            path.write_text(template)
            command = [sys.executable, str(SKILLS / "shared/scripts/panel_round.py"), "--routing", str(path),
                       "--phase", "review", "--goal", "Inspect only", "--working-dir", str(base), "--out", str(base / "out")]
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            snapshot = (base / "out/resolved_routing.json").read_text()
            path.write_text(template.replace('route = "code-exploration"', 'route = "technical-analysis"'))
            result = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Panel routing changed", result.stderr)
            self.assertEqual((base / "out/resolved_routing.json").read_text(), snapshot)

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
            shutil.copytree(skill_dir("codex-runner", root=SKILLS), root / "codex-runner", ignore=shutil.ignore_patterns("__pycache__"))
            result = subprocess.run([sys.executable, str(root / "shared" / "scripts" / "model_routing.py"), "resolve", "isolated-implementation", "--family", "gpt"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["roles"]["implementer"]["seat"], "luna")
            result = subprocess.run([sys.executable, str(root / "codex-runner" / "scripts" / "run_codex.py"), "--help"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

            changed = copy.deepcopy(self.config)
            changed["models"]["astra"]["model"] = "routingtest"
            (root / "shared/model-routing.json").write_text(json.dumps(changed))
            result = subprocess.run([sys.executable, str(root / "codex-runner/scripts/run_codex.py"), "--help"], cwd=directory, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("routingtest", result.stdout)


if __name__ == "__main__":
    unittest.main()
