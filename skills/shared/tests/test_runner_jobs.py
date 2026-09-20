#!/usr/bin/env python3
"""Exercise bounded waits against disposable job records."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import runner_jobs as jobs


class WaitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = jobs.jobs_root(str(self.root)) / "fixture"
        self.job.mkdir(parents=True)
        jobs.write_manifest(self.job, {"pid": os.getpid(), "job_id": "fixture"})
        self.targets = [{"working_dir": str(self.root), "job_id": "fixture"}]

    def test_timeout_is_observation_only_and_returns_cursor(self):
        result = jobs.wait_many(self.targets, timeout=0)
        self.assertEqual(result["reason"], "timeout")
        self.assertEqual(result["targets"][0]["status"], "running")
        self.assertFalse((self.job / "result.json").exists())
        again = jobs.wait_many(self.targets, result["cursor"], timeout=0)
        self.assertEqual(again["changed"], [])

    def test_wait_returns_new_completion_without_replaying_prior_results(self):
        cursor = jobs.wait_many(self.targets, timeout=0)["cursor"]
        def finish(_):
            (self.job / "result.json").write_text('{"success": true}')
        with patch.object(jobs.time, "sleep", side_effect=finish):
            result = jobs.wait_many(self.targets, cursor, timeout=1)
        self.assertEqual(result["changed"][0]["status"], "completed")
        self.assertEqual(jobs.wait_many(self.targets, result["cursor"], timeout=0)["changed"], [])

    def test_missing_failed_and_dead_jobs_are_terminal(self):
        (self.job / "result.json").write_text('{"success": false}')
        self.assertEqual(jobs.wait_many(self.targets, timeout=0)["targets"][0]["status"], "failed")
        (self.job / "result.json").unlink()
        jobs.write_manifest(self.job, {"pid": -1})
        self.assertEqual(jobs.wait_many(self.targets, timeout=0)["targets"][0]["status"], "died")
        (self.job / "manifest.json").unlink()
        self.assertEqual(jobs.wait_many(self.targets, timeout=0)["targets"][0]["status"], "missing")

    def test_invalid_targets_cursors_and_limits_fail(self):
        for targets in ([], self.targets * 2, *[[{"working_dir": str(self.root), "job_id": value}] for value in ("../outside", "..", ".", None)]):
            with self.assertRaises(ValueError):
                jobs.wait_many(targets, timeout=0)
        with self.assertRaises(ValueError):
            jobs.wait_many(self.targets, {"different": "cursor"}, timeout=0)
        with self.assertRaises(ValueError):
            jobs.wait_many(self.targets, timeout=61)


if __name__ == "__main__":
    unittest.main()
