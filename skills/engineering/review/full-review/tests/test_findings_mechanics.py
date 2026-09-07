#!/usr/bin/env python3
"""Regression checks for preserving findings and their evidence strength."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "findings_mechanics.py"
SPEC = importlib.util.spec_from_file_location("findings_mechanics", SCRIPT)
mechanics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mechanics)


def finding(**changes):
    value = {
        "severity": "MEDIUM", "confidence": 0.8, "category": "correctness",
        "path": "src/service.py", "line_start": 8, "line_end": 8,
        "title": "Missing state check", "problem": "A closed record accepts a write.",
        "evidence": ["The write path does not check record state."],
        "suggested_fix": "Reject writes to closed records.",
        "tests_to_run": "Check a write against a closed record.",
        "verification": "Observed in the scoped source.",
    }
    value.update(changes)
    return value


def run_filter(returns, *arguments):
    output = io.StringIO()
    with patch("sys.argv", [str(SCRIPT), *arguments]), patch("sys.stdin", io.StringIO(json.dumps(returns))), contextlib.redirect_stdout(output):
        code = mechanics.main()
    return code, json.loads(output.getvalue())


class FindingsMechanicsTests(unittest.TestCase):
    def test_distinct_problems_at_one_location_survive(self):
        _, result = run_filter([{"source": "reviewer", "comments": [finding(), finding(problem="A missing record causes a crash.")]}])
        self.assertEqual(len(result["findings"]), 2)

    def test_agreement_does_not_raise_confidence_above_threshold(self):
        _, result = run_filter([
            {"source": "first", "comments": [finding(confidence=0.7)]},
            {"source": "second", "comments": [finding(confidence=0.72)]},
        ])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["suppressed_findings"][0]["confidence"], 0.72)

    def test_lower_severity_evidence_cannot_create_a_blocker(self):
        _, result = run_filter([
            {"source": "first", "comments": [finding(severity="HIGH", confidence=0.6)]},
            {"source": "second", "comments": [finding(severity="MEDIUM", confidence=0.95)]},
        ])
        self.assertEqual([item["severity"] for item in result["findings"]], ["MEDIUM"])
        self.assertEqual(result["suppressed_findings"][0]["confidence"], 0.6)

    def test_exact_duplicates_preserve_evidence_and_source_labels(self):
        _, result = run_filter([
            {"source": "first", "comments": [finding()]},
            {"source": "second", "comments": [finding(confidence=0.85, evidence=["A focused reproduction confirms the write."])]},
        ])
        self.assertEqual(len(result["findings"]), 1)
        kept = result["findings"][0]
        self.assertEqual(kept["severity"], "MEDIUM")
        self.assertEqual(kept["confidence"], 0.85)
        self.assertEqual(len(kept["evidence"]), 2)
        self.assertEqual({kept["source"], *kept["corroborated_by"]}, {"first", "second"})

    def test_nonblocking_cap_preserves_blockers_and_uses_confidence(self):
        _, result = run_filter([{"source": "reviewer", "comments": [
            finding(severity="HIGH", confidence=0.8),
            finding(severity="LOW", confidence=0.95, line_start=20, line_end=20),
            finding(severity="MEDIUM", confidence=0.8, line_start=30, line_end=30),
        ]}], "--max-non-blockers", "1")
        self.assertEqual([item["severity"] for item in result["findings"]], ["HIGH", "LOW"])
        self.assertEqual(result["suppressed_by_cap"], 1)

    def test_malformed_returns_and_line_values_remain_visible(self):
        code, result = run_filter([{"source": "missing", "comments": None}, {"source": "reviewer", "comments": [finding(line_start=True)]}])
        self.assertEqual(code, 0)
        self.assertEqual(result["malformed_returns"], 1)
        self.assertEqual(result["malformed_findings"], 1)
        self.assertEqual(result["findings"], [])

    def test_case_distinct_paths_do_not_merge(self):
        _, result = run_filter([{"source": "reviewer", "comments": [finding(path="src/Foo.py"), finding(path="src/foo.py")]}])
        self.assertEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
