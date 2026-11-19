#!/usr/bin/env python3
"""Captured evidence keeps real output and goes stale when any recorded input changes."""
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

    def contract(self, text):
        path = self.root / ".ai-workflow" / "contract.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return str(path)

    def capture_with_inputs(self, name, contract):
        return self.cli("run", "--out", str(self.root / ".ai-workflow" / name), "--base", "HEAD",
                        "--contract", contract, "--", "true")

    def test_worker_record_is_stale_when_the_target_checkout_changed(self):
        worker = self.root.parent / (self.root.name + "-worker")
        subprocess.run(["git", "clone", "-q", str(self.root), str(worker)], check=True)
        self.addCleanup(subprocess.run, ["rm", "-rf", str(worker)])
        out = str(self.root / ".ai-workflow/worker.json")
        captured = self.cli("run", "--out", out, "--cwd", str(worker), "--", "true")
        self.assertEqual(captured.returncode, 0)
        (self.root / "app.txt").write_text("integrated\n")
        self.assertEqual(self.cli("stale", out).returncode, 1)
        self.assertEqual(self.cli("stale", "--target", str(worker), out).returncode, 0)

    def test_changed_contract_makes_evidence_stale_with_the_same_source(self):
        contract = self.contract("criteria one\n")
        self.assertEqual(self.capture_with_inputs("a.json", contract).returncode, 0)
        evidence = str(self.root / ".ai-workflow/a.json")
        self.assertEqual(self.cli("stale", evidence).returncode, 0)
        self.contract("criteria two\n")
        self.assertEqual(self.cli("stale", evidence).returncode, 1)
        self.assertEqual(self.cli("stale", "--contract", contract, evidence).returncode, 1)

    def test_all_inputs_equal_is_current(self):
        contract = self.contract("criteria\n")
        self.assertEqual(self.capture_with_inputs("a.json", contract).returncode, 0)
        evidence = str(self.root / ".ai-workflow/a.json")
        result = self.cli("stale", "--target", str(self.root), "--base", "HEAD", "--contract", contract,
                          "--command", "true", evidence)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.cli("stale", "--command", "false", evidence).returncode, 1)
        base = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "--allow-empty", "-m", "moved base"], check=True)
        self.assertEqual(self.cli("stale", evidence).returncode, 1)
        self.assertEqual(self.cli("stale", "--base", base, evidence).returncode, 0)

    def test_record_without_a_requested_input_is_stale(self):
        self.assertEqual(self.capture("a.json", "true").returncode, 0)
        evidence = str(self.root / ".ai-workflow/a.json")
        self.assertEqual(self.cli("stale", evidence).returncode, 0)
        self.assertEqual(self.cli("stale", "--base", "HEAD", evidence).returncode, 1)
        self.assertEqual(self.cli("stale", "--contract", self.contract("c\n"), evidence).returncode, 1)

    def test_old_format_record_is_stale(self):
        self.assertEqual(self.capture("a.json", "true").returncode, 0)
        path = self.root / ".ai-workflow/a.json"
        record = json.loads(path.read_text())
        old = {key: record[key] for key in ("command", "cwd", "root", "head", "tree", "exit_code", "duration_s", "stdout", "stderr")}
        old_path = self.root / ".ai-workflow/old.json"
        old_path.write_text(json.dumps(old))
        result = self.cli("stale", str(old_path))
        self.assertEqual(result.returncode, 1)
        self.assertIn("old format", result.stdout)


if __name__ == "__main__":
    unittest.main()
