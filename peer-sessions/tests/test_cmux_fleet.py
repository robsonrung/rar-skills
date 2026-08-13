#!/usr/bin/env python3
"""Tests for peer-session cmux launch state and teardown boundaries."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cmux_fleet


class TeardownPlanTests(unittest.TestCase):
    def state(self, surface_mode: str) -> dict:
        terminals = [
            {"peer": "research", "workspace_id": "workspace:1", "surface_id": "surface:1"},
            {"peer": "review", "workspace_id": "workspace:1", "surface_id": "surface:2"},
        ]
        if surface_mode == "workspace":
            terminals[1]["workspace_id"] = "workspace:2"
        return cmux_fleet.terminal_state(surface_mode, Path("/tmp/peer-fleet"), terminals)

    def test_split_teardown_closes_only_recorded_peer_surfaces(self):
        commands = cmux_fleet.teardown_plan(self.state("split"))
        self.assertEqual(
            commands,
            [
                ["cmux", "close-surface", "--workspace", "workspace:1", "--surface", "surface:1"],
                ["cmux", "close-surface", "--workspace", "workspace:1", "--surface", "surface:2"],
            ],
        )

    def test_tab_teardown_never_closes_the_shared_workspace(self):
        commands = cmux_fleet.teardown_plan(self.state("tab"))
        self.assertTrue(all(command[1] == "close-surface" for command in commands))
        self.assertTrue(all("close-workspace" not in command for command in commands))

    def test_workspace_teardown_closes_each_created_workspace_once(self):
        commands = cmux_fleet.teardown_plan(self.state("workspace"))
        self.assertEqual(
            commands,
            [
                ["cmux", "close-workspace", "--workspace", "workspace:1"],
                ["cmux", "close-workspace", "--workspace", "workspace:2"],
            ],
        )

    def test_teardown_rejects_an_unowned_state_file(self):
        state = self.state("split")
        state["created_by"] = "other-launcher"
        with self.assertRaisesRegex(cmux_fleet.UsageError, "not created"):
            cmux_fleet.teardown_plan(state)


class TeardownExecutionTests(unittest.TestCase):
    def test_successful_teardown_records_no_remaining_peer_terminal(self):
        state = cmux_fleet.terminal_state(
            "tab",
            Path("/tmp/peer-fleet"),
            [{"peer": "research", "workspace_id": "workspace:1", "surface_id": "surface:1"}],
        )
        completed = completed_process()
        with mock.patch("cmux_fleet.run_teardown_command", return_value=completed) as close, mock.patch(
            "cmux_fleet.remaining_terminals", return_value=[]
        ):
            result = cmux_fleet.teardown(state)
        self.assertEqual(close.call_args.args[0], ["cmux", "close-surface", "--workspace", "workspace:1", "--surface", "surface:1"])
        self.assertTrue(result["teardown"]["success"])
        self.assertEqual(result["teardown"]["remaining"], [])

    def test_teardown_marks_a_remaining_peer_terminal_as_failure(self):
        state = cmux_fleet.terminal_state(
            "split",
            Path("/tmp/peer-fleet"),
            [{"peer": "research", "workspace_id": "workspace:1", "surface_id": "surface:1"}],
        )
        completed = completed_process()
        remaining = [{"peer": "research", "workspace_id": "workspace:1", "surface_id": "surface:1"}]
        with mock.patch("cmux_fleet.run_teardown_command", return_value=completed), mock.patch(
            "cmux_fleet.remaining_terminals", return_value=remaining
        ):
            result = cmux_fleet.teardown(state)
        self.assertFalse(result["teardown"]["success"])
        self.assertEqual(result["teardown"]["remaining"], remaining)


def completed_process():
    class Result:
        returncode = 0
        stdout = "OK\n"
        stderr = ""

    return Result()


if __name__ == "__main__":
    unittest.main(verbosity=2)
