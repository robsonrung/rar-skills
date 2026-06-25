#!/usr/bin/env python3
"""Unit tests for dcode-runner (run_dcode.py).

Run: python3 -m unittest discover -s dcode-runner/tests -p 'test_*.py'
  or python3 dcode-runner/tests/test_run_dcode.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import run_dcode  # noqa: E402


class NormalizeEnvelopeTests(unittest.TestCase):
    def test_missing_cli_auth_ok_is_none_not_false(self):
        env = run_dcode.normalize_envelope(
            {"return_code": -2, "runner": "dcode", "effective_runner": None},
            requested_runner="dcode",
        )
        self.assertIsNone(env["auth_ok"], "missing CLI must be untested (None), not False")
        self.assertEqual(env["status"], "seat_unavailable")

    def test_success_auth_ok_true(self):
        env = run_dcode.normalize_envelope({"return_code": 0}, requested_runner="dcode")
        self.assertTrue(env["auth_ok"])

    def test_passthrough_error_auth_ok_none(self):
        env = run_dcode.normalize_envelope({"return_code": 1}, requested_runner="dcode")
        self.assertIsNone(env["auth_ok"])

    def test_effective_provider_never_null_for_dcode(self):
        env = run_dcode.normalize_envelope(
            {"return_code": -2, "effective_runner": None}, requested_runner="dcode"
        )
        self.assertEqual(env["effective_provider"], "deepagents")

    def test_explicit_auth_false_is_preserved(self):
        env = run_dcode.normalize_envelope(
            {"return_code": 1, "auth_ok": False}, requested_runner="dcode"
        )
        self.assertFalse(env["auth_ok"])

    def test_idempotent(self):
        once = run_dcode.normalize_envelope({"return_code": -2}, requested_runner="dcode")
        twice = run_dcode.normalize_envelope(dict(once), requested_runner="dcode")
        self.assertEqual(once, twice)

    def test_required_keys_present_after_normalize(self):
        env = run_dcode.normalize_envelope({"return_code": -2}, requested_runner="dcode")
        self.assertEqual(run_dcode.validate_envelope(env), [])


class ResolveRestrictToolsTests(unittest.TestCase):
    def test_explicit_restrict_wins(self):
        self.assertTrue(run_dcode.resolve_restrict_tools("implementer", True, True))

    def test_allow_write_opts_out(self):
        self.assertFalse(run_dcode.resolve_restrict_tools("codereviewer", False, True))

    def test_analysis_role_defaults_to_restricted(self):
        self.assertTrue(run_dcode.resolve_restrict_tools("codereviewer", False, False))

    def test_implementer_defaults_open(self):
        self.assertFalse(run_dcode.resolve_restrict_tools("implementer", False, False))

    def test_no_role_defaults_open(self):
        self.assertFalse(run_dcode.resolve_restrict_tools(None, False, False))


class ComputeTimeoutsTests(unittest.TestCase):
    def test_inner_timeout_is_below_outer(self):
        inner, outer = run_dcode.compute_timeouts(3600)
        self.assertLess(inner, outer)
        self.assertEqual(outer, 3600)

    def test_minimum_one_second(self):
        inner, outer = run_dcode.compute_timeouts(1)
        self.assertGreaterEqual(inner, 1)
        self.assertGreaterEqual(outer, 1)


class StripJsonFencesTests(unittest.TestCase):
    def test_strips_json_fence_and_validates(self):
        cleaned, ok = run_dcode.strip_json_fences('```json\n{"a": 1}\n```')
        self.assertEqual(cleaned, '{"a": 1}')
        self.assertTrue(ok)

    def test_unfenced_json_validates(self):
        cleaned, ok = run_dcode.strip_json_fences('{"b": 2}')
        self.assertTrue(ok)
        self.assertEqual(cleaned, '{"b": 2}')

    def test_non_json_reports_invalid(self):
        cleaned, ok = run_dcode.strip_json_fences("not json at all")
        self.assertFalse(ok)


class MissingCliBehaviorTests(unittest.TestCase):
    def test_missing_dcode_with_disable_fallback_returns_seat_unavailable(self):
        with mock.patch("run_dcode.shutil.which", return_value=None):
            env = run_dcode.run_dcode(
                "hi", timeout=5, disable_fallback=True
            )
        self.assertFalse(env["success"])
        self.assertEqual(env["return_code"], -2)
        self.assertEqual(env["status"], "seat_unavailable")
        self.assertIsNone(env["auth_ok"])
        self.assertEqual(env["runner"], "dcode")
        # normalize_envelope coerces a None effective_runner back to the
        # requested runner so the field is never null in the contract.
        self.assertEqual(env["effective_runner"], "dcode")
        self.assertEqual(env["effective_provider"], "deepagents")


class CommandShapeTests(unittest.TestCase):
    """Confirm the wrapper does NOT forward --model to dcode and DOES use -n -q --no-stream."""

    def _captured_cmd(self, **kwargs):
        captured = {}

        class FakeCompleted:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd, **_):
            captured["cmd"] = cmd
            return FakeCompleted()

        with mock.patch("run_dcode.shutil.which", return_value="/usr/bin/dcode"), \
                mock.patch("run_dcode.subprocess.run", side_effect=fake_run):
            run_dcode.run_dcode("hello", timeout=10, disable_fallback=True, **kwargs)
        return captured["cmd"]

    def test_basic_command_uses_non_interactive_quiet_no_stream(self):
        cmd = self._captured_cmd()
        self.assertIn("-n", cmd)
        self.assertIn("-q", cmd)
        self.assertIn("--no-stream", cmd)
        self.assertIn("--timeout", cmd)

    def test_model_is_not_forwarded(self):
        cmd = self._captured_cmd(model="anthropic:claude-opus-4-8")
        self.assertNotIn("--model", cmd)
        self.assertNotIn("-M", cmd)
        self.assertNotIn("anthropic:claude-opus-4-8", cmd)

    def test_auto_approve_forwards_dash_y(self):
        cmd = self._captured_cmd(auto_approve=True)
        self.assertIn("-y", cmd)

    def test_auto_approve_off_does_not_forward_dash_y(self):
        cmd = self._captured_cmd()
        self.assertNotIn("-y", cmd)

    def test_max_turns_forwards(self):
        cmd = self._captured_cmd(max_turns=8)
        self.assertIn("--max-turns", cmd)
        self.assertIn("8", cmd)

    def test_resume_session_forwards_id(self):
        cmd = self._captured_cmd(resume_session="abc-123")
        self.assertIn("-r", cmd)
        self.assertIn("abc-123", cmd)

    def test_continue_forwards_r_without_id(self):
        cmd = self._captured_cmd(dcode_continue=True)
        # `-r` is present and is NOT followed by a session id (we never supplied
        # one); dcode treats a bare `-r` as "resume most recent".
        self.assertIn("-r", cmd)
        r_index = cmd.index("-r")
        # Either `-r` is the last argv element, or the next element starts with
        # `-` (another flag), never a session id.
        if r_index + 1 < len(cmd):
            self.assertTrue(cmd[r_index + 1].startswith("-"))


if __name__ == "__main__":
    unittest.main()
