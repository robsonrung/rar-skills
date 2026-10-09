#!/usr/bin/env python3
"""Offline routing and installation integrity regression tests."""
import copy
import json
import os
import subprocess
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import install_drift
from model_routing import CONFIG_PATH, config_digest, load_config
from runner_preflight import COMPATIBILITY_PATH


class InstallDriftTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.installed = Path(self.temp.name) / "installed"
        for root in (self.source, self.installed):
            for relative in install_drift.CRITICAL_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n")
            shutil.copyfile(CONFIG_PATH, root / "shared/model-routing.json")
            shutil.copyfile(COMPATIBILITY_PATH, root / "shared/runner-compatibility.json")

    def change_sol(self):
        path = self.installed / "shared/model-routing.json"
        data = json.loads(path.read_text())
        data["models"]["sol"]["model"] = "gpt-5.6-sol"
        path.write_text(json.dumps(data))

    def test_matching_tree_and_seat(self):
        report = install_drift.compare_install(self.source, self.installed, seat="sol", effort="high")
        self.assertFalse(report["blocked"], report["reasons"])
        self.assertFalse(report["route_checks"]["installed"]["blocked"])
        self.assertEqual(report["evidence"]["installed"]["model-routing.json"]["path"], str(self.installed / "shared/model-routing.json"))

    def test_stale_seat_blocks_without_rewriting(self):
        self.change_sol()
        before = (self.installed / "shared/model-routing.json").read_bytes()
        report = install_drift.compare_install(self.source, self.installed, seat="sol", effort="high")
        self.assertTrue(report["blocked"])
        self.assertTrue(report["route_checks"]["installed"]["blocked"])
        self.assertEqual(before, (self.installed / "shared/model-routing.json").read_bytes())

    def test_approved_snapshot_stays_immutable(self):
        config = load_config()
        route = {"config_digest": config_digest(config), "roles": {"reviewer": {
            "seat": "sol", "model": config["models"]["sol"]["model"], "runner": config["models"]["sol"]["runner"], "effort": "high"}}}
        original = copy.deepcopy(route)
        self.change_sol()
        result = install_drift.check_loaded_install(self.installed, approved_route=route)
        self.assertTrue(result["blocked"])
        self.assertEqual(route, original)

    def test_unmanifested_install_provenance_is_unknown(self):
        result = install_drift.check_loaded_install(self.installed)
        self.assertFalse(result["blocked"])
        self.assertEqual(result["status"], "unknown")
        self.assertIn("unknown", result["evidence"]["provenance"])
        self.change_sol()
        result = install_drift.check_loaded_install(self.installed, source_root=self.source)
        self.assertTrue(result["blocked"])
        self.assertIn("unknown", result["evidence"]["provenance"])

    def test_manifest_detects_loaded_script_change(self):
        install_drift.write_manifest(self.source, self.installed)
        self.assertEqual(install_drift.check_loaded_install(self.installed)["status"], "match")
        (self.installed / "shared/scripts/model_routing.py").write_text("changed")
        result = install_drift.check_loaded_install(self.installed)
        self.assertTrue(result["blocked"])
        self.assertIn("Loaded file", " ".join(result["reasons"]))

    def test_manifest_detects_source_change_and_missing_source(self):
        install_drift.write_manifest(self.source, self.installed)
        (self.source / "shared/scripts/model_routing.py").write_text("changed")
        self.assertTrue(install_drift.check_loaded_install(self.installed)["blocked"])
        shutil.rmtree(self.source)
        report = install_drift.check_loaded_install(self.installed)
        self.assertFalse(report["blocked"])
        self.assertEqual(report["source_status"], "unknown")
        self.assertEqual(report["status"], "unknown")

    def test_manifest_outside_shared_symlink(self):
        shutil.rmtree(self.installed / "shared")
        (self.installed / "shared").symlink_to(self.source / "shared", target_is_directory=True)
        path = install_drift.write_manifest(self.source, self.installed)
        self.assertEqual(path.parent, self.installed)
        self.assertFalse((self.source / install_drift.MANIFEST_NAME).exists())

    def test_comparison_never_calls_a_cli(self):
        with patch("subprocess.run", side_effect=AssertionError("No process allowed")):
            self.assertEqual(install_drift.main(["--source-root", str(self.source), "--installed-root", str(self.installed), "--seat", "sol", "--effort", "high"]), 0)

    def test_invalid_manifest_blocks(self):
        for content in ("[]", '{"schema_version": 1, "files": {}}'):
            (self.installed / install_drift.MANIFEST_NAME).write_text(content)
            self.assertTrue(install_drift.check_loaded_install(self.installed)["blocked"])

    def test_prompt_dependency_drift_and_legacy_coverage_are_explicit(self):
        for relative in ("shared/scripts/runner_prompt.py", "shared/scripts/context_packet.py"):
            with self.subTest(relative=relative):
                path = install_drift.write_manifest(self.source, self.installed)
                original = (self.installed / relative).read_bytes()
                (self.installed / relative).write_text("changed behavior")
                report = install_drift.check_loaded_install(self.installed)
                self.assertTrue(report["blocked"])
                self.assertIn(relative, " ".join(report["reasons"]))
                (self.installed / relative).write_bytes(original)
        current = json.loads(path.read_text())
        legacy = copy.deepcopy(current)
        legacy["files"] = {key: value for key, value in current["files"].items()
                           if key in install_drift.LEGACY_CRITICAL_FILES}
        path.write_text(json.dumps(legacy))
        before = path.read_bytes()
        report = install_drift.check_loaded_install(self.installed)
        self.assertTrue(report["blocked"])
        self.assertEqual(report["manifest_coverage"], "legacy")
        self.assertIn("refresh", " ".join(report["reasons"]))
        self.assertEqual(set(report["evidence"]["files"]), set(install_drift.LEGACY_CRITICAL_FILES))
        (self.installed / "shared/scripts/model_receipt.py").write_text("changed old dependency")
        report = install_drift.check_loaded_install(self.installed)
        self.assertIn("Loaded file differs", " ".join(report["reasons"]))
        self.assertEqual(path.read_bytes(), before)

    def test_flat_copy_runs_all_adapters_with_shared_prompt_dependency(self):
        source = Path(__file__).resolve().parents[3]
        bundle = Path(self.temp.name) / "flat-copy"
        shutil.copytree(source / "skills/shared", bundle / "shared", ignore=shutil.ignore_patterns("__pycache__"))
        names = ("claude", "codex", "gemini", "grok", "pi")
        for name in names:
            shutil.copytree(install_drift.runner_script(name, root=source / "skills").parent.parent,
                            bundle / f"{name}-runner", ignore=shutil.ignore_patterns("__pycache__"))
        manifest_path = install_drift.write_manifest(source, bundle)
        self.assertEqual(install_drift.check_loaded_install(bundle)["status"], "match")
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("shared/scripts/runner_prompt.py", manifest["files"])
        self.assertIn("shared/scripts/context_packet.py", manifest["files"])
        for name in names:
            with self.subTest(name=name):
                metadata = {"prompt_context": {}, "execution_provenance": {"resources": ["envelope-only"]}}
                result = subprocess.run([sys.executable, str(bundle / f"{name}-runner/scripts/run_{name}.py"),
                    "Review", "--json", "--disable-fallback", "--metadata-json", json.dumps(metadata)],
                    cwd=self.temp.name, env={**os.environ, "PATH": ""}, text=True, capture_output=True)
                envelope = json.loads(result.stdout)
                self.assertEqual(envelope["return_code"], -2, envelope)
                self.assertEqual(envelope["dispatch_metadata"], metadata)
                self.assertNotIn("envelope-only", envelope["command"])
                self.assertEqual(envelope["adapter_input_measurement"]["scope"], "adapter_rendered_input")

    def test_null_approved_route_is_not_accepted(self):
        path = self.installed / "approved.json"
        path.write_text("null")
        self.assertEqual(install_drift.main(["--source-root", str(self.source), "--installed-root", str(self.installed), "--approved-route", str(path)]), 1)

    def test_approved_route_requires_explicit_effort(self):
        config = load_config()
        route = {"roles": {"reviewer": {"seat": "opus", "model": "claude-opus-5-5",
                                         "runner": "claude", "effort": None}}}
        original = copy.deepcopy(route)
        self.assertTrue(install_drift.verify_route(route, config)["blocked"])
        self.assertEqual(original, route)


if __name__ == "__main__":
    unittest.main()
