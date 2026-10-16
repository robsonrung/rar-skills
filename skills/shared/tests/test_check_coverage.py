#!/usr/bin/env python3
"""Check that declared aggregate coverage preserves executable evidence."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import review_evidence as evidence


class CheckCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.records = Path(self.temp.name) / "records"
        self.records.mkdir()
        self.calls = self.records / "calls.txt"
        self.contract = self.records / "contract.md"
        self.contract.write_text("All checks must pass.\n")
        (self.root / "app.txt").write_text("valid\n")
        (self.root / "other.txt").write_text("unrelated\n")
        (self.root / "checks.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "with Path(sys.argv[2]).open('a') as calls: calls.write(sys.argv[1] + '\\n')\n"
            "def unit(): assert Path('app.txt').read_text().strip() == 'valid'\n"
            "def lint(): assert '\\t' not in Path('app.txt').read_text()\n"
            "checks = {'unit': unit, 'lint': lint}\n"
            "for name in (checks if sys.argv[1] == 'all' else [sys.argv[1]]): checks[name]()\n")
        for args in [("init", "-q"), ("config", "user.name", "Test"),
                     ("config", "user.email", "test@example.test"), ("add", "."), ("commit", "-qm", "Fixture")]:
            self.git(*args)
        self.base = self.git("rev-parse", "HEAD").strip()
        self.plan = {"context": {"runtime": sys.version}, "checks": [], "observations": [], "exclusions": {}}
        for key in ("all", "unit", "lint"):
            self.plan["checks"].append({"id": key, "command": [sys.executable, "checks.py", key, str(self.calls)],
                                        "cwd": ".", "timeout_seconds": 5, "environment": "local-python",
                                        "inputs": ["app.txt", "checks.py"]})
        self.plan["checks"][0]["covers"] = {"checks": ["unit", "lint"],
            "evidence": [{"path": "checks.py", "sha256": evidence.file_hash(self.root / "checks.py")}],
            "reason": "checks.py all invokes unit and lint in the same process and environment."}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True)

    def prepare(self, name="current", plan=None):
        requirements = self.records / f"{name}.requirements.json"
        requirements.write_text(json.dumps(self.plan if plan is None else plan))
        return evidence.prepare(self.root, self.base, self.contract, requirements,
                                self.records / name, artifact_dir=self.records)

    def actions(self, path, **kwargs):
        return {row["id"]: row for row in evidence.select_checks(path, **kwargs)["checks"]}

    def assessment(self, old, target):
        proof = self.records / "environment.txt"
        proof.write_text("Runtime, dependencies, external state and base interactions checked.\n")
        row = {"reason": "The observed environment is unchanged.", "evidence": [evidence.evidence_link(proof)]}
        payload = {"from_snapshot_sha256": evidence.file_hash(old),
                   "to_source_id": evidence.load_record(target)["source_id"],
                   **{key: row for key in ("runtime", "dependencies", "external_state", "base_interactions")}}
        path = self.records / (target.parent.name + ".assessment.json")
        path.write_text(json.dumps(payload))
        return path

    def test_aggregate_runs_once_and_preserves_all_required_evidence_and_acceptance(self):
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot)
        self.assertTrue(result["passed"])
        self.assertEqual(self.calls.read_text().splitlines(), ["all"])
        self.assertEqual(set(result["captures"]), {"all", "unit", "lint"})
        covered = evidence.load_record(result["captures"]["unit"])
        self.assertEqual(covered["kind"], "coverage")
        self.assertNotIn("exit_code", covered)
        self.assertNotIn("logs", covered)
        packet = evidence.prepare_packet(snapshot, self.records / "packet.json", observations=[])
        response = {"snapshot_sha256": evidence.file_hash(snapshot), "coverage": [], "findings": [],
                    "evidence_packet": evidence.evidence_link(packet), "summary": "Checks and review pass."}
        evidence.record_review(snapshot, response, {"success": True, "agent_message": json.dumps(response)})
        self.assertEqual(evidence.assess(snapshot, self.base)["status"], "ready")

    def test_fresh_and_explicit_fresh_execute_children(self):
        self.plan["checks"][1]["fresh"] = True
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot, fresh=["lint"])
        self.assertTrue(result["passed"])
        self.assertEqual(self.calls.read_text().splitlines(), ["all", "unit", "lint"])
        self.assertNotIn("kind", evidence.load_record(result["captures"]["unit"]))

    def test_distinct_or_missing_environment_does_not_cover(self):
        for index, environment in ((1, "other-platform"), (2, None)):
            if environment:
                self.plan["checks"][index]["environment"] = environment
            else:
                self.plan["checks"][index].pop("environment")
        result = evidence.run_plan(self.prepare())
        self.assertEqual(self.calls.read_text().splitlines(), ["all", "unit", "lint"])
        self.assertTrue(result["passed"])

    def test_optional_aggregate_is_never_activated(self):
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot, selected=["unit", "lint"])
        self.assertEqual(self.calls.read_text().splitlines(), ["unit", "lint"])
        self.assertEqual(set(result["captures"]), {"unit", "lint"})

    def test_insufficient_or_unknown_child_inputs_execute_independently(self):
        self.plan["checks"][1]["inputs"].append("other.txt")
        self.plan["checks"][2].pop("inputs")
        result = evidence.run_plan(self.prepare())
        self.assertEqual(self.calls.read_text().splitlines(), ["all", "unit", "lint"])
        self.assertTrue(result["passed"])

    def test_whole_source_aggregate_can_cover_unknown_child_scope(self):
        for row in self.plan["checks"]:
            row.pop("inputs")
        self.assertTrue(evidence.run_plan(self.prepare())["passed"])
        self.assertEqual(self.calls.read_text().splitlines(), ["all"])

    def test_failure_cannot_create_coverage_or_complete_packet(self):
        (self.root / "app.txt").write_text("invalid\n")
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot)
        self.assertFalse(result["passed"])
        self.assertEqual(set(result["captures"]), {"all"})
        with self.assertRaisesRegex(ValueError, "did not pass"):
            evidence.cover_check(snapshot, "unit", result["captures"]["all"])
        with self.assertRaises(OSError):
            evidence.prepare_packet(snapshot, self.records / "packet.json", observations=[])

    def test_direct_check_still_executes_requested_child(self):
        snapshot = self.prepare()
        evidence.run_check(snapshot, "unit")
        self.assertEqual(self.calls.read_text().splitlines(), ["unit"])

    def test_modified_or_missing_config_is_rejected(self):
        snapshot = self.prepare()
        (self.root / "checks.py").write_text("print('different')\n")
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            evidence.select_checks(snapshot)
        (self.root / "checks.py").unlink()
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            self.prepare("missing")

    def test_coverage_config_must_be_captured_and_in_scoped_inputs(self):
        self.plan["checks"][0]["inputs"] = ["app.txt"]
        with self.assertRaisesRegex(ValueError, "omit coverage configuration"):
            self.prepare()
        self.plan["checks"][0].pop("inputs")
        config = self.root / "ignored.json"
        config.write_text("{}")
        (self.root / ".gitignore").write_text("ignored.json\n")
        self.plan["checks"][0]["covers"]["evidence"] = [{"path": "ignored.json", "sha256": evidence.file_hash(config)}]
        with self.assertRaisesRegex(ValueError, "outside captured source"):
            self.prepare("ignored")

    def test_nested_and_self_coverage_rejected(self):
        self.plan["checks"][0]["covers"]["checks"].append("all")
        with self.assertRaisesRegex(ValueError, "itself"):
            self.prepare()
        self.plan["checks"][0]["covers"]["checks"].remove("all")
        self.plan["checks"][1]["covers"] = copy.deepcopy(self.plan["checks"][0]["covers"])
        self.plan["checks"][1]["covers"]["checks"] = ["lint"]
        with self.assertRaisesRegex(ValueError, "nested or cyclic"):
            self.prepare("nested")

    def test_tampered_aggregate_output_invalidates_covered_packet(self):
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot)
        aggregate = Path(result["captures"]["all"])
        (aggregate.parent / "stdout.log").write_text("altered")
        with self.assertRaisesRegex(ValueError, "log checksum"):
            evidence.validate_check(result["captures"]["unit"], evidence.load_record(snapshot), self.plan["checks"][1])

    def test_rebound_coverage_record_cannot_claim_execution_fields(self):
        snapshot = self.prepare()
        result = evidence.run_plan(snapshot)
        path = Path(result["captures"]["unit"])
        record = evidence.load_record(path)
        record["exit_code"] = 0
        path.unlink()
        evidence.write_record(path, record)
        with self.assertRaisesRegex(ValueError, "invalid derived"):
            evidence.validate_check(path, evidence.load_record(snapshot), self.plan["checks"][1])

    def test_transferred_original_aggregate_rebuilds_covered_records(self):
        old = self.prepare("old")
        first = evidence.run_plan(old)
        (self.root / "other.txt").write_text("independent change\n")
        target = self.prepare("target")
        actions = self.actions(target, from_snapshot=old, checks=first["captures"])
        self.assertEqual(actions["all"]["action"], "transfer")
        self.assertEqual(actions["unit"]["action"], "covered")
        with self.assertRaisesRegex(ValueError, "original captured"):
            evidence.transfer_check(old, target, first["captures"]["unit"], self.assessment(old, target))
        aggregate = evidence.transfer_check(old, target, first["captures"]["all"], self.assessment(old, target))
        child = evidence.cover_check(target, "unit", aggregate)
        self.assertTrue(evidence.validate_check(child, evidence.load_record(target), self.plan["checks"][1]))
        self.assertEqual(self.calls.read_text().splitlines(), ["all"])

    def test_changed_child_definition_does_not_reuse_aggregate_coverage(self):
        old = self.prepare("old")
        aggregate = evidence.run_check(old, "all")
        self.plan["checks"][1]["command"].append("changed-argument")
        target = self.prepare("target")
        actions = self.actions(target, from_snapshot=old, checks={"all": str(aggregate)})
        self.assertEqual(actions["all"]["action"], "transfer")
        self.assertEqual(actions["unit"]["action"], "run")
        self.assertEqual(actions["lint"]["action"], "covered")
        moved = evidence.transfer_check(old, target, aggregate, self.assessment(old, target))
        with self.assertRaisesRegex(ValueError, "matching covered"):
            evidence.cover_check(target, "unit", moved)

    def test_narrow_origin_cannot_prove_child_added_in_later_projection(self):
        narrow = copy.deepcopy(self.plan)
        narrow["checks"] = narrow["checks"][:1]
        old = self.prepare("old", narrow)
        aggregate = evidence.run_check(old, "all")
        target = self.prepare("target")
        actions = self.actions(target, from_snapshot=old, checks={"all": str(aggregate)})
        self.assertEqual(actions["all"]["action"], "transfer")
        self.assertEqual(actions["unit"]["action"], "run")
        self.assertEqual(actions["lint"]["action"], "run")

    def test_source_or_context_changes_require_new_aggregate_execution(self):
        old = self.prepare("old")
        aggregate = evidence.run_check(old, "all")
        self.plan["context"]["runtime"] = "different-runtime"
        target = self.prepare("context")
        self.assertEqual(self.actions(target, from_snapshot=old, checks={"all": str(aggregate)})["all"]["action"], "run")
        self.plan["context"]["runtime"] = sys.version
        (self.root / "app.txt").write_text("valid\n\n")
        target = self.prepare("source")
        self.assertEqual(self.actions(target, from_snapshot=old, checks={"all": str(aggregate)})["all"]["action"], "run")

    def test_cli_fresh_selection_runs_explicit_child(self):
        snapshot = self.prepare()
        result = subprocess.run([sys.executable, evidence.__file__, "run-plan", "--snapshot", str(snapshot),
                                 "--id", "all", "--id", "unit", "--fresh", "unit"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])
        self.assertEqual(self.calls.read_text().splitlines(), ["all", "unit"])
        with self.assertRaisesRegex(ValueError, "outside selected"):
            evidence.select_checks(snapshot, selected=["all"], fresh=["unit"])

    def test_legacy_plan_without_coverage_runs_all_commands(self):
        self.plan["checks"][0].pop("covers")
        for row in self.plan["checks"]:
            row.pop("environment")
        self.assertTrue(evidence.run_plan(self.prepare())["passed"])
        self.assertEqual(self.calls.read_text().splitlines(), ["all", "unit", "lint"])


if __name__ == "__main__":
    unittest.main()
