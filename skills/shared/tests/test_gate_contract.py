#!/usr/bin/env python3
"""Check approval readiness without losing legacy task compatibility."""

import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from gate_contract import readiness_errors


def gate():
    return {"schema_version": 1, "verdict": "proceed", "lenses_run": [],
            "blocking_findings": [], "advisory_findings": [], "required_changes": [],
            "decision_required": None, "review_focus": []}


def task(value):
    return '# T1: Change\n## Gates\nVerdict: proceed\nDecision required: none\nSecurity: standard; trigger: none\n```gate-result\n' + json.dumps(value) + '\n```\n## Rollback note\nRevert.\n'


def finding(status="resolved"):
    return {"id": "T1-boundary-F1", "lens": "architecture-lens", "summary": "Own the invariant",
            "evidence": ["src/domain.py:3"], "status": status,
            "resolution": None if status == "open" else {"reason": "Invariant is enforced", "evidence": ["test_domain.py:8"]}}


class GateContractTests(unittest.TestCase):
    def test_empty_and_evidence_closed_gate_is_ready(self):
        self.assertEqual(readiness_errors(task(gate())), [])
        for status in ("resolved", "dismissed"):
            value = gate()
            value["blocking_findings"] = [finding(status)]
            value["required_changes"] = [{"id": "T1-C1", "finding_id": "T1-boundary-F1", "summary": "Enforce boundary", "status": "resolved", "resolution": {"reason": "Checked", "evidence": ["result.json"]}}]
            self.assertEqual(readiness_errors(task(value)), [])

    def test_proceed_cannot_hide_blocker_or_required_change(self):
        value = gate()
        value["blocking_findings"] = [finding("open")]
        self.assertTrue(any("open blocking" in error for error in readiness_errors(task(value))))
        value["blocking_findings"] = [finding()]
        value["required_changes"] = [{"id": "T1-C1", "finding_id": "T1-boundary-F1", "summary": "Repair", "status": "open", "resolution": None}]
        self.assertTrue(any("open required" in error for error in readiness_errors(task(value))))

    def test_closure_needs_evidence_and_reason(self):
        for status in ("resolved", "dismissed"):
            for bad in (None, {}, {"reason": "approved", "evidence": []}, {"reason": "", "evidence": ["test.py"]}):
                value = gate()
                entry = finding(status)
                entry["resolution"] = bad
                value["blocking_findings"] = [entry]
                self.assertTrue(readiness_errors(task(value)))

    def test_missing_fields_bad_types_and_duplicate_ids_fail(self):
        for field in gate():
            value = gate()
            del value[field]
            self.assertTrue(readiness_errors(task(value)), field)
        for field, bad in (("schema_version", True), ("lenses_run", {}), ("review_focus", "none"), ("blocking_findings", None), ("required_changes", {}), ("decision_required", [])):
            value = gate()
            value[field] = bad
            self.assertTrue(readiness_errors(task(value)), field)
        value = gate()
        value["blocking_findings"] = [finding()]
        value["advisory_findings"] = [copy.deepcopy(finding())]
        self.assertTrue(readiness_errors(task(value)))

    def test_labels_and_decisions_must_agree(self):
        value = gate()
        value["decision_required"] = {"id": "D4", "owner": "user", "question": "Choose access scope"}
        self.assertTrue(readiness_errors(task(value)))
        value = gate()
        value["verdict"] = "revise"
        self.assertTrue(readiness_errors(task(value)))
        self.assertTrue(readiness_errors(task(gate()).replace("Verdict: proceed", "Verdict: revise")))
        self.assertTrue(readiness_errors(task(gate()).replace("Decision required: none", "Decision required: none\nDecision required: none")))

    def test_malformed_new_record_never_falls_back(self):
        valid = task(gate())
        for malformed in (valid.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'), valid.replace('"schema_version": 1', '"schema_version": NaN'), valid.replace('```\n## Rollback', '## Rollback'), valid.replace('```gate-result', '```gate-result-v2'), valid.replace('```gate-result', '```json'), valid.replace('Verdict: proceed', 'Verdict: proceed\nBlocking findings: open F1'), valid + valid, '## Gates\nBlocking findings: none\nVerdict: proceed\nDecision required: none\n'):
            self.assertTrue(readiness_errors(malformed), malformed)

    def test_unknown_change_reference_and_open_resolution_fail(self):
        value = gate()
        value["required_changes"] = [{"id": "T1-C1", "finding_id": "missing", "summary": "Repair", "status": "resolved", "resolution": {"reason": "Checked", "evidence": ["test.py"]}}]
        self.assertTrue(readiness_errors(task(value)))
        value = gate()
        entry = finding()
        entry["status"] = "open"
        value["advisory_findings"] = [entry]
        self.assertTrue(readiness_errors(task(value)))

    def test_legacy_reader_keeps_ownership_of_old_forms(self):
        for value in ('# Old task\n', '# Old task\n## Acceptance\nReturn {"schema_version": 1}.\n', '## Gates\n1. Lenses run: none\n2. Verdict: proceed\n3. Required changes and resolved findings: none\n4. Decision required: none\nSecurity: standard; trigger: none\n'):
            self.assertEqual(readiness_errors(value), [])


if __name__ == "__main__":
    unittest.main()
