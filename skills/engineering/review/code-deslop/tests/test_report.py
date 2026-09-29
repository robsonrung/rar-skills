"""Structural report checks, not verification of real source claims."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("report_validator", ROOT / "scripts/validate_report.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / "assets/report.example.json").read_text())

    def fixed(self):
        self.report["mode"] = "fix"
        self.report["changed_files"] = ["example/count.ts"]
        self.report["findings"][0].update(status="fixed", category="control-flow")
        self.report["checks"][0].update(kind="test", command="example-local-check", baseline="passed", after="passed")
        return self.report

    def test_illustrative_audit_is_valid(self):
        self.assertEqual(validator.validate(self.report), [])

    def test_supported_fix_is_structurally_valid(self):
        self.assertEqual(validator.validate(self.fixed()), [])

    def test_audit_cannot_claim_changed_files(self):
        self.report["changed_files"] = ["x.py"]
        self.assertTrue(validator.validate(self.report))

    def test_audit_cannot_claim_fixed_finding(self):
        self.report["findings"][0]["status"] = "fixed"
        self.assertTrue(validator.validate(self.report))

    def test_missing_evidence_is_invalid(self):
        del self.report["findings"][0]["counterevidence"]
        self.assertTrue(validator.validate(self.report))

    def test_not_run_is_not_passed(self):
        self.fixed()["checks"][0]["after"] = "not-run"
        self.assertTrue(validator.validate(self.report))

    def test_existing_failure_is_not_passing_baseline(self):
        self.fixed()["checks"][0]["baseline"] = "failed"
        self.assertTrue(validator.validate(self.report))

    def test_executable_change_needs_more_than_static_review(self):
        self.fixed()["checks"][0]["kind"] = "static"
        self.assertTrue(validator.validate(self.report))

    def test_comment_cleanup_can_use_static_review(self):
        self.fixed()["findings"][0]["category"] = "noise"
        self.report["checks"][0]["kind"] = "static"
        self.assertEqual(validator.validate(self.report), [])

    def test_unknown_check_is_invalid(self):
        self.report["findings"][0]["check_ids"] = ["not-real"]
        self.assertTrue(validator.validate(self.report))

    def test_high_risk_fix_needs_separate_task(self):
        self.fixed()["findings"][0]["risk"] = "high"
        self.assertTrue(validator.validate(self.report))

    def test_absent_reviewer_cannot_pass(self):
        self.report["review"]["result"] = "passed"
        self.assertTrue(validator.validate(self.report))

    def test_duplicate_identifiers_rejected(self):
        for field in ("findings", "checks"):
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.report)
                candidate[field].append(copy.deepcopy(candidate[field][0]))
                self.assertTrue(validator.validate(candidate))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"mode":"audit","mode":"fix"}', object_pairs_hook=validator.no_duplicate_keys)

    def test_paths_cannot_escape(self):
        for path in ("/etc/passwd", "../private", "src/../../private", ""):
            with self.subTest(path=path):
                self.report["findings"][0]["path"] = path
                self.assertTrue(validator.validate(self.report))

    def test_positive_integer_line_required(self):
        for line in (0, -1, True, "1", None):
            with self.subTest(line=line):
                self.report["findings"][0]["line"] = line
                self.assertTrue(validator.validate(self.report))

    def test_executed_check_needs_command(self):
        self.fixed()["checks"][0]["command"] = None
        self.assertTrue(validator.validate(self.report))

    def test_malformed_types_return_errors_without_crashing(self):
        for key in ("mode", "scope", "findings", "checks", "review"):
            for value in ([], {}, 5, None):
                with self.subTest(key=key, value=value):
                    candidate = copy.deepcopy(self.report)
                    candidate[key] = value
                    errors = validator.validate(candidate)
                    self.assertIsInstance(errors, list)
        for section, keys in (("checks", ("kind", "baseline", "after")), ("findings", ("status", "category", "risk"))):
            for key in keys:
                for value in ([], {}, None):
                    with self.subTest(section=section, key=key, value=value):
                        candidate = copy.deepcopy(self.report)
                        candidate[section][0][key] = value
                        self.assertTrue(validator.validate(candidate))

    def test_commands_are_never_executed(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / "must-not-exist"
            self.fixed()["checks"][0]["command"] = f"touch {sentinel}"
            self.assertEqual(validator.validate(self.report), [])
            self.assertFalse(sentinel.exists())

    def test_non_object_report_rejected(self):
        for value in (None, [], "test", 1):
            self.assertTrue(validator.validate(value))


if __name__ == "__main__":
    unittest.main()
