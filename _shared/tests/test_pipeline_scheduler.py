#!/usr/bin/env python3
"""Tests for the pipeline scheduler — the deterministic half of ship phases 3-6.

What is worth testing here is exactly what the scheduler took away from the
model: the ledger's arithmetic, the once-only retries, the readiness rule, and
the resume path. The agent's reasoning is not under test and is stubbed out.

The crash-resume case is not optional. `run-state-contract.md` calls it a
required check for any skill adopting the contract: kill a run mid-flight,
restart it, and assert it resumes at the right phase, that attempts survived,
and that no side effect executed twice.

All tests run offline — no agent is ever spawned.

Run: python3 _shared/tests/test_pipeline_scheduler.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import pipeline_scheduler as ps  # noqa: E402


TASKS_MD = """# TASKS

## T1. Ledger and resume

Status: todo

### Acceptance contract

- Commands: `python3 _shared/tests/test_pipeline_scheduler.py`
- Behaviors: a killed run resumes at its recorded phase

### Gates

- Lenses: agent-architecture-lens
- Security: standard

## Blocked by

None - can start immediately

## T2. Handoff I/O

Status: todo

### Acceptance contract

- Commands: `python3 scripts/check_leitworter.py`

## Blocked by

None - can start immediately

## T3. Step dispatch

Status: todo

### Acceptance contract

- Commands: `python3 _shared/tests/test_runner_parity.py`

## Blocked by

T1, T2

## T9. Already finished

Status: done

## Blocked by

None
"""


class LedgerTest(unittest.TestCase):
    """T1 — the run-state contract's arithmetic."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_contract_keys_present(self):
        state = ps.RunState.create(self.ws, "r1")
        for key in ("run_id", "skill", "status", "phase", "attempts",
                    "ceilings", "gates", "side_effects", "steps"):
            self.assertIn(key, state.data, f"missing contract key {key}")
        self.assertEqual(state.status, ps.RUNNING)

    def test_state_path_is_two_levels_deep_for_the_board(self):
        # pipeline-board globs .ai-workflow/*/*/run-state.json; a deeper path
        # would render no cards.
        path = ps.RunState.state_path(self.ws, "r1")
        self.assertEqual(path.relative_to(self.ws).parts,
                         (".ai-workflow", "ship", "r1", "run-state.json"))

    def test_attempt_is_counted_before_the_attempt(self):
        state = ps.RunState.create(self.ws, "r1")
        state.begin_attempt("fix_cycle", 3)
        # The increment must already be on disk — a crash mid-attempt still
        # counts as an attempt.
        reloaded = ps.RunState.load(self.ws, "r1")
        self.assertEqual(reloaded.attempts("fix_cycle"), 1)

    def test_ceiling_stops_the_loop(self):
        state = ps.RunState.create(self.ws, "r1")
        state.begin_attempt("evidence_recovery", 1)
        with self.assertRaises(ps.CeilingHit):
            state.begin_attempt("evidence_recovery", 1)

    def test_gate_survives_and_is_not_duplicated(self):
        state = ps.RunState.create(self.ws, "r1")
        self.assertFalse(state.has_gate(ps.APPROVAL_GATE))
        state.record_gate(ps.APPROVAL_GATE)
        state.record_gate(ps.APPROVAL_GATE)
        reloaded = ps.RunState.load(self.ws, "r1")
        self.assertTrue(reloaded.has_gate(ps.APPROVAL_GATE))
        self.assertEqual(len(reloaded.data["gates"]), 1)

    def test_side_effect_is_claimed_once(self):
        state = ps.RunState.create(self.ws, "r1")
        self.assertTrue(state.claim_side_effect("pr:feat-auth"))
        self.assertFalse(state.claim_side_effect("pr:feat-auth"))

    def test_steps_append_and_never_rewrite(self):
        state = ps.RunState.create(self.ws, "r1")
        state.record_step("03-design-gate", "failed")
        state.record_step("03-design-gate", "ok", report="r.md")
        self.assertEqual(len(state.data["steps"]), 2)
        self.assertEqual(state.step_result("03-design-gate"), "ok")

    def test_write_is_atomic_under_a_failure(self):
        state = ps.RunState.create(self.ws, "r1")
        state.record_step("03-design-gate", "ok")
        state.data["boom"] = {1, 2}  # not JSON-serializable
        with self.assertRaises(TypeError):
            state._flush()
        # The prior good ledger must still parse, and no temp file left behind.
        json.loads(state.path.read_text(encoding="utf-8"))
        self.assertEqual(list(state.path.parent.glob("*.tmp")), [])


