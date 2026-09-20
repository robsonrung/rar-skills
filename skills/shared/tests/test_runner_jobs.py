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

    def test_batch_reads_each_job_once_without_processes(self):
        (self.job / "result.json").write_text('{"success": true, "session_id": "session"}')
        target = (str(self.root), "fixture")
        with patch.object(jobs.subprocess, "run", side_effect=AssertionError("no process")), \
             patch.object(jobs, "load_result", wraps=jobs.load_result) as read:
            result = jobs.observe_many([target, target])
        self.assertEqual(read.call_count, 1)
        self.assertEqual(result[target]["result"]["session_id"], "session")

    def test_cache_checks_content_even_when_size_and_mtime_match(self):
        path = self.job / "result.json"
        path.write_text('{"success": true, "session_id": "first"}')
        target = (str(self.root), "fixture")
        cache = {}
        first = jobs.observe_many([target], cache)[target]
        stamp = path.stat()
        path.write_text('{"success": true, "session_id": "other"}')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        second = jobs.observe_many([target], cache)[target]
        self.assertEqual(first["result"]["session_id"], "first")
        self.assertEqual(second["result"]["session_id"], "other")
        path.write_text("[]")
        self.assertEqual(jobs.observe_many([target], cache)[target]["status"], "failed")
        path.write_bytes(b"\xff")
        self.assertEqual(jobs.observe_many([target], cache)[target]["status"], "failed")
        path.unlink()
        self.assertEqual(jobs.observe_many([target], cache)[target]["status"], "running")

    def test_log_tail_bounds_reads_and_single_line_unicode_output(self):
        path = self.job / "run.log"
        path.write_text("界" * 1_000_000)
        manifest = {"pid": os.getpid(), "log_file": str(path)}
        with patch.object(Path, "read_text", side_effect=AssertionError("unbounded read")):
            payload = jobs.status_payload(self.job, manifest)
        self.assertLessEqual(len("\n".join(payload["log_tail"]).encode()), jobs.LOG_TAIL_BYTES)
        self.assertTrue(payload["log_tail_truncated"])
        path.write_text("one\n\ntwo\n")
        self.assertEqual(jobs.bounded_log_tail(manifest), (["one", "two"], False))

    def test_batch_terminal_failures(self):
        target = (str(self.root), "fixture")
        for content in ('{"success": false}', 'partial', '[]'):
            (self.job / "result.json").write_text(content)
            self.assertEqual(jobs.observe_many([target])[target]["status"], "failed")
        (self.job / "result.json").unlink()
        jobs.write_manifest(self.job, {"pid": -1})
        self.assertEqual(jobs.observe_many([target])[target]["status"], "died")
        jobs.write_manifest(self.job, {"pid": -1, "status": "cancelled"})
        self.assertEqual(jobs.observe_many([target])[target]["status"], "cancelled")
        for malformed in ({"pid": "bad"}, {"result_file": 42}, {"pid": None}):
            jobs.write_manifest(self.job, malformed)
            self.assertEqual(jobs.observe_many([target])[target]["status"], "failed")
        (self.job / "manifest.json").write_text("[]")
        self.assertEqual(jobs.observe_many([target])[target]["status"], "missing")

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
