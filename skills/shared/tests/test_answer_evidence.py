#!/usr/bin/env python3
"""Check portable user evidence, immutable corrections, and authority mapping."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from answer_evidence import capture, packet_source
from context_packet import prepare, verify
from review_evidence import load_record


class AnswerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "answer.json"

    def test_missing_locator_preserves_exact_answer_and_reuses_identity(self):
        answer = "Use option 2.\r\nKeep the existing access scope.\n"
        first = capture(answer, "user", "user_instruction", self.path)
        before = self.path.read_bytes()
        second = capture(answer, "user", "user_instruction", self.path)
        self.assertEqual(first, second)
        self.assertEqual(self.path.read_bytes(), before)
        value = load_record(self.path)
        self.assertEqual(value["actual_answer"], answer)
        self.assertIsNone(value["native_locator"])
        self.assertTrue(value["locator_limit"])

    def test_native_locator_is_retained_without_a_limit(self):
        capture("Approved", "user", "approved_decision", self.path, native_locator="message:actual-19")
        value = load_record(self.path)
        self.assertEqual(value["native_locator"], "message:actual-19")
        self.assertIsNone(value["locator_limit"])

    def test_inference_cannot_become_user_authority(self):
        for authority in ("user_instruction", "approved_decision"):
            with self.assertRaises(ValueError):
                capture("Assume option 2", "role", authority, self.path)
        self.assertFalse(self.path.exists())

    def test_refuses_empty_text_overwrite_and_bad_locator(self):
        for answer, locator in (("", None), ("Answer", "")):
            with self.assertRaises(ValueError):
                capture(answer, "user", "user_instruction", self.path, locator)
        capture("First answer", "user", "user_instruction", self.path)
        with self.assertRaises(ValueError):
            capture("Changed answer", "user", "user_instruction", self.path)
        self.assertEqual(load_record(self.path)["actual_answer"], "First answer")

    def test_corrections_preserve_history_and_packet_compatibility(self):
        first = capture("Option 1", "user", "user_instruction", self.path)
        before = self.path.read_bytes()
        correction = self.path.with_name("correction.json")
        capture("Correction: option 2", "user", "approved_decision", correction, supersedes=self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(load_record(correction)["supersedes"]["source_id"], first["source_id"])
        brief = self.path.with_name("brief.md")
        brief.write_text("Implement option 2.")
        packet = prepare(brief, [packet_source(correction), packet_source(self.path, superseded=True)], self.path.with_name("packet.json"))
        self.assertEqual([row["authority"] for row in verify(packet)["sources"]], ["decision", "superseded"])

    def test_inference_maps_to_evidence_and_dry_run_writes_nothing(self):
        dry = capture("Likely option 2", "role", "inference", self.path, dry_run=True)
        self.assertFalse(self.path.exists())
        actual = capture("Likely option 2", "role", "inference", self.path)
        self.assertEqual(dry, actual)
        self.assertEqual(packet_source(self.path)["authority"], "evidence")


if __name__ == "__main__":
    unittest.main()
