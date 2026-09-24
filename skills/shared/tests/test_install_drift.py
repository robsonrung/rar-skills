#!/usr/bin/env python3
"""Offline routing and installation integrity regression tests."""
import copy
import json
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

    def test_null_approved_route_is_not_accepted(self):
        path = self.installed / "approved.json"
        path.write_text("null")
        self.assertEqual(install_drift.main(["--source-root", str(self.source), "--installed-root", str(self.installed), "--approved-route", str(path)]), 1)

    def test_approved_route_requires_explicit_effort(self):
        config = load_config()
        route = {"roles": {"reviewer": {"seat": "opus-5-5", "model": "claude-opus-5-5",
                                         "runner": "claude", "effort": None}}}
        original = copy.deepcopy(route)
        self.assertTrue(install_drift.verify_route(route, config)["blocked"])
        self.assertEqual(original, route)


if __name__ == "__main__":
    unittest.main()
