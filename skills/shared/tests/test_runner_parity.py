#!/usr/bin/env python3
"""Cross-runner parity tests for the wrapper scripts (claude, codex, gemini,
grok, pi) and the named seats they serve (pi: kimi, glm, qwen, gemma, muse,
minimax, mistral-small) via `--seat`.

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
4. Codex-family aliases resolve before launch, including Luna, and runner
   discovery recognizes every rostered Codex-family seat without calling a
   provider.

All tests run offline: PATH is stripped so no real CLI is ever found, and
--disable-fallback keeps the claude/codex/gemini chains from routing.

Run: python3 shared/tests/test_runner_parity.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
from skill_paths import skill_dir, runner_script  # noqa: E402


def P(rel: str):
    """Resolve "<skill>/<path>" by skill name in either layout."""
    name, _, rest = rel.partition("/")
    return skill_dir(name, root=REPO_ROOT) / rest if rest else skill_dir(name, root=REPO_ROOT)

_PI = runner_script("pi", root=REPO_ROOT)
DISCOVER_RUNNERS = REPO_ROOT / "shared" / "scripts" / "discover_runners.py"

# runner label -> (script, extra args that select the seat)
RUNNER_SCRIPTS = {
    "claude": (runner_script("claude", root=REPO_ROOT), ()),
    "codex": (runner_script("codex", root=REPO_ROOT), ()),
    "gemini": (runner_script("gemini", root=REPO_ROOT), ()),
    "grok": (runner_script("grok", root=REPO_ROOT), ()),
    "pi": (_PI, ()),
    "kimi": (_PI, ("--seat", "kimi")),
    "glm": (_PI, ("--seat", "glm")),
    "qwen": (_PI, ("--seat", "qwen")),
    "gemma": (_PI, ("--seat", "gemma")),
    "muse": (_PI, ("--seat", "muse")),
    "minimax": (_PI, ("--seat", "minimax")),
    "mistral-small": (_PI, ("--seat", "mistral-small")),
}

REQUIRED_KEYS = (
    "runner",
    "effective_runner",
    "effective_model",
    "requested_model",
    "configured_model",
    "model_receipt",
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


def run_script(
    script: Path | tuple[Path, tuple[str, ...]], *args: str, cwd: str | None = None
) -> subprocess.CompletedProcess:
    seat_args: tuple[str, ...] = ()
    if isinstance(script, tuple):
        script, seat_args = script
    args = (*seat_args, *args)
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
            check=False,
        )


def run_discovery(*args: str) -> subprocess.CompletedProcess:
    """Run discovery without finding or invoking a real local CLI."""
    env = os.environ.copy()
    with tempfile.TemporaryDirectory() as empty:
        env["PATH"] = empty
        return subprocess.run(
            [sys.executable, str(DISCOVER_RUNNERS), "probe", *args],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            check=False,
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
                self.assertEqual(env["model_receipt"]["status"], "unverified")
                self.assertIsNone(
                    env["effective_model"],
                    f"{name}: a requested or configured model must not be called served",
                )
                if name == "qwen":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "qwen/qwen3.8-max")
                    self.assertEqual(env["effective_provider"], "qwen")
                    self.assertIn("Pi CLI not found", env["stderr"])
                if name == "kimi":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "moonshotai/kimi-k3")
                    self.assertEqual(env["effective_provider"], "moonshotai")
                    self.assertIn("Pi CLI not found", env["stderr"])
                if name == "glm":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "z-ai/glm-5.3-flash")
                    self.assertEqual(env["effective_provider"], "z-ai")
                    self.assertIn("Pi CLI not found", env["stderr"])
                if name == "gemma":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "google/gemma-4-31b-it")
                    self.assertEqual(env["effective_provider"], "google")
                if name == "muse":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "meta/muse-spark-1.3")
                    self.assertEqual(env["effective_provider"], "meta")
                if name == "minimax":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "minimax/minimax-m2.7")
                    self.assertEqual(env["effective_provider"], "minimax")
                if name == "mistral-small":
                    self.assertEqual(env["effective_runner"], "pi")
                    self.assertEqual(env["configured_model"], "mistralai/mistral-small-3.2")
                    self.assertEqual(env["effective_provider"], "mistralai")


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


class CodexFamilyAliasAndDiscoveryTests(unittest.TestCase):
    def test_codex_family_aliases_resolve_before_cli_availability(self):
        expected_models = {
            "astra": "gpt-6-astra",
            "sol": "gpt-6-sol",
            "terra": "gpt-6-terra",
            "luna": "gpt-6-luna",
        }
        codex = RUNNER_SCRIPTS["codex"]
        for alias, model in expected_models.items():
            with self.subTest(alias=alias):
                proc = run_script(
                    codex,
                    "hi",
                    "--model",
                    alias,
                    "--json",
                    "--disable-fallback",
                    "--timeout",
                    "5",
                )
                env = json.loads(proc.stdout)
                self.assertEqual(env["return_code"], -2, env.get("stderr"))
                self.assertEqual(env["configured_model"], model)
                self.assertIsNone(env["effective_model"])

    def test_discovery_lists_all_codex_family_seats(self):
        proc = run_discovery(
            "--seat",
            "astra",
            "--seat",
            "sol",
            "--seat",
            "terra",
            "--seat",
            "luna",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        seats = {seat["seat"]: seat for seat in payload["seats"]}
        self.assertEqual(set(seats), {"astra", "sol", "terra", "luna"})
        for name in seats:
            with self.subTest(seat=name):
                self.assertEqual(seats[name]["execution_path"], "codex_runner")
                self.assertFalse(seats[name]["available"])
                self.assertIn("not found on PATH", seats[name]["blocked_reason"])

    def test_native_claude_transport_includes_fable_without_model_claim(self):
        proc = run_discovery("--native-agent", "yes", "--seat", "fable")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(len(payload["seats"]), 1)
        seat = payload["seats"][0]
        self.assertEqual(seat["seat"], "fable")
        self.assertTrue(seat["available"])
        self.assertEqual(seat["execution_path"], "agent_native")
        self.assertIn("exact model and effort remain unchecked", seat["notes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