class EnvelopeTest(unittest.TestCase):
    """T2 — recovering the envelope from whatever the agent actually said."""

    def test_bare_object(self):
        got = ps.parse_envelope('{"step": "05-verify", "status": "complete"}')
        self.assertEqual(got["status"], "complete")

    def test_wrapped_in_prose_and_fences(self):
        got = ps.parse_envelope(
            'Done. Here is the envelope:\n\n```json\n'
            '{"step": "04-implement", "status": "complete", "verdict": "pass"}\n'
            '```\n\nLet me know if you need more.')
        self.assertEqual(got["verdict"], "pass")

    def test_last_object_wins_over_an_earlier_example(self):
        got = ps.parse_envelope(
            'The contract said {"status": "complete | failed"}.\n'
            'My result: {"step": "06-deliver", "status": "failed"}')
        self.assertEqual(got["step"], "06-deliver")

    def test_braces_inside_strings_do_not_break_scanning(self):
        got = ps.parse_envelope(
            '{"status": "complete", "next_inputs": ["use {} for the default",'
            ' "escaped \\" quote"], "blockers": []}')
        self.assertEqual(got["next_inputs"][0], "use {} for the default")

    def test_nested_objects(self):
        got = ps.parse_envelope('{"status": "complete", "meta": {"a": {"b": 1}}}')
        self.assertEqual(got["meta"]["a"]["b"], 1)

    def test_prose_only_is_not_an_envelope(self):
        self.assertIsNone(ps.parse_envelope("I finished the slice, it went well."))
        self.assertIsNone(ps.parse_envelope(""))

    def test_object_without_status_is_not_an_envelope(self):
        self.assertIsNone(ps.parse_envelope('{"note": "some other json"}'))


