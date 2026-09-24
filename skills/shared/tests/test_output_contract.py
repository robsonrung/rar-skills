#!/usr/bin/env python3
"""Offline contract tests for schema-bearing Pi and Grok runner results."""

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

from output_contract import validate_output_contract, validate_value, validate_schema, validate_document  # noqa: E402

OPENING_SCHEMA = skill_dir("models-consensus", root=REPO_ROOT) / "schemas" / "opening-answer.schema.json"


def opening_answer() -> dict:
    return {
        "answer": "Use a local receipt.",
        "key_points": ["One final JSON value is required."],
        "assumptions": [],
        "confidence": 90,
    }


def run_runner(name: str, text: str) -> tuple[subprocess.CompletedProcess, dict]:
    script = runner_script(name, root=REPO_ROOT)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        command = bin_dir / name
        if name == "pi":
            # Fake the Pi CLI: emit one native --mode json message_end event.
            native = json.dumps({
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                    "model": "moonshotai/kimi-k3",
                    "provider": "openrouter",
                    "stopReason": "stop",
                    "usage": {"input": 1, "output": 1},
                },
            })
            command.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' {json.dumps(native)}\n",
                encoding="utf-8",
            )
        else:
            command.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"history\" ]; then printf '[]'; "
                "else printf '%s\\n' \"$RUNNER_FAKE_OUTPUT\"; fi\n",
                encoding="utf-8",
            )
            native = json.dumps({
                "text": text,
                "sessionId": "test-session",
                "modelUsage": {"grok-test": {}},
            })
            command.chmod(0o755)
        command.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
        env["RUNNER_FAKE_OUTPUT"] = native
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

    def test_prose_fence_is_opt_in_and_ambiguous_values_are_rejected(self):
        value = json.dumps(opening_answer())
        message = "Result follows.\n```json\n" + value + "\n```\nEnd."
        self.assertFalse(validate_output_contract(message, OPENING_SCHEMA).valid)
        self.assertTrue(validate_output_contract(message, OPENING_SCHEMA, allow_prose_fence=True).valid)
        for invalid in (message + " {}", "[] " + message, message + " true", message + " 12", message + ' "other"',
                        message + " ```json\n{}\n```", "```json\n" + value + " {}\n```", "Result: " + value):
            with self.subTest(message=invalid):
                self.assertFalse(validate_output_contract(invalid, OPENING_SCHEMA, allow_prose_fence=True).valid)

    def test_duplicate_keys_invalid_constants_and_overflow_fail(self):
        value = json.dumps(opening_answer())
        invalid = [value.replace('"confidence": 90', '"confidence": 90, "confidence": 91'),
                   value.replace('"confidence": 90', '"confidence": NaN'),
                   value.replace('"confidence": 90', '"confidence": Infinity'),
                   value.replace('"confidence": 90', '"confidence": 1e9999')]
        for message in invalid:
            self.assertFalse(validate_output_contract(message, OPENING_SCHEMA).valid)

    def test_schema_precheck_visits_absent_properties_empty_arrays_and_extra_rules(self):
        for schema in ({"type": "object", "properties": {"absent": {"pattern": "x"}}},
                       {"type": "array", "items": {"uniqueItems": True}},
                       {"type": "object", "additionalProperties": {"format": "email"}},
                       {"type": "string", "properties": {"absent": {"type": "invalid"}}},
                       {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}):
            with self.subTest(schema=schema):
                with self.assertRaises(ValueError):
                    validate_schema(schema)
                self.assertFalse(validate_document({}, schema).valid)

    def test_schema_rule_types_and_json_numeric_semantics(self):
        for schema in ({"required": "x"}, {"type": []}, {"type": ["integer", "integer"]},
                       {"additionalProperties": "false"}, {"minItems": True}, {"maximum": "5"},
                       {"items": []}, {"enum": []}, {"enum": [1, 1.0]}, {"required": ["x", "x"]}):
            with self.assertRaises(ValueError):
                validate_schema(schema)
        self.assertFalse(validate_document(True, {"enum": [1]}).valid)
        self.assertTrue(validate_document(1.0, {"type": "integer"}).valid)
        self.assertTrue(validate_document(10 ** 400, {"type": "integer"}).valid)
        self.assertFalse(validate_document(float("nan"), {"type": "number"}).valid)
        self.assertFalse(validate_document({"a": True}, {"enum": [{"a": 1}]}).valid)

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
        for schema in (skill_dir("models-consensus", root=REPO_ROOT) / "schemas").glob("*.json"):
            with self.subTest(schema=schema.name):
                validate_schema(json.loads(schema.read_text()))
                result = validate_value({}, schema)
                self.assertNotIn("unsupported schema keyword", result.error or "")


class RunnerOutputContractTests(unittest.TestCase):
    def test_pi_and_grok_accept_only_schema_valid_final_answers(self):
        valid = json.dumps(opening_answer())
        for name in ("pi", "grok"):
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
