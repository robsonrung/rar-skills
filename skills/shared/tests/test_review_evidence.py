#!/usr/bin/env python3
"""Regression checks for source binding and review readiness."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_evidence as evidence


class ReviewEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.artifacts = Path(self.temp.name) / "records"
        self.artifacts.mkdir()
        self.contract = self.artifacts / "task.md"
        self.contract.write_text("Check the result.\n**Status:** ready-for-agent\n")
        self.requirements = self.artifacts / "requirements.json"
        self.plan = {"context": {"runtime": sys.version}, "checks": [], "observations": [], "exclusions": {}}
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.test")
        self.git("config", "user.name", "Test")
        (self.root / "app.txt").write_text("before\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Initial fixture")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.root / "app.txt").write_text("after\n")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def prepare(self):
        self.requirements.write_text(json.dumps(self.plan))
        return evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "review")

    def response(self, path):
        snapshot = evidence.load_record(path)
        return {
            "snapshot_sha256": evidence.file_hash(path),
            "coverage": [{"path": name, "outcome": "reviewed", "reason": "Read the changed behavior and its callers."} for name in snapshot["source"]["changed_paths"]],
            "findings": [], "checks": {}, "observations": [], "summary": "No defect found.",
        }

    def record(self, path, result):
        return evidence.record_review(path, result, {"success": True, "agent_message": json.dumps(result)})

    def command(self, program):
        self.plan["checks"] = [{"id": "check", "command": [sys.executable, "-c", program], "cwd": ".", "timeout_seconds": 5}]

    def test_ready_requires_a_recorded_review(self):
        path = self.prepare()
        with self.assertRaises(OSError):
            evidence.assess(path, self.base)
        self.record(path, self.response(path))
        self.assertEqual(evidence.assess(path, self.base)["status"], "ready")

    def test_untracked_deleted_and_renamed_paths_require_coverage(self):
        (self.root / "app.txt").rename(self.root / "new.txt")
        path = self.prepare()
        result = self.response(path)
        self.assertEqual({x["path"] for x in result["coverage"]}, {"app.txt", "new.txt"})
        result["coverage"].pop()
        with self.assertRaisesRegex(ValueError, "coverage is incomplete"):
            self.record(path, result)

    def test_duplicate_coverage_and_unapproved_exclusions_are_rejected(self):
        path = self.prepare()
        result = self.response(path)
        result["coverage"].append(copy.deepcopy(result["coverage"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate coverage"):
            self.record(path, result)
        result = self.response(path)
        result["coverage"][0]["outcome"] = "excluded"
        with self.assertRaisesRegex(ValueError, "exclusion differs"):
            self.record(path, result)

    def test_stale_working_tree_index_base_and_untracked_files_are_rejected(self):
        path = self.prepare()
        self.record(path, self.response(path))
        (self.root / "app.txt").write_text("new edit\n")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(path, self.base)
        (self.root / "app.txt").write_text("after\n")
        self.git("add", "app.txt")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(path, self.base)
        self.git("reset", "-q", self.base, "--", "app.txt")
        (self.root / "extra.txt").write_text("extra")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(path, self.base)
        (self.root / "extra.txt").unlink()
        self.git("commit", "--allow-empty", "-qm", "Move base")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(path, "HEAD")

    def test_contract_status_can_change_but_acceptance_and_context_cannot(self):
        path = self.prepare()
        self.contract.write_text("Check the result.\n**Status:** done\n")
        evidence.current_snapshot(path)
        self.contract.write_text("Check a different result.\n")
        with self.assertRaisesRegex(ValueError, "contract changed"):
            evidence.current_snapshot(path)
        self.contract.write_text("Check the result.\n")
        self.plan["context"]["runtime"] = "different runtime"
        self.requirements.write_text(json.dumps(self.plan))
        with self.assertRaisesRegex(ValueError, "requirements changed"):
            evidence.current_snapshot(path)

    def test_findings_threshold_and_resolution_evidence(self):
        path = self.prepare()
        result = self.response(path)
        result["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2", "status": "deferred", "evidence": "The edge case still fails."}]
        self.record(path, result)
        self.assertEqual(evidence.assess(path, self.base)["status"], "needs-work")
        with self.assertRaisesRegex(ValueError, "different content"):
            changed = self.response(path)
            self.record(path, changed)

    def test_missing_or_unknown_severity_is_not_accepted(self):
        path = self.prepare()
        for severity in (None, "P4", "low"):
            with self.subTest(severity=severity):
                result = self.response(path)
                result["findings"] = [{"id": "F1", "path": "app.txt", "severity": severity, "status": "open", "evidence": "Observed failure."}]
                with self.assertRaisesRegex(ValueError, "severity"):
                    self.record(path, result)

    def test_required_checks_must_have_captured_results(self):
        self.command("print('ok')")
        path = self.prepare()
        result = self.response(path)
        with self.assertRaisesRegex(ValueError, "checks are missing"):
            self.record(path, result)
        check = evidence.run_check(path, "check")
        result["checks"]["check"] = str(check)
        self.record(path, result)
        self.assertEqual(evidence.assess(path, self.base)["status"], "ready")
        payload = evidence.load_record(check)
        Path(payload["logs"][0]["path"]).write_text("changed log")
        with self.assertRaisesRegex(ValueError, "log checksum"):
            evidence.assess(path, self.base)

    def test_failed_command_cannot_approve_and_cannot_be_overwritten(self):
        self.command("raise SystemExit(3)")
        path = self.prepare()
        check = evidence.run_check(path, "check")
        result = self.response(path)
        result["checks"]["check"] = str(check)
        self.record(path, result)
        self.assertEqual(evidence.assess(path, self.base)["failed_checks"], ["check"])
        with self.assertRaises(FileExistsError):
            evidence.run_check(path, "check")

    def test_command_that_changes_source_invalidates_its_pass(self):
        self.command("from pathlib import Path; Path('app.txt').write_text('changed by check')")
        path = self.prepare()
        check = evidence.run_check(path, "check")
        self.assertTrue(evidence.load_record(check)["source_changed"])
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(path, self.base)

    def test_snapshot_tampering_and_wrong_response_binding_fail(self):
        path = self.prepare()
        result = self.response(path)
        result["snapshot_sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "different snapshot"):
            self.record(path, result)
        data = json.loads(path.read_text())
        data["payload"]["source"]["base"] = "changed"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            evidence.current_snapshot(path)

    def test_review_result_must_match_recorded_response(self):
        path = self.prepare()
        result = self.response(path)
        execution = {"success": True, "agent_message": "{}"}
        with self.assertRaisesRegex(ValueError, "differs"):
            evidence.record_review(path, result, execution)

    def test_browser_observations_require_evidence_and_pass(self):
        self.plan["observations"] = ["checkout"]
        path = self.prepare()
        result = self.response(path)
        with self.assertRaisesRegex(ValueError, "observations are missing"):
            self.record(path, result)
        capture = self.artifacts / "browser.txt"
        capture.write_text("Driver could not reach the application.")
        result["observations"] = [{"id": "checkout", "result": "skipped", "evidence": [{"path": str(capture), "sha256": evidence.file_hash(capture)}]}]
        self.record(path, result)
        self.assertEqual(evidence.assess(path, self.base)["failed_observations"], ["checkout"])

    def test_artifacts_cannot_hide_tracked_source(self):
        with self.assertRaisesRegex(ValueError, "tracked source"):
            evidence.source_state(self.root, self.base, self.root)

    def test_timeout_is_captured_as_failure(self):
        self.command("import time; time.sleep(5)")
        self.plan["checks"][0]["timeout_seconds"] = 1
        path = self.prepare()
        check = evidence.run_check(path, "check")
        self.assertTrue(evidence.load_record(check)["timed_out"])
        self.assertFalse(evidence.validate_check(check, evidence.load_record(path), self.plan["checks"][0]))

    def test_matching_check_can_be_reused_in_another_bundle(self):
        self.command("print('ok')")
        path = self.prepare()
        check = evidence.run_check(path, "check")
        other = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "second")
        result = self.response(other)
        result["checks"]["check"] = str(check)
        self.record(other, result)
        self.assertEqual(evidence.assess(other, self.base)["status"], "ready")

    def test_deferred_p3_with_reason_does_not_block(self):
        path = self.prepare()
        result = self.response(path)
        result["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P3", "status": "deferred", "evidence": "The naming change belongs to a separate cleanup."}]
        self.record(path, result)
        self.assertEqual(evidence.assess(path, self.base)["status"], "ready")

    def test_recheck_cannot_drop_or_lower_an_existing_finding(self):
        path = self.prepare()
        result = self.response(path)
        result["findings"] = [{"id": "task1-F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "A required edge case fails."}]
        previous = self.record(path, result)
        current = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "recheck", previous_reviews=[previous])
        recheck = self.response(current)
        with self.assertRaisesRegex(ValueError, "dropped"):
            self.record(current, recheck)
        recheck["findings"] = copy.deepcopy(result["findings"])
        recheck["findings"][0]["severity"] = "P3"
        with self.assertRaisesRegex(ValueError, "severity changed"):
            self.record(current, recheck)
        recheck["findings"][0].update(severity="P2", status="rejected", evidence="The caller already enforces the required condition.")
        self.record(current, recheck)
        self.assertEqual(evidence.assess(current, self.base)["status"], "ready")

    def test_links_outside_source_are_rejected(self):
        (self.root / "outside").symlink_to(self.contract)
        with self.assertRaisesRegex(ValueError, "target escapes"):
            self.prepare()

    def test_verifier_cli_returns_blocked_for_malformed_records(self):
        path = self.artifacts / "snapshot.json"
        path.write_text('{"payload": [], "sha256": "wrong"}')
        result = subprocess.run([sys.executable, evidence.__file__, "verify", "--snapshot", str(path), "--base", self.base], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def recheck(self, path, previous, name="second"):
        current = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                   self.artifacts / name, previous_reviews=[previous])
        delta = {"mode": "recheck", "snapshot_sha256": evidence.file_hash(current),
                 "previous_review": {"path": str(previous), "sha256": evidence.file_hash(previous)},
                 "reuse_assessment": "Reviewed callers; unchanged paths retain their earlier assessment.",
                 "affected_paths": [], "coverage": [], "findings": [], "checks": {},
                 "observations": [], "summary": "Focused recheck."}
        return current, delta

    def test_delta_keeps_open_findings_until_reviewer_resolves_them(self):
        path = self.prepare()
        first = self.response(path)
        first["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Failure observed."}]
        previous = self.record(path, first)
        current, delta = self.recheck(path, previous)
        self.record(current, delta)
        self.assertEqual(evidence.assess(current, self.base)["open_findings"], ["F1"])
        saved = evidence.load_record(current.parent / "review.json")
        self.assertEqual(json.loads(saved["execution"]["agent_message"]), delta)
        self.assertEqual(saved["result"]["findings"], first["findings"])

    def test_delta_requires_changed_and_affected_coverage(self):
        (self.root / "other.txt").write_text("another changed file")
        path = self.prepare()
        previous = self.record(path, self.response(path))
        (self.root / "app.txt").write_text("fixed")
        current, delta = self.recheck(path, previous)
        with self.assertRaisesRegex(ValueError, "fresh coverage"):
            self.record(current, delta)
        delta["coverage"] = [{"path": "app.txt", "outcome": "reviewed", "reason": "Read the fix and caller."}]
        delta["affected_paths"] = ["other.txt"]
        with self.assertRaisesRegex(ValueError, "fresh coverage"):
            self.record(current, delta)
        delta["coverage"].append({"path": "other.txt", "outcome": "reviewed", "reason": "Verified the affected caller."})
        self.record(current, delta)
        self.assertEqual(evidence.assess(current, self.base)["status"], "ready")

    def test_addendum_corrects_prose_without_closing_findings(self):
        path = self.prepare()
        result = self.response(path)
        result["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Two failing calls."}]
        previous = self.record(path, result)
        current, delta = self.recheck(path, previous)
        delta["mode"] = "addendum"
        delta["findings"] = [{**result["findings"][0], "status": "fixed", "evidence": "Three calls."}]
        with self.assertRaisesRegex(ValueError, "cannot change finding"):
            self.record(current, delta)
        delta["findings"][0]["status"] = "open"
        self.record(current, delta)
        self.assertEqual(evidence.assess(current, self.base)["status"], "needs-work")

    def test_addendum_cannot_cover_changed_source(self):
        path = self.prepare()
        previous = self.record(path, self.response(path))
        (self.root / "app.txt").write_text("changed")
        current, delta = self.recheck(path, previous)
        delta.update(mode="addendum", coverage=self.response(current)["coverage"])
        with self.assertRaisesRegex(ValueError, "unchanged source"):
            self.record(current, delta)

    def test_delta_cannot_change_finding_severity_or_reference_an_unbound_review(self):
        path = self.prepare()
        first = self.response(path)
        first["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Observed failure."}]
        previous = self.record(path, first)
        current, delta = self.recheck(path, previous)
        delta["previous_review"]["sha256"] = "wrong"
        with self.assertRaisesRegex(ValueError, "bound prior"):
            self.record(current, delta)
        delta["previous_review"]["sha256"] = evidence.file_hash(previous)
        delta["findings"] = [{**first["findings"][0], "severity": "P3"}]
        with self.assertRaisesRegex(ValueError, "severity changed"):
            self.record(current, delta)

    def transfer_assessment(self, old, target):
        probe = self.artifacts / "environment.txt"
        probe.write_text("Fresh runtime, installed dependencies, external state and base inspection.")
        row = {"reason": "Inspected both environments and base interactions.", "evidence": [{"path": str(probe), "sha256": evidence.file_hash(probe)}]}
        assessment = {"from_snapshot_sha256": evidence.file_hash(old),
                      "to_source_id": evidence.load_record(target)["source_id"],
                      **{key: row for key in ("runtime", "dependencies", "external_state", "base_interactions")}}
        path = self.artifacts / "transfer-assessment.json"
        path.write_text(json.dumps(assessment))
        return path

    def test_commit_of_identical_content_transfers_checks_with_provenance(self):
        self.command("print('pass')")
        old = self.prepare()
        check = evidence.run_check(old, "check")
        self.git("add", ".")
        self.git("commit", "-qm", "Commit identical content")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "committed")
        self.assertNotEqual(evidence.load_record(old)["source_id"], evidence.load_record(target)["source_id"])
        moved = evidence.transfer_check(old, target, check, self.transfer_assessment(old, target))
        result = self.response(target)
        result["checks"]["check"] = str(moved)
        self.record(target, result)
        self.assertEqual(evidence.assess(target, self.base)["status"], "ready")
        (self.artifacts / "environment.txt").write_text("changed probe")
        with self.assertRaisesRegex(ValueError, "assessment evidence changed"):
            evidence.assess(target, self.base)

    def test_transfer_between_worktrees_preserves_deleted_files_and_modes(self):
        (self.root / "removed.txt").write_text("old")
        self.git("add", "removed.txt")
        self.git("commit", "-qm", "Add removal fixture")
        (self.root / "removed.txt").unlink()
        self.command("print('pass')")
        old = self.prepare()
        check = evidence.run_check(old, "check")
        self.git("add", ".")
        self.git("commit", "-qm", "Capture source")
        target_root = self.artifacts / "worktree"
        self.git("worktree", "add", "--detach", str(target_root), "HEAD")
        target = evidence.prepare(target_root, self.base, self.contract, self.requirements, self.artifacts / "transferred")
        moved = evidence.transfer_check(old, target, check, self.transfer_assessment(old, target))
        self.assertTrue(evidence.validate_check(moved, evidence.load_record(target), self.plan["checks"][0]))
        (target_root / "app.txt").chmod(0o755)
        changed = evidence.prepare(target_root, self.base, self.contract, self.requirements, self.artifacts / "mode-change")
        with self.assertRaisesRegex(ValueError, "content differs"):
            evidence.transfer_check(old, changed, check, self.transfer_assessment(old, changed))

    def test_transfer_rejects_changed_dependency_context_and_missing_assessment(self):
        self.command("print('pass')")
        old = self.prepare()
        check = evidence.run_check(old, "check")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target")
        assessment = self.transfer_assessment(old, target)
        data = json.loads(assessment.read_text())
        del data["base_interactions"]
        assessment.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "base_interactions"):
            evidence.transfer_check(old, target, check, assessment)
        new_requirements = self.artifacts / "new-requirements.json"
        changed_plan = copy.deepcopy(self.plan)
        changed_plan["context"]["dependencies"] = "different installed packages"
        new_requirements.write_text(json.dumps(changed_plan))
        changed = evidence.prepare(self.root, self.base, self.contract, new_requirements, self.artifacts / "dependency-change")
        with self.assertRaisesRegex(ValueError, "context differs"):
            evidence.transfer_check(old, changed, check, self.transfer_assessment(old, changed))

    def test_transfer_rejects_generated_content_and_symlink_changes(self):
        self.command("print('pass')")
        generated = self.root / "generated.txt"
        generated.write_text("first generation")
        link = self.root / "current.txt"
        link.symlink_to("app.txt")
        old = self.prepare()
        check = evidence.run_check(old, "check")
        generated.write_text("changed generation")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "generated-change")
        with self.assertRaisesRegex(ValueError, "content differs"):
            evidence.transfer_check(old, target, check, self.transfer_assessment(old, target))
        generated.write_text("first generation")
        link.unlink()
        link.symlink_to("generated.txt")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "link-change")
        with self.assertRaisesRegex(ValueError, "content differs"):
            evidence.transfer_check(old, target, check, self.transfer_assessment(old, target))

    def test_transfer_rejects_failed_checks(self):
        self.command("raise SystemExit(1)")
        old = self.prepare()
        check = evidence.run_check(old, "check")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target")
        with self.assertRaisesRegex(ValueError, "passing"):
            evidence.transfer_check(old, target, check, self.transfer_assessment(old, target))



if __name__ == "__main__":
    unittest.main()
