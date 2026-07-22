#!/usr/bin/env python3
"""Cross-runner parity tests for the four wrapper scripts (claude, codex,
gemini, cline).

Locks in the family-wide contract so the per-script copies cannot drift:

1. Missing-CLI runs emit a fully normalized envelope on stdout (--json) with
   the required keys, return_code -2, status seat_unavailable, and
   auth_ok null (untested — never false for a missing binary).
2. --json + --output-file prints the compact pointer including the seat
   identity keys (runner, effective_runner, effective_provider, status), and
   writes the full envelope to the file.
3. Relative --prompt-file paths resolve against --working-dir (not the
   process cwd): an existing file under the working dir reaches the -2
   missing-CLI path, a missing one is a -3 input error.

All tests run offline: PATH is stripped so no real CLI is ever found, and
--disable-fallback keeps the claude/codex/gemini chains from routing.

Run: python3 _shared/tests/test_runner_parity.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

RUNNER_SCRIPTS = {
    "claude": REPO_ROOT / "claude-runner" / "scripts" / "run_claude.py",
    "codex": REPO_ROOT / "codex-runner" / "scripts" / "run_codex.py",
    "gemini": REPO_ROOT / "gemini-runner" / "scripts" / "run_gemini.py",
    "cline": REPO_ROOT / "cline-runner" / "scripts" / "run_cline.py",
}

REQUIRED_KEYS = (
    "runner",
    "effective_runner",
    "effective_model",
    "effective_provider",
    "auth_ok",
    "fallback_reason",
    "success",
    "return_code",
)

POINTER_KEYS = (
    "success",
    "return_code",
    "output_file",
    "runner",
    "effective_runner",
    "effective_provider",
    "fallback_from",
    "status",
)


def run_script(script: Path, *args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Strip PATH so shutil.which() finds no native CLI; the scripts themselves
    # are launched via sys.executable, which does not consult PATH.
    with tempfile.TemporaryDirectory() as empty:
        env["PATH"] = empty
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd,
            env=env,
        )


class MissingCliEnvelopeParityTests(unittest.TestCase):
    def test_missing_cli_emits_normalized_envelope(self):
        for name, script in RUNNER_SCRIPTS.items():
            with self.subTest(runner=name):
                proc = run_script(script, "hi", "--json", "--disable-fallback", "--timeout", "5")
                self.assertNotEqual(proc.returncode, 0, f"{name}: missing CLI must exit nonzero")
                env = json.loads(proc.stdout)
                missing = [k for k in REQUIRED_KEYS if k not in env]
                self.assertEqual(missing, [], f"{name}: required envelope keys missing: {missing}")
                self.assertFalse(env["success"])
                self.assertEqual(env["return_code"], -2, f"{name}: {env.get('stderr')}")
                self.assertEqual(env["status"], "seat_unavailable")
                self.assertIsNone(
                    env["auth_ok"],
                    f"{name}: a missing CLI is untested auth (null), never false",
                )
                self.assertEqual(env["runner"], name)


class OutputFilePointerParityTests(unittest.TestCase):
    def test_pointer_contains_seat_identity(self):
        for name, script in RUNNER_SCRIPTS.items():
            with self.subTest(runner=name), tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, "out.json")
                proc = run_script(
                    script, "hi", "--json", "--disable-fallback",
                    "--timeout", "5", "--output-file", out,
                )
                pointer = json.loads(proc.stdout)
                missing = [k for k in POINTER_KEYS if k not in pointer]
                self.assertEqual(missing, [], f"{name}: pointer keys missing: {missing}")
                self.assertEqual(pointer["runner"], name)
                self.assertEqual(pointer["status"], "seat_unavailable")
                full = json.loads(Path(out).read_text(encoding="utf-8"))
                self.assertEqual([k for k in REQUIRED_KEYS if k not in full], [],
                                 f"{name}: output file missing required keys")


class WorkingDirPathResolutionParityTests(unittest.TestCase):
    def test_relative_prompt_file_resolves_against_working_dir(self):
        for name, script in RUNNER_SCRIPTS.items():
            with self.subTest(runner=name), tempfile.TemporaryDirectory() as d:
                (Path(d) / "p.md").write_text("hello", encoding="utf-8")
                # Run from a different cwd than --working-dir to prove the
                # resolution target. Resolvable file -> the run proceeds to the
                # missing-CLI (-2) path, not a -3 file-not-found input error.
                with tempfile.TemporaryDirectory() as other_cwd:
                    proc = run_script(
                        script, "--json", "--disable-fallback", "--timeout", "5",
                        "--working-dir", d, "--prompt-file", "p.md",
                        cwd=other_cwd,
                    )
                env = json.loads(proc.stdout)
                self.assertEqual(env["return_code"], -2,
                                 f"{name}: relative prompt file was not resolved "
                                 f"against --working-dir: {env.get('stderr')}")

    def test_missing_relative_prompt_file_is_input_error(self):
        for name, script in RUNNER_SCRIPTS.items():
            with self.subTest(runner=name), tempfile.TemporaryDirectory() as d:
                proc = run_script(
                    script, "--json", "--disable-fallback", "--timeout", "5",
                    "--working-dir", d, "--prompt-file", "does-not-exist.md",
                )
                env = json.loads(proc.stdout)
                self.assertEqual(env["return_code"], -3, f"{name}: {env.get('stderr')}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
