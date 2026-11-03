#!/usr/bin/env python3
"""Captured evidence keeps real output and goes stale when the tree changes."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "capture_check.py"


class CaptureCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for args in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(self.root), *args], check=True)
        (self.root / "app.txt").write_text("one\n")
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=self.root)

    def capture(self, name, *command):
        return self.cli("run", "--out", str(self.root / ".ai-workflow" / name), "--", *command)

    def test_records_output_exit_code_and_tree(self):
        result = self.capture("fail.json", sys.executable, "-c", "print('boom'); raise SystemExit(3)")
        self.assertEqual(result.returncode, 3)
        record = json.loads((self.root / ".ai-workflow/fail.json").read_text())
        self.assertEqual((record["exit_code"], record["stdout"].strip()), (3, "boom"))
        self.assertTrue(record["head"] and record["tree"])

    def test_evidence_goes_stale_on_tracked_or_untracked_change_but_not_on_evidence(self):
        self.assertEqual(self.capture("a.json", "true").returncode, 0)
        self.assertEqual(self.capture("b.json", "true").returncode, 0)
        evidence = str(self.root / ".ai-workflow/a.json")
        self.assertEqual(self.cli("stale", evidence).returncode, 0)
        (self.root / "new.txt").write_text("untracked\n")
        self.assertEqual(self.cli("stale", evidence).returncode, 1)
        (self.root / "new.txt").unlink()
        (self.root / "app.txt").write_text("two\n")
        self.assertEqual(self.cli("stale", evidence).returncode, 1)

    def test_commit_of_the_same_content_keeps_evidence_current(self):
        (self.root / "app.txt").write_text("two\n")
        self.assertEqual(self.capture("a.json", "true").returncode, 0)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qam", "change"], check=True)
        self.assertEqual(self.cli("stale", str(self.root / ".ai-workflow/a.json")).returncode, 0)

    def test_never_overwrites_earlier_evidence(self):
        self.assertEqual(self.capture("a.json", "true").returncode, 0)
        self.assertNotEqual(self.capture("a.json", "true").returncode, 0)


if __name__ == "__main__":
    unittest.main()
