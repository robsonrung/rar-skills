#!/usr/bin/env python3
"""Check complete input budgets without provider calls or tokenizer estimates."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import context_packet as packet


class RenderedInputTests(unittest.TestCase):
    def test_exact_utf8_size_hash_and_unknown_tokens(self):
        text = "Ação\r\n東京"
        encoded = text.encode("utf-8")
        measured = packet.measure_rendered(text, {"max_bytes": len(encoded)})
        self.assertEqual(measured["utf8_bytes"], len(encoded))
        self.assertEqual(measured["sha256"], hashlib.sha256(encoded).hexdigest())
        self.assertIsNone(measured["token_count"])
        self.assertIn("role_history", measured["unmeasured"])
        self.assertIn("tool_schemas", measured["unmeasured"])
        with self.assertRaises(packet.ContextBudgetError) as caught:
            packet.measure_rendered(text, {"max_bytes": len(encoded) - 1})
        self.assertEqual(caught.exception.measurement["utf8_bytes"], len(encoded))

    def test_limits_validate_without_silently_raising_the_ceiling(self):
        for budget in ({"max_bytes": 0}, {"max_bytes": True}, {"max_bytes": "24000"},
                       {"max_bytes": 24001}, {"max_bytes": 24001, "reason": " "},
                       {"max_bytes": 12, "ignore_overflow": True}):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                packet.validate_budget(budget)
        approved = {"max_bytes": 30000, "reason": "Required acceptance cases need this space"}
        self.assertEqual(packet.measure_rendered("x" * 25000, approved)["max_bytes"], 30000)
        with self.assertRaises(packet.ContextBudgetError):
            packet.measure_rendered("x" * 25000)

    def test_measure_cli_is_read_only_and_preserves_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.md"
            content = "Ação\r\n契約".encode("utf-8")
            path.write_bytes(content)
            command = [sys.executable, str(SCRIPTS / "context_packet.py"), "measure", "--input", str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["input_measurement"]["utf8_bytes"], len(content))
            blocked = subprocess.run(command + ["--max-bytes", "1"], capture_output=True, text=True)
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(json.loads(blocked.stdout)["input_measurement"]["utf8_bytes"], len(content))
            self.assertEqual(path.read_bytes(), content)
            self.assertEqual(list(Path(directory).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
