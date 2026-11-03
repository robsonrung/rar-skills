#!/usr/bin/env python3
"""Checks for runner support modules that outlived the removed pipeline ledger tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import browser_preflight as browser
import runner_jobs


class RunnerSupportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.brief = self.root / "brief.md"
        self.brief.write_text("Build the bounded change.")

    def test_invalid_terminal_runner_output_is_failed(self):
        result = self.root / "result.json"
        for output in ("partial json", "[]", '{"success":"yes"}'):
            result.write_text(output)
            self.assertEqual(runner_jobs.job_status(self.root, {"result_file": str(result)}), "failed")

    def browser_record(self):
        driver = self.root / "playwright-cli"
        driver.write_text("fixture driver")
        observation = self.root / "observed.json"
        observation.write_text('{"navigation":true,"saved":"after reload"}')
        record = {"mechanism": "playwright-cli", "working_dir": str(self.root), "status": "ready", "ready": True,
                  "checks": {key: True for key in browser.CHECKS}, "evidence": [browser.reference(observation)],
                  "driver": {**browser.reference(driver), "version": "fixture"}}
        path = self.root / "preflight.json"
        path.write_text(json.dumps(record))
        return {"mechanism": "playwright-cli", "preflight": browser.reference(path)}, record, driver

    def test_browser_preflight_rejects_changed_driver_workspace_or_checks(self):
        bound, record, driver = self.browser_record()
        with patch.object(browser.shutil, "which", return_value=str(driver)):
            browser.load_bound_preflight(bound, self.root)
            with self.assertRaisesRegex(ValueError, "workspace"):
                browser.load_bound_preflight(bound, self.root / "other")
            record["checks"]["interaction"] = False
            with self.assertRaisesRegex(ValueError, "capability"):
                browser.validate_preflight(record, "playwright-cli", self.root)
            record["checks"]["interaction"] = True
            driver.write_text("new driver")
            with self.assertRaisesRegex(ValueError, "evidence changed"):
                browser.load_bound_preflight(bound, self.root)


if __name__ == "__main__":
    unittest.main()
