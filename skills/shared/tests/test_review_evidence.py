#!/usr/bin/env python3
"""Regression checks for source binding and review readiness."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
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

    def scoped_review(self, *, checks=False, findings=None, observations=None):
        content = self.artifacts / "prospective-notes.txt"
        content.write_text("Independent meeting notes.\n")
        self.plan["review_scope"] = {
            "inputs": ["app.txt"], "complete": True,
            "reason": "The fixture reads only app.txt; notes have no readers or build role.",
            "changes": [{"path": "notes.txt", "content": evidence.evidence_link(content),
                         "reason": "These exact notes do not change behavior or acceptance."}],
        }
        if checks:
            self.command("print('pass')")
            self.plan["checks"][0]["fresh"] = True
        self.requirements.write_text(json.dumps(self.plan))
        original = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                    self.artifacts / "review", artifact_dir=self.artifacts)
        result = self.response(original)
        result["scope_approval"] = evidence.digest(self.plan["review_scope"])
        if checks:
            result["checks"] = {"check": str(evidence.run_check(original, "check"))}
        result["findings"] = findings or []
        result["observations"] = observations or []
        self.record(original, result)
        return original, content

    def checkpoint_inputs(self, original, content, *, run_checks=True, retain_findings=True):
        (self.root / "notes.txt").write_bytes(content.read_bytes())
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "target",
                                  artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"] if retain_findings else [])
        if run_checks:
            for row in self.plan["checks"]:
                evidence.run_check(target, row["id"])
        packet = evidence.prepare_packet(target, self.artifacts / "packet.json", observations=[])
        assessment = self.transfer_assessment(original, target)
        return target, assessment, packet

    def batch_review(self, *, finding=False, fresh_checks=True, final_check=False, task_failure=False,
                     reuse_check=False, reuse_observation=False, observation_inputs=None, change_app=True, new_context=None, unchanged_source=False):
        self.command("from pathlib import Path; assert not Path('schema.sql').exists()" if task_failure else "print('verified')")
        self.plan["checks"][0]["fresh"] = not reuse_check
        if reuse_check:
            self.plan["checks"][0]["inputs"] = ["app.txt"]
            self.plan["checks"].append({"id": "fresh-check", "command": [sys.executable, "-c", "print('fresh')"],
                                        "cwd": ".", "timeout_seconds": 5, "fresh": True})
        self.plan["observations"] = ["browser"]
        if observation_inputs is not None:
            self.plan["observation_inputs"] = {"browser": observation_inputs}
        originals = {}
        for task_id in ("T1", "T2"):
            contract = self.artifacts / f"{task_id}.md"
            contract.write_text(f"# {task_id}: Acceptance\nRequired behavior passes.\n")
            requirements = self.artifacts / f"{task_id}.requirements.json"
            requirements.write_text(json.dumps(self.plan))
            path = evidence.prepare(self.root, self.base, contract, requirements,
                                    self.artifacts / task_id / "old", artifact_dir=self.artifacts)
            capture = self.artifacts / f"{task_id}.old-browser.txt"
            capture.write_text("Actual old observation")
            response = self.response(path)
            response["checks"] = {check["id"]: str(evidence.run_check(path, check["id"])) for check in self.plan["checks"]}
            response["observations"] = [{"id": "browser", "result": "pass", "evidence": [evidence.evidence_link(capture)]}]
            if finding and task_id == "T1":
                response["findings"] = [{"id": "T1-P2-1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Contract failure."}]
            self.record(path, response)
            originals[task_id] = path
        if not unchanged_source:
            if change_app:
                (self.root / "app.txt").write_text("integrated behavior\n")
            (self.root / "schema.sql").write_text("new schema\n")
            self.git("add", ".")
            self.git("commit", "-qm", "Combined fixture")
        base = self.git("rev-parse", "HEAD").strip()
        rows = {}
        if new_context is not None:
            self.plan["context"] = new_context
        for task_id, old in originals.items():
            previous = evidence.load_record(old)
            target_requirements = previous["requirements"]["path"]
            if new_context is not None:
                target_requirements = self.artifacts / f"{task_id}.new-requirements.json"
                target_requirements.write_text(json.dumps(self.plan))
            target = evidence.prepare(self.root, base, previous["contract"]["path"], target_requirements,
                                      self.artifacts / task_id / "current", artifact_dir=self.artifacts,
                                      previous_reviews=[old.parent / "review.json"])
            if fresh_checks:
                for check in self.plan["checks"]:
                    if reuse_check == "direct" and check["id"] == "check":
                        continue
                    if reuse_check and check["id"] == "check":
                        assessment = self.artifacts / f"{task_id}.transfer.json"
                        assessment.write_bytes(self.transfer_assessment(old, target).read_bytes())
                        evidence.transfer_check(old, target, old.parent / "checks/check/result.json", assessment)
                    else:
                        evidence.run_check(target, check["id"])
            capture = self.artifacts / f"{task_id}.{'old' if reuse_observation else 'current'}-browser.txt"
            if not reuse_observation:
                capture.write_text("Actual current observation")
            checks = ({"check": str(old.parent / "checks/check/result.json"),
                       "fresh-check": str(target.parent / "checks/fresh-check/result.json")} if reuse_check == "direct" else None)
            packet = evidence.prepare_packet(target, self.artifacts / f"{task_id}.packet.json", checks=checks,
                                             observations=[{"id": "browser", "result": "pass", "evidence": [str(capture)]}])
            rows[task_id] = {"snapshot": evidence.evidence_link(target), "prior_review": evidence.evidence_link(old.parent / "review.json"),
                             "evidence_packet": evidence.evidence_link(packet)}
        source = evidence.load_record(target)
        capture = self.artifacts / "environment-capture.txt"
        capture.write_text("Captured runtime, installed dependencies, schema, configuration, and base interaction checks.")
        environment = {"to_source_id": source["source_id"], "context_id": evidence.digest(evidence.context_identity(self.plan["context"]))}
        for key in ("runtime", "dependencies", "external_state", "base_interactions", "configuration", "schema"):
            environment[key] = {"reason": f"Inspected {key} for combined state", "evidence": [evidence.evidence_link(capture)]}
        environment_path = self.artifacts / "environment.json"
        environment_path.write_text(json.dumps(environment))
        plan = {"context": self.plan["context"], "checks": [], "observations": [], "exclusions": {},
                "batch": {"tasks": rows, "interactions": ["schema and task behavior"], "environment": evidence.evidence_link(environment_path)}}
        if final_check:
            plan["checks"] = [{"id": "feature", "command": [sys.executable, "-c", "raise SystemExit(1)"], "cwd": ".", "timeout_seconds": 5, "fresh": True}]
        contract = self.artifacts / "batch-contract.md"
        contract.write_text("Review retained task contracts and their combined interactions for dependency release.\n")
        requirements = self.artifacts / "batch-requirements.json"
        requirements.write_text(json.dumps(plan))
        path = evidence.prepare(self.root, base, contract, requirements, self.artifacts / "batch", artifact_dir=self.artifacts,
                                previous_reviews=[old.parent / "review.json" for old in originals.values()])
        response = self.response(path)
        if final_check:
            response["checks"] = {"feature": str(evidence.run_check(path, "feature"))}
        contract = evidence.response_contract(path)
        response.update(batch_approval=contract["batch_approval"],
                        endorsements={key: {"snapshot_sha256": row["snapshot_sha256"], "coverage_paths": row["coverage_paths"],
                                            "acceptance": "Assessed all task requirements on the combined state."}
                                      for key, row in contract["endorsement_contracts"].items()},
                        interactions={key: "Assessed schema compatibility and both task callers." for key in plan["batch"]["interactions"]},
                        findings=list(contract["prior_findings"].values()))
        return path, originals, response, base

    def test_batch_current_review_endorses_two_contracts_after_source_base_and_index_changes(self):
        path, originals, response, base = self.batch_review()
        self.record(path, response)
        for key, old in originals.items():
            with self.assertRaisesRegex(ValueError, "stale"):
                evidence.assess(old, self.base)
            result = evidence.assess_batch(evidence.evidence_link(path), key, old, base)
            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["task_ids"], ["T1", "T2"])
        self.assertEqual(len(list((self.artifacts / "batch").glob("review.json"))), 1)

    def test_batch_requires_fresh_task_checks_and_its_own_combined_gate(self):
        with self.assertRaises(OSError):
            self.batch_review(fresh_checks=False)

    def test_batch_cannot_use_task_passes_to_override_failed_final_combined_check(self):
        path, originals, response, base = self.batch_review(final_check=True)
        self.record(path, response)
        assessment = evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)
        self.assertEqual(assessment["status"], "needs-work")
        self.assertEqual(assessment["failed_checks"], ["feature"])

    def test_batch_retains_failed_current_task_checks(self):
        path, originals, response, base = self.batch_review(task_failure=True)
        self.record(path, response)
        assessment = evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)
        self.assertEqual(assessment["status"], "needs-work")
        self.assertEqual(assessment["failed_checks"], ["T1:check", "T2:check"])

    def test_batch_mixes_valid_transfer_fresh_check_and_unchanged_scoped_observation(self):
        path, originals, response, base = self.batch_review(reuse_check=True, reuse_observation=True,
                                                            observation_inputs=["app.txt"], change_app=False)
        self.record(path, response)
        with evidence.validation_context():
            self.assertEqual(evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)["status"], "ready")
        row = evidence.load_record(path)["requirements"]["value"]["batch"]["tasks"]["T1"]
        packet = evidence.load_record(row["evidence_packet"]["path"])
        self.assertIn("transfer", evidence.load_record(packet["checks"]["check"]))
        self.assertNotIn("transfer", evidence.load_record(packet["checks"]["fresh-check"]))
        target = row["snapshot"]["path"]
        old = originals["T1"]
        with self.assertRaisesRegex(ValueError, "fresh checks cannot transfer"):
            evidence.transfer_check(old, target, old.parent / "checks/fresh-check/result.json", self.transfer_assessment(old, target))

    def test_batch_mixes_direct_unchanged_check_reuse_and_required_fresh_check(self):
        path, originals, response, base = self.batch_review(reuse_check="direct", reuse_observation=True,
                                                            observation_inputs=["app.txt"], unchanged_source=True)
        self.record(path, response)
        with evidence.validation_context():
            self.assertEqual(evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)["status"], "ready")
        task = evidence.load_record(path)["requirements"]["value"]["batch"]["tasks"]["T1"]
        packet = evidence.load_record(task["evidence_packet"]["path"])
        self.assertEqual(packet["checks"]["check"], str(originals["T1"].parent / "checks/check/result.json"))
        self.assertEqual(evidence.load_record(packet["checks"]["fresh-check"])["snapshot_sha256"], task["snapshot"]["sha256"])

    def test_batch_check_transfer_rejects_changed_declared_dependency(self):
        with self.assertRaisesRegex(ValueError, "transfer check inputs differ"):
            self.batch_review(reuse_check=True)

    def test_batch_observation_reuse_rejects_affected_inputs(self):
        with self.assertRaisesRegex(ValueError, "fresh observation browser: declared observation inputs changed"):
            self.batch_review(reuse_observation=True, observation_inputs=["app.txt"])

    def test_batch_observation_reuse_rejects_unknown_scope_after_source_change(self):
        with self.assertRaisesRegex(ValueError, "fresh observation browser: source changed without"):
            self.batch_review(reuse_observation=True, change_app=False)

    def test_batch_observation_reuse_rejects_environment_identity_change(self):
        with self.assertRaisesRegex(ValueError, "fresh observation browser: environment identity changed"):
            self.batch_review(reuse_observation=True, observation_inputs=["app.txt"], change_app=False,
                              new_context={"runtime": "changed"})

    def next_batch_with_observations(self, *, use_original=False):
        first, originals, response, base = self.batch_review(observation_inputs=["app.txt"])
        self.record(first, response)
        original_batch = evidence.load_record(first)
        plan = copy.deepcopy(original_batch["requirements"]["value"])
        (self.root / "unrelated.txt").write_text("Later independent content")
        for key, row in plan["batch"]["tasks"].items():
            old_target = evidence.load_record(row["snapshot"]["path"])
            target = evidence.prepare(self.root, base, old_target["contract"]["path"], old_target["requirements"]["path"],
                                      self.artifacts / key / "next", artifact_dir=self.artifacts,
                                      previous_reviews=[row["prior_review"]["path"]])
            evidence.run_check(target, "check")
            observations = (evidence.load_record(row["prior_review"]["path"])["result"]["observations"] if use_original else
                            evidence.load_record(row["evidence_packet"]["path"])["observations"])
            packet = evidence.prepare_packet(target, self.artifacts / f"{key}.next-packet.json", observations=observations)
            row["snapshot"], row["evidence_packet"] = evidence.evidence_link(target), evidence.evidence_link(packet)
        environment = evidence.read_json(plan["batch"]["environment"]["path"])
        environment["to_source_id"] = evidence.load_record(target)["source_id"]
        environment_path = self.artifacts / "next-environment.json"
        environment_path.write_text(json.dumps(environment))
        plan["batch"]["environment"] = evidence.evidence_link(environment_path)
        requirements = self.artifacts / "next-batch-requirements.json"
        requirements.write_text(json.dumps(plan))
        second = evidence.prepare(self.root, base, original_batch["contract"]["path"], requirements,
                                  self.artifacts / "next-batch", artifact_dir=self.artifacts,
                                  previous_reviews=[row["path"] for row in original_batch["previous_reviews"]] + [first.parent / "review.json"])
        contract = evidence.response_contract(second)
        result = self.response(second)
        result.update(batch_approval=contract["batch_approval"], interactions=response["interactions"],
                      endorsements={key: {"snapshot_sha256": row["snapshot_sha256"], "coverage_paths": row["coverage_paths"],
                                          "acceptance": "Retained task acceptance and affected callers remain valid."}
                                    for key, row in contract["endorsement_contracts"].items()})
        self.record(second, result)
        return first, second, originals, base

    def test_batch_observations_reuse_latest_endorsed_state_after_unrelated_change(self):
        first, second, originals, base = self.next_batch_with_observations()
        with evidence.validation_context():
            result = evidence.assess_batch(evidence.evidence_link(second), "T1", originals["T1"], base)
            contract = evidence.response_contract(second)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(contract["endorsement_contracts"]["T1"]["fresh_observations"], {})
        self.assertEqual(contract["endorsement_contracts"]["T1"]["observation_baseline"], evidence.evidence_link(first.parent / "review.json"))

    def test_batch_cannot_reuse_capture_older_than_latest_endorsed_state(self):
        with self.assertRaisesRegex(ValueError, "latest endorsed capture"):
            self.next_batch_with_observations(use_original=True)

    def test_batch_rejects_partial_forged_task_endorsements_and_interaction_coverage(self):
        path, _, response, _ = self.batch_review()
        snapshot = evidence.load_record(path)
        mutations = [lambda r: r["endorsements"].pop("T2"),
                     lambda r: r["endorsements"].update(T3=r["endorsements"]["T2"]),
                     lambda r: r["endorsements"]["T1"].update(snapshot_sha256="forged"),
                     lambda r: r["endorsements"]["T1"].update(coverage_paths=[]),
                     lambda r: r.update(batch_approval="forged"),
                     lambda r: r.update(interactions={})]
        for change in mutations:
            broken = copy.deepcopy(response)
            change(broken)
            with self.assertRaises(ValueError):
                evidence.validate_result(broken, snapshot, path)

    def test_batch_keeps_prior_findings_and_cannot_pass_with_unresolved_findings(self):
        path, originals, response, base = self.batch_review(finding=True)
        broken = {**response, "findings": []}
        with self.assertRaisesRegex(ValueError, "prior findings were dropped"):
            self.record(path, broken)
        self.record(path, response)
        self.assertEqual(evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)["status"], "needs-work")

    def test_dense_review_ancestry_validates_each_immutable_node_once(self):
        links = []
        for number in range(16):
            directory = self.artifacts / f"history-{number}"
            snapshot = evidence.write_record(directory / "snapshot.json", {
                "source": {}, "source_id": evidence.digest({}), "previous_reviews": list(links),
            })
            review = evidence.write_record(directory / "review.json", {
                "snapshot_path": str(snapshot), "snapshot_sha256": evidence.file_hash(snapshot),
            })
            links.append(evidence.evidence_link(review))
        for count in (8, 12, 16):
            with evidence.validation_context():
                with mock.patch.object(evidence, "load_record", wraps=evidence.load_record) as loads:
                    ancestors = evidence.review_ancestors(links[count - 1])
                    self.assertEqual(evidence.review_ancestors(links[count - 1]), ancestors)
            self.assertEqual(ancestors, {(link["path"], link["sha256"]) for link in links[:count - 1]})
            self.assertLessEqual(loads.call_count, 2 * count)

    def test_review_ancestry_rejects_active_cycle_and_clears_traversal_state(self):
        snapshot = evidence.write_record(self.artifacts / "cycle/snapshot.json", {
            "source": {}, "source_id": evidence.digest({}), "previous_reviews": [],
        })
        review = evidence.write_record(self.artifacts / "cycle/review.json", {
            "snapshot_path": str(snapshot), "snapshot_sha256": evidence.file_hash(snapshot),
        })
        link = evidence.evidence_link(review)
        load = evidence.load_record
        def cyclic_snapshot(path):
            value = copy.deepcopy(load(path))
            if Path(path) == snapshot:
                value["previous_reviews"] = [link]
            return value
        with mock.patch.object(evidence, "load_record", side_effect=cyclic_snapshot):
            with self.assertRaisesRegex(ValueError, "cyclic or excessive review ancestry"):
                evidence.review_ancestors(link)
        self.assertEqual(evidence.review_ancestors(link), set())

    def test_batch_history_uses_verified_descendant_resolution_across_three_reviews(self):
        first, originals, response, base = self.batch_review(finding=True)
        response["findings"][0].update(status="fixed", evidence="Independent current inspection confirms the repair.")
        self.record(first, response)
        snapshot = evidence.load_record(first)
        reviews = [row["path"] for row in snapshot["previous_reviews"]] + [first.parent / "review.json"]
        latest = first
        for number in (2, 3):
            latest = evidence.prepare(self.root, base, snapshot["contract"]["path"], snapshot["requirements"]["path"],
                                      self.artifacts / f"batch-{number}", artifact_dir=self.artifacts, previous_reviews=list(reversed(reviews)))
            current = copy.deepcopy(response)
            current["snapshot_sha256"] = evidence.file_hash(latest)
            current["findings"][0]["evidence"] = f"Independent inspection {number} confirms the repaired interaction."
            self.record(latest, current)
            reviews.append(latest.parent / "review.json")
            self.assertEqual(evidence.assess_batch(evidence.evidence_link(latest), "T1", originals["T1"], base)["status"], "ready")
        self.assertEqual(evidence.response_contract(latest)["prior_findings"]["T1-P2-1"]["status"], "fixed")
        self.assertEqual(len(reviews), 5)

    def test_batch_history_rejects_a_resolution_not_in_the_actual_response(self):
        first, _, response, base = self.batch_review(finding=True)
        self.record(first, response)
        review_path = first.parent / "review.json"
        payload = evidence.load_record(review_path)
        payload["result"]["findings"][0].update(status="fixed", evidence="Forged resolution")
        review_path.write_text(json.dumps({"payload": payload, "sha256": evidence.digest(payload)}))
        snapshot = evidence.load_record(first)
        with self.assertRaisesRegex(ValueError, "result differs from execution"):
            evidence.prepare(self.root, base, snapshot["contract"]["path"], snapshot["requirements"]["path"],
                             self.artifacts / "forged-resolution", artifact_dir=self.artifacts,
                             previous_reviews=[row["path"] for row in snapshot["previous_reviews"]] + [review_path])

    def test_batch_history_rejects_conflicting_unrelated_review_branches(self):
        first, _, response, base = self.batch_review(finding=True)
        response["findings"][0].update(status="fixed", evidence="The reviewed repair passes.")
        self.record(first, response)
        snapshot = evidence.load_record(first)
        other = evidence.prepare(self.root, base, snapshot["contract"]["path"], snapshot["requirements"]["path"],
                                 self.artifacts / "other-branch", artifact_dir=self.artifacts,
                                 previous_reviews=[row["path"] for row in snapshot["previous_reviews"]])
        disputed = copy.deepcopy(response)
        disputed["snapshot_sha256"] = evidence.file_hash(other)
        disputed["findings"][0].update(status="disputed", evidence="A separate branch disputes the repair.")
        self.record(other, disputed)
        with self.assertRaisesRegex(ValueError, "unrelated review branches"):
            evidence.prepare(self.root, base, snapshot["contract"]["path"], snapshot["requirements"]["path"],
                             self.artifacts / "conflict", artifact_dir=self.artifacts,
                             previous_reviews=[first.parent / "review.json", other.parent / "review.json"])

    def test_batch_accepts_new_findings_on_retained_paths_after_base_change(self):
        path, originals, response, base = self.batch_review()
        self.assertEqual(evidence.load_record(path)["source"]["changed_paths"], [])
        response["findings"] = [{"id": "integration-P2-1", "path": "schema.sql", "severity": "P2", "status": "open", "evidence": "New interaction defect."}]
        self.record(path, response)
        assessment = evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)
        self.assertEqual(assessment["status"], "needs-work")
        self.assertEqual(assessment["open_findings"], ["integration-P2-1"])
        snapshot = evidence.load_record(path)
        fixed = evidence.prepare(self.root, base, snapshot["contract"]["path"], snapshot["requirements"]["path"],
                                 self.artifacts / "batch-fixed", artifact_dir=self.artifacts,
                                 previous_reviews=[row["path"] for row in snapshot["previous_reviews"]] + [path.parent / "review.json"])
        resolved = copy.deepcopy(response)
        resolved["snapshot_sha256"] = evidence.file_hash(fixed)
        resolved["findings"][0].update(status="rejected", evidence="Independent review confirms the schema preserves the required interaction.")
        self.record(fixed, resolved)
        self.assertEqual(evidence.assess_batch(evidence.evidence_link(fixed), "T1", originals["T1"], base)["status"], "ready")

    def test_batch_rejects_later_dependency_configuration_schema_runtime_and_index_drift(self):
        path, originals, response, base = self.batch_review()
        self.record(path, response)
        for name in ("lockfile", "config.json", "schema.sql", "runtime.txt", "app.txt"):
            with self.subTest(name=name):
                source = self.root / name
                before = source.read_bytes() if source.exists() else None
                source.write_text("changed after review")
                with self.assertRaisesRegex(ValueError, "stale"):
                    evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)
                if before is None:
                    source.unlink()
                else:
                    source.write_bytes(before)
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], self.base)
        self.git("update-index", "--chmod=+x", "app.txt")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess_batch(evidence.evidence_link(path), "T1", originals["T1"], base)

    def test_batch_rechecks_task_logs_and_fresh_captures(self):
        path, _, response, _ = self.batch_review()
        snapshot = evidence.load_record(path)
        row = snapshot["requirements"]["value"]["batch"]["tasks"]["T1"]
        packet_path = Path(row["evidence_packet"]["path"])
        packet = evidence.load_record(packet_path)
        check = evidence.load_record(packet["checks"]["check"])
        log = Path(check["logs"][0]["path"])
        log.write_text("altered log")
        with self.assertRaisesRegex(ValueError, "log checksum"):
            self.record(path, response)

    def test_batch_rejects_changed_contract_missing_environment_and_changed_task_set(self):
        path, _, _, _ = self.batch_review()
        snapshot = evidence.load_record(path)
        changed = copy.deepcopy(snapshot)
        changed["requirements"]["value"]["batch"]["tasks"]["T3"] = changed["requirements"]["value"]["batch"]["tasks"].pop("T2")
        # A changed task set cannot retain the original response digest.
        original_contract = evidence.batch_response_contract(snapshot)
        self.assertNotEqual(original_contract["batch_approval"], evidence.batch_response_contract(changed)["batch_approval"])
        environment = Path(snapshot["requirements"]["value"]["batch"]["environment"]["path"])
        original_environment = environment.read_text()
        value = json.loads(original_environment)
        value.pop("schema")
        environment.write_text(json.dumps(value))
        changed = copy.deepcopy(snapshot)
        changed["requirements"]["value"]["batch"]["environment"] = evidence.evidence_link(environment)
        with self.assertRaisesRegex(ValueError, "fresh schema evidence"):
            evidence.validate_batch(changed)
        environment.write_text(original_environment)
        task_snapshot = evidence.load_record(snapshot["requirements"]["value"]["batch"]["tasks"]["T1"]["snapshot"]["path"])
        Path(task_snapshot["contract"]["path"]).write_text("Changed acceptance")
        with self.assertRaisesRegex(ValueError, "contract changed"):
            evidence.validate_batch(snapshot)

    def test_scoped_checkpoint_releases_dependency_without_a_second_review(self):
        original, content = self.scoped_review(checks=True)
        contract = evidence.response_contract(original)
        self.assertEqual(contract["review_scope"], self.plan["review_scope"])
        self.assertEqual(contract["scope_approval"], evidence.digest(self.plan["review_scope"]))
        target, assessment, packet = self.checkpoint_inputs(original, content)
        path = self.artifacts / "carry.json"
        command = [sys.executable, str(Path(evidence.__file__)), "carry-forward",
                   "--from-snapshot", str(original), "--to-snapshot", str(target),
                   "--assessment", str(assessment), "--packet", str(packet), "--output", str(path)]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["carry_forward"], evidence.evidence_link(path))
        repeated = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual(json.loads(repeated.stdout), json.loads(completed.stdout))
        result = evidence.assess_carry_forward(evidence.evidence_link(path), original, self.base)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["scope"], "dependency-release-only")
        self.assertEqual(result["changed_paths"], ["notes.txt"])
        self.assertFalse((target.parent / "review.json").exists())
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess(original, self.base)
        with self.assertRaises(OSError):
            evidence.assess(target, self.base)

    def test_scoped_checkpoint_requires_explicit_original_reviewer_approval(self):
        original, _ = self.scoped_review()
        response = self.response(original)
        with self.assertRaisesRegex(ValueError, "invalid review result fields"):
            evidence.validate_result(response, evidence.load_record(original), original)
        response["scope_approval"] = "different"
        with self.assertRaisesRegex(ValueError, "reviewer must approve"):
            evidence.validate_result(response, evidence.load_record(original), original)

    def test_legacy_review_cannot_gain_a_scope_after_review(self):
        original = self.prepare()
        self.record(original, self.response(original))
        content = self.artifacts / "prospective-notes.txt"
        content.write_text("Notes")
        target, assessment, packet = self.checkpoint_inputs(original, content)
        with self.assertRaisesRegex(ValueError, "no approved carry forward scope"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")

    def test_scope_rejects_unknown_dependencies_overlap_and_omitted_check_inputs(self):
        _, _ = self.scoped_review()
        invalid = copy.deepcopy(self.plan)
        invalid["review_scope"]["complete"] = False
        with self.assertRaisesRegex(ValueError, "unknown dependencies"):
            evidence.validate_requirements(invalid, self.root.resolve())
        invalid = copy.deepcopy(self.plan)
        invalid["review_scope"]["inputs"].append("notes.txt")
        with self.assertRaisesRegex(ValueError, "overlap"):
            evidence.validate_requirements(invalid, self.root.resolve())
        invalid = copy.deepcopy(self.plan)
        invalid["checks"] = [{"id": "test", "command": ["true"], "cwd": ".", "timeout_seconds": 1,
                              "inputs": ["dependency.txt"]}]
        with self.assertRaisesRegex(ValueError, "omits declared"):
            evidence.validate_requirements(invalid, self.root.resolve())

    def test_scoped_checkpoint_blocks_dependency_and_unlisted_changes(self):
        original, content = self.scoped_review()
        for name in ("app.txt", "config.json", "schema.sql", "runtime.txt", "public-api.txt", "other-notes.txt"):
            with self.subTest(name=name):
                path = self.root / name
                previous = path.read_bytes() if path.exists() else None
                path.write_text("new content")
                target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                          self.artifacts / name,
                                          artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
                packet = evidence.prepare_packet(target, self.artifacts / f"{name}.packet", observations=[])
                with self.assertRaisesRegex(ValueError, "dependency inputs changed|outside the approved scope"):
                    evidence.carry_forward(original, target, self.transfer_assessment(original, target), packet,
                                           self.artifacts / "carry.json")
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)

    def test_scoped_checkpoint_requires_exact_content_and_mode(self):
        original, content = self.scoped_review()
        for label, text, mode in (("text", "Unreviewed notes", 0o644),
                                  ("mode", content.read_text(), 0o755)):
            with self.subTest(label=label):
                notes = self.root / "notes.txt"
                notes.write_text(text)
                notes.chmod(mode)
                target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                          self.artifacts / label, artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
                packet = evidence.prepare_packet(target, self.artifacts / f"{label}.packet", observations=[])
                with self.assertRaisesRegex(ValueError, "exact approved change"):
                    evidence.carry_forward(original, target, self.transfer_assessment(original, target), packet,
                                           self.artifacts / "carry.json")

    def test_checkpoint_rechecks_integrity_and_current_source(self):
        original, content = self.scoped_review(checks=True)
        target, assessment, packet = self.checkpoint_inputs(original, content)
        path = evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        link = evidence.evidence_link(path)
        (self.root / "notes.txt").write_text("Later change")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess_carry_forward(link, original, self.base)
        (self.root / "notes.txt").write_bytes(content.read_bytes())
        self.git("add", "notes.txt")
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.assess_carry_forward(link, original, self.base)
        self.git("reset", "-q", self.base, "--", "notes.txt")
        (target.parent / "checks/check/stdout.log").write_text("Changed capture")
        with self.assertRaisesRegex(ValueError, "log checksum"):
            evidence.assess_carry_forward(link, original, self.base)

    def test_checkpoint_rejects_source_changes_during_packet_validation(self):
        original, content = self.scoped_review()
        target, assessment, packet = self.checkpoint_inputs(original, content)
        path = evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        load_packet = evidence.load_packet

        def change_after_validation(*args, **kwargs):
            result = load_packet(*args, **kwargs)
            (self.root / "app.txt").write_text("Changed during validation")
            return result

        with mock.patch.object(evidence, "load_packet", side_effect=change_after_validation):
            with self.assertRaisesRegex(ValueError, "stale"):
                evidence.assess_carry_forward(evidence.evidence_link(path), original, self.base)

    def test_checkpoint_rejects_nonobject_environment_assessment(self):
        original, content = self.scoped_review()
        target, assessment, packet = self.checkpoint_inputs(original, content)
        assessment.write_text("[]")
        with self.assertRaisesRegex(ValueError, "assessment must be an object"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        result = subprocess.run([sys.executable, str(Path(evidence.__file__)), "carry-forward",
                                 "--from-snapshot", str(original), "--to-snapshot", str(target),
                                 "--assessment", str(assessment), "--packet", str(packet),
                                 "--output", str(self.artifacts / "carry.json")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertIn("assessment must be an object", json.loads(result.stdout)["error"])

    def test_checkpoint_cannot_clear_blocking_findings_or_drop_prior_review(self):
        finding = {"id": "F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Still broken."}
        original, content = self.scoped_review(findings=[finding])
        target, assessment, packet = self.checkpoint_inputs(original, content)
        with self.assertRaisesRegex(ValueError, "original review is not ready"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")

    def test_checkpoint_requires_finding_binding_even_for_resolved_findings(self):
        original, content = self.scoped_review()
        target, assessment, packet = self.checkpoint_inputs(original, content, retain_findings=False)
        with self.assertRaisesRegex(ValueError, "retain its original findings"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")

    def test_checkpoint_cannot_reuse_a_required_fresh_check(self):
        original, content = self.scoped_review(checks=True)
        (self.root / "notes.txt").write_bytes(content.read_bytes())
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target",
                                  artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
        with self.assertRaisesRegex(ValueError, "check source does not match"):
            evidence.prepare_packet(target, self.artifacts / "packet.json",
                                    checks={"check": str(original.parent / "checks/check/result.json")}, observations=[])
        with self.assertRaisesRegex(ValueError, "fresh checks cannot transfer"):
            evidence.transfer_check(original, target, original.parent / "checks/check/result.json",
                                    self.transfer_assessment(original, target))

    def test_checkpoint_rejects_environment_or_scope_evidence_changes(self):
        original, content = self.scoped_review()
        target, assessment, packet = self.checkpoint_inputs(original, content)
        data = json.loads(assessment.read_text())
        del data["runtime"]
        assessment.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "runtime evidence"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        assessment = self.transfer_assessment(original, target)
        content.write_text("Different proposed content")
        with self.assertRaisesRegex(ValueError, "scoped change content checksum"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")

    def test_checkpoint_requires_fresh_unscoped_observations(self):
        self.plan["observations"] = ["browser"]
        capture = self.artifacts / "browser-before.txt"
        capture.write_text("Observed passing browser flow before notes.")
        observation = {"id": "browser", "result": "pass", "evidence": [evidence.evidence_link(capture)]}
        original, content = self.scoped_review(observations=[observation])
        (self.root / "notes.txt").write_bytes(content.read_bytes())
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target",
                                  artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
        packet = evidence.prepare_packet(target, self.artifacts / "old-observation.json", observations=[observation])
        assessment = self.transfer_assessment(original, target)
        with self.assertRaisesRegex(ValueError, "fresh observation captures"):
            evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        fresh = self.artifacts / "browser-after.txt"
        fresh.write_text("Observed passing browser flow on target.")
        observation["evidence"] = [evidence.evidence_link(fresh)]
        packet = evidence.prepare_packet(target, self.artifacts / "new-observation.json", observations=[observation])
        checkpoint = evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        self.assertEqual(evidence.assess_carry_forward(evidence.evidence_link(checkpoint), original, self.base)["status"], "ready")

    def test_checkpoint_rejects_new_environment_contract_and_base(self):
        original, content = self.scoped_review()
        (self.root / "notes.txt").write_bytes(content.read_bytes())
        different_plan = self.artifacts / "different-requirements.json"
        value = copy.deepcopy(self.plan)
        value["context"]["runtime"] = "Different runtime"
        different_plan.write_text(json.dumps(value))
        different_contract = self.artifacts / "different-contract.md"
        different_contract.write_text("A different acceptance contract")
        self.git("commit", "--allow-empty", "-qm", "Changed base")
        for label, contract, requirements, base in (
            ("environment", self.contract, different_plan, self.base),
            ("contract", different_contract, self.requirements, self.base),
            ("base", self.contract, self.requirements, "HEAD"),
        ):
            with self.subTest(label=label):
                target = evidence.prepare(self.root, base, contract, requirements, self.artifacts / label,
                                          artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
                packet = evidence.prepare_packet(target, self.artifacts / f"{label}.packet", observations=[])
                with self.assertRaisesRegex(ValueError, "contract or requirements changed|base, index"):
                    evidence.carry_forward(original, target, self.transfer_assessment(original, target), packet,
                                           self.artifacts / "carry.json")

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

    def test_packet_hashes_observations_and_preserves_reviewer_response(self):
        self.command("print('pass')")
        self.plan["observations"] = ["save"]
        snapshot = self.prepare()
        evidence.run_check(snapshot, "check")
        capture = self.artifacts / "browser.json"
        capture.write_text('{"saved": true}')
        packet = evidence.prepare_packet(snapshot, self.artifacts / "packet.json", observations=[
            {"id": "save", "result": "pass", "evidence": [str(capture)]}])
        response = self.response(snapshot)
        del response["checks"], response["observations"]
        response["evidence_packet"] = evidence.evidence_link(packet)
        review = self.record(snapshot, response)
        self.assertEqual(evidence.assess(snapshot, self.base)["status"], "ready")
        self.assertEqual(json.loads(evidence.load_record(review)["execution"]["agent_message"]), response)
        capture.write_text('{"saved": false}')
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            evidence.assess(snapshot, self.base)

    def test_recheck_packet_replaces_prior_evidence_and_retains_findings(self):
        self.command("print('old check')")
        self.plan["observations"] = ["old-flow"]
        original = self.prepare()
        check = evidence.run_check(original, "check")
        capture = self.artifacts / "browser.txt"
        capture.write_text("Observed both flows")
        first = self.response(original)
        first["checks"] = {"check": str(check)}
        first["observations"] = [{"id": "old-flow", "result": "pass",
                                  "evidence": [evidence.evidence_link(capture)]}]
        first["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2",
                              "status": "open", "evidence": "Unresolved defect."}]
        previous = self.record(original, first)

        self.plan["checks"][0]["id"] = "current-check"
        self.plan["observations"] = ["current-flow"]
        self.requirements.write_text(json.dumps(self.plan))
        current, delta = self.recheck(original, previous)
        evidence.run_check(current, "current-check")
        packet = evidence.prepare_packet(current, self.artifacts / "current-packet.json", observations=[
            {"id": "current-flow", "result": "pass", "evidence": [str(capture)]}])
        del delta["checks"], delta["observations"]
        delta["evidence_packet"] = evidence.evidence_link(packet)
        review = self.record(current, delta)
        recorded = evidence.load_record(review)
        self.assertEqual(set(recorded["result"]["checks"]), {"current-check"})
        self.assertEqual([row["id"] for row in recorded["result"]["observations"]], ["current-flow"])
        self.assertEqual(recorded["result"]["findings"], first["findings"])
        self.assertEqual(json.loads(recorded["execution"]["agent_message"]), delta)
        self.assertEqual(evidence.assess(current, self.base)["status"], "needs-work")

    def test_packet_rejects_missing_observations_before_dispatch(self):
        self.plan["observations"] = ["save", "denied"]
        snapshot = self.prepare()
        with self.assertRaisesRegex(ValueError, "observations are missing"):
            evidence.prepare_packet(snapshot, self.artifacts / "packet.json", observations=[])
        self.assertFalse((self.artifacts / "packet.json").exists())
        self.assertEqual(evidence.response_contract(snapshot)["fresh_observation_ids"], ["denied", "save"])

    def test_packet_does_not_correct_a_supplied_bad_hash_or_infer_pass(self):
        self.plan["observations"] = ["save"]
        snapshot = self.prepare()
        capture = self.artifacts / "browser.txt"
        capture.write_text("No connection")
        row = {"id": "save", "result": "skipped", "evidence": [{"path": str(capture), "sha256": "wrong"}]}
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            evidence.prepare_packet(snapshot, self.artifacts / "packet.json", observations=[row])
        row["evidence"] = [str(capture)]
        packet = evidence.prepare_packet(snapshot, self.artifacts / "packet.json", observations=[row])
        response = self.response(snapshot)
        del response["checks"], response["observations"]
        response["evidence_packet"] = evidence.evidence_link(packet)
        self.record(snapshot, response)
        self.assertEqual(evidence.assess(snapshot, self.base)["failed_observations"], ["save"])

    def test_context_notes_do_not_invalidate_observations_but_identity_does(self):
        self.plan["context"] = {"version": 2, "identity": {"runtime": "one"}, "notes": "First review"}
        self.plan["observations"] = ["save"]
        original = self.prepare()
        first = self.response(original)
        capture = self.artifacts / "browser.txt"
        capture.write_text("Saved and reloaded")
        first["observations"] = [{"id": "save", "result": "pass", "evidence": [evidence.evidence_link(capture)]}]
        prior = self.record(original, first)
        for name, identity in [("notes", "one"), ("runtime", "two")]:
            plan = copy.deepcopy(self.plan)
            plan["context"].update(identity={"runtime": identity}, notes="Correction explained")
            requirements = self.artifacts / (name + ".json")
            requirements.write_text(json.dumps(plan))
            current = evidence.prepare(self.root, self.base, self.contract, requirements, self.artifacts / name, previous_reviews=[prior])
            delta = {"mode": "recheck", "snapshot_sha256": evidence.file_hash(current), "previous_review": evidence.evidence_link(prior),
                     "reuse_assessment": "Environment and unchanged behavior inspected.", "affected_paths": [], "coverage": [],
                     "findings": [], "checks": {}, "observations": [], "summary": "No new defect."}
            if identity == "one":
                self.record(current, delta)
                self.assertEqual(evidence.assess(current, self.base)["status"], "ready")
                self.assertEqual(evidence.response_contract(current)["fresh_observation_ids"], [])
            else:
                with self.assertRaisesRegex(ValueError, "fresh observations"):
                    self.record(current, delta)
                self.assertEqual(evidence.response_contract(current)["fresh_observation_ids"], ["save"])

    def test_scoped_check_transfer_reuses_only_declared_unchanged_inputs(self):
        self.command("print('pass')")
        self.plan["checks"][0]["inputs"] = ["app.txt"]
        original = self.prepare()
        check = evidence.run_check(original, "check")
        (self.root / "unrelated.txt").write_text("new")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target")
        moved = evidence.transfer_check(original, target, check, self.transfer_assessment(original, target))
        self.assertTrue(evidence.validate_check(moved, evidence.load_record(target), self.plan["checks"][0]))
        (self.root / "app.txt").write_text("changed dependency")
        changed = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "changed")
        with self.assertRaisesRegex(ValueError, "inputs differ"):
            evidence.transfer_check(original, changed, check, self.transfer_assessment(original, changed))

    def test_observation_dependencies_require_fresh_evidence(self):
        self.plan["observations"] = ["save"]
        self.plan["observation_inputs"] = {"save": ["app.txt"]}
        original = self.prepare()
        before = evidence.load_record(original)
        (self.root / "app.txt").write_text("changed behavior")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements, self.artifacts / "target")
        self.assertEqual(evidence.fresh_observations(before, evidence.load_record(target)), {"save"})

    def test_input_scopes_reject_empty_directory_and_traversal(self):
        self.command("print('pass')")
        for inputs in ([], ["."], ["../outside"], ["app.txt", "app.txt"]):
            self.plan["checks"][0]["inputs"] = inputs
            with self.assertRaises(ValueError):
                self.prepare()

    def test_completion_preserves_review_verdict_and_is_idempotent(self):
        import run_state
        snapshot = self.prepare()
        response = self.response(snapshot)
        response["findings"] = [{"id": "F1", "path": "app.txt", "severity": "P2", "status": "open", "evidence": "Observed defect."}]
        route = {"id": "reviewer", "task_id": "T1", "role": "reviewer", "model": "fixture", "effort": "high", "input_path": "../records/task.md"}
        plan = self.artifacts / "route-plan.json"
        plan.write_text(json.dumps({"approval": {"status": "approved"}, "routes": [route]}))
        state = {}
        run_state.initialize(state, plan, "run", {"total_role_calls": 1, "reviewer": 1})
        run_state.reserve(state, "reviewer", "call-1", self.contract, "review", review_snapshot=snapshot)
        receipt = self.artifacts / "receipt.json"
        receipt.write_text(json.dumps({"success": True, "call_id": "call-1", "input_revision": run_state.sha(self.contract),
            "configured_model": "fixture", "configured_effort": "high", "context_id": "review-context", "agent_message": json.dumps(response)}))
        with mock.patch.object(evidence, "assess", side_effect=OSError("interrupted after writing review")):
            with self.assertRaises(OSError):
                run_state.complete(state, "call-1", receipt)
        self.assertEqual(state["call_ledger"]["calls"]["call-1"]["status"], "pending")
        self.assertEqual(state["steps"], [])
        self.assertTrue((snapshot.parent / "review.json").exists())
        result = run_state.complete(state, "call-1", receipt)
        self.assertEqual(state["call_ledger"]["calls"]["call-1"]["review"], result["review"])
        self.assertEqual(result["review_status"], "needs-work")
        self.assertEqual(result, run_state.complete(state, "call-1", receipt))
        self.assertEqual(len(state["steps"]), 1)
        state_path = self.artifacts / "run-state.json"
        run_state.atomic_write(state_path, state)
        proc = subprocess.run([sys.executable, run_state.__file__, "--state", str(state_path),
                               "complete", "--call", "call-1", "--receipt", str(receipt)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        output = json.loads(proc.stdout)
        self.assertEqual(output["execution_status"], "completed")
        self.assertEqual(output["review_status"], "needs-work")
        self.assertNotIn("assessment", output)
        self.assertLess(len(proc.stdout.encode()), 2048)
        self.assertEqual(json.loads(state_path.read_text())["attempts"], state["attempts"])
        receipt.write_text('{}')
        with self.assertRaisesRegex(ValueError, "different receipt"):
            run_state.complete(state, "call-1", receipt)


    def test_scoped_inputs_reject_ignored_files_and_symbolic_links(self):
        self.command("print('pass')")
        (self.root / ".gitignore").write_text("ignored.txt\n")
        (self.root / "ignored.txt").write_text("not captured")
        (self.root / "link.txt").symlink_to("app.txt")
        for name in ("ignored.txt", "link.txt", "./app.txt"):
            self.plan["checks"][0]["inputs"] = [name]
            with self.assertRaises(ValueError):
                self.prepare()

    def test_select_checks_transfers_unchanged_scoped_inputs_and_runs_affected_inputs(self):
        self.command("print('pass')")
        self.plan["checks"][0]["inputs"] = ["app.txt"]
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        (self.root / "unrelated.txt").write_text("new unrelated file\n")
        unchanged = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                     self.artifacts / "unchanged-inputs")

        selected = evidence.select_checks(unchanged, original, {"check": str(captured)})
        self.assertEqual(selected["changed_paths"], ["unrelated.txt"])
        self.assertEqual(selected["checks"], [{
            "id": "check",
            "action": "transfer",
            "reason": "unchanged declared inputs; fresh environment and base assessment required",
            "inputs": ["app.txt"],
            "check": evidence.evidence_link(captured),
        }])

        (self.root / "app.txt").write_text("changed declared input\n")
        affected = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                    self.artifacts / "affected-input")
        row = evidence.select_checks(affected, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(row["action"], "run")
        self.assertIn("declared check inputs changed", row["reason"])
        self.assertNotIn("check", row)

    def test_select_checks_runs_whole_source_checks_after_any_content_change(self):
        self.command("print('pass')")
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        (self.root / "unrelated.txt").write_text("new unrelated file\n")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "whole-source")

        row = evidence.select_checks(target, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(row["action"], "run")
        self.assertEqual(row["inputs"], "whole-source")
        self.assertIn("unknown dependencies require whole source scope", row["reason"])
        self.assertNotIn("check", row)

    def test_select_checks_cli_reports_transfer_and_named_fresh_execution(self):
        self.command("print('pass')")
        self.plan["checks"][0]["inputs"] = ["app.txt"]
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        (self.root / "unrelated.txt").write_text("new unrelated file\n")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "cli-target")
        checks = self.artifacts / "checks.json"
        checks.write_text(json.dumps({"check": str(captured)}))
        command = [sys.executable, evidence.__file__, "select-checks", "--snapshot", str(target),
                   "--from-snapshot", str(original), "--checks", str(checks)]

        transfer = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(transfer.returncode, 0, transfer.stdout + transfer.stderr)
        transfer_payload = json.loads(transfer.stdout)
        self.assertEqual(transfer_payload["changed_paths"], ["unrelated.txt"])
        self.assertEqual(transfer_payload["checks"][0]["action"], "transfer")
        self.assertEqual(transfer_payload["checks"][0]["inputs"], ["app.txt"])
        self.assertEqual(transfer_payload["checks"][0]["check"], evidence.evidence_link(captured))

        fresh = subprocess.run([*command, "--fresh", "check"], capture_output=True, text=True)
        self.assertEqual(fresh.returncode, 0, fresh.stdout + fresh.stderr)
        fresh_row = json.loads(fresh.stdout)["checks"][0]
        self.assertEqual(fresh_row["action"], "run")
        self.assertEqual(fresh_row["reason"], "fresh execution required")
        self.assertEqual(fresh_row["inputs"], ["app.txt"])

    def test_fresh_checks_cannot_reuse_a_separate_snapshot_or_transfer(self):
        self.command("print('pass')")
        self.plan["checks"][0]["fresh"] = True
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "fresh-target")
        definition = evidence.check_definition(evidence.load_record(target), "check")

        row = evidence.select_checks(target, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(row["action"], "run")
        self.assertEqual(row["reason"], "fresh execution required")
        with self.assertRaisesRegex(ValueError, "fresh"):
            evidence.validate_check(captured, evidence.load_record(target), definition)
        with self.assertRaisesRegex(ValueError, "fresh"):
            evidence.transfer_check(original, target, captured, self.transfer_assessment(original, target))

    def test_selection_invalidates_reuse_for_contract_context_command_failure_and_log_changes(self):
        self.command("print('pass')")
        original = self.prepare()
        captured = evidence.run_check(original, "check")

        self.contract.write_text("Check a different result.\n**Status:** ready-for-agent\n")
        changed_contract = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                            self.artifacts / "changed-contract")
        contract_row = evidence.select_checks(changed_contract, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(contract_row["action"], "run")
        self.assertIn("acceptance contract changed", contract_row["reason"])

        self.contract.write_text("Check the result.\n**Status:** ready-for-agent\n")
        changed_context_plan = copy.deepcopy(self.plan)
        changed_context_plan["context"] = {"runtime": "different"}
        changed_context_requirements = self.artifacts / "changed_context.json"
        changed_context_requirements.write_text(json.dumps(changed_context_plan))
        changed_context = evidence.prepare(self.root, self.base, self.contract, changed_context_requirements,
                                           self.artifacts / "changed-context")
        context_row = evidence.select_checks(changed_context, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(context_row["action"], "run")
        self.assertIn("environment identity changed", context_row["reason"])

        changed_command_plan = copy.deepcopy(self.plan)
        changed_command_plan["checks"][0]["command"] = [sys.executable, "-c", "print('different command')"]
        changed_command_requirements = self.artifacts / "changed_command.json"
        changed_command_requirements.write_text(json.dumps(changed_command_plan))
        changed_command = evidence.prepare(self.root, self.base, self.contract, changed_command_requirements,
                                           self.artifacts / "changed-command")
        command_row = evidence.select_checks(changed_command, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(command_row["action"], "run")
        self.assertIn("command or inputs declaration changed", command_row["reason"])

        failed_plan = copy.deepcopy(self.plan)
        failed_plan["checks"][0]["command"] = [sys.executable, "-c", "raise SystemExit(2)"]
        failed_requirements = self.artifacts / "failed_requirements.json"
        failed_requirements.write_text(json.dumps(failed_plan))
        failed_original = evidence.prepare(self.root, self.base, self.contract, failed_requirements,
                                           self.artifacts / "failed-original")
        failed_capture = evidence.run_check(failed_original, "check")
        failed_target = evidence.prepare(self.root, self.base, self.contract, failed_requirements,
                                         self.artifacts / "failed-target")
        failed_row = evidence.select_checks(failed_target, failed_original, {"check": str(failed_capture)})["checks"][0]
        self.assertEqual(failed_row["action"], "run")
        self.assertIn("prior check failed", failed_row["reason"])

        log_original = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                        self.artifacts / "log-original")
        log_capture = evidence.run_check(log_original, "check")
        log = next(row for row in evidence.load_record(log_capture)["logs"] if Path(row["path"]).name == "stdout.log")
        Path(log["path"]).write_text("changed output\n")
        log_target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                      self.artifacts / "log-target")
        log_row = evidence.select_checks(log_target, log_original, {"check": str(log_capture)})["checks"][0]
        self.assertEqual(log_row["action"], "run")
        self.assertIn("log checksum", log_row["reason"])

    def test_direct_capture_reuses_identical_evidence_and_rejects_forged_snapshot_binding(self):
        self.command("print('pass')")
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "identical-target")
        definition = evidence.check_definition(evidence.load_record(target), "check")

        self.assertTrue(evidence.validate_check(captured, evidence.load_record(target), definition))
        reused = evidence.select_checks(target, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(reused["action"], "reuse")
        self.assertEqual(reused["check"], evidence.evidence_link(captured))
        record = json.loads(captured.read_text())
        record["payload"]["snapshot_path"] = str(target)
        record["payload"]["snapshot_sha256"] = evidence.file_hash(target)
        record["sha256"] = evidence.digest(record["payload"])
        captured.write_text(json.dumps(record))

        with self.assertRaisesRegex(ValueError, "capture path"):
            evidence.validate_check(captured, evidence.load_record(target), definition)
        row = evidence.select_checks(target, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(row["action"], "run")
        self.assertIn("capture path", row["reason"])

        record["payload"]["snapshot_path"] = "snapshot.json"
        record["sha256"] = evidence.digest(record["payload"])
        captured.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, "capture snapshot"):
            evidence.validate_check(captured, evidence.load_record(target), definition)
        malformed = evidence.select_checks(target, original, {"check": str(captured)})["checks"][0]
        self.assertEqual(malformed["action"], "run")
        self.assertIn("capture snapshot", malformed["reason"])

    def test_transfer_preserves_stdout_and_stderr_provenance(self):
        self.command("import sys; print('standard output'); print('standard error', file=sys.stderr)")
        original = self.prepare()
        captured = evidence.run_check(original, "check")
        captured_result = evidence.load_record(captured)
        stdout = next(row for row in captured_result["logs"] if Path(row["path"]).name == "stdout.log")
        stderr = next(row for row in captured_result["logs"] if Path(row["path"]).name == "stderr.log")
        self.assertEqual(Path(stdout["path"]).read_text(), "standard output\n")
        self.assertEqual(Path(stderr["path"]).read_text(), "standard error\n")

        self.git("add", ".")
        self.git("commit", "-qm", "Commit captured source")
        target = evidence.prepare(self.root, self.base, self.contract, self.requirements,
                                  self.artifacts / "provenance-target")
        moved = evidence.transfer_check(original, target, captured, self.transfer_assessment(original, target))
        moved_result = evidence.load_record(moved)

        self.assertEqual(moved_result["logs"], captured_result["logs"])
        self.assertEqual(moved_result["transfer"]["check"], evidence.evidence_link(captured))
        self.assertEqual(Path(stdout["path"]).read_text(), "standard output\n")
        self.assertEqual(Path(stderr["path"]).read_text(), "standard error\n")
        self.assertTrue(evidence.validate_check(moved, evidence.load_record(target), self.plan["checks"][0]))

    def test_unscoped_observations_need_fresh_evidence_after_any_content_change(self):
        self.plan["observations"] = ["save"]
        original = self.prepare()
        capture = self.artifacts / "browser.txt"
        capture.write_text("Saved and reloaded\n")
        first = self.response(original)
        first["observations"] = [{"id": "save", "result": "pass", "evidence": [evidence.evidence_link(capture)]}]
        previous = self.record(original, first)
        (self.root / "unrelated.txt").write_text("changed unrelated source\n")

        target, delta = self.recheck(original, previous, "unscoped-observation")
        delta["coverage"] = [{"path": "unrelated.txt", "outcome": "reviewed",
                               "reason": "Read the changed source."}]
        with self.assertRaisesRegex(ValueError, "fresh observations"):
            self.record(target, delta)
        self.assertEqual(evidence.fresh_observations(evidence.load_record(original), evidence.load_record(target)), {"save"})


    def test_scoped_packet_cli_preserves_unit_capture_without_completing_review(self):
        self.command("print('unit capture')")
        self.plan["observations"] = ["save"]
        snapshot = self.prepare()
        evidence.run_check(snapshot, "check")
        observations = self.artifacts / "observations.json"
        observations.write_text("[]")
        output = self.artifacts / "unit-packet.json"
        command = subprocess.run([sys.executable, evidence.__file__, "prepare-packet", "--snapshot", str(snapshot),
                                  "--observations", str(observations), "--id", "check", "--output", str(output)],
                                 capture_output=True, text=True)
        self.assertEqual(command.returncode, 0, command.stdout + command.stderr)
        packet = evidence.load_packet(json.loads(command.stdout)["evidence_packet"], evidence.load_record(snapshot), snapshot, allow_partial=True)
        self.assertEqual(packet["scope"], ["check"])
        self.assertEqual(set(packet["checks"]), {"check"})
        response = self.response(snapshot)
        del response["checks"], response["observations"]
        response["evidence_packet"] = evidence.evidence_link(output)
        with self.assertRaisesRegex(ValueError, "packet is incomplete"):
            self.record(snapshot, response)
        with self.assertRaisesRegex(ValueError, "packet is incomplete"):
            evidence.load_packet(evidence.evidence_link(output), evidence.load_record(snapshot), snapshot)
        for index, scope in enumerate(([], ["unknown"], ["check", "check"], ["save"])):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                evidence.prepare_packet(snapshot, self.artifacts / ("bad-scope-" + str(index) + ".json"),
                                        observations=[], scope=scope)



    def test_prepared_snapshot_copy_cannot_claim_a_fresh_bundle(self):
        self.command("print('pass')")
        self.plan["checks"][0]["fresh"] = True
        original = self.prepare()
        evidence.run_check(original, "check")
        copied = self.artifacts / "copied" / "snapshot.json"
        copied.parent.mkdir()
        copied.write_bytes(original.read_bytes())
        with self.assertRaisesRegex(ValueError, "snapshot path differs"):
            evidence.current_snapshot(copied)



if __name__ == "__main__":
    unittest.main()