class EvidenceGateTest(unittest.TestCase):
    """T4 — the machine-checkable stand-in for 'coherent evidence'."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.report = Path(self._tmp.name) / "04-implement.report.md"

    def tearDown(self):
        self._tmp.cleanup()

    def test_populated_evidence_section_passes(self):
        self.report.write_text(
            "# 04-implement\n\n## Verdict\npass\n\n## Evidence\n"
            "```\n$ pytest -q\n12 passed\n```\n\n## Artifacts\nnone\n",
            encoding="utf-8")
        self.assertTrue(ps.has_evidence(self.report))

    def test_empty_evidence_section_fails(self):
        self.report.write_text(
            "# 04-implement\n\n## Evidence\n\n## Artifacts\nnone\n",
            encoding="utf-8")
        self.assertFalse(ps.has_evidence(self.report))

    def test_missing_section_fails(self):
        self.report.write_text("# 04-implement\n\n## Verdict\npass\n",
                               encoding="utf-8")
        self.assertFalse(ps.has_evidence(self.report))

    def test_missing_report_fails(self):
        self.assertFalse(ps.has_evidence(self.report))


class QueueTest(unittest.TestCase):
    """T5 — parsing the work queue and computing readiness."""

    def setUp(self):
        self.slices = ps.parse_tasks(TASKS_MD)
        self.by_id = {s.id: s for s in self.slices}

    def test_every_slice_is_found_with_its_title(self):
        self.assertEqual([s.id for s in self.slices], ["T1", "T2", "T3", "T9"])
        self.assertEqual(self.by_id["T2"].title, "Handoff I/O")

    def test_h2_blocked_by_does_not_split_a_task(self):
        # `## Blocked by` sits at the same heading level as a task title; only
        # `## T<N>` may start a new task.
        self.assertEqual(self.by_id["T3"].blocked_by, ["T1", "T2"])

    def test_none_reads_as_no_blockers(self):
        self.assertEqual(self.by_id["T1"].blocked_by, [])

    def test_status_is_lifted(self):
        self.assertEqual(self.by_id["T1"].status, "todo")
        self.assertEqual(self.by_id["T9"].status, "done")

    def test_acceptance_commands_are_lifted(self):
        self.assertEqual(self.by_id["T2"].acceptance,
                         ["python3 scripts/check_leitworter.py"])

    def test_blocked_slice_never_becomes_ready(self):
        ready = {s.id for s in ps.ready_slices(self.slices, done=set())}
        self.assertEqual(ready, {"T1", "T2"})
        self.assertNotIn("T3", ready)

    def test_readiness_advances_only_when_all_blockers_are_done(self):
        partial = {s.id for s in ps.ready_slices(self.slices, done={"T1"})}
        self.assertNotIn("T3", partial)
        full = {s.id for s in ps.ready_slices(self.slices, done={"T1", "T2"})}
        self.assertIn("T3", full)

    def test_finished_slice_is_not_rescheduled(self):
        ready = [s.id for s in ps.ready_slices(self.slices, done=set())]
        self.assertNotIn("T9", ready)


class BriefTest(unittest.TestCase):
    """T2 — the ten fields, and the path-not-payload rule."""

    def test_brief_carries_every_contract_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = ps.write_brief(
                Path(tmp), "04-implement", run_id="r1",
                run_state=Path(tmp) / "run-state.json",
                goal="Build T3.", inputs=["`TASKS.md` § T3"],
                constraints=["Stay inside T3."],
                deliverable="Invoke implement-and-review.",
                verification=["pytest -q"], escalation="models-consensus")
            body = path.read_text(encoding="utf-8")
        for field in ("run_id", "run_state", "step", "## Goal", "## Inputs",
                      "## Constraints and non-goals", "## Deliverable",
                      "## Required verification", "## Escalation",
                      "## Output contract"):
            self.assertIn(field, body, f"brief is missing {field}")
        self.assertIn("04-implement.report.md", body)


class DispatchTest(unittest.TestCase):
    """T3 — the seat contract, without launching anything."""

    def test_every_registered_runner_exists(self):
        for seat, (script, _) in ps.RUNNERS.items():
            self.assertTrue((REPO_ROOT / script).is_file(),
                            f"seat {seat} points at a missing runner: {script}")

    def test_argv_uses_only_the_parity_flags(self):
        argv = ps.runner_argv("codex", Path("/b.md"), Path("/w"), "implementer",
                              60, Path("/o.json"))
        for flag in ("--prompt-file", "--working-dir", "--allow-write", "--role",
                     "--timeout", "--json", "--output-file"):
            self.assertIn(flag, argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_unknown_seat_is_reported_never_substituted(self):
        ok, message = ps.dispatch("nonexistent", Path("/b.md"), Path("/tmp"),
                                  "implementer", 5, Path("/tmp/o.json"))
        self.assertFalse(ok)
        self.assertIn("seat_unavailable", message)


class SliceRunnerTest(unittest.TestCase):
    """T4 — the phase sequencer, with the agent stubbed out."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        self.slice = ps.parse_tasks(TASKS_MD)[0]
        self.calls: list[str] = []
        self._real_dispatch = ps.dispatch

    def tearDown(self):
        ps.dispatch = self._real_dispatch
        self._tmp.cleanup()

    def _scheduler(self):
        return SimpleNamespace(seat="opus", timeout=5, local_only=True,
                               tasks_path=self.ws / "TASKS.md")

    def _stub(self, *, fail_at=None, omit_evidence_once=False, crash_at=None):
        state = {"evidence_attempts": 0}

        def stub(seat, brief, cwd, role, timeout, out_file):
            step = brief.name.split(".")[0]
            self.calls.append(step)
            if crash_at and step == crash_at:
                raise KeyboardInterrupt("simulated kill")
            report = brief.parent / f"{step}.report.md"
            evidence = "```\n$ pytest -q\n3 passed\n```"
            if omit_evidence_once and step == "04-implement":
                state["evidence_attempts"] += 1
                if state["evidence_attempts"] == 1:
                    evidence = ""
            report.write_text(
                f"# {step}\n\n## Verdict\npass\n\n## Evidence\n{evidence}\n",
                encoding="utf-8")
            status = "failed" if step == fail_at else "complete"
            return True, json.dumps(
                {"step": step, "status": status, "verdict": "pass",
                 "report": str(report), "artifacts": [], "next_inputs": [],
                 "blockers": []})
        return stub

    def test_happy_path_runs_every_phase_in_order(self):
        ps.dispatch = self._stub()
        state = ps.RunState.create(self.ws, "r1")
        outcome = ps.SliceRunner(self._scheduler(), self.slice, self.ws,
                                 state).run()
        self.assertEqual(outcome, ps.COMPLETE)
        self.assertEqual(self.calls, ["03-design-gate", "04-implement",
                                      "05-verify", "06-deliver"])

    def test_a_failed_phase_stops_the_slice(self):
        ps.dispatch = self._stub(fail_at="04-implement")
        state = ps.RunState.create(self.ws, "r1")
        outcome = ps.SliceRunner(self._scheduler(), self.slice, self.ws,
                                 state).run()
        self.assertEqual(outcome, ps.FAILED)
        self.assertNotIn("05-verify", self.calls)  # never verify unverified work

    def test_missing_evidence_triggers_exactly_one_recovery(self):
        ps.dispatch = self._stub(omit_evidence_once=True)
        state = ps.RunState.create(self.ws, "r1")
        outcome = ps.SliceRunner(self._scheduler(), self.slice, self.ws,
                                 state).run()
        self.assertEqual(outcome, ps.COMPLETE)
        self.assertEqual(self.calls.count("04-implement"), 2)
        self.assertEqual(state.attempts("04-implement:evidence_recovery"), 1)

    def test_prose_return_is_reprompted_once_then_failed(self):
        def prose(seat, brief, cwd, role, timeout, out_file):
            self.calls.append(brief.name.split(".")[0])
            return True, "I finished it, looks good to me."
        ps.dispatch = prose
        state = ps.RunState.create(self.ws, "r1")
        outcome = ps.SliceRunner(self._scheduler(), self.slice, self.ws,
                                 state).run()
        self.assertEqual(outcome, ps.FAILED)
        self.assertEqual(self.calls, ["03-design-gate", "03-design-gate"])


