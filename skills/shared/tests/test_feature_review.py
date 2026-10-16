#!/usr/bin/env python3
"""Feature acceptance requires current captures and an independent receipt."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import feature_review as feature
import review_evidence as evidence
import run_state
from task_queue import launcher_module


class FeatureReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "source"
        self.root.mkdir()
        self.artifacts = Path(self.temp.name) / "evidence"
        self.artifacts.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.test")
        self.git("config", "user.name", "Test")
        (self.root / "app.txt").write_text("before\n")
        (self.root / "feature.md").write_text("The combined feature meets both task contracts.\n")
        (self.root / "T1.md").write_text("# T1: Focused behavior\n**Status:** ready-for-agent\nThe focused behavior passes.\n")
        self.route = {"id": "feature-review", "task_id": "feature-review", "input_path": "feature.md",
                      "track": "main", "role": "reviewer", "seat": "astra", "runner": "codex",
                      "model": "gpt-6-astra", "model_verification": "required", "effort": "high",
                      "effort_control": "runner", "mode": "runner", "unavailable": {"action": "block"}}
        self.check = {"id": "focused", "command": [sys.executable, "-c", "print('passed')"],
                      "cwd": ".", "timeout_seconds": 5, "inputs": ["app.txt"]}
        self.plan = {"requirements": {"context": {"runtime": sys.version}, "checks": [self.check],
                                      "observations": ["interaction"], "exclusions": {},
                                      "observation_inputs": {"interaction": ["app.txt"]}},
                     "required_checks": {"focused": True}, "interactions": ["interaction"]}
        self.policy = {"schema_version": 1, "mode": "feature", "queue": "queue.json", "feature_contract": "feature.md",
                       "check_plan": "checks.json", "tasks": {"T1": {"contract": "T1.md", "review": "deferred",
                       "reason": "No public boundary changes.", "focused_checks": ["focused"]}},
                       "final_review": {"scope": "feature.md", "route": self.route}}
        self.policy_path = self.root / "review-policy.json"
        (self.root / "queue.json").write_text(json.dumps({"schema_version": 1, "id": "feature", "parent_prd": "feature.md",
            "review_policy": "review-policy.json", "concurrency": {"max_active": 1, "isolation": "working-tree"},
            "tasks": [{"id": "T1", "manifest": "T1.md", "launch_manifest": "artifacts/T1/launch-manifest.json",
                       "write_paths": ["app.txt"], "blocked_by": [], "shared_surfaces": []}]}))
        self.save_policy()
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture")
        self.base = self.git("rev-parse", "HEAD").strip()
        (self.root / "app.txt").write_text("after\n")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def save_policy(self):
        self.policy_path.write_text(json.dumps(self.policy))
        (self.root / self.policy["check_plan"]).write_text(json.dumps(self.plan))

    def snapshot(self, task_id="T1", name="snapshot", run=True, fail_observation=False, previous=()):
        requirements = feature.requirements(self.policy_path, self.root, task_id)
        req_path = self.artifacts / (name + ".requirements.json")
        req_path.write_text(json.dumps(requirements))
        contract = self.policy["tasks"][task_id]["contract"] if task_id else self.policy["feature_contract"]
        snapshot = evidence.prepare(self.root, self.base, self.root / contract, req_path,
                                    self.artifacts / name, artifact_dir=self.artifacts, previous_reviews=previous)
        if run:
            for check in requirements["checks"]:
                evidence.run_check(snapshot, check["id"])
        observations = []
        for key in requirements["observations"]:
            captured = self.artifacts / (name + "-" + key + ".txt")
            captured.write_text("Captured combined behavior.\n")
            observations.append({"id": key, "result": "fail" if fail_observation else "pass",
                                 "evidence": [str(captured)]})
        packet = evidence.prepare_packet(snapshot, self.artifacts / (name + ".packet.json"), observations=observations) if run else None
        return snapshot, packet

    def task_assessment(self, snapshot, packet):
        return feature.assess_task(self.policy_path, "T1", snapshot, evidence.evidence_link(packet), self.base, self.root)

    def record_review(self, snapshot, packet, execution=None, findings=None):
        contract = evidence.response_contract(snapshot)
        result = {"snapshot_sha256": contract["snapshot_sha256"], "coverage": [
            {"path": name, "outcome": "reviewed", "reason": "Read the changed behavior."}
            for name in contract["coverage_paths"]], "findings": findings or [],
            "evidence_packet": evidence.evidence_link(packet), "summary": "Feature contract passes."}
        if "scope_approval" in contract:
            result["scope_approval"] = contract["scope_approval"]
        execution = {**(execution or {}), "success": True, "agent_message": json.dumps(result)}
        return evidence.record_review(snapshot, result, execution), execution

    def final_fixture(self):
        snapshot, packet = self.snapshot(None, "final")
        execution = {"call_id": "final-call", "configured_model": self.route["model"], "configured_effort": "high",
                     "context_id": "independent-context", "input_revision": evidence.file_hash(self.root / self.policy["feature_contract"]),
                     "effective_runner": "codex", "effective_model": self.route["model"], "effective_effort": "high",
                     "model_receipt": {"status": "verified", "source": "provider_event", "observed_model": self.route["model"]}}
        review, execution = self.record_review(snapshot, packet, execution)
        receipt_path = self.artifacts / "receipt.json"
        receipt_path.write_text(json.dumps(execution))
        plan_path = self.artifacts / "routing.json"
        plan_path.write_text(json.dumps(self.routing_plan()))
        call = {"status": "completed", "review_status": "ready", "review": evidence.evidence_link(review),
                "receipt_ref": evidence.evidence_link(receipt_path), "intent": {"route": self.route,
                "review_snapshot": evidence.evidence_link(snapshot), "input": evidence.evidence_link(self.root / self.policy["feature_contract"])}}
        ledger = {"plan": evidence.evidence_link(plan_path), "calls": {"final-call": call},
                  "contexts": {self.route["id"]: "independent-context"}}
        return snapshot, call, ledger

    def routing_plan(self):
        launcher = launcher_module()
        implementation = {**self.route, "id": "T1-implementer", "task_id": "T1", "role": "implementer",
                          "input_path": self.policy["tasks"]["T1"]["contract"], "seat": "sol", "model": "gpt-6.1-sol"}
        routes = [implementation, self.route]
        if self.policy["tasks"]["T1"]["review"] == "critical":
            routes.append({**self.route, "id": "T1-reviewer", "task_id": "T1",
                           "input_path": self.policy["tasks"]["T1"]["contract"]})
        inputs = [{"path": path, "content_sha256": launcher.content_digest(self.root / path)}
                  for path in feature.policy_inputs(self.policy_path, self.root)]
        return {"schema_version": 1, "approval": {"status": "approved",
            "scope_digest": launcher.canonical_digest(launcher.normalized_scope_inputs(inputs)),
            "routes_digest": launcher.canonical_digest(launcher.normalized_routes(routes))},
            "scope": {"inputs": inputs}, "routes": routes, "review_policy": self.policy_path.relative_to(self.root).as_posix()}

    def final_assessment(self, snapshot, call, ledger):
        return feature.assess_feature(self.policy_path, snapshot, self.base, call, self.root, ledger)

    def scoped_fixture(self):
        (self.root / "config.txt").write_text("stable config\n")
        (self.root / "later.txt").write_text("unrelated original\n")
        row = self.policy["tasks"]["T1"]
        row["review"] = "critical"
        row["reuse_scope"] = {"inputs": ["app.txt", "config.txt", "future.txt"],
                              "independent_paths": ["later.txt"], "complete": True,
                              "reason": "All callers, configuration, and dependencies are listed."}
        self.save_policy()
        snapshot, packet = self.snapshot(name="original-critical")
        route = next(route for route in self.routing_plan()["routes"] if route["id"] == "T1-reviewer")
        execution = {"call_id": "critical-call", "configured_model": route["model"], "configured_effort": "high",
                     "context_id": "critical-context", "input_revision": evidence.file_hash(self.root / "T1.md"),
                     "effective_runner": "codex", "effective_model": route["model"], "effective_effort": "high",
                     "model_receipt": {"status": "verified", "source": "provider_event", "observed_model": route["model"]}}
        review, execution = self.record_review(snapshot, packet, execution)
        receipt = self.artifacts / "critical-receipt.json"
        receipt.write_text(json.dumps(execution))
        routing = self.artifacts / "critical-routing.json"
        routing.write_text(json.dumps(self.routing_plan()))
        call = {"status": "completed", "review_status": "ready", "review": evidence.evidence_link(review),
                "receipt_ref": evidence.evidence_link(receipt), "intent": {"route": route,
                "review_snapshot": evidence.evidence_link(snapshot), "input": evidence.evidence_link(self.root / "T1.md")}}
        ledger = {"plan": evidence.evidence_link(routing), "calls": {"critical-call": call},
                  "contexts": {route["id"]: "critical-context"}}
        reference = {"snapshot": evidence.evidence_link(snapshot), "call_id": "critical-call"}
        return snapshot, packet, reference, ledger

    def scoped_assessment(self, snapshot, packet, reference, ledger, environment=True):
        reference = copy.deepcopy(reference)
        old = evidence.load_record(reference["snapshot"]["path"])
        current = evidence.load_record(snapshot)
        if environment and old["source_id"] != current["source_id"]:
            capture = snapshot.parent / "environment.txt"
            capture.write_text("Fixture runtime, dependencies, external state, and base interactions are unchanged.\n")
            assessment = {"from_snapshot_sha256": reference["snapshot"]["sha256"], "to_source_id": current["source_id"],
                          **{key: {"reason": "Fixture environment is unchanged.", "evidence": [evidence.evidence_link(capture)]}
                             for key in ("runtime", "dependencies", "external_state", "base_interactions")}}
            path = snapshot.parent / "environment.json"
            path.write_text(json.dumps(assessment))
            reference["assessment"] = evidence.evidence_link(path)
        return feature.assess_task(self.policy_path, "T1", snapshot, evidence.evidence_link(packet), self.base,
                                   self.root, critical_review=reference, call_ledger=ledger)

    def later_critical_review(self, ledger, prior, call_id, hour, findings=None, retain=True):
        old_call = ledger["calls"][prior["call_id"]]
        snapshot, packet = self.snapshot(name=call_id, previous=[old_call["review"]["path"]] if retain else ())
        execution = evidence.read_json(old_call["receipt_ref"]["path"])
        execution["call_id"] = call_id
        review, execution = self.record_review(snapshot, packet, execution, findings=findings)
        receipt = self.artifacts / (call_id + "-receipt.json")
        receipt.write_text(json.dumps(execution))
        call = {**copy.deepcopy(old_call), "review_status": evidence.assess(snapshot, self.base)["status"],
                "reserved_at": f"2026-10-16T{hour:02d}:00:00+00:00", "completed_at": f"2026-10-16T{hour:02d}:10:00+00:00",
                "review": evidence.evidence_link(review), "receipt_ref": evidence.evidence_link(receipt)}
        call["intent"]["review_snapshot"] = evidence.evidence_link(snapshot)
        ledger["calls"][call_id] = call
        return snapshot, packet, {"snapshot": evidence.evidence_link(snapshot), "call_id": call_id}

    def test_scoped_review_cannot_reuse_superseded_ready_or_drop_later_findings(self):
        original, packet, reference, ledger = self.scoped_fixture()
        ledger["calls"]["critical-call"].update(reserved_at="2026-10-16T01:00:00+00:00",
                                                  completed_at="2026-10-16T01:10:00+00:00")
        finding = {"id": "critical-defect", "path": "app.txt", "severity": "P1", "status": "open",
                   "evidence": "The dependency contract has a missing case."}
        _, _, later = self.later_critical_review(ledger, reference, "later-needs-work", 2, [finding])
        result = self.scoped_assessment(original, packet, reference, ledger)
        self.assertFalse(result["dependency_release"], result)
        self.assertIn("superseded", " ".join(result["reasons"]))
        fresh, fresh_packet, omitted = self.later_critical_review(ledger, later, "omitted-history", 3, retain=False)
        result = self.scoped_assessment(fresh, fresh_packet, omitted, ledger)
        self.assertFalse(result["dependency_release"], result)
        self.assertIn("omits an earlier review", " ".join(result["reasons"]))
        ledger["calls"].pop("omitted-history")
        resolved = {**finding, "status": "rejected", "evidence": "The existing guard covers the reported case."}
        fresh, fresh_packet, newest = self.later_critical_review(ledger, later, "resolved-review", 4, [resolved])
        ledger["calls"]["failed-attempt"] = {"status": "failed", "intent": copy.deepcopy(ledger["calls"]["critical-call"]["intent"])}
        result = self.scoped_assessment(fresh, fresh_packet, newest, ledger)
        self.assertTrue(result["dependency_release"], result)
        self.assertFalse(result["feature_accepted"])

    def test_scoped_review_fails_closed_on_ambiguous_history(self):
        original, packet, reference, ledger = self.scoped_fixture()
        ledger["calls"]["critical-call"].update(reserved_at="2026-10-16T01:00:00+00:00",
                                                  completed_at="2026-10-16T01:10:00+00:00")
        fresh, fresh_packet, newest = self.later_critical_review(ledger, reference, "new-review", 2)
        for kind in ("missing", "overlap", "timezone", "tampered-receipt"):
            candidate = copy.deepcopy(ledger)
            with self.subTest(kind=kind):
                if kind == "missing":
                    candidate["calls"]["critical-call"].pop("completed_at")
                elif kind == "overlap":
                    candidate["calls"]["new-review"]["reserved_at"] = "2026-10-16T01:05:00+00:00"
                elif kind == "timezone":
                    candidate["calls"]["critical-call"]["reserved_at"] = "2026-10-16T01:00:00"
                else:
                    candidate["calls"]["critical-call"]["receipt_ref"]["sha256"] = "0" * 64
                self.assertFalse(self.scoped_assessment(fresh, fresh_packet, newest, candidate)["dependency_release"])

    def test_scoped_critical_review_reuses_actual_receipt_after_independent_edit(self):
        original, _, reference, ledger = self.scoped_fixture()
        (self.root / "later.txt").write_text("unrelated next task\n")
        current, packet = self.snapshot(name="current-critical")
        self.assertFalse(self.scoped_assessment(current, packet, reference, ledger, environment=False)["dependency_release"])
        result = self.scoped_assessment(current, packet, reference, ledger)
        self.assertTrue(result["dependency_release"], result)
        self.assertFalse(result["feature_accepted"])
        self.assertFalse((current.parent / "review.json").exists())
        self.assertFalse(feature.assess_feature(self.policy_path, current, self.base,
                                                ledger["calls"]["critical-call"], self.root, ledger)["final_review_ready"])
        with self.assertRaisesRegex(ValueError, "stale"):
            evidence.current_snapshot(original)

    def test_scoped_critical_review_invalidates_dependency_config_absent_and_mode_changes(self):
        _, _, reference, ledger = self.scoped_fixture()
        for name in ("app.txt", "config.txt", "future.txt", "unknown.txt"):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes() if path.exists() else None
                path.write_text("dependency changed\n")
                current, packet = self.snapshot(name="changed-" + name)
                result = self.scoped_assessment(current, packet, reference, ledger)
                self.assertFalse(result["dependency_release"], result)
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)
        path = self.root / "app.txt"
        path.chmod(path.stat().st_mode | 0o100)
        current, packet = self.snapshot(name="changed-mode")
        self.assertFalse(self.scoped_assessment(current, packet, reference, ledger)["dependency_release"])

    def test_scoped_critical_review_rejects_receipt_tamper_pending_and_shared_context(self):
        current, packet, reference, ledger = self.scoped_fixture()
        for kind in ("pending", "context", "checksum", "missing", "wrong-call"):
            candidate, ref = copy.deepcopy(ledger), copy.deepcopy(reference)
            with self.subTest(kind=kind):
                if kind == "pending":
                    candidate["calls"]["other"] = {"status": "pending"}
                elif kind == "context":
                    candidate["contexts"]["writer"] = "critical-context"
                elif kind == "checksum":
                    candidate["calls"]["critical-call"]["receipt_ref"]["sha256"] = "0" * 64
                elif kind == "missing":
                    candidate["calls"]["critical-call"].pop("receipt_ref")
                else:
                    ref["call_id"] = "missing"
                self.assertFalse(self.scoped_assessment(current, packet, ref, candidate)["dependency_release"])
        self.assertFalse(self.task_assessment(current, packet)["dependency_release"])

    def test_scoped_critical_review_rejects_changed_environment_contract_and_index(self):
        _, _, reference, ledger = self.scoped_fixture()
        for kind in ("environment", "contract", "index", "base"):
            with self.subTest(kind=kind):
                original_plan = copy.deepcopy(self.plan)
                contract = (self.root / "T1.md").read_bytes()
                if kind == "environment":
                    self.plan["requirements"]["context"]["runtime"] = "changed"
                    self.save_policy()
                elif kind == "contract":
                    (self.root / "T1.md").write_bytes(contract + b"Changed acceptance.\n")
                elif kind == "index":
                    self.git("add", "later.txt")
                else:
                    self.git("commit", "--allow-empty", "-qm", "New base")
                    self.base = self.git("rev-parse", "HEAD").strip()
                current, packet = self.snapshot(name="changed-" + kind)
                self.assertFalse(self.scoped_assessment(current, packet, reference, ledger)["dependency_release"])
                self.plan = original_plan
                self.save_policy()
                (self.root / "T1.md").write_bytes(contract)
                if kind == "index":
                    self.git("reset", "-q", "HEAD", "later.txt")

    def test_scoped_policy_rejects_unknown_closure_overlap_globs_and_missing_check_inputs(self):
        self.scoped_fixture()
        before = copy.deepcopy(self.policy)
        for kind in ("incomplete", "overlap", "ownership", "glob", "check"):
            self.policy = copy.deepcopy(before)
            scope = self.policy["tasks"]["T1"]["reuse_scope"]
            with self.subTest(kind=kind):
                if kind == "incomplete":
                    scope["complete"] = False
                elif kind == "overlap":
                    scope["independent_paths"] = ["config.txt"]
                elif kind == "ownership":
                    scope["inputs"] = ["config.txt"]
                    scope["independent_paths"] = ["app.txt"]
                elif kind == "glob":
                    scope["independent_paths"] = ["*.txt"]
                else:
                    self.check.pop("inputs")
                self.save_policy()
                with self.assertRaises(ValueError):
                    feature.validate_policy(self.policy_path, self.root)
        self.check["inputs"] = ["app.txt"]

    def test_scoped_review_requires_original_scope_acknowledgement(self):
        self.scoped_fixture()
        snapshot, packet = self.snapshot(name="missing-approval")
        result = {"snapshot_sha256": evidence.file_hash(snapshot), "coverage": [
            {"path": name, "outcome": "reviewed", "reason": "Reviewed."}
            for name in evidence.response_contract(snapshot)["coverage_paths"]],
            "findings": [], "evidence_packet": evidence.evidence_link(packet), "summary": "Ready."}
        with self.assertRaisesRegex(ValueError, "fields"):
            evidence.record_review(snapshot, result, {"success": True, "agent_message": json.dumps(result)})

    def test_scoped_inputs_cannot_hide_ignored_or_artifact_dependencies(self):
        self.scoped_fixture()
        (self.root / ".gitignore").write_text("hidden.txt\n")
        (self.root / "hidden.txt").write_text("secret dependency\n")
        self.policy["tasks"]["T1"]["reuse_scope"]["inputs"].append("hidden.txt")
        self.save_policy()
        with self.assertRaisesRegex(ValueError, "outside captured source"):
            self.snapshot(name="ignored-input")

    def test_focused_capture_releases_dependency_without_feature_acceptance(self):
        snapshot, packet = self.snapshot()
        result = self.task_assessment(snapshot, packet)
        self.assertTrue(result["dependency_release"], result)
        self.assertFalse(result["feature_accepted"])
        self.assertFalse(result["independent_review_required"])
        self.assertFalse((snapshot.parent / "review.json").exists())

    def test_critical_task_still_requires_existing_review(self):
        self.policy["tasks"]["T1"]["review"] = "critical"
        self.save_policy()
        snapshot, packet = self.snapshot()
        result = self.task_assessment(snapshot, packet)
        self.assertFalse(result["dependency_release"])
        self.assertTrue(result["independent_review_required"])
        self.record_review(snapshot, packet)
        self.assertTrue(self.task_assessment(snapshot, packet)["dependency_release"])

    def test_source_contract_and_check_changes_invalidate_focused_evidence(self):
        for name in ("app.txt", "T1.md", "checks.json"):
            with self.subTest(name=name):
                snapshot, packet = self.snapshot(name=name)
                path = self.root / name
                before = path.read_bytes()
                path.write_bytes(before + b"\n")
                self.assertFalse(self.task_assessment(snapshot, packet)["dependency_release"])
                path.write_bytes(before)

    def test_failed_capture_and_wrong_packet_binding_block_release(self):
        self.check["command"] = [sys.executable, "-c", "raise SystemExit(1)"]
        self.save_policy()
        snapshot, packet = self.snapshot()
        self.assertIn("failed", " ".join(self.task_assessment(snapshot, packet)["reasons"]))
        second, _ = self.snapshot(name="second")
        self.assertFalse(self.task_assessment(second, packet)["dependency_release"])

    def test_missing_capture_blocks_packet(self):
        snapshot, _ = self.snapshot(run=False)
        with self.assertRaises(OSError):
            evidence.prepare_packet(snapshot, self.artifacts / "missing.json", observations=[])

    def test_checks_alone_and_review_without_receipt_cannot_accept_feature(self):
        snapshot, packet = self.snapshot(None, "final")
        self.assertFalse(self.final_assessment(snapshot, None, None)["final_review_ready"])
        self.record_review(snapshot, packet)
        self.assertFalse(self.final_assessment(snapshot, None, None)["final_review_ready"])

    def test_actual_independent_completed_review_accepts_feature(self):
        snapshot, call, ledger = self.final_fixture()
        result = self.final_assessment(snapshot, call, ledger)
        self.assertEqual(result["status"], "ready", result)
        self.assertTrue(result["final_review_ready"])
        self.assertNotIn("feature_accepted", result)

    def test_final_rejects_status_only_tampered_receipt_pending_call_and_shared_context(self):
        snapshot, call, ledger = self.final_fixture()
        for change in ("missing-receipt", "wrong-route", "pending", "context", "model"):
            candidate, calls = copy.deepcopy(call), copy.deepcopy(ledger)
            with self.subTest(change=change):
                if change == "missing-receipt":
                    candidate.pop("receipt_ref")
                elif change == "wrong-route":
                    candidate["intent"]["route"]["input_path"] = "T1.md"
                elif change == "pending":
                    calls["calls"]["other"] = {"status": "pending"}
                elif change == "context":
                    calls["contexts"]["writer"] = "independent-context"
                elif change == "model":
                    candidate["intent"]["route"]["model"] = "wrong-model"
                calls["calls"]["final-call"] = candidate
                self.assertFalse(self.final_assessment(snapshot, candidate, calls)["final_review_ready"])

    def test_failed_feature_interaction_blocks_acceptance(self):
        snapshot, packet = self.snapshot(None, "final", fail_observation=True)
        self.record_review(snapshot, packet)
        self.assertFalse(self.final_assessment(snapshot, None, None)["final_review_ready"])

    def test_policy_cannot_omit_flags_task_reason_or_interactions(self):
        for field in ("flags", "reason", "interactions"):
            policy, plan = copy.deepcopy(self.policy), copy.deepcopy(self.plan)
            with self.subTest(field=field):
                if field == "flags":
                    self.plan["required_checks"] = {}
                elif field == "reason":
                    self.policy["tasks"]["T1"]["reason"] = ""
                else:
                    self.plan["interactions"] = []
                self.save_policy()
                with self.assertRaises(ValueError):
                    feature.validate_policy(self.policy_path, self.root)
                self.policy, self.plan = policy, plan

    def test_cli_derives_requirements_from_explicit_root(self):
        result = subprocess.run([sys.executable, feature.__file__, "requirements", "--policy", self.policy_path.relative_to(self.root).as_posix(),
                                 "--root", str(self.root), "--task", "T1"], cwd=self.artifacts,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), feature.requirements(self.policy_path, self.root, "T1"))

    def test_queue_selection_blocks_policy_pointer_substitution(self):
        other = self.root / "other-policy.json"
        other.write_text(self.policy_path.read_text())
        with self.assertRaisesRegex(ValueError, "exact review policy"):
            feature.validate_policy(other, self.root)

    def ignored_workflow(self):
        workflow = self.root / ".ai-workflow"
        workflow.mkdir()
        (self.root / ".gitignore").write_text("/.ai-workflow\n")
        for name in ("feature.md", "T1.md", "checks.json", "queue.json", "review-policy.json"):
            (self.root / name).rename(workflow / name)
        self.policy_path = workflow / "review-policy.json"
        for field in ("queue", "feature_contract", "check_plan"):
            self.policy[field] = ".ai-workflow/" + self.policy[field]
        self.policy["tasks"]["T1"]["contract"] = ".ai-workflow/T1.md"
        self.policy["final_review"]["scope"] = ".ai-workflow/feature.md"
        self.route["input_path"] = ".ai-workflow/feature.md"
        queue_path = workflow / "queue.json"
        queue = json.loads(queue_path.read_text())
        queue["parent_prd"] = ".ai-workflow/feature.md"
        queue["review_policy"] = ".ai-workflow/review-policy.json"
        queue["tasks"][0]["manifest"] = ".ai-workflow/T1.md"
        queue_path.write_text(json.dumps(queue))
        self.save_policy()

    def transfer(self, old, target):
        probe = self.artifacts / "environment.txt"
        probe.write_text("Captured runtime and dependency inspection for current source.\n")
        row = {"reason": "Checked the current runtime, dependencies, external state and base.",
               "evidence": [evidence.evidence_link(probe)]}
        assessment = self.artifacts / "transfer.json"
        assessment.write_text(json.dumps({"from_snapshot_sha256": evidence.file_hash(old),
            "to_source_id": evidence.load_record(target)["source_id"],
            **{key: row for key in ("runtime", "dependencies", "external_state", "base_interactions")}}))
        return evidence.transfer_check(old, target, old.parent / "checks/focused/result.json", assessment)

    def test_ignored_workflow_inputs_bind_actual_final_acceptance(self):
        self.ignored_workflow()
        snapshot, call, ledger = self.final_fixture()
        source = evidence.load_record(snapshot)["source"]["files"]
        self.assertFalse(any(name.startswith(".ai-workflow/") for name in source))
        self.assertTrue(self.final_assessment(snapshot, call, ledger)["final_review_ready"])

    def test_focused_check_transfers_to_feature_contract_without_second_execution(self):
        self.ignored_workflow()
        old, _ = self.snapshot()
        target, _ = self.snapshot(None, "final", run=False)
        selection = evidence.select_checks(target, old, {"focused": str(old.parent / "checks/focused/result.json")})
        self.assertEqual(selection["checks"][0]["action"], "transfer", selection)
        transferred = self.transfer(old, target)
        captured = self.artifacts / "final-interaction.txt"
        captured.write_text("Captured combined behavior.\n")
        packet = evidence.prepare_packet(target, self.artifacts / "final.packet.json", observations=[
            {"id": "interaction", "result": "pass", "evidence": [str(captured)]}])
        self.assertTrue(evidence.validate_check(transferred, evidence.load_record(target), self.check))
        self.assertEqual(len(list(self.artifacts.rglob("stdout.log"))), 1)
        self.record_review(target, packet)
        self.assertEqual(evidence.assess(target, self.base)["status"], "ready")

    def test_status_only_contract_change_retains_capture_but_acceptance_change_rejects_it(self):
        self.ignored_workflow()
        old, packet = self.snapshot()
        contract = self.root / self.policy["tasks"]["T1"]["contract"]
        before = contract.read_text()
        contract.write_text(before.replace("ready-for-agent", "done"))
        self.assertTrue(self.task_assessment(old, packet)["dependency_release"])
        target, _ = self.snapshot(None, "final", run=False)
        self.transfer(old, target)
        contract.write_text(contract.read_text() + "Additional acceptance behavior.\n")
        changed, _ = self.snapshot(None, "changed", run=False)
        selection = evidence.select_checks(changed, old, {"focused": str(old.parent / "checks/focused/result.json")})
        self.assertEqual(selection["checks"][0]["action"], "run", selection)
        with self.assertRaises(ValueError):
            self.transfer(old, changed)

    def test_incomplete_shared_check_contract_cannot_enable_cross_contract_reuse(self):
        binding = feature.check_contract(self.policy_path, self.root)
        binding["inputs"] = binding["inputs"][:-1]
        requirements = copy.deepcopy(self.plan["requirements"])
        requirements["check_contract"] = binding
        with self.assertRaisesRegex(ValueError, "omits or changes"):
            evidence.validate_requirements(requirements, self.root)

    def test_unrelated_integration_reuses_scoped_capture_on_current_snapshot(self):
        self.ignored_workflow()
        old, packet = self.snapshot()
        (self.root / "notes.txt").write_text("Independent integration notes.\n")
        self.assertFalse(self.task_assessment(old, packet)["dependency_release"])
        current, _ = self.snapshot(name="integrated", run=False)
        selection = evidence.select_checks(current, old, {"focused": str(old.parent / "checks/focused/result.json")})
        self.assertEqual(selection["checks"][0]["action"], "transfer", selection)
        self.transfer(old, current)
        current_packet = evidence.prepare_packet(current, self.artifacts / "integrated.packet.json", observations=[])
        self.assertTrue(self.task_assessment(current, current_packet)["dependency_release"])
        self.assertEqual(len(list(self.artifacts.rglob("stdout.log"))), 1)

    def test_shared_check_binding_rejects_unrelated_review_contract(self):
        requirements = feature.requirements(self.policy_path, self.root, "T1")
        req_path = self.artifacts / "foreign-requirements.json"
        req_path.write_text(json.dumps(requirements))
        foreign = self.artifacts / "foreign-contract.md"
        foreign.write_text("An unrelated acceptance contract.\n")
        snapshot = evidence.prepare(self.root, self.base, foreign, req_path, self.artifacts / "foreign",
                                    artifact_dir=self.artifacts)
        evidence.run_check(snapshot, "focused")
        with self.assertRaisesRegex(ValueError, "does not include"):
            evidence.prepare_packet(snapshot, self.artifacts / "foreign.packet.json", observations=[])

    def test_new_feature_reservations_need_root_and_current_approved_inputs(self):
        routing = self.artifacts / "routing.json"
        routing.write_text(json.dumps(self.routing_plan()))
        limits = {"total_role_calls": 2, self.route["id"]: 2}
        state = {}
        run_state.initialize(state, routing, "run", limits)
        with self.assertRaisesRegex(ValueError, "explicit source root"):
            run_state.reserve(state, self.route["id"], "review-1", self.root / "feature.md", "review")
        (self.root / "checks.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "scope input changed"):
            run_state.reserve(state, self.route["id"], "review-1", self.root / "feature.md", "review", root=self.root)
        self.assertEqual(state["call_ledger"]["calls"], {})
        self.assertEqual(state["attempts"], {})

    def test_feature_plan_requires_all_deferred_and_critical_task_roles(self):
        launcher = launcher_module()
        for classification, missing_role in (("deferred", "implementer"), ("critical", "reviewer")):
            with self.subTest(classification=classification):
                self.policy["tasks"]["T1"]["review"] = classification
                self.save_policy()
                plan = self.routing_plan()
                self.assertIsNotNone(feature.validate_plan_policy(plan, self.root))
                plan["routes"] = [route for route in plan["routes"]
                                  if not (route["task_id"] == "T1" and route["role"] == missing_role)]
                plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
                with self.assertRaisesRegex(ValueError, "routing plan needs roles"):
                    feature.validate_plan_policy(plan, self.root)

    def test_feature_reserve_cli_uses_explicit_root_from_another_directory(self):
        routing = self.artifacts / "routing.json"
        routing.write_text(json.dumps(self.routing_plan()))
        state = {}
        run_state.initialize(state, routing, "run", {"total_role_calls": 2, self.route["id"]: 2})
        state_path = self.artifacts / "state.json"
        state_path.write_text(json.dumps(state))
        result = subprocess.run([sys.executable, run_state.__file__, "--state", str(state_path), "reserve",
            "--route", self.route["id"], "--call", "review-1", "--brief", str(self.root / "feature.md"),
            "--phase", "review", "--root", str(self.root)], cwd=self.artifacts, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
