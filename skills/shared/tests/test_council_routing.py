#!/usr/bin/env python3
"""Offline checks for council default seats in the central routing configuration."""

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

    def council_cli(self, *arguments: str, script: Path = SCRIPT, cwd: str | Path | None = None):
        return subprocess.run([sys.executable, str(script), "council", *arguments],
                              capture_output=True, text=True, cwd=cwd)

    def test_every_council_resolves_three_distinct_openings_and_two_judges(self):
        for name in self.config["councils"]:
            with self.subTest(council=name):
                council = routing.resolve_council(name, config=self.config)
                self.assertEqual(council["council_name"], name)
                self.assertEqual(len({opening["model"] for opening in council["openings"]}), 3)
                self.assertEqual(len(council["judges"]), 2)
                for role in [*council["openings"], council["organizer"], *council["judges"], council["synthesis"]]:
                    self.assertEqual(role["model"], self.config["models"][role["seat"]]["model"])

    def test_invalid_council_fails_validation(self):
        mutations = (
            lambda config: config["councils"]["technical"]["judges"][0].update(seat="missing"),
            lambda config: config["councils"]["technical"]["openings"][1].update(seat="astra"),
            lambda config: config["councils"]["technical"]["judges"].pop(),
            lambda config: config["councils"]["technical"]["organizer"].update(effort="unsupported"),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.config)
            mutate(changed)
            with self.assertRaises(ValueError):
                routing.validate_config(changed)

    def test_unknown_council_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown council"):
            routing.resolve_council("missing", config=self.config)
        rejected = self.council_cli("missing")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("Unknown council", rejected.stderr)

    def test_flat_install_resolves_a_council_from_an_arbitrary_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "installed"
            shutil.copytree(SHARED, root / "shared", ignore=shutil.ignore_patterns("__pycache__"))
            result = self.council_cli("routine", script=root / "shared" / "scripts" / "model_routing.py", cwd=directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["council_name"], "routine")


if __name__ == "__main__":
    unittest.main()
