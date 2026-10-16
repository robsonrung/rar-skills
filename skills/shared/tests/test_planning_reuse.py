#!/usr/bin/env python3
"""Verify shared decisions are copied without stale evidence or weaker task gates."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gate_contract import BLOCK, readiness_errors
from planning_reuse import render, selected_gate
from task_queue import canonical_text_sha256


def gate():
    return {"schema_version": 1, "verdict": "proceed", "lenses_run": [],
            "blocking_findings": [], "advisory_findings": [], "required_changes": [],
            "decision_required": None, "review_focus": []}


def finding():
    return {"id": "D1-F1", "lens": "architecture-lens", "summary": "One owner",
            "evidence": ["source.py:1"], "status": "resolved",
            "resolution": {"reason": "Ownership is explicit", "evidence": ["decisions.md#D1"]}}


class PlanningReuseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        (self.root / "source.py").write_text("def owner(): pass\n")
        self.shared = gate()
        self.shared["blocking_findings"] = [finding()]
        self.shared["required_changes"] = [{"id": "D1-C1", "finding_id": "D1-F1", "summary": "Set owner",
                                            "status": "resolved", "resolution": finding()["resolution"]}]
        self.write_shared()
        self.request = {"schema_version": 1,
                        "shared": [{"decision_id": "D1", "path": "decisions.md", "content_sha256": self.digest("decisions.md"), "scope": "shared API"}],
                        "sources": [{"path": "source.py", "content_sha256": self.digest("source.py")}],
                        "task": {"id": "T1", "assessment": "Existing API ownership applies; local input validation is assessed.",
                                 "surfaces": [{"scope": "shared API", "decision_id": "D1", "status": "unchanged"},
                                              {"scope": "input validation", "decision_id": None, "status": "assessed"}],
                                 "security": {"level": "deep", "trigger": "untrusted input"}, "gate": gate()}}

    def digest(self, name):
        return canonical_text_sha256((self.root / name).read_text())

    def write_shared(self):
        (self.root / "decisions.md").write_text("# Decisions\n## D1: API ownership\nScope: shared API\n```gate-result\n" + json.dumps(self.shared) + "\n```\n")

    def run_render(self):
        (self.root / "render.json").write_text(json.dumps(self.request))
        return render("render.json", self.root)

    def test_complete_v1_gate_preserves_findings_changes_and_security(self):
        result = self.run_render()
        section = result["gate_section"]
        self.assertEqual(readiness_errors(section), [])
        value = json.loads(BLOCK.findall(section)[0])
        self.assertEqual(value["blocking_findings"], self.shared["blocking_findings"])
        self.assertEqual(value["required_changes"], self.shared["required_changes"])
        self.assertIn("Shared decision D1: decisions.md#D1", value["review_focus"])
        self.assertIn("Security: deep; trigger: untrusted input", section)
        self.assertFalse(result["approval_granted"])
        self.assertEqual(result, self.run_render())

    def test_only_render_inputs_enter_approved_scope(self):
        result = self.run_render()
        self.assertEqual({item["path"] for item in result["scope_inputs"]}, {"decisions.md", "render.json"})
        self.assertEqual(result["checked_sources"], self.request["sources"])
        for item in result["scope_inputs"]:
            self.assertEqual(item["content_sha256"], self.digest(item["path"]))

    def test_source_drift_and_missing_sources_block_reuse(self):
        (self.root / "source.py").write_text("def changed_owner(): pass\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.run_render()
        (self.root / "source.py").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_render()

    def test_decision_revision_and_scope_drift_block_reuse(self):
        (self.root / "decisions.md").write_text((self.root / "decisions.md").read_text() + "Changed basis.\n")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.run_render()
        self.write_shared()
        self.request["shared"][0]["scope"] = "other API"
        with self.assertRaisesRegex(ValueError, "scope is missing or changed"):
            self.run_render()

    def test_unknown_changed_or_unmatched_applicability_blocks_reuse(self):
        surface = self.request["task"]["surfaces"][0]
        for status in ("unknown", "changed", "assessed"):
            surface["status"] = status
            with self.assertRaises(ValueError):
                self.run_render()
        surface["status"] = "unchanged"
        surface["scope"] = "other API"
        with self.assertRaisesRegex(ValueError, "must match"):
            self.run_render()

    def test_unresolved_shared_or_task_findings_cannot_be_labeled_proceed(self):
        self.shared["blocking_findings"][0].update(status="open", resolution=None)
        self.write_shared()
        self.request["shared"][0]["content_sha256"] = self.digest("decisions.md")
        with self.assertRaisesRegex(ValueError, "open blocking"):
            self.run_render()
        self.shared["blocking_findings"] = [finding()]
        self.write_shared()
        self.request["shared"][0]["content_sha256"] = self.digest("decisions.md")
        self.request["task"]["gate"]["decision_required"] = {"id": "D2", "question": "Which owner?", "owner": "user"}
        with self.assertRaisesRegex(ValueError, "unresolved decision"):
            self.run_render()

    def test_conflicting_disposition_or_severity_cannot_replace_shared_finding(self):
        delta = self.request["task"]["gate"]
        delta["blocking_findings"] = [finding()]
        delta["blocking_findings"][0]["resolution"]["reason"] = "A different conclusion"
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.run_render()
        delta["blocking_findings"] = []
        delta["advisory_findings"] = [finding()]
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.run_render()

    def test_identical_findings_are_deduplicated_and_task_findings_retained(self):
        delta = self.request["task"]["gate"]
        delta["blocking_findings"] = [finding()]
        advisory = finding()
        advisory.update(id="T1-F1", status="open", resolution=None)
        delta["advisory_findings"] = [advisory]
        value = json.loads(BLOCK.findall(self.run_render()["gate_section"])[0])
        self.assertEqual(value["blocking_findings"], [finding()])
        self.assertEqual(value["advisory_findings"], [advisory])

    def test_task_security_and_risk_assessment_remain_required(self):
        for bad in ({"level": "inherit", "trigger": "parent"}, {"level": "standard", "trigger": ""}, {"level": "deep", "trigger": "x\nSecurity: standard"}):
            self.request["task"]["security"] = bad
            with self.assertRaisesRegex(ValueError, "security"):
                self.run_render()
        self.request["task"]["security"] = {"level": "standard", "trigger": "no exposed surface"}
        self.request["task"]["assessment"] = ""
        with self.assertRaisesRegex(ValueError, "risk assessment"):
            self.run_render()

    def test_missing_duplicate_decision_and_unselected_scope_are_rejected(self):
        self.request["shared"][0]["decision_id"] = "D2"
        with self.assertRaisesRegex(ValueError, "heading"):
            self.run_render()
        self.request["shared"][0]["decision_id"] = "D1"
        self.request["shared"].append(copy.deepcopy(self.request["shared"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.run_render()
        self.request["shared"].pop()
        self.request["task"]["surfaces"] = [self.request["task"]["surfaces"][1]]
        with self.assertRaisesRegex(ValueError, "every selected decision"):
            self.run_render()

    def test_paths_cannot_escape_root(self):
        for path in ("../outside.md", "https://example.com/source", str(self.root / "source.py")):
            self.request["sources"][0]["path"] = path
            with self.assertRaises(ValueError):
                self.run_render()

    def test_alias_and_symlink_inputs_are_rejected(self):
        (self.root / "alias.py").symlink_to(self.root / "source.py")
        for value in ("alias.py", "./source.py", "child/../source.py"):
            self.request["sources"][0]["path"] = value
            with self.assertRaises(ValueError):
                self.run_render()
        self.request["sources"][0]["path"] = "source.py"
        self.run_render()
        (self.root / "alias.json").symlink_to(self.root / "render.json")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            render(self.root / "alias.json", self.root)

    def test_mid_render_source_drift_is_rejected(self):
        def change_source(*args):
            result = selected_gate(*args)
            (self.root / "source.py").write_text("changed while rendering\n")
            return result
        with patch("planning_reuse.selected_gate", side_effect=change_source):
            with self.assertRaisesRegex(ValueError, "source changed"):
                self.run_render()

    def test_cli_hash_uses_existing_scope_normalization(self):
        (self.root / "task.md").write_bytes(b"# Task\r\n**Status:** ready-for-agent\r\nContract\r\n")
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/planning_reuse.py"),
                   "--root", str(self.root), "--hash-input", "task.md", "--hash-input", "decisions.md"]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [{"path": name, "content_sha256": self.digest(name)}
                                                     for name in ("task.md", "decisions.md")])
        self.assertEqual(self.digest("task.md"), canonical_text_sha256("# Task\nContract\n"))

    def test_cli_is_read_only_and_resolves_explicit_root(self):
        self.run_render()
        before = {path.name: path.read_bytes() for path in self.root.iterdir()}
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/planning_reuse.py"),
                   "--root", str(self.root), "--request", "render.json"]
        result = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["approval_granted"])
        self.assertEqual(before, {path.name: path.read_bytes() for path in self.root.iterdir()})
        (self.root / "render.json").write_text('{"schema_version":1,"schema_version":1}')
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate", result.stderr)


if __name__ == "__main__":
    unittest.main()
