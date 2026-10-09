#!/usr/bin/env python3
"""Exercise capture through real CLI writes and synthetic execution receipts."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import run_state as ledger
import workflow_comparison as comparison
from execution_metrics import normalize_metrics

IDENTITY = {"case_id": "local-capture", "case_kind": "bounded-fix", "source_start_revision": "a" * 40,
            "requirements_sha256": "b" * 64, "checks_sha256": "c" * 64, "environment_sha256": "d" * 64}


def write(path, value):
    path.write_text(json.dumps(value))
    return path


def ref(path):
    return {"path": str(path), "sha256": ledger.sha(path)}


def cli(path, *args, code=0):
    result = subprocess.run([sys.executable, str(SCRIPTS / "run_state.py"), "--state", str(path), *map(str, args)],
                            capture_output=True, text=True)
    if result.returncode != code:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def fixture(root):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "state.json"
    event_file = root / "event.json"
    def capture(id, kind, **facts):
        write(event_file, {"id": id, "kind": kind, **facts})
        return cli(path, "capture", "--event", event_file)
    capture("start", "start", identity=IDENTITY)
    for stage in ("to-prd", "to-tasks"):
        capture(stage + "-start", "stage-start", stage=stage)
        capture(stage + "-end", "stage-end", stage=stage)
    route = {"id": "writer", "task_id": "T1", "model": "fixture", "effort": "high"}
    plan = write(root / "plan.json", {"approval": {"status": "approved"}, "routes": [route, {**route, "id": "reviewer"}]})
    limits = write(root / "limits.json", {"total_role_calls": 3, "writer": 2, "reviewer": 1})
    cli(path, "init", "--plan", plan, "--run-id", root.name, "--limits", limits)
    brief = root / "brief.md"
    brief.write_text("Synthetic fixture only.")
    capture("implementation-start", "stage-start", stage="implement-tasks")
    cli(path, "reserve", "--route", "writer", "--call", "failed", "--brief", brief, "--phase", "implementation")
    cli(path, "reserve", "--route", "reviewer", "--call", "review", "--brief", brief, "--phase", "review")
    capture("wait-a-start", "wait-start", wait="a")
    capture("wait-b-start", "wait-start", wait="b")
    capture("wait-a-end", "wait-end", wait="a")
    capture("wait-b-end", "wait-end", wait="b")
    for call, success, context in (("failed", False, "writer-context"), ("review", True, "review-context"), ("repair", True, "writer-context")):
        if call == "repair":
            cli(path, "reserve", "--route", "writer", "--call", call, "--brief", brief, "--phase", "repair")
            capture("repair-id", "repair", call_id=call)
        receipt = write(root / (call + ".json"), {
            "success": success, "call_id": call, "input_revision": ledger.sha(brief),
            "configured_model": "fixture", "configured_effort": "high", "context_id": context,
            "native_usage": {"input": 2, "cacheRead": 3, "cacheWrite": 0, "output": 2, "cost": {"total": 0.002}},
            "native_usage_total": {"input": 10, "cacheRead": 70, "cacheWrite": 20, "output": 15, "cost": {"total": 0.01}},
            "duration_ms": 5})
        cli(path, "reconcile", "--call", call, "--receipt", receipt)
    capture("implementation-end", "stage-end", stage="implement-tasks")
    capture("validation-start", "stage-start", stage="validate-e2e")
    for n in range(2):
        started = ledger.now()
        result = subprocess.run([sys.executable, "-c", "print('fixture command')"], capture_output=True, text=True)
        evidence = root / f"command-{n}.txt"
        evidence.write_text(result.stdout)
        capture(f"command-{n}", "command", key="fixture-command@fixture-root", evidence=ref(evidence),
                started_at=started, exit_code=result.returncode)
    # A retry captures the same execution; evidence reuse creates no new event.
    cli(path, "capture", "--event", event_file)
    coordinator = write(root / "coordinator.json", {"metrics": {"input_tokens": 4, "cached_input_tokens": 0,
                        "cache_write_input_tokens": 0, "output_tokens": 2, "reasoning_output_tokens": 0,
                        "duration_ms": 1, "reported_cost_usd": 0.005}})
    capture("coordinator", "coordinator", receipt=ref(coordinator))
    capture("validation-end", "stage-end", stage="validate-e2e")
    capture("terminal", "terminal", status="complete")
    capture("coverage", "coverage", areas=["workers", "coordinator", "commands", "waits", "repairs"])
    observation = root / "observation.txt"
    observation.write_text("Synthetic acceptance passed. Fixture fault probes found no missed defects.")
    capture("outcome", "outcome", acceptance={"passed": True, "evidence": ref(observation)},
            missed_defects={"count": 0, "evidence": ref(observation), "observation_window": "local fixture assertions"})
    return path


def fixture_pair(root):
    before, after = fixture(root / "baseline"), fixture(root / "candidate")
    process = subprocess.run([sys.executable, str(SCRIPTS / "workflow_comparison.py"), "--baseline", str(before),
                              "--candidate", str(after)], capture_output=True, text=True)
    if process.returncode != 1:
        raise AssertionError(process.stdout + process.stderr)
    report = json.loads(process.stdout)
    write(root / "comparison.json", report)
    return report


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_actual_cli_pair_keeps_unknown_reasoning_and_observed_elapsed(self):
        report = fixture_pair(self.root)
        self.assertTrue(report["observed_acceptance_match"])
        self.assertEqual(report["status"], "incomplete")
        for name in ("baseline", "candidate"):
            row = report[name]
            self.assertEqual(row["incomplete_fields"], ["workers.reasoning_output_tokens"])
            self.assertEqual((row["worker_calls"], row["failed_calls"], row["repair_calls"]), (3, 1, 1))
            self.assertEqual((row["commands"], row["repeated_commands"]), (2, 1))
            self.assertEqual(row["workers"]["input_tokens"]["measured_sum"], 300)
            self.assertAlmostEqual(row["total_reported_cost_usd"], 0.035)
            self.assertGreater(row["workflow_elapsed_ms"], row["approval_wait_ms"])
            self.assertEqual(len(row["stage_elapsed_ms"]), 4)
        self.assertEqual(report["deltas"]["workers"]["input_tokens"], 0)
        self.assertIsNone(report["deltas"]["workers"]["reasoning_output_tokens"])
        state = json.loads((self.root / "candidate" / "state.json").read_text())
        self.assertEqual(state["status"], "running")
        original = copy.deepcopy(state)
        replacement = copy.deepcopy(state["workflow_measurement"]["events"]["outcome"]["input"])
        replacement["id"] = "replace-outcome"
        replacement["missed_defects"]["observation_window"] = "different protocol"
        with self.assertRaisesRegex(ValueError, "already has different facts"):
            ledger.capture(state, replacement)
        self.assertEqual(state, original)
        state["workflow_measurement"]["identity"]["case_id"] = "different"
        baseline = json.loads((self.root / "baseline" / "state.json").read_text())
        self.assertEqual(comparison.compare(baseline, state)["status"], "mismatched")
        state["workflow_measurement"]["identity"] = copy.deepcopy(IDENTITY)
        state["workflow_measurement"]["missed_defects"]["observation_window"] = "different protocol"
        mismatch = comparison.compare(baseline, state)
        self.assertEqual(mismatch["status"], "mismatched")
        self.assertEqual(mismatch["mismatched_fields"], ["missed_defects.observation_window"])
        self.assertIsNone(mismatch["deltas"])
        self.assertFalse(mismatch["observed_acceptance_match"])
        del state["workflow_measurement"]["missed_defects"]
        self.assertIsNone(comparison.compare(baseline, state)["deltas"])

    def test_separate_stage_authority_imports_without_double_counting(self):
        feature = {}
        ledger.capture(feature, {"id": "start", "kind": "start", "identity": IDENTITY})
        unknown_feature = copy.deepcopy(feature)
        stage = {}
        ledger.capture(stage, {"id": "start", "kind": "start", "identity": {}})
        brief = self.root / "brief.md"
        brief.write_text("Synthetic stage input.")
        route = {"id": "worker", "task_id": "T1", "model": "fixture", "effort": "high"}
        def initialize(state, name):
            plan = write(self.root / (name + "-plan.json"), {"approval": {"status": "approved"}, "stage": name, "routes": [route]})
            ledger.initialize(state, plan, name, {"total_role_calls": 2, "worker": 2})
        def execute(state, name):
            ledger.reserve(state, "worker", name, brief, "work")
            receipt = write(self.root / (name + "-receipt.json"), {
                "success": True, "call_id": name, "input_revision": ledger.sha(brief), "configured_model": "fixture",
                "configured_effort": "high", "context_id": name, "native_usage_total": {
                    "input": 10, "output": 5, "cacheRead": 20, "cacheWrite": 0, "cost": {"total": .01}}})
            ledger.reconcile(state, name, receipt)
        initialize(stage, "interview")
        execute(stage, "interview-call")
        stage["status"] = "complete"
        ledger.capture(stage, {"id": "terminal", "kind": "terminal", "status": "complete"})
        uncovered_stage = copy.deepcopy(stage)
        ledger.capture(stage, {"id": "repairs", "kind": "coverage", "areas": ["repairs"]})
        self.assertNotIn("repair_call_ids", stage["workflow_measurement"])
        stage_path = write(self.root / "interview-state.json", stage)
        original = stage_path.read_bytes()
        event = {"id": "import", "kind": "stage-ledger", "stage": "interview-me", "ledger": ref(stage_path)}
        ledger.capture(feature, event)
        ledger.capture(feature, event)
        # The same receipt under another import must not count twice.
        ledger.capture(feature, {**event, "id": "duplicate-import", "stage": "same-call"})
        initialize(feature, "implementation")
        execute(feature, "implementation-call")
        ledger.capture(feature, {"id": "terminal", "kind": "terminal", "status": "complete"})
        ledger.capture(feature, {"id": "coverage", "kind": "coverage", "areas": ["workers", "repairs"]})
        with self.assertRaisesRegex(ValueError, "terminal"):
            ledger.reserve(feature, "worker", "reopened", brief, "work")
        report = comparison.summarize(feature)
        self.assertEqual(report["worker_calls"], 2)
        self.assertEqual(report["workers"]["input_tokens"]["measured_sum"], 60)
        self.assertEqual(report["repair_calls"], 0)
        self.assertEqual(feature["attempts"]["total_role_calls"], 1)
        self.assertEqual(stage_path.read_bytes(), original)
        self.assertNotEqual(feature["call_ledger"]["plan"], stage["call_ledger"]["plan"])
        uncovered_path = write(self.root / "uncovered-interview.json", uncovered_stage)
        ledger.capture(unknown_feature, {"id": "import", "kind": "stage-ledger", "stage": "interview-me", "ledger": ref(uncovered_path)})
        ledger.capture(unknown_feature, {"id": "terminal", "kind": "terminal", "status": "complete"})
        ledger.capture(unknown_feature, {"id": "coverage", "kind": "coverage", "areas": ["workers", "repairs"]})
        self.assertIsNone(comparison.summarize(unknown_feature)["repair_calls"])
        incomplete = copy.deepcopy(feature)
        del incomplete["workflow_measurement"]["stage_ledgers"]["interview-me"]["repair_call_ids"]
        self.assertIsNone(comparison.summarize(incomplete)["repair_calls"])

    def test_missing_or_pending_stage_import_preserves_unknown_coverage(self):
        state = {}
        ledger.capture(state, {"id": "s", "kind": "start", "identity": IDENTITY})
        original = copy.deepcopy(state)
        source = write(self.root / "pending.json", {"status": "complete", "call_ledger": {"calls": {"call": {"status": "pending"}}}})
        with self.assertRaisesRegex(ValueError, "unresolved"):
            ledger.capture(state, {"id": "stage", "kind": "stage-ledger", "stage": "to-prd", "ledger": ref(source)})
        self.assertEqual(state, original)
        self.assertIsNone(comparison.summarize(state)["worker_calls"])
        with self.assertRaises(OSError):
            ledger.capture(state, {"id": "stage", "kind": "stage-ledger", "stage": "to-prd",
                                   "ledger": {"path": str(self.root / "absent"), "sha256": "a" * 64}})
        self.assertEqual(state, original)

    def test_early_start_binds_identity_without_losing_prior_observations(self):
        state = {}
        ledger.capture(state, {"id": "s", "kind": "start", "identity": {"case_id": "local-capture"}})
        ledger.capture(state, {"id": "prd", "kind": "stage-start", "stage": "to-prd"})
        ledger.capture(state, {"id": "wait", "kind": "wait-start", "wait": "approval"})
        ledger.capture(state, {"id": "answer", "kind": "wait-end", "wait": "approval"})
        ledger.capture(state, {"id": "prd-end", "kind": "stage-end", "stage": "to-prd"})
        original = copy.deepcopy(state["workflow_measurement"])
        self.assertIn("identity.requirements_sha256", comparison.summarize(state)["incomplete_fields"])
        ledger.capture(state, {"id": "bind-prd", "kind": "identity", "identity": {"requirements_sha256": "b" * 64}})
        ledger.capture(state, {"id": "bind-rest", "kind": "identity", "identity": IDENTITY})
        plan = write(self.root / "plan.json", {"approval": {"status": "approved"}, "routes": []})
        ledger.initialize(state, plan, "run", {"total_role_calls": 1})
        measurement = state["workflow_measurement"]
        for key in ("started_at", "stages", "waits"):
            self.assertEqual(measurement[key], original[key])
        self.assertEqual(measurement["identity"], IDENTITY)
        bound = copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError, "already has different facts"):
            ledger.capture(state, {"id": "replace", "kind": "identity", "identity": {"checks_sha256": "e" * 64}})
        self.assertEqual(bound, state)

    def test_idempotence_conflicts_and_authority_are_atomic(self):
        state = {"attempts": {"total_role_calls": 9}, "gates": ["existing"], "status": "awaiting_human"}
        event = {"id": "start", "kind": "start", "identity": IDENTITY}
        ledger.capture(state, event)
        original = copy.deepcopy(state)
        self.assertEqual(ledger.capture(state, event)["capture"], "existing")
        self.assertEqual(original, state)
        for changed in ({**event, "identity": {**IDENTITY, "case_id": "changed"}},
                        {"id": "new", "kind": "stage-start", "stage": "x", "unexpected": True},
                        {"id": "new", "kind": "wait-end", "wait": "absent"},
                        {"id": "new", "kind": "coverage", "areas": ["workers"]},
                        {"id": "new", "kind": "command", "key": "x", "evidence": {}, "started_at": ledger.now(), "exit_code": True}):
            with self.assertRaises(ValueError):
                ledger.capture(state, changed)
            self.assertEqual(original, state)

    def test_unknown_coverage_remains_unknown_and_terminal_cannot_reopen(self):
        state = {}
        ledger.capture(state, {"id": "s", "kind": "start", "identity": IDENTITY})
        ledger.capture(state, {"id": "t", "kind": "terminal", "status": "failed"})
        report = comparison.summarize(state)
        self.assertIsNone(report["commands"])
        self.assertIsNone(report["repair_calls"])
        self.assertIsNone(report["coordinator"])
        with self.assertRaisesRegex(ValueError, "terminal"):
            ledger.capture(state, {"id": "new", "kind": "stage-start", "stage": "reopened"})

    def test_bad_evidence_and_event_time_do_not_write(self):
        path, event_path = self.root / "state.json", self.root / "event.json"
        write(event_path, {"id": "s", "kind": "start", "identity": IDENTITY})
        cli(path, "capture", "--event", event_path)
        original = path.read_bytes()
        for facts in ({"id": "bad", "kind": "stage-start", "stage": "x", "at": "bad"},
                      {"id": "bad", "kind": "coordinator", "receipt": {"path": str(event_path), "sha256": "a" * 64}}):
            write(event_path, facts)
            cli(path, "capture", "--event", event_path, code=2)
            self.assertEqual(path.read_bytes(), original)

    def test_concurrent_events_survive_atomic_updates(self):
        path = self.root / "state.json"
        processes = []
        for n in range(5):
            event = write(self.root / f"event-{n}.json", {"id": str(n), "kind": "stage-start", "stage": str(n)})
            processes.append(subprocess.Popen([sys.executable, str(SCRIPTS / "run_state.py"), "--state", str(path),
                                              "capture", "--event", str(event)], stdout=subprocess.PIPE, stderr=subprocess.PIPE))
        for process in processes:
            out, err = process.communicate()
            self.assertEqual(process.returncode, 0, out + err)
        self.assertEqual(len(json.loads(path.read_text())["workflow_measurement"]["events"]), 5)

    def test_actual_producer_partial_requests_remain_unknown_in_ledger_and_comparison(self):
        runner = SCRIPTS.parents[1] / "engineering" / "seats" / "pi-runner" / "scripts"
        sys.path.insert(0, str(runner))
        self.addCleanup(lambda: sys.path.remove(str(runner)))
        from run_pi import total_native_usage

        complete = {"input": 10, "output": 5, "cacheRead": 30, "cacheWrite": 10,
                    "totalTokens": 55, "cost": {"total": .02}}
        variants = [("complete", complete, None)]
        for field, metric in (("input", "input_tokens"), ("output", "output_tokens"),
                              ("cacheRead", "cached_input_tokens"), ("cacheWrite", "cache_write_input_tokens"),
                              ("cost", "reported_cost_usd")):
            partial = copy.deepcopy(complete)
            del partial[field]
            variants.append((field, partial, metric))
        variants.append(("cost-total", {**complete, "cost": {}}, "reported_cost_usd"))
        variants.append(("usage", None, "input_tokens"))
        for value in (True, -1, float("nan"), float("inf"), "10"):
            variants.append(("input-invalid-" + str(value), {**complete, "input": value}, "input_tokens"))
        brief = self.root / "brief.md"
        brief.write_text("Synthetic producer fixture.")
        route = {"id": "worker", "task_id": "T1", "model": "fixture", "effort": "high"}
        plan = write(self.root / "plan.json", {"approval": {"status": "approved"}, "routes": [route]})
        for name, usage, unknown in variants:
            with self.subTest(field=name):
                messages = [{"role": "assistant", "usage": complete}, {"role": "assistant"}]
                if usage is not None:
                    messages[1]["usage"] = usage
                events = [{"type": "message_end", "message": message} for message in messages]
                events += [{"type": "message_end", "message": {"role": "tool", "usage": complete}},
                           {"type": "agent_end", "messages": messages}]
                totals = total_native_usage("\n".join(json.dumps(event) for event in events))
                state = {}
                ledger.initialize(state, plan, name, {"total_role_calls": 1, "worker": 1})
                ledger.reserve(state, "worker", "call", brief, "work")
                receipt = write(self.root / (name + "-receipt.json"), {
                    "success": False, "call_id": "call", "input_revision": ledger.sha(brief),
                    "configured_model": "fixture", "configured_effort": "high",
                    "native_usage": usage, "native_usage_total": totals})
                ledger.reconcile(state, "call", receipt)
                row = comparison.summarize(state)["workers"]
                self.assertEqual(state["call_ledger"]["calls"]["call"]["status"], "failed")
                if unknown:
                    self.assertEqual(row[unknown], {"measured_sum": 0, "measured_calls": 0, "unknown_calls": 1})
                    if name in {"input", "cacheRead", "cacheWrite", "usage"}:
                        self.assertEqual(row["input_tokens"]["unknown_calls"], 1)
                    if name == "usage":
                        self.assertEqual(row["reported_cost_usd"]["unknown_calls"], 1)
                    elif name not in {"cost", "cost-total"}:
                        self.assertEqual(row["reported_cost_usd"]["measured_sum"], .04)
                    if name in {"cost", "cost-total"}:
                        self.assertEqual(row["input_tokens"]["measured_sum"], 100)
                else:
                    self.assertEqual(row["input_tokens"]["measured_sum"], 100)
                    self.assertEqual(row["reported_cost_usd"]["measured_sum"], .04)
                    self.assertEqual(row["output_tokens"]["measured_sum"], 10)

    def test_native_totals_override_last_message_and_preserve_unknowns(self):
        receipt = {"native_usage_total": {"input": 10, "cacheRead": 70, "cacheWrite": 20, "output": 15, "cost": {"total": .01}},
                   "native_usage": {"input": 999, "cacheRead": 0, "cacheWrite": 0, "output": 999, "cost": {"total": 99}}}
        row = normalize_metrics(receipt)
        self.assertEqual((row["input_tokens"], row["output_tokens"], row["reported_cost_usd"]), (100, 15, .01))
        self.assertIsNone(row["reasoning_output_tokens"])
        self.assertIsNone(row["duration_ms"])
        receipt["native_usage_total"] = {}
        self.assertTrue(all(value is None for value in normalize_metrics(receipt).values()))
        del receipt["native_usage_total"]
        self.assertEqual(normalize_metrics(receipt)["input_tokens"], 999)
        del receipt["native_usage"]["cacheWrite"]
        self.assertIsNone(normalize_metrics(receipt)["input_tokens"])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fixture-dir":
        print(json.dumps(fixture_pair(Path(sys.argv[2]).resolve()), indent=2))
    else:
        unittest.main()
