#!/usr/bin/env python3
"""Offline lean poll dispatch, evidence, budget and recovery checks."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_council_state as fixtures
import model_routing

council = fixtures.council


def poll_document(profile="lean", gaps=True):
    document = fixtures.preview_document()
    preview = document["preview"]
    if profile is not None:
        preview.update(poll_profile=profile, poll_policy=council.council_poll_policy(), risk_flags=[], council_name="routine")
        preview["conditional_stages"] = {"gap_repair": 3, "judge": 2 if profile == "lean" else 0}
    gap_ids = [f"gap-{index}" for index in range(3)] if gaps else []

    def add(call, stage, seat_index, dependencies, conditional=False, continuity=None):
        source = preview["roles"][seat_index]
        preview["roles"].append({**source, "call": call, "role": stage,
                                  "continuity_key": continuity or call, "depends_on": dependencies,
                                  "conditional": conditional})
        preview["effort"].append({**preview["effort"][seat_index], "call": call})
        preview["execution"].append({**preview["execution"][seat_index], "call": call,
                                      "continuity_key": continuity or call})

    add("organizer", "organizer", 0, [f"opening-{index}" for index in range(3)])
    for index, key in enumerate(gap_ids):
        add(key, "gap_repair", index, ["organizer"], True, f"opening-{index}")
    for index in range(2):
        add(f"judge-{index}", "judge", index + 1, ["organizer", *gap_ids], profile == "lean")
    add("synthesis", "synthesis", 0, ["organizer", *gap_ids, "judge-0", "judge-1"])
    count = len(preview["roles"])
    preview.update(base_calls=5 if profile == "lean" else 7,
                   conditional_calls=(2 if profile == "lean" else 0) + len(gap_ids),
                   validation_retry_ceiling=count, maximum_calls=count * 2)
    if profile is not None:
        preview["poll_budget"] = {key: preview[key] for key in
                                 ("base_calls", "conditional_calls", "validation_retry_ceiling", "maximum_calls")}
    return document


def organizer(**overrides):
    result = {"consensus": [], "contradictions": [], "partial_coverage": [], "unique_insights": [],
              "blind_spots": [], "material_gaps": False, "confidence": 90, "high_risk": False}
    result.update(overrides)
    return result


def synthesis():
    return {"consensus_answer": "Use the supported option.", "attribution_map": [],
            "confidence_rationale": "All openings agree.", "confidence": 90}


class LeanPollTests(unittest.TestCase):
    approve = fixtures.CouncilStateTests.approve
    initialize = fixtures.CouncilStateTests.initialize
    reset = fixtures.CouncilStateTests.reset
    read = fixtures.CouncilStateTests.read
    reserve = fixtures.CouncilStateTests.reserve
    receipt = fixtures.CouncilStateTests.receipt
    reconcile = fixtures.CouncilStateTests.reconcile

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "state.json"
        self.approval = self.root / "approval.json"
        self.brief = self.root / "brief.txt"
        self.brief.write_text("Which option has the strongest evidence?")
        self.document = poll_document()
        self.initialize()

    def emit(self, step, response, call=None, **overrides):
        call = call or step
        reservation = self.reserve(call, step)
        state = self.read()
        route_id = council.read_plan(state)["steps"][step]["route_id"]
        context = state["call_ledger"]["contexts"].get(route_id, "context-" + route_id)
        result = self.reconcile(self.receipt(call, context=context, message=json.dumps(response), **overrides), call)
        return reservation, result

    def opening_and_organizer(self, **overrides):
        for index in range(3):
            self.emit(f"opening-{index}", fixtures.answer())
        return self.emit("organizer", organizer(**overrides))

    def skip_step(self, step):
        with council.ledger.locked(self.path) as state:
            return council.skip(state, step, "Organizer evidence does not require this call.")

    def skip_gaps(self):
        for index in range(3):
            self.skip_step(f"gap-{index}")

    def complete_judges(self):
        for index in range(2):
            self.emit(f"judge-{index}", {"verdicts": []})

    def test_five_calls_complete_with_actual_evidence_and_no_judge_execution(self):
        self.opening_and_organizer()
        self.skip_gaps()
        for index in range(2):
            result = self.skip_step(f"judge-{index}")
            self.assertEqual(result["status"], "conditional-not-needed")
        self.emit("synthesis", synthesis())
        state = self.read()
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["attempts"]["total_role_calls"], 5)
        self.assertFalse(any(call["intent"]["route"]["role"] == "judge" for call in state["call_ledger"]["calls"].values()))
        record = state["council"]["skipped"]["judge-0"]
        decision = json.loads(Path(record["decision"]["path"]).read_text())
        response = json.loads(Path(decision["evidence"]["path"]).read_text())
        self.assertEqual(response["response"], organizer())
        self.assertFalse(decision["judges_required"])
        self.assertEqual(decision["raw_receipt"], response["raw_receipt"])
        summary = council.status(state)
        self.assertEqual(summary["step_outcomes"]["judge-0"], "conditional-not-needed")

    def test_central_councils_can_plan_exact_judge_models_outside_opening_registry(self):
        for name in ("technical", "analysis", "routine"):
            resolved = model_routing.resolve_council(name, "lean")
            document = poll_document()
            preview = document["preview"]
            preview.update(council_name=name, poll_policy=resolved["poll_policy"], poll_budget=resolved["poll_budget"])
            selections = {f"opening-{index}": selection for index, selection in enumerate(resolved["openings"])}
            selections.update(organizer=resolved["organizer"], synthesis=resolved["synthesis"])
            selections.update({f"judge-{index}": selection for index, selection in enumerate(resolved["judges"])})
            selections.update({f"gap-{index}": selection for index, selection in enumerate(resolved["openings"])})
            unique = {selection["seat"]: selection for selection in selections.values()}
            preview["seats"] = [{"id": key, "provider": model_routing.load_config()["runners"][selection["runner"]]["provider"],
                                 "requested_model": selection["model"],
                                 "model_receipt": {"status": "unverified", "source": "not_observed", "observed_model": None}}
                                for key, selection in unique.items()]
            for role in preview["roles"]:
                selection = selections[role["call"]]
                role.update(seat=selection["seat"], requested_model=selection["model"], effort=selection["effort"])
            preview["effort"] = [{"call": role["call"], "effort": role["effort"], "effort_control": role["effort_control"]}
                                 for role in preview["roles"]]
            self.document = document
            self.reset()
            self.opening_and_organizer(high_risk=True)
            self.skip_gaps()
            self.complete_judges()
            self.emit("synthesis", synthesis())
            self.assertEqual(self.read()["status"], "completed")
            plan = council.read_plan(self.read())
            self.assertEqual(plan["routes"][-2]["model"], resolved["judges"][-1]["model"])
            self.assertEqual(len([role for role in preview["roles"] if role["role"] == "opening"]), 3)
            if name == "routine":
                self.assertEqual(len(preview["seats"]), 4)
            changed = copy.deepcopy(document)
            next(role for role in changed["preview"]["roles"] if role["call"] == "opening-2").update(
                seat=resolved["openings"][0]["seat"], requested_model=resolved["openings"][0]["model"])
            self.assert_plan_blocked(changed, "model diversity")

    def test_judges_need_valid_organizer_before_skip_or_dispatch(self):
        with self.assertRaisesRegex(ValueError, "organizer evidence"):
            self.skip_step("judge-0")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            self.reserve("judge-0", "judge-0")
        self.opening_and_organizer()
        self.skip_gaps()
        with self.assertRaisesRegex(ValueError, "conditional-not-needed"):
            self.reserve("judge-0", "judge-0")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 4)

    def test_each_trigger_requires_both_judges_even_after_gap_repair(self):
        conflict = [{"point_id": "C1", "statement": "The options conflict.",
                     "positions": [{"seat": "seat-0", "position": "Use option A."},
                                   {"seat": "seat-1", "position": "Use option B."}]}]
        for evidence in ({"material_gaps": True}, {"contradictions": conflict},
                         {"confidence": 69}, {"high_risk": True}):
            with self.subTest(evidence=evidence):
                self.reset()
                self.opening_and_organizer(**evidence)
                if evidence.get("material_gaps"):
                    for index in range(3):
                        reservation, result = self.emit(f"gap-{index}", {"item_responses": [], "confidence": 90})
                        self.assertEqual(reservation["context_id"], f"context-opening-{index}")
                        self.assertEqual(result["status"], "valid")
                else:
                    self.skip_gaps()
                with self.assertRaisesRegex(ValueError, "required by organizer"):
                    self.skip_step("judge-0")
                self.emit("judge-0", {"verdicts": []})
                with self.assertRaisesRegex(ValueError, "prerequisites"):
                    self.reserve("synthesis", "synthesis")
                self.emit("judge-1", {"verdicts": []})
                self.assertEqual(self.emit("synthesis", synthesis())[1]["status"], "valid")
                expected = 10 if evidence.get("material_gaps") else 7
                self.assertEqual(self.read()["attempts"]["total_role_calls"], expected)

    def test_threshold_boundary_allows_skips_and_low_confidence_requires_judges(self):
        threshold = self.document["preview"]["poll_policy"]["low_confidence_threshold"]
        self.opening_and_organizer(confidence=threshold)
        self.skip_gaps()
        self.skip_step("judge-0")
        self.skip_step("judge-1")
        self.assertTrue(self.reserve("synthesis", "synthesis")["dispatch_allowed"])

    def test_gap_repair_cannot_be_skipped_when_required(self):
        self.opening_and_organizer(material_gaps=True)
        with self.assertRaisesRegex(ValueError, "required by organizer"):
            self.skip_step("gap-0")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            self.reserve("judge-0", "judge-0")

    def test_lean_organizer_requires_confidence_and_risk_evidence(self):
        for field in ("confidence", "high_risk"):
            self.reset()
            for index in range(3):
                self.emit(f"opening-{index}", fixtures.answer())
            response = organizer()
            del response[field]
            self.assertEqual(self.emit("organizer", response)[1]["status"], "malformed")
            with self.assertRaisesRegex(ValueError, "organizer evidence"):
                self.skip_step("judge-0")

    def test_skip_evidence_tampering_blocks_synthesis(self):
        self.opening_and_organizer()
        self.skip_gaps()
        self.skip_step("judge-0")
        self.skip_step("judge-1")
        state = self.read()
        record = state["council"]["skipped"]["judge-0"]
        Path(record["decision"]["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.reserve("synthesis", "synthesis")
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 4)

    def test_changed_gap_skip_evidence_blocks_judges_without_spending(self):
        self.opening_and_organizer(contradictions=[{"point_id": "C1", "statement": "The choices conflict.", "positions": []}])
        self.skip_gaps()
        state = self.read()
        decision = state["council"]["skipped"]["gap-0"]["decision"]
        Path(decision["path"]).write_text("{}")
        original = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.reserve("judge-0", "judge-0")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.skip_step("judge-0")
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 4)

    def test_organizer_raw_receipt_tampering_blocks_skip_and_synthesis(self):
        self.opening_and_organizer()
        state = self.read()
        Path(state["call_ledger"]["calls"]["organizer"]["council"]["raw_receipt"]["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "evidence changed"):
            self.skip_step("judge-0")

    def test_pending_judge_on_resume_does_not_dispatch_again_or_allow_skip(self):
        self.opening_and_organizer(high_risk=True)
        self.skip_gaps()
        self.reserve("judge-0", "judge-0")
        with patch.object(council, "council_poll_policy", side_effect=AssertionError("Do not reread defaults")):
            self.initialize()
            result = self.reserve("judge-0", "judge-0")
        self.assertFalse(result["dispatch_allowed"])
        self.assertEqual(self.read()["attempts"]["total_role_calls"], 5)
        with self.assertRaisesRegex(ValueError, "attempted step"):
            self.skip_step("judge-0")
        self.assertEqual(self.reconcile(self.receipt("judge-0", context="context-judge-0", message=json.dumps({"verdicts": []})), "judge-0")["status"], "valid")
        self.emit("judge-1", {"verdicts": []})
        self.emit("synthesis", synthesis())
        self.assertEqual(self.read()["status"], "completed")

    def test_unavailable_required_judge_stays_failed_and_blocks_synthesis(self):
        self.opening_and_organizer(high_risk=True)
        self.skip_gaps()
        self.emit("judge-0", {}, success=False, error="Route unavailable.")
        retry, result = self.emit("judge-0", {}, call="judge-retry", success=False, error="Route unavailable.")
        self.assertEqual(retry["context_id"], "context-judge-0")
        self.assertEqual(result["status"], "execution_failed")
        with self.assertRaisesRegex(ValueError, "retry ceiling"):
            self.reserve("judge-third", "judge-0")
        with self.assertRaisesRegex(ValueError, "attempted step"):
            self.skip_step("judge-0")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            self.reserve("synthesis", "synthesis")
        self.assertEqual(self.read()["phase"], "recovery_exhausted")

    def test_actual_judge_route_drift_leaves_pending_and_blocks_synthesis(self):
        self.opening_and_organizer(confidence=20)
        self.skip_gaps()
        self.reserve("judge-0", "judge-0")
        with self.assertRaisesRegex(ValueError, "binding differs"):
            self.reconcile(self.receipt("judge-0", context="context-judge-0", configured_model="other"), "judge-0")
        self.assertEqual(council.step_status(self.read(), "judge-0"), "pending")
        with self.assertRaisesRegex(ValueError, "prerequisites"):
            self.reserve("synthesis", "synthesis")

    def test_approved_profile_policy_budget_and_route_changes_block_resume(self):
        for key, value in (("poll_profile", "standard"), ("risk_flags", ["money"]),
                           ("poll_policy", {"low_confidence_threshold": 1, "full_required_flags": []}),
                           ("base_calls", 7)):
            self.document = poll_document()
            self.reset()
            self.document["preview"][key] = value
            self.approve()
            with self.assertRaisesRegex(ValueError, "different approval"):
                self.initialize()
        self.document = poll_document()
        self.reset()
        self.document["preview"]["roles"][-2]["requested_model"] = "other"
        self.approve()
        with self.assertRaisesRegex(ValueError, "different approval"):
            self.initialize()

    def test_missing_judges_required_flags_and_wrong_policy_fail_initialization(self):
        for flag in council.council_poll_policy()["full_required_flags"]:
            document = poll_document()
            document["preview"]["risk_flags"] = [flag]
            self.assert_plan_blocked(document, "standard poll")
        document = poll_document()
        document["preview"]["council_name"] = "security"
        self.assert_plan_blocked(document, "standard poll")
        document = poll_document()
        document["preview"]["poll_policy"]["low_confidence_threshold"] = 1
        self.assert_plan_blocked(document, "central configuration")
        document = poll_document()
        for field in ("roles", "effort", "execution"):
            document["preview"][field] = [entry for entry in document["preview"][field] if entry["call"] != "judge-1"]
        document["preview"]["roles"][-1]["depends_on"].remove("judge-1")
        document["preview"].update(conditional_calls=4, maximum_calls=18, validation_retry_ceiling=9)
        document["preview"]["poll_budget"].update(conditional_calls=4, maximum_calls=18, validation_retry_ceiling=9)
        self.assert_plan_blocked(document, "both judges")

    def assert_plan_blocked(self, document, error):
        fingerprint = council.fingerprint(document)
        document["preview"]["scope_fingerprint"] = fingerprint
        document["approval"] = {"status": "approved", "scope_fingerprint": fingerprint}
        with self.assertRaisesRegex(ValueError, error):
            council.plan_from(document)

    def test_bypassed_dependencies_and_conditionals_fail_initialization(self):
        for call, dependencies in (("organizer", ["opening-0"]), ("judge-0", ["organizer"]),
                                   ("synthesis", ["organizer", "judge-0"])):
            document = poll_document()
            next(role for role in document["preview"]["roles"] if role["call"] == call)["depends_on"] = dependencies
            self.assert_plan_blocked(document, "lean")
        document = poll_document()
        next(role for role in document["preview"]["roles"] if role["call"] == "judge-0")["conditional"] = False
        document["preview"].update(base_calls=6, conditional_calls=4)
        document["preview"]["poll_budget"].update(base_calls=6, conditional_calls=4)
        self.assert_plan_blocked(document, "conditional stages")

    def test_lean_preview_requires_all_three_optional_gap_routes_and_matching_budget(self):
        self.assert_plan_blocked(poll_document(gaps=False), "three gap repairs")
        document = poll_document()
        document["preview"]["poll_budget"]["maximum_calls"] = 14
        self.assert_plan_blocked(document, "budget snapshot")
        document = poll_document()
        document["preview"]["conditional_stages"] = {"gap_repair": 0, "judge": 5}
        self.assert_plan_blocked(document, "conditional stage snapshot")
        del document["preview"]["conditional_stages"]
        self.assert_plan_blocked(document, "conditional stage snapshot")

    def test_completed_skip_evidence_is_verified_on_status_and_resume(self):
        for reference_kind in ("decision", "organizer_receipt"):
            with self.subTest(reference_kind=reference_kind):
                self.reset()
                self.opening_and_organizer()
                self.skip_gaps()
                self.skip_step("judge-0")
                self.skip_step("judge-1")
                self.emit("synthesis", synthesis())
                state = self.read()
                self.assertEqual(state["status"], "completed")
                reference = (state["council"]["skipped"]["judge-0"]["decision"] if reference_kind == "decision"
                             else state["call_ledger"]["calls"]["organizer"]["council"]["raw_receipt"])
                Path(reference["path"]).write_text("{}")
                original = self.path.read_bytes()
                with self.assertRaisesRegex(ValueError, "evidence changed"):
                    council.status(self.read())
                with self.assertRaisesRegex(ValueError, "evidence changed"):
                    self.initialize()
                self.assertEqual(self.path.read_bytes(), original)

    def test_approved_smaller_retry_budget_blocks_before_dispatch(self):
        preview = self.document["preview"]
        preview.update(validation_retry_ceiling=0, maximum_calls=10)
        preview["poll_budget"].update(validation_retry_ceiling=0, maximum_calls=10)
        self.reset()
        self.opening_and_organizer(high_risk=True)
        self.skip_gaps()
        self.emit("judge-0", {}, success=False, error="Unavailable.")
        before = self.read()["attempts"]
        with self.assertRaisesRegex(ValueError, "retry ceiling"):
            self.reserve("judge-retry", "judge-0")
        self.assertEqual(before, self.read()["attempts"])

    def test_legacy_and_explicit_standard_keep_seven_base_calls_and_old_schema(self):
        for profile in (None, "standard"):
            self.document = poll_document(profile=profile)
            self.reset()
            for index in range(3):
                self.emit(f"opening-{index}", fixtures.answer())
            response = organizer()
            del response["confidence"], response["high_risk"]
            self.assertEqual(self.emit("organizer", response)[1]["status"], "valid")
            self.skip_gaps()
            self.complete_judges()
            self.emit("synthesis", synthesis())
            self.assertEqual(self.read()["attempts"]["total_role_calls"], 7)
            self.assertEqual(self.read()["status"], "completed")
            self.assertTrue(all(isinstance(value, str) for value in self.read()["council"]["skipped"].values()))

    def test_lean_route_runs_from_flat_installation_with_local_shared_config(self):
        flat = self.root / "installed"
        shutil.copytree(Path(council.__file__).resolve().parents[1], flat / "models-consensus")
        shutil.copytree(Path(council.ledger.__file__).resolve().parents[1], flat / "shared")
        approval = self.root / "flat-approval.json"
        document = poll_document()
        fingerprint = council.fingerprint(document)
        document["preview"]["scope_fingerprint"] = fingerprint
        document["approval"] = {"status": "approved", "scope_fingerprint": fingerprint}
        approval.write_text(json.dumps(document))
        result = subprocess.run([sys.executable, str(flat / "models-consensus/scripts/council_state.py"),
                                 "--state", str(self.root / "flat-state.json"), "init", "--approval-state", str(approval)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["poll_profile"], "lean")

    def test_cmux_cannot_adopt_or_relay_lean_poll(self):
        document = copy.deepcopy(self.document)
        document["preview"]["transport"] = "cmux"
        with self.assertRaisesRegex(ValueError, "per_call"):
            import cmux_council
            cmux_council.approval_scope_payload(document)
        document["preview"]["poll_profile"] = "lean "
        with self.assertRaisesRegex(ValueError, "unknown poll profile"):
            cmux_council.approval_scope_payload(document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
