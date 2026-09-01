#!/usr/bin/env python3
"""Offline contract tests for schema-bearing Cline and Grok runner results."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

from output_contract import validate_output_contract, validate_value  # noqa: E402

OPENING_SCHEMA = REPO_ROOT / "models-consensus" / "schemas" / "opening-answer.schema.json"


def opening_answer() -> dict:
    return {
        "answer": "Use a local receipt.",
        "key_points": ["One final JSON value is required."],
        "assumptions": [],
        "confidence": 90,
    }


def run_runner(name: str, text: str) -> tuple[subprocess.CompletedProcess, dict]:
    script = REPO_ROOT / f"{name}-runner" / "scripts" / f"run_{name}.py"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        command = bin_dir / name
        command.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = \"history\" ]; then printf '[]'; "
            "else printf '%s\\n' \"$RUNNER_FAKE_OUTPUT\"; fi\n",
            encoding="utf-8",
        )
        command.chmod(0o755)
        if name == "cline":
            native = {
                "type": "run_result",
                "text": text,
                "finishReason": "completed",
                "model": {"id": "moonshotai/kimi-k3", "provider": "moonshotai"},
            }
        else:
            native = {
                "text": text,
                "sessionId": "test-session",
                "modelUsage": {"grok-test": {}},
            }
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
        env["RUNNER_FAKE_OUTPUT"] = json.dumps(native)
        proc = subprocess.run(
            [sys.executable, str(script), "answer", "--json", "--output-schema", str(OPENING_SCHEMA)],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            env=env,
            check=False,
        )
        return proc, json.loads(proc.stdout)


class OutputContractUnitTests(unittest.TestCase):
    def test_accepts_one_json_value_or_a_single_json_fence(self):
        direct = validate_output_contract(json.dumps(opening_answer()), OPENING_SCHEMA)
        fenced = validate_output_contract(f"```json\n{json.dumps(opening_answer())}\n```", OPENING_SCHEMA)
        self.assertTrue(direct.valid)
        self.assertTrue(fenced.valid)

    def test_rejects_json_concatenation_and_schema_mismatch(self):
        concatenated = json.dumps(opening_answer()) + json.dumps(opening_answer())
        result = validate_output_contract(concatenated, OPENING_SCHEMA)
        self.assertFalse(result.valid)
        self.assertEqual(result.error_kind, "invalid_json")
        malformed = dict(opening_answer(), extra="not allowed")
        result = validate_output_contract(json.dumps(malformed), OPENING_SCHEMA)
        self.assertFalse(result.valid)
        self.assertEqual(result.error_kind, "schema_invalid")

    def test_all_bundled_consensus_schemas_use_the_supported_subset(self):
        for schema in (REPO_ROOT / "models-consensus" / "schemas").glob("*.json"):
            with self.subTest(schema=schema.name):
                result = validate_value({}, schema)
                self.assertNotIn("unsupported schema keyword", result.error or "")


class RunnerOutputContractTests(unittest.TestCase):
    def test_cline_and_grok_accept_only_schema_valid_final_answers(self):
        valid = json.dumps(opening_answer())
        for name in ("cline", "grok"):
            with self.subTest(runner=name, case="valid"):
                proc, envelope = run_runner(name, valid)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertTrue(envelope["success"])
                self.assertTrue(envelope["output_json_valid"])
                self.assertTrue(envelope["schema_valid"])
                self.assertEqual(json.loads(envelope["agent_message"]), opening_answer())

            with self.subTest(runner=name, case="concatenated"):
                proc, envelope = run_runner(name, valid + valid)
                self.assertNotEqual(proc.returncode, 0)
                self.assertFalse(envelope["success"])
                self.assertEqual(envelope["return_code"], -3)
                self.assertEqual(envelope["status"], "malformed_output")
                self.assertTrue(envelope["auth_ok"])
                self.assertFalse(envelope["output_json_valid"])
                self.assertFalse(envelope["schema_valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
