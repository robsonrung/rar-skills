#!/usr/bin/env python3
"""Offline guards for the 24 hour preflight result cache."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
import subprocess
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
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
        entry["result_sha256"] = preflight_cache.result_digest(entry["result"])
        data = {"schema_version": preflight_cache.SCHEMA_VERSION, "entries": {seat: entry}}
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

    def test_lookup_rejects_malformed_entry_identity(self):
        mutations = {
            "seat": "other-seat",
            "runner": "",
            "fingerprint": "",
            "ttl_seconds": 1,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                self.store()
                data = json.loads(self.cache.read_text())
                data["entries"]["glm"][field] = value
                self.cache.write_text(json.dumps(data), encoding="utf-8")
                entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
                self.assertIsNone(entry)
                self.assertIn("entry", reason)
        self.store()
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1", runner="claude")
        self.assertIsNone(entry)
        self.assertIn("runner mismatch", reason)

    def test_future_timestamp_is_a_miss(self):
        self.store(age=-3600)
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        self.assertIn("future", reason)

    def test_nonfinite_and_boolean_timestamps_are_misses(self):
        for timestamp in (True, float("nan"), float("inf"), -float("inf")):
            with self.subTest(timestamp=timestamp):
                self.store()
                data = json.loads(self.cache.read_text())
                data["entries"]["glm"]["checked_at_epoch"] = timestamp
                self.cache.write_text(json.dumps(data), encoding="utf-8")
                entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
                self.assertIsNone(entry)
                self.assertIn("timestamp", reason)

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

    def test_result_digest_detects_structurally_valid_corruption(self):
        self.store()
        data = json.loads(self.cache.read_text())
        data["entries"]["glm"]["result"] = {"available": False}
        self.cache.write_text(json.dumps(data), encoding="utf-8")
        entry, reason = preflight_cache.lookup(self.cache, "glm", "fp-1")
        self.assertIsNone(entry)
        self.assertIn("digest", reason)

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

    def test_upgrade_changes_fingerprint_and_invalidates_entry(self):
        with patch.object(preflight_cache, "resolve_cli", return_value="/mock/claude"), patch.object(preflight_cache.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "2.1.275", "")
            old = preflight_cache.compute_fingerprint("claude")
            self.store(fingerprint=old)
            run.return_value = subprocess.CompletedProcess([], 0, "2.1.280", "")
            upgraded = preflight_cache.compute_fingerprint("claude")
            self.assertNotEqual(old, upgraded)
            self.assertIsNone(preflight_cache.lookup(self.cache, "glm", upgraded)[0])
            self.assertTrue(all(call.args[0] == ["/mock/claude", "--version"] for call in run.call_args_list))

    def test_unparsed_successful_version_still_changes_generic_fingerprint(self):
        with patch.object(preflight_cache, "resolve_cli", return_value="/mock/claude"), \
             patch.object(preflight_cache.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "Claude Code build alpha", "")
            first = preflight_cache.compute_fingerprint("claude")
            snapshot = preflight_cache.fingerprint_snapshot("claude")
            run.return_value = subprocess.CompletedProcess([], 0, "Claude Code build beta", "")
            second = preflight_cache.compute_fingerprint("claude")
        self.assertNotEqual(first, second)
        self.assertFalse(snapshot["cacheable"])
        self.assertIsNone(snapshot["version_probe"]["version"])

    def test_context_and_policy_changes_invalidate(self):
        first = preflight_cache.compute_fingerprint("missing-cli", launch_context="restricted", policy_digest="one")
        second = preflight_cache.compute_fingerprint("missing-cli", launch_context="host", policy_digest="one")
        third = preflight_cache.compute_fingerprint("missing-cli", launch_context="restricted", policy_digest="two")
        self.assertEqual(len({first, second, third}), 3)

    def test_live_auth_receipts_and_entitlement_rejected(self):
        for result in ({"auth_ok": True}, {"checks": {"auth_visibility": {"status": "true"}}},
                       {"checks": {"is_authenticated": True}}, {"checks": {"request_policy": {"safe": True}}},
                       {"model_receipt": {"model": "example"}}, {"model_entitlement": True}):
            self.assertEqual(self.run_cli("set", "--seat", "test", "--runner", "test", "--fingerprint", "fp", "--result", json.dumps(result)), 2)
        self.assertFalse(self.cache.exists())

    def test_old_schema_and_missing_fingerprint_are_misses(self):
        self.store()
        self.assertIsNone(preflight_cache.lookup(self.cache, "glm", None)[0])
        data = json.loads(self.cache.read_text())
        data["schema_version"] = 1
        self.cache.write_text(json.dumps(data))
        self.assertIsNone(preflight_cache.lookup(self.cache, "glm", "fp-1")[0])

    def test_cli_file_change_invalidates_without_version_change(self):
        cli = Path(self.tmp.name) / "cli"
        cli.write_text("version one")
        with patch.object(preflight_cache, "resolve_cli", return_value=str(cli)), patch.object(preflight_cache.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "1.0.0", "")):
            before = preflight_cache.compute_fingerprint("cli")
            cli.write_text("different binary contents")
            after = preflight_cache.compute_fingerprint("cli")
        self.assertNotEqual(before, after)

    def test_model_routing_source_change_invalidates_cacheability_fingerprint(self):
        cli = Path(self.tmp.name) / "cli"
        helper = Path(self.tmp.name) / "model_routing_fixture.py"
        cli.write_text("version one")
        helper.write_text("routing revision one")
        with patch.object(preflight_cache, "MODEL_ROUTING_PATH", helper), \
             patch.object(preflight_cache, "resolve_cli", return_value=str(cli)), \
             patch.object(preflight_cache.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "1.0.0", "")):
            before = preflight_cache.fingerprint_snapshot("cli")
            self.assertTrue(before["cacheable"])
            self.store(fingerprint=before["fingerprint"])
            helper.write_text("routing revision two")
            after = preflight_cache.fingerprint_snapshot("cli")
        self.assertTrue(after["cacheable"])
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])
        self.assertIsNone(preflight_cache.lookup(self.cache, "glm", after["fingerprint"])[0])

    def test_relative_path_tracks_child_executable_when_version_is_unchanged(self):
        parent = Path(self.tmp.name)
        child = parent / "child"
        for directory in (parent, child):
            binary = directory / "bin" / "claude"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\nprintf '2.1.280\\n'\n")
            binary.chmod(0o755)
        original_cwd = Path.cwd()
        try:
            os.chdir(parent)
            for command in ("claude", "bin/claude"):
                with self.subTest(command=command):
                    before = preflight_cache.compute_fingerprint(command, working_dir="child", env={"PATH": "bin"})
                    self.store(fingerprint=before)
                    binary = child / "bin" / "claude"
                    binary.write_text(binary.read_text() + "# changed child executable\n")
                    after = preflight_cache.compute_fingerprint(command, working_dir="child", env={"PATH": "bin"})
                    self.assertNotEqual(before, after)
                    self.assertIsNone(preflight_cache.lookup(self.cache, "glm", after)[0])
            self.assertEqual((parent / "bin" / "claude").read_text(), "#!/bin/sh\nprintf '2.1.280\\n'\n")
        finally:
            os.chdir(original_cwd)

    def test_concurrent_stores_preserve_each_entry(self):
        original_write = preflight_cache.write_cache

        def delayed_write(path, data):
            time.sleep(0.01)
            original_write(path, data)

        def store(index):
            return preflight_cache.store(
                self.cache,
                f"seat-{index}",
                "runner",
                f"fingerprint-{index}",
                {"available": True},
            )

        with patch.object(preflight_cache, "write_cache", side_effect=delayed_write):
            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(store, range(8)))
        data = preflight_cache.read_cache(self.cache)
        self.assertEqual(set(data["entries"]), {f"seat-{index}" for index in range(8)})


if __name__ == "__main__":
    unittest.main(verbosity=2)
