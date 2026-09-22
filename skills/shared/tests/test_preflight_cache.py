#!/usr/bin/env python3
"""Offline guards for the 24 hour preflight result cache."""

from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
import preflight_cache


class PreflightCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / "preflight-cache.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        return preflight_cache.main(["--cache", str(self.cache), *argv])

    def store(self, seat="glm", fingerprint="fp-1", age=0):
        entry = {
            "seat": seat,
            "runner": "pi",
            "fingerprint": fingerprint,
            "checked_at": "2026-09-22T12:00:00+00:00",
            "checked_at_epoch": time.time() - age,
            "ttl_seconds": preflight_cache.TTL_SECONDS,
            "result": {"available": True},
        }
        data = {"schema_version": 1, "entries": {seat: entry}}
        self.cache.write_text(json.dumps(data), encoding="utf-8")
        return entry

    def test_set_then_get_roundtrip(self):
        self.assertEqual(
            self.run_cli("set", "--seat", "glm", "--runner", "pi",
                         "--fingerprint", "fp-1", "--result", '{"available": true}'),
            0,
        )
        self.assertEqual(self.run_cli("get", "--seat", "glm", "--fingerprint", "fp-1"), 0)
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNotNone(entry, reason)
        self.assertEqual(entry["result"], {"available": True})
        self.assertEqual(entry["ttl_seconds"], 24 * 60 * 60)

    def test_missing_entry_is_a_miss(self):
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        self.assertIn("no cached entry", reason)
        self.assertEqual(self.run_cli("get", "--seat", "glm"), 1)

    def test_expired_entry_is_a_miss(self):
        self.store(age=preflight_cache.TTL_SECONDS + 60)
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        self.assertIn("expired", reason)

    def test_fresh_entry_just_inside_ttl(self):
        self.store(age=preflight_cache.TTL_SECONDS - 60)
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNotNone(entry, reason)

    def test_fingerprint_mismatch_is_a_miss(self):
        self.store(fingerprint="fp-1")
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-2")
        self.assertIsNone(entry)
        self.assertIn("fingerprint mismatch", reason)

    def test_future_timestamp_is_a_miss(self):
        self.store(age=-3600)
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        self.assertIn("future", reason)

    def test_corrupt_file_is_a_miss_and_set_recovers(self):
        self.cache.write_text("{not json", encoding="utf-8")
        entry, reason = preflight_cache.lookup(self.cache, "glm", None)
        self.assertIsNone(entry)
        self.assertIn("corrupt", reason)
        self.assertEqual(
            self.run_cli("set", "--seat", "glm", "--runner", "pi",
                         "--fingerprint", "fp-1", "--result", '{"available": true}'),
            0,
        )
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNotNone(entry, reason)

    def test_clear_one_seat_and_all(self):
        self.store(seat="glm")
        self.store(seat="grok")
        self.assertEqual(self.run_cli("clear", "--seat", "glm"), 0)
        entry, _ = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        entry, reason = preflight_cache.lookup(self.cache, "grok", "fp-1")
        self.assertIsNotNone(entry, reason)
        self.assertEqual(self.run_cli("clear"), 0)
        self.assertFalse(self.cache.exists())

    def test_status_lists_freshness(self):
        self.store(seat="glm")
        self.store(seat="grok", age=preflight_cache.TTL_SECONDS + 60)
        self.assertEqual(self.run_cli("status"), 0)

    def test_set_rejects_non_object_result(self):
        self.assertEqual(
            self.run_cli("set", "--seat", "glm", "--runner", "pi",
                         "--fingerprint", "fp-1", "--result", '[1, 2]'),
            2,
        )

    def test_fingerprint_changes_with_config_digest(self):
        first = preflight_cache.compute_fingerprint("definitely-missing-cli", "digest-a")
        second = preflight_cache.compute_fingerprint("definitely-missing-cli", "digest-b")
        self.assertNotEqual(first, second)
        self.assertEqual(first, preflight_cache.compute_fingerprint("definitely-missing-cli", "digest-a"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