class CrashResumeTest(unittest.TestCase):
    """The required check from run-state-contract.md.

    Kill a run mid-flight, restart it, and assert three things: it resumes at
    the right phase, attempts survived, and no side effect executed twice.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        self.slice = ps.parse_tasks(TASKS_MD)[0]
        self.calls: list[str] = []
        self._real_dispatch = ps.dispatch

    def tearDown(self):
        ps.dispatch = self._real_dispatch
        self._tmp.cleanup()

    def _scheduler(self):
        return SimpleNamespace(seat="opus", timeout=5, local_only=True,
                               tasks_path=self.ws / "TASKS.md")

    def _stub(self, crash_at=None):
        def stub(seat, brief, cwd, role, timeout, out_file):
            step = brief.name.split(".")[0]
            self.calls.append(step)
            if step == crash_at:
                raise KeyboardInterrupt("simulated kill")
            report = brief.parent / f"{step}.report.md"
            report.write_text(
                f"# {step}\n\n## Evidence\n```\n$ pytest -q\nok\n```\n",
                encoding="utf-8")
            return True, json.dumps({"step": step, "status": "complete",
                                     "verdict": "pass", "report": str(report)})
        return stub

    def test_resume_skips_finished_phases_and_keeps_counters(self):
        state = ps.RunState.create(self.ws, "run-a")
        state.begin_attempt("04-implement:evidence_recovery", 1)
        state.claim_side_effect("commit:T1")

        # Die during phase 5, after 3 and 4 are on the ledger.
        ps.dispatch = self._stub(crash_at="05-verify")
        with self.assertRaises(KeyboardInterrupt):
            ps.SliceRunner(self._scheduler(), self.slice, self.ws, state).run()
        self.assertEqual(self.calls,
                         ["03-design-gate", "04-implement", "05-verify"])
        self.assertEqual(state.phase, 5)

        # Restart: a brand-new object, loading only what reached disk.
        self.calls.clear()
        resumed = ps.RunState.load(self.ws, "run-a")

        # 1. resumes at the right phase — the two finished phases are not redone
        ps.dispatch = self._stub()
        outcome = ps.SliceRunner(self._scheduler(), self.slice, self.ws,
                                 resumed).run()
        self.assertEqual(outcome, ps.COMPLETE)
        self.assertEqual(self.calls, ["05-verify", "06-deliver"])
        self.assertNotIn("03-design-gate", self.calls)
        self.assertNotIn("04-implement", self.calls)

        # 2. attempts survived — a crash does not reset a counter
        self.assertEqual(resumed.attempts("04-implement:evidence_recovery"), 1)

        # 3. no side effect executed twice
        self.assertFalse(resumed.claim_side_effect("commit:T1"))
        self.assertEqual(resumed.side_effect_keys().count("commit:T1"), 1)

    def test_a_gate_absent_from_the_ledger_was_never_granted(self):
        state = ps.RunState.create(self.ws, "run-b")
        self.assertFalse(ps.RunState.load(self.ws, "run-b").has_gate(
            ps.APPROVAL_GATE))
        state.record_gate(ps.APPROVAL_GATE)
        self.assertTrue(ps.RunState.load(self.ws, "run-b").has_gate(
            ps.APPROVAL_GATE))


class IntegrationTest(unittest.TestCase):
    """T5 — real worktrees and real merges against a throwaway repo.

    This is the slice with no prior implementation to lean on, so it is tested
    against git itself rather than a stub.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self._tmp.name)
        self._real_dispatch = ps.dispatch
        ps.git(self.ws, "init", "-q", ".")
        ps.git(self.ws, "config", "user.email", "t@t")
        ps.git(self.ws, "config", "user.name", "t")
        (self.ws / "TASKS.md").write_text(TASKS_MD, encoding="utf-8")
        ps.git(self.ws, "add", "-A")
        ps.git(self.ws, "commit", "-qm", "seed")

    def tearDown(self):
        ps.dispatch = self._real_dispatch
        self._tmp.cleanup()

    def _stub_that_commits(self):
        def stub(seat, brief, cwd, role, timeout, out_file):
            step = brief.name.split(".")[0]
            if step == "04-implement":  # do real work in the real worktree
                marker = cwd / f"{cwd.name}.txt"
                marker.write_text(step, encoding="utf-8")
                ps.git(cwd, "add", "-A")
                ps.git(cwd, "commit", "-qm", f"work in {cwd.name}")
            report = brief.parent / f"{step}.report.md"
            report.write_text(f"# {step}\n\n## Evidence\n```\nok\n```\n",
                              encoding="utf-8")
            return True, json.dumps({"step": step, "status": "complete",
                                     "verdict": "pass", "report": str(report)})
        return stub

    def _scheduler(self, **kwargs):
        slices = ps.parse_tasks(TASKS_MD)[:1]  # T1 only — no blockers
        scheduler = ps.Scheduler(
            self.ws, "run-i", slices, seat="opus", max_in_flight=1, timeout=5,
            tasks_path=self.ws / "TASKS.md", **kwargs)
        scheduler.state.record_gate(ps.APPROVAL_GATE)
        return scheduler

    def test_slice_work_is_isolated_then_merged_to_the_integration_head(self):
        ps.dispatch = self._stub_that_commits()
        scheduler = self._scheduler()
        head_before = ps.git(self.ws, "rev-parse", "HEAD").stdout.strip()
        outcomes = scheduler.run()

        self.assertEqual(outcomes["T1"], ps.COMPLETE)
        # The work happened in a worktree, not the main tree...
        worktrees = ps.git(self.ws, "worktree", "list").stdout
        self.assertIn("run-i-T1", worktrees)
        # ...and landed on the integration head via a merge.
        head_after = ps.git(self.ws, "rev-parse", "HEAD").stdout.strip()
        self.assertNotEqual(head_before, head_after)
        self.assertEqual(scheduler.integration_head, head_after)
        self.assertIn("merge:T1", scheduler.state.side_effect_keys())

    def test_a_merge_is_never_replayed_on_resume(self):
        ps.dispatch = self._stub_that_commits()
        first = self._scheduler()
        first.run()
        head = ps.git(self.ws, "rev-parse", "HEAD").stdout.strip()

        # Same run id: the ledger already carries merge:T1 and a complete slice.
        second = self._scheduler()
        second.run()
        self.assertEqual(ps.git(self.ws, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(second.state.side_effect_keys().count("merge:T1"), 1)

    def test_the_run_stops_when_the_approval_gate_is_absent(self):
        slices = ps.parse_tasks(TASKS_MD)[:1]
        scheduler = ps.Scheduler(self.ws, "run-nogate", slices, seat="opus",
                                 max_in_flight=1, timeout=5,
                                 tasks_path=self.ws / "TASKS.md")
        with self.assertRaises(SystemExit):
            scheduler.run()
        self.assertEqual(scheduler.state.status, ps.AWAITING_HUMAN)

    def test_dry_run_shows_the_whole_schedule(self):
        slices = ps.parse_tasks(TASKS_MD)[:3]  # T3 is blocked by T1 and T2
        scheduler = ps.Scheduler(self.ws, "run-dry", slices, seat="opus",
                                 max_in_flight=3, timeout=5,
                                 tasks_path=self.ws / "TASKS.md", dry_run=True)
        scheduler.state.record_gate(ps.APPROVAL_GATE)
        outcomes = scheduler.run()
        self.assertEqual({v for v in outcomes.values()}, {"dry-run"})

    def test_dry_run_leaves_no_live_looking_cards(self):
        slices = ps.parse_tasks(TASKS_MD)[:3]
        scheduler = ps.Scheduler(self.ws, "run-dry2", slices, seat="opus",
                                 max_in_flight=3, timeout=5,
                                 tasks_path=self.ws / "TASKS.md", dry_run=True)
        scheduler.state.record_gate(ps.APPROVAL_GATE)
        scheduler.run()
        # No per-slice ledger at all — a phantom `running` card on the board is
        # worse than no card.
        states = list((self.ws / ".ai-workflow" / "ship").glob("*/run-state.json"))
        self.assertEqual([p.parent.name for p in states], ["run-dry2"])
        # And the feature ledger is not stamped failed by a rehearsal.
        self.assertNotEqual(scheduler.state.status, ps.FAILED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
