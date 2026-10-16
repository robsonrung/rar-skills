#!/usr/bin/env python3
"""Batch refresh preserves checks, immutable captures, and final acceptance gates."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import test_feature_review as fixtures
import test_task_queue as queue_fixtures
import feature_refresh as refresh
import feature_review as feature
import review_evidence as evidence


class FeatureRefreshTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FeatureReviewTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.artifacts = self.fixture.artifacts
        self.policy_path = self.fixture.policy_path
        self.base = self.fixture.base
        self.ledger_path = self.artifacts / "state.json"
        self.environment = self.artifacts / "environment.json"
        self.output = self.artifacts / "refresh"

    def ledger(self, task_ids=("T1",), capture=True):
        fx = self.fixture
        queue = evidence.read_json(self.root / "queue.json")
        for key in task_ids:
            if key == "T1":
                continue
            (self.root / (key + ".md")).write_text(f"# {key}: Other task\n**Status:** ready-for-agent\nBehavior passes.\n")
            fx.policy["tasks"].setdefault(key, {**fx.policy["tasks"]["T1"], "contract": key + ".md"})
            queue["tasks"].append({**queue["tasks"][0], "id": key, "manifest": key + ".md",
                                   "launch_manifest": f"artifacts/{key}/launch-manifest.json"})
        (self.root / "queue.json").write_text(json.dumps(queue))
        fx.save_policy()
        plan = fx.routing_plan()
        for key in task_ids:
            if key != "T1":
                plan["routes"].append({**plan["routes"][0], "id": key + "-implementer", "task_id": key,
                                       "input_path": key + ".md"})
        launcher = __import__("task_queue").launcher_module()
        plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
        plan_path = self.artifacts / "plan.json"
        plan_path.write_text(json.dumps(plan))
        entries = {}
        for key in task_ids:
            snapshot, packet = fx.snapshot(key, "original-" + key, run=capture)
            entries[key] = {"snapshot": evidence.evidence_link(snapshot), "base": self.base,
                            "launch_manifest": f"artifacts/{key}/launch-manifest.json"}
            if packet:
                entries[key]["evidence_packet"] = evidence.evidence_link(packet)
        self.state = {"call_ledger": {"plan": evidence.evidence_link(plan_path), "calls": {}},
                      "integration_evidence": entries}
        self.ledger_path.write_text(json.dumps(self.state))
        self.bind_environment()

    def bind_environment(self, output=None):
        proof = self.artifacts / "environment-proof.txt"
        proof.write_text("Current runtime, dependencies, external state, and base interactions checked.\n")
        value = {key: {"reason": "Current evidence checked.", "evidence": [evidence.evidence_link(proof)]}
                 for key in ("runtime", "dependencies", "external_state", "base_interactions")}
        source = evidence.source_state(self.root, self.base, output or self.output)
        value.update(to_source_id=evidence.digest(source),
                     context_id=evidence.digest(evidence.context_identity(self.fixture.plan["requirements"]["context"])))
        self.environment.write_text(json.dumps(value))

    def run_refresh(self, **kwargs):
        return refresh.refresh(self.policy_path, self.root, self.base, self.ledger_path,
                               kwargs.pop("output", self.output), self.environment, **kwargs)

    def aggregate_plan(self, *, child_fresh=False, fail=False, separate_environment=False):
        config = self.root / "check-config.json"
        config.write_text(json.dumps({"aggregate": ["focused"]}))
        marker = self.artifacts / "executions.txt"
        def command(label, status=0):
            return [sys.executable, "-c", "from pathlib import Path; "
                    f"p=Path({str(marker)!r}); p.open('a').write({label + chr(10)!r}); raise SystemExit({status})"]
        self.fixture.check.update(command=command("focused"), environment="unit", inputs=["app.txt", "check-config.json"])
        if child_fresh:
            self.fixture.check["fresh"] = True
        aggregate = {**self.fixture.check, "id": "aggregate", "command": command("aggregate", int(fail)),
                     "covers": {"checks": ["focused"], "reason": "The repository command includes the focused suite.",
                                "evidence": [{"path": "check-config.json", "sha256": evidence.file_hash(config)}]}}
        aggregate.pop("fresh", None)
        self.fixture.plan["requirements"]["checks"].append(aggregate)
        self.fixture.plan["required_checks"]["aggregate"] = True
        self.fixture.policy["tasks"]["T1"]["focused_checks"].append("aggregate")
        if separate_environment:
            self.fixture.plan["requirements"]["checks"].append({**self.fixture.check, "id": "other-environment",
                "command": command("other-environment"), "environment": "integration"})
            self.fixture.plan["required_checks"]["other-environment"] = True
            self.fixture.policy["tasks"]["T1"]["focused_checks"].append("other-environment")
        return marker

    def test_complete_feature_plan_rejects_unknown_covered_check(self):
        self.aggregate_plan()
        self.fixture.plan["requirements"]["checks"][-1]["covers"]["checks"] = ["missing"]
        self.fixture.save_policy()
        with self.assertRaisesRegex(ValueError, "unknown check"):
            feature.validate_policy(self.policy_path, self.root)

    def test_cli_aggregate_runs_once_across_tasks_with_explicit_child_evidence(self):
        marker = self.aggregate_plan()
        self.ledger(("T1", "T2"), capture=False)
        command = [sys.executable, str(Path(refresh.__file__).resolve()), "--policy", str(self.policy_path),
                   "--root", str(self.root), "--base", self.base, "--ledger", str(self.ledger_path),
                   "--output", str(self.output), "--environment", str(self.environment), "--execute"]
        completed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(marker.read_text().splitlines(), ["aggregate"])
        self.assertFalse(result["feature_accepted"])
        for task in ("T1", "T2"):
            entry = result["integration_evidence_patch"][task]
            snapshot = evidence.checked_link(entry["snapshot"], "snapshot")
            packet = evidence.load_packet(entry["evidence_packet"], evidence.snapshot_record(snapshot), snapshot)
            self.assertEqual(set(packet["checks"]), {"focused", "aggregate"})
            child = evidence.load_record(packet["checks"]["focused"])
            self.assertEqual(child["kind"], "coverage")
            self.assertNotIn("exit_code", child)
            final = feature.assess_feature(self.policy_path, snapshot, self.base, None, self.root)
            self.assertFalse(final["final_review_ready"])
        prior = refresh.candidates(result["integration_evidence_patch"], self.root)
        self.assertEqual(len(prior), 1)
        self.assertEqual(evidence.load_record(prior[0][1])["definition"]["id"], "aggregate")
        self.state["integration_evidence"] = result["integration_evidence_patch"]
        self.ledger_path.write_text(json.dumps(self.state))
        (self.root / "unrelated.txt").write_text("Later independent edit.\n")
        next_output = self.artifacts / "later-refresh"
        self.bind_environment(next_output)
        later = self.run_refresh(execute=True, output=next_output)
        self.assertEqual(later["status"], "ready", later)
        self.assertEqual(marker.read_text().splitlines(), ["aggregate"])

    def test_aggregate_capture_without_child_contract_keeps_child_execution(self):
        marker = self.aggregate_plan()
        self.fixture.policy["tasks"]["T2"] = {**self.fixture.policy["tasks"]["T1"], "contract": "T2.md"}
        self.fixture.policy["tasks"]["T1"]["focused_checks"] = ["aggregate"]
        self.ledger(("T1", "T2"), capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertCountEqual(marker.read_text().splitlines(), ["aggregate", "focused"])
        self.assertEqual(next(row["action"] for row in result["tasks"]["T2"]["checks"]
                              if row["id"] == "focused"), "run")

    def test_aggregate_failure_does_not_publish_partial_task_evidence(self):
        marker = self.aggregate_plan(fail=True)
        self.ledger(("T1", "T2"), capture=False)
        before = self.ledger_path.read_bytes()
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(marker.read_text().splitlines(), ["aggregate"])
        self.assertEqual(result["integration_evidence_patch"], {})
        self.assertEqual(self.ledger_path.read_bytes(), before)

    def test_aggregate_preserves_required_fresh_child_for_each_snapshot(self):
        marker = self.aggregate_plan(child_fresh=True)
        self.ledger(("T1", "T2"), capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        executions = marker.read_text().splitlines()
        self.assertEqual(executions.count("focused"), 2)
        self.assertEqual(executions.count("aggregate"), 1)
        for task in result["tasks"].values():
            self.assertEqual(next(row["action"] for row in task["checks"] if row["id"] == "focused"), "run")

    def test_aggregate_keeps_distinct_environment_command(self):
        marker = self.aggregate_plan(separate_environment=True)
        self.ledger(capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertCountEqual(marker.read_text().splitlines(), ["aggregate", "other-environment"])
        self.assertEqual(set(row["id"] for row in result["tasks"]["T1"]["checks"]),
                         {"focused", "aggregate", "other-environment"})

    def test_unselected_optional_aggregate_does_not_replace_focused_check(self):
        marker = self.aggregate_plan()
        self.fixture.plan["required_checks"]["aggregate"] = False
        self.fixture.policy["tasks"]["T1"]["focused_checks"] = ["focused"]
        self.ledger(capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(marker.read_text().splitlines(), ["focused"])
        self.assertEqual([row["id"] for row in feature.requirements(self.policy_path, self.root)["checks"]], ["focused"])

    def test_aggregate_projection_does_not_add_optional_child(self):
        marker = self.aggregate_plan()
        self.fixture.plan["required_checks"]["focused"] = False
        self.fixture.policy["tasks"]["T1"]["focused_checks"] = ["aggregate"]
        self.ledger(capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(marker.read_text().splitlines(), ["aggregate"])
        final = feature.requirements(self.policy_path, self.root)
        self.assertEqual([row["id"] for row in final["checks"]], ["aggregate"])
        self.assertEqual(final["checks"][0]["covers"]["checks"], ["focused"])
        self.assertEqual([row["id"] for row in result["tasks"]["T1"]["checks"]], ["aggregate"])

    def test_cli_preview_without_environment_exposes_bindings_without_writes(self):
        self.ledger(capture=False)
        command = [sys.executable, str(Path(refresh.__file__).resolve()), "--policy", str(self.policy_path),
                   "--root", str(self.root), "--base", self.base, "--ledger", str(self.ledger_path),
                   "--output", str(self.output)]
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "preview")
        self.assertTrue(result["environment_required"])
        self.assertEqual(len(result["request"]["source_id"]), 64)
        self.assertEqual(len(result["request"]["context_id"]), 64)
        self.assertFalse(self.output.exists())
        rejected = subprocess.run([*command, "--execute"], capture_output=True, text=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("explicit environment", rejected.stderr)
        self.assertFalse(self.output.exists())

    def test_preview_is_read_only_and_does_not_run_commands(self):
        self.ledger()
        before = self.ledger_path.read_bytes()
        with patch.object(evidence, "run_check", side_effect=AssertionError("must not execute")):
            result = self.run_refresh()
        self.assertEqual(result["status"], "preview")
        self.assertFalse(self.output.exists())
        self.assertEqual(before, self.ledger_path.read_bytes())
        self.assertFalse(result["feature_accepted"])

    def test_two_tasks_share_one_new_execution(self):
        self.ledger(("T1", "T2"), capture=False)
        before = self.ledger_path.read_bytes()
        with patch.object(evidence, "run_check", wraps=evidence.run_check) as run:
            result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(run.call_count, 1)
        self.assertIn(result["tasks"]["T2"]["checks"][0]["action"], {"reuse", "transfer"})
        self.assertEqual(set(result["integration_evidence_patch"]), {"T1", "T2"})
        self.assertEqual(before, self.ledger_path.read_bytes())
        self.assertNotIn("feature_review", result["integration_evidence_patch"]["T1"])

    def test_unchanged_inputs_reuse_original_after_unrelated_change(self):
        self.ledger(("T1", "T2"))
        (self.root / "unrelated.txt").write_text("Other behavior.\n")
        self.bind_environment()
        with patch.object(evidence, "run_check", side_effect=AssertionError("must reuse")):
            result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertTrue(all(row["checks"][0]["action"] == "transfer" for row in result["tasks"].values()))

    def test_changed_inputs_execute_once_across_tasks(self):
        self.ledger(("T1", "T2"))
        (self.root / "app.txt").write_text("New behavior.\n")
        self.bind_environment()
        with patch.object(evidence, "run_check", wraps=evidence.run_check) as run:
            result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(run.call_count, 1)

    def test_fresh_checks_run_for_each_target_snapshot(self):
        self.fixture.check["fresh"] = True
        self.ledger(("T1", "T2"))
        with patch.object(evidence, "run_check", wraps=evidence.run_check) as run:
            result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        self.assertEqual(run.call_count, 2)

    def test_source_mutation_discards_entire_patch_and_preserves_failure(self):
        self.fixture.check["command"] = [sys.executable, "-c", "from pathlib import Path; Path('app.txt').write_text('changed')"]
        self.ledger(capture=False)
        before = self.ledger_path.read_bytes()
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["integration_evidence_patch"], {})
        self.assertTrue(result["captures"])
        self.assertEqual(before, self.ledger_path.read_bytes())
        self.assertTrue((self.output / "result.json").is_file())

    def test_failed_later_check_resume_reuses_completed_original(self):
        marker = self.artifacts / "allow-pass"
        self.fixture.plan["requirements"]["checks"].append({**self.fixture.check, "id": "second", "command": [
            sys.executable, "-c", f"from pathlib import Path; raise SystemExit(0 if Path({str(marker)!r}).exists() else 1)"]})
        self.fixture.plan["required_checks"]["second"] = True
        self.fixture.policy["tasks"]["T1"]["focused_checks"].append("second")
        self.ledger(capture=False)
        first = self.run_refresh(execute=True)
        self.assertEqual(first["status"], "blocked")
        saved = (self.output / "result.json").read_bytes()
        marker.touch()
        new_output = self.artifacts / "retry"
        self.bind_environment(new_output)
        with patch.object(evidence, "run_check", wraps=evidence.run_check) as run:
            second = self.run_refresh(execute=True, output=new_output, resume_from=self.output / "result.json")
        self.assertEqual(second["status"], "ready", second)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(saved, (self.output / "result.json").read_bytes())

    def test_completed_replay_runs_nothing(self):
        self.ledger(capture=False)
        result = self.run_refresh(execute=True)
        before = (self.output / "result.json").read_bytes()
        with patch.object(evidence, "run_check", side_effect=AssertionError("must not rerun")):
            replay = self.run_refresh(execute=True)
        self.assertEqual(replay, result)
        self.assertEqual(before, (self.output / "result.json").read_bytes())

    def test_changed_environment_evidence_blocks_before_commands(self):
        self.ledger(capture=False)
        (self.artifacts / "environment-proof.txt").write_text("Changed.\n")
        with patch.object(evidence, "run_check", side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(ValueError, "assessment evidence changed"):
                self.run_refresh(execute=True)
        self.assertFalse(self.output.exists())

    def test_pending_and_unknown_calls_block_before_commands(self):
        self.ledger(capture=False)
        for status in ("pending", "unknown"):
            self.state["call_ledger"]["calls"] = {"call": {"status": status}}
            self.ledger_path.write_text(json.dumps(self.state))
            with self.assertRaisesRegex(ValueError, "pending or unknown"):
                self.run_refresh(execute=True)
        self.assertFalse(self.output.exists())

    def test_old_plan_without_policy_is_not_migrated(self):
        self.ledger()
        plan_path = Path(self.state["call_ledger"]["plan"]["path"])
        plan = evidence.read_json(plan_path)
        del plan["review_policy"]
        plan_path.write_text(json.dumps(plan))
        self.state["call_ledger"]["plan"] = evidence.evidence_link(plan_path)
        self.ledger_path.write_text(json.dumps(self.state))
        before = self.ledger_path.read_bytes()
        with self.assertRaises((ValueError, KeyError)):
            self.run_refresh(execute=True)
        self.assertEqual(before, self.ledger_path.read_bytes())
        self.assertFalse(self.output.exists())

    def test_critical_refresh_preserves_original_receipt_and_checks_environment(self):
        snapshot, packet, reference, ledger = self.fixture.scoped_fixture()
        entry = {"snapshot": evidence.evidence_link(snapshot), "evidence_packet": evidence.evidence_link(packet),
                 "base": self.base, "launch_manifest": "artifacts/T1/launch-manifest.json"}
        self.ledger_path.write_text(json.dumps({"call_ledger": ledger, "integration_evidence": {"T1": entry}}))
        (self.root / "later.txt").write_text("Independent later change.\n")
        self.bind_environment()
        with patch.object(evidence, "run_check", side_effect=AssertionError("must reuse")):
            result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        refreshed = result["integration_evidence_patch"]["T1"]["critical_review"]
        self.assertEqual(refreshed["snapshot"], reference["snapshot"])
        self.assertEqual(refreshed["call_id"], reference["call_id"])
        self.assertIn("assessment", refreshed)
        self.assertFalse(result["feature_accepted"])

    def test_legacy_critical_blocks_before_commands(self):
        self.fixture.policy["tasks"]["T1"]["review"] = "critical"
        self.ledger()
        with patch.object(evidence, "run_check", side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(ValueError, "scoped reuse was not approved"):
                self.run_refresh(execute=True)
        self.assertFalse(self.output.exists())

    def test_guarded_apply_uses_real_queue_and_replay_preserves_state(self):
        fx = queue_fixtures.TaskQueueTests()
        fx.setUp()
        self.addCleanup(fx.doCleanups)
        config, plan, ledger = fx.feature_fixture(("T1", "T2"))
        fx.feature_implementation("T1", plan)
        fx.feature_capture("T1", ledger)
        output = fx.artifacts / "refresh"
        proof = fx.artifacts / "environment-proof.txt"
        proof.write_text("Current environment inspected.\n")
        environment = {key: {"reason": "Current evidence checked.", "evidence": [evidence.evidence_link(proof)]}
                       for key in ("runtime", "dependencies", "external_state", "base_interactions")}
        environment.update(to_source_id=evidence.digest(evidence.source_state(fx.root, "HEAD", fx.artifacts)),
                           context_id=evidence.digest({"runtime": "fixture"}))
        environment_path = fx.artifacts / "environment.json"
        environment_path.write_text(json.dumps(environment))
        result = refresh.refresh(fx.root / "policy.json", fx.root, "HEAD", ledger, output, environment_path, execute=True)
        self.assertEqual(result["status"], "ready", result)
        old = evidence.read_json(ledger)
        applied = refresh.apply_result(output / "result.json", fx.root)
        self.assertEqual(applied["status"], "applied", applied)
        state = evidence.read_json(ledger)
        self.assertEqual(state["call_ledger"], old["call_ledger"])
        self.assertNotIn("feature_review", state)
        before = ledger.read_bytes()
        replay = refresh.apply_result(output / "result.json", fx.root)
        self.assertEqual(replay["status"], "already-applied")
        self.assertEqual(ledger.read_bytes(), before)
        schedule = queue_fixtures.queue.schedule(config, plan, ledger, fx.root)
        self.assertEqual(schedule["implemented"], ["T1"])
        self.assertEqual(schedule["integrated"], [])

    def test_apply_checks_ledger_hash_without_mutation(self):
        self.ledger(capture=False)
        self.run_refresh(execute=True)
        self.state["new_fact"] = True
        self.ledger_path.write_text(json.dumps(self.state))
        before = self.ledger_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "ledger changed"):
            refresh.apply_result(self.output / "result.json", self.root)
        self.assertEqual(before, self.ledger_path.read_bytes())

    def test_apply_rejects_missing_actual_implementation_receipt(self):
        self.ledger(capture=False)
        result = self.run_refresh(execute=True)
        self.assertEqual(result["status"], "ready", result)
        before = self.ledger_path.read_bytes()
        with self.assertRaises(ValueError):
            refresh.apply_result(self.output / "result.json", self.root)
        self.assertEqual(before, self.ledger_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
