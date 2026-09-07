#!/usr/bin/env python3
"""Tests for the interactive cmux transport used by models-consensus."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cmux_council


def council_state(status: str = "approved") -> dict:
    state = {
        "session_id": "council-42",
        "status": "awaiting_human",
        "question": "Which option has the lower delivery risk?",
        "mode": "poll",
        "preview": {
            "seats": [
                {
                    "id": "astra",
                    "requested_model": "model-astra",
                    "provider": "provider-a",
                    "model_receipt": {
                        "status": "unverified",
                        "source": "configured_model",
                        "observed_model": None,
                    },
                },
                {
                    "id": "fable",
                    "requested_model": "model-fable",
                    "provider": "provider-b",
                    "model_receipt": {
                        "status": "unverified",
                        "source": "configured_model",
                        "observed_model": None,
                    },
                },
            ],
            "roles": [
                {
                    "call": "opening-astra",
                    "role": "opening",
                    "seat": "astra",
                    "requested_model": "model-astra",
                    "effort": "high",
                    "effort_control": "configured",
                },
                {
                    "call": "opening-fable",
                    "role": "opening",
                    "seat": "fable",
                    "requested_model": "model-fable",
                    "effort": "high",
                    "effort_control": "configured",
                },
            ],
            "effort": [
                {"call": "opening-astra", "effort": "high", "effort_control": "configured"},
                {"call": "opening-fable", "effort": "high", "effort_control": "configured"},
            ],
            "transport": "cmux",
            "serving_receipt": "explicitly_allowed_unverified",
            "tool_profile": "no_tools",
            "base_calls": 2,
            "conditional_calls": 0,
            "validation_retry_ceiling": 2,
            "maximum_calls": 4,
        },
        "approval": {"status": status},
    }
    fingerprint = cmux_council.approval_scope_fingerprint(state)
    state["preview"]["scope_fingerprint"] = fingerprint
    if status == "approved":
        state["approval"]["scope_fingerprint"] = fingerprint
    return state


class SessionIdentityTests(unittest.TestCase):
    def test_session_name_is_namespaced_and_safe(self):
        self.assertEqual(cmux_council.session_name("council-42"), "consensus-council-42")
        with self.assertRaises(cmux_council.UsageError):
            cmux_council.session_name("../../other-session")


class RelayProtocolTests(unittest.TestCase):
    def test_send_targets_the_recorded_surface_and_uses_enter_separately(self):
        commands = cmux_council.build_send_plan("surface:7", "question; do not shell expand")
        self.assertEqual(commands[0][:3], ["cmux", "send", "--surface"])
        self.assertEqual(commands[0][-1], "question; do not shell expand")
        self.assertEqual(commands[1], ["cmux", "send-key", "--surface", "surface:7", "enter"])

    def test_collect_requires_a_valid_json_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "seat.json"
            output.write_text('{"answer":"new answer"}', encoding="utf-8")
            receipt = cmux_council.collect_artifact("grok", 1, output)
        self.assertEqual(receipt["execution_path"], "cmux_interactive")
        self.assertIsNone(receipt["effective_model"])
        self.assertEqual(receipt["model_receipt"]["status"], "unverified")
        self.assertEqual(receipt["agent_message"], '{"answer":"new answer"}')

    def test_collect_rejects_invalid_json_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "seat.json"
            output.write_text("not json", encoding="utf-8")
            with self.assertRaisesRegex(cmux_council.UsageError, "valid JSON"):
                cmux_council.collect_artifact("grok", 1, output)

class PeerFleetAdoptionTests(unittest.TestCase):
    def write_peer_fleet(self, root: Path, delivery_mode: str = "coordinator") -> Path:
        run_dir = root / "peer-fleet"
        run_dir.mkdir()
        (run_dir / "state.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "delivery_mode": delivery_mode,
                    "peers": [{"id": "astra"}, {"id": "fable"}],
                }
            ),
            encoding="utf-8",
        )
        return run_dir

    def test_adopt_peer_fleet_records_existing_surfaces(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self.write_peer_fleet(root)
            terminal_state = root / "terminals.json"
            terminal_state.write_text(
                json.dumps(
                    {
                        "run_dir": str(run_dir),
                        "transport": "cmux",
                        "terminals": [
                            {"peer": "fable", "workspace_id": "workspace:2", "surface_id": "surface:2"},
                            {"peer": "astra", "workspace_id": "workspace:1", "surface_id": "surface:1"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            adopted = cmux_council.adopt_peer_fleet(
                "council-42", str(run_dir), str(terminal_state), ["astra", "fable"]
            )
        self.assertEqual(adopted["session"], "consensus-council-42")
        self.assertEqual([seat["id"] for seat in adopted["seats"]], ["astra", "fable"])
        self.assertEqual(adopted["seats"][0]["surface_id"], "surface:1")

    def test_adopt_rejects_mailbox_peer_fleet(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self.write_peer_fleet(root, delivery_mode="mailbox")
            terminal_state = root / "terminals.json"
            terminal_state.write_text(
                json.dumps({"run_dir": str(run_dir), "transport": "cmux", "terminals": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(cmux_council.UsageError, "delivery_mode coordinator"):
                cmux_council.adopt_peer_fleet(
                    "council-42", str(run_dir), str(terminal_state), ["astra", "fable"]
                )

    def test_adopt_rejects_a_fleet_with_unselected_seats(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = self.write_peer_fleet(root)
            terminal_state = root / "terminals.json"
            terminal_state.write_text(
                json.dumps(
                    {
                        "run_dir": str(run_dir),
                        "transport": "cmux",
                        "terminals": [
                            {"peer": "fable", "workspace_id": "workspace:2", "surface_id": "surface:2"},
                            {"peer": "astra", "workspace_id": "workspace:1", "surface_id": "surface:1"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(cmux_council.UsageError, "does not match"):
                cmux_council.adopt_peer_fleet("council-42", str(run_dir), str(terminal_state), ["astra"])


class ApprovalGuardTests(unittest.TestCase):
    def write_json(self, root: Path, name: str, payload: dict) -> Path:
        path = root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def write_adopted_state(self, root: Path, state: dict) -> Path:
        fingerprint = state["preview"]["scope_fingerprint"]
        return self.write_json(
            root,
            "adopted.json",
            {
                "session_id": "council-42",
                "transport": "cmux_interactive",
                "approval_scope_fingerprint": fingerprint,
                "approved_seats": ["astra", "fable"],
                "seats": [
                    {"id": "astra", "workspace_id": "workspace:1", "surface_id": "surface:1"},
                    {"id": "fable", "workspace_id": "workspace:2", "surface_id": "surface:2"},
                ],
            },
        )

    def test_adoption_requires_an_explicit_approved_plan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            approval_path = self.write_json(Path(temp_dir), "approval.json", council_state("pending"))
            with self.assertRaisesRegex(cmux_council.UsageError, "not approved"):
                cmux_council.adopt_approved_peer_fleet(str(approval_path), "unused", "unused")

    def test_send_does_not_call_cmux_before_explicit_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = council_state("pending")
            approval_path = self.write_json(root, "approval.json", state)
            adopted_path = self.write_adopted_state(root, state)
            prompt_path = root / "prompt.txt"
            prompt_path.write_text("Answer the question.", encoding="utf-8")
            with mock.patch("cmux_council.run_cmux") as run_cmux, contextlib.redirect_stderr(io.StringIO()):
                exit_code = cmux_council.main(
                    [
                        "send",
                        "--approval-state",
                        str(approval_path),
                        "--adopted-state",
                        str(adopted_path),
                        "--seat",
                        "astra",
                        "--message-file",
                        str(prompt_path),
                    ]
                )
        self.assertEqual(exit_code, 2)
        run_cmux.assert_not_called()

    def test_changed_scope_invalidates_the_approval(self):
        state = council_state()
        state["preview"]["roles"][0]["effort"] = "medium"
        state["preview"]["effort"][0]["effort"] = "medium"
        with self.assertRaisesRegex(cmux_council.UsageError, "does not match its scope"):
            cmux_council.approved_plan(state)

    def test_runtime_effort_requires_null_and_is_accepted(self):
        state = council_state()
        state["preview"]["roles"][1]["effort"] = None
        state["preview"]["roles"][1]["effort_control"] = "runtime"
        state["preview"]["effort"][1]["effort"] = None
        state["preview"]["effort"][1]["effort_control"] = "runtime"
        fingerprint = cmux_council.approval_scope_fingerprint(state)
        state["preview"]["scope_fingerprint"] = fingerprint
        state["approval"]["scope_fingerprint"] = fingerprint
        self.assertEqual(cmux_council.approved_plan(state)[1], fingerprint)

    def test_mismatched_verified_observed_model_blocks_the_plan(self):
        state = council_state()
        state["preview"]["seats"][0]["model_receipt"] = {
            "status": "verified",
            "source": "provider_event",
            "observed_model": "different-model",
        }
        with self.assertRaisesRegex(cmux_council.UsageError, "differs from the approved requested model"):
            cmux_council.approval_scope_fingerprint(state)

    def test_send_uses_only_the_surface_recorded_for_the_approved_seat(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            state = council_state()
            approval_path = self.write_json(root, "approval.json", state)
            adopted_path = self.write_adopted_state(root, state)
            prompt_path = root / "prompt.txt"
            prompt_path.write_text("Answer the question.", encoding="utf-8")
            with mock.patch("cmux_council.run_cmux") as run_cmux, contextlib.redirect_stdout(io.StringIO()):
                exit_code = cmux_council.main(
                    [
                        "send",
                        "--approval-state",
                        str(approval_path),
                        "--adopted-state",
                        str(adopted_path),
                        "--seat",
                        "astra",
                        "--message-file",
                        str(prompt_path),
                    ]
                )
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [call.args[0] for call in run_cmux.call_args_list],
            [
                ["cmux", "send", "--surface", "surface:1", "Answer the question."],
                ["cmux", "send-key", "--surface", "surface:1", "enter"],
            ],
        )

    def test_send_parser_does_not_accept_a_raw_surface(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cmux_council.parse_args(["send", "--surface", "surface:1", "--message-file", "prompt.txt"])


class CmuxInvocationTests(unittest.TestCase):
    def test_missing_cmux_is_reported_as_a_usage_error(self):
        with (
            mock.patch("cmux_council.subprocess.run", side_effect=FileNotFoundError),
            self.assertRaisesRegex(cmux_council.UsageError, "not found"),
        ):
            cmux_council.run_cmux(["cmux", "ping"])

    def test_start_command_is_not_available(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cmux_council.parse_args(["start"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
