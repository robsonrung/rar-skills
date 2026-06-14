#!/usr/bin/env python3
"""Unit tests for gemini-runner (run_gemini.py).

Run: python3 -m unittest discover -s gemini-runner/tests -p 'test_*.py'
  or python3 gemini-runner/tests/test_run_gemini.py
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

import run_gemini  # noqa: E402


class NormalizeEnvelopeTests(unittest.TestCase):
    def test_missing_cli_auth_ok_is_none_not_false(self):
        env = run_gemini.normalize_envelope(
            {"return_code": -2, "runner": "gemini", "effective_runner": None},
            requested_runner="gemini",
        )
        self.assertIsNone(env["auth_ok"], "missing CLI must be untested (None), not False")
        self.assertEqual(env["status"], "seat_unavailable")

    def test_success_auth_ok_true(self):
        env = run_gemini.normalize_envelope({"return_code": 0}, requested_runner="gemini")
        self.assertTrue(env["auth_ok"])

    def test_passthrough_error_auth_ok_none(self):
        env = run_gemini.normalize_envelope({"return_code": 1}, requested_runner="gemini")
        self.assertIsNone(env["auth_ok"])

    def test_effective_provider_never_null_for_gemini(self):
        env = run_gemini.normalize_envelope(
            {"return_code": -2, "effective_runner": None}, requested_runner="gemini"
        )
        self.assertEqual(env["effective_provider"], "google")

    def test_explicit_auth_false_is_preserved(self):
        env = run_gemini.normalize_envelope(
            {"return_code": 1, "auth_ok": False}, requested_runner="gemini"
        )
        self.assertFalse(env["auth_ok"])

    def test_idempotent(self):
        once = run_gemini.normalize_envelope({"return_code": -2}, requested_runner="gemini")
        twice = run_gemini.normalize_envelope(dict(once), requested_runner="gemini")
        self.assertEqual(once, twice)

    def test_required_keys_present_after_normalize(self):
        env = run_gemini.normalize_envelope({"return_code": -2}, requested_runner="gemini")
        self.assertEqual(run_gemini.validate_envelope(env), [])


class ResolveRestrictToolsTests(unittest.TestCase):
    def test_analysis_role_defaults_readonly(self):
        self.assertTrue(run_gemini.resolve_restrict_tools("codereviewer", False, False))

    def test_implementer_not_readonly(self):
        self.assertFalse(run_gemini.resolve_restrict_tools("implementer", False, False))

    def test_no_role_not_readonly(self):
        self.assertFalse(run_gemini.resolve_restrict_tools(None, False, False))

    def test_allow_write_overrides_default(self):
        self.assertFalse(run_gemini.resolve_restrict_tools("codereviewer", False, True))

    def test_explicit_restrict_wins_over_allow_write(self):
        self.assertTrue(run_gemini.resolve_restrict_tools("codereviewer", True, True))


class TimeoutTests(unittest.TestCase):
    def test_print_timeout_below_subprocess_timeout(self):
        agy_print, sub = run_gemini.compute_timeouts(480)
        self.assertLess(agy_print, sub)
        self.assertEqual(sub, 480)

    def test_tiny_timeout_stays_positive(self):
        agy_print, sub = run_gemini.compute_timeouts(1)
        self.assertGreaterEqual(agy_print, 1)
        self.assertEqual(sub, 1)


class JsonFenceTests(unittest.TestCase):
    def test_strip_fenced_json(self):
        cleaned, valid = run_gemini.strip_json_fences('```json\n{"a": 1}\n```')
        self.assertEqual(cleaned, '{"a": 1}')
        self.assertTrue(valid)

    def test_invalid_json_reported(self):
        cleaned, valid = run_gemini.strip_json_fences("not json at all")
        self.assertFalse(valid)


class WriteJsonOutputFileTests(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "nested", "out.json")
            payload = {"success": True, "value": 42}
            run_gemini.write_json_output_file(target, payload)
            self.assertEqual(json.loads(Path(target).read_text()), payload)

    def test_no_temp_file_left_on_replace_failure(self):
        with tempfile.TemporaryDirectory() as d:
            target = os.path.join(d, "out.json")
            with mock.patch("run_gemini.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    run_gemini.write_json_output_file(target, {"x": 1})
            leftovers = list(Path(d).iterdir())
            self.assertEqual(leftovers, [], f"temp file leaked: {leftovers}")


class RelativePathResolutionTests(unittest.TestCase):
    def test_relative_prompt_file_resolved_against_working_dir(self):
        # With agy "missing" and fallback disabled, a resolvable prompt file must
        # reach the -2 (seat unavailable) path, NOT the -3 (file not found) path.
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "p.md").write_text("hello", encoding="utf-8")
            with mock.patch("run_gemini.shutil.which", return_value=None):
                env = run_gemini.run_gemini(
                    prompt="",
                    working_dir=d,
                    prompt_files=["p.md"],
                    disable_fallback=True,
                )
            self.assertEqual(env["return_code"], -2, env.get("stderr"))

    def test_missing_relative_prompt_file_is_input_error(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch("run_gemini.shutil.which", return_value=None):
                env = run_gemini.run_gemini(
                    prompt="",
                    working_dir=d,
                    prompt_files=["does-not-exist.md"],
                    disable_fallback=True,
                )
            self.assertEqual(env["return_code"], -3)


class MissingCliEnvelopeTests(unittest.TestCase):
    def test_disable_fallback_reflects_requested_model(self):
        with mock.patch("run_gemini.shutil.which", return_value=None):
            env = run_gemini.run_gemini(
                prompt="hi", model="gemini-3-pro", disable_fallback=True
            )
        self.assertEqual(env["return_code"], -2)
        self.assertEqual(env["effective_model"], "gemini-3-pro")
        self.assertIsNone(env["auth_ok"])
        self.assertEqual(env["effective_provider"], "google")
        self.assertEqual(run_gemini.validate_envelope(env), [])


class FallbackSelectionTests(unittest.TestCase):
    def test_skips_unavailable_to_first_success(self):
        calls = []

        def fake_invoke(script, *args, **kwargs):
            name = Path(script).name
            calls.append(name)
            if name == "run_qwen.py":
                return {"success": False, "return_code": -2, "status": "seat_unavailable",
                        "stderr": "qwen missing"}
            if name == "run_kimi.py":
                return {"success": True, "return_code": 0, "runner": "kimi",
                        "effective_runner": "kimi", "agent_message": "answer"}
            return {"success": True, "return_code": 0}

        with mock.patch("run_gemini.shutil.which", return_value=None), \
             mock.patch("run_gemini.Path.is_file", return_value=True), \
             mock.patch("run_gemini.invoke_fallback", side_effect=fake_invoke):
            env = run_gemini.run_gemini(prompt="hi", disable_fallback=False)

        self.assertTrue(env["success"])
        self.assertEqual(env["fallback_from"], "gemini")
        self.assertEqual(env["effective_runner"], "kimi")
        self.assertEqual(env["runner"], "gemini")
        # qwen was tried and skipped before kimi succeeded.
        self.assertIn("run_qwen.py", calls)
        self.assertTrue(any(a.get("status") == "seat_unavailable"
                            for a in env.get("fallback_attempts", [])))

    def test_does_not_select_failed_fallback_as_success(self):
        def fake_invoke(script, *args, **kwargs):
            name = Path(script).name
            if name == "run_qwen.py":
                # A real failure (e.g. auth), not "unavailable".
                return {"success": False, "return_code": 1, "status": "auth_failed",
                        "stderr": "auth failed"}
            return {"success": False, "return_code": -2, "status": "seat_unavailable"}

        with mock.patch("run_gemini.shutil.which", return_value=None), \
             mock.patch("run_gemini.Path.is_file", return_value=True), \
             mock.patch("run_gemini.invoke_fallback", side_effect=fake_invoke):
            env = run_gemini.run_gemini(prompt="hi", disable_fallback=False)

        # No fallback truly succeeded → must not report success.
        self.assertFalse(env["success"])
        # The informative failure is surfaced rather than a bare unavailable.
        self.assertEqual(env["status"], "auth_failed")
        self.assertEqual(env["fallback_from"], "gemini")


class AuthDetectionTests(unittest.TestCase):
    def test_auth_failure_on_exit_zero_forces_failure(self):
        completed = mock.Mock(stdout="here is the answer", stderr="Authentication required", returncode=0)
        with mock.patch("run_gemini.shutil.which", return_value="/usr/bin/agy"), \
             mock.patch("run_gemini.subprocess.run", return_value=completed):
            env = run_gemini.run_gemini(prompt="hi")
        self.assertFalse(env["success"])
        self.assertFalse(env["auth_ok"])
        self.assertEqual(env["status"], "auth_failed")
        self.assertNotEqual(env["return_code"], 0)

    def test_answer_mentioning_auth_on_success_is_not_flagged(self):
        # The model's answer (stdout) mentions "not authenticated" but the run
        # succeeded (exit 0, nothing on stderr) — must NOT be treated as failure.
        completed = mock.Mock(
            stdout="The error 'not authenticated' means the token expired.",
            stderr="",
            returncode=0,
        )
        with mock.patch("run_gemini.shutil.which", return_value="/usr/bin/agy"), \
             mock.patch("run_gemini.subprocess.run", return_value=completed):
            env = run_gemini.run_gemini(prompt="explain the auth error")
        self.assertTrue(env["success"])
        self.assertTrue(env["auth_ok"])

    def test_json_output_fence_stripped(self):
        completed = mock.Mock(stdout='```json\n{"ok": true}\n```', stderr="", returncode=0)
        with mock.patch("run_gemini.shutil.which", return_value="/usr/bin/agy"), \
             mock.patch("run_gemini.subprocess.run", return_value=completed):
            env = run_gemini.run_gemini(prompt="hi", output_format="json")
        self.assertEqual(env["agent_message"], '{"ok": true}')
        self.assertTrue(env["output_json_valid"])


class CliArgumentTests(unittest.TestCase):
    SCRIPT = str(SCRIPTS_DIR / "run_gemini.py")

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, text=True, timeout=30,
        )

    def test_prompt_and_prompt_file_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md") as f:
            r = self._run("hello", "--prompt-file", f.name)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not both", r.stderr)

    def test_invalid_metadata_json_rejected(self):
        r = self._run("hello", "--metadata-json", "{not valid")
        self.assertEqual(r.returncode, 2)
        self.assertIn("valid JSON", r.stderr)

    def test_no_prompt_rejected(self):
        r = self._run()
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
