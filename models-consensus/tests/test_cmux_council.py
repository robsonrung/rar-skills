#!/usr/bin/env python3
"""Tests for the interactive cmux transport used by models-consensus."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import cmux_council  # noqa: E402


class SessionIdentityTests(unittest.TestCase):
    def test_session_name_is_namespaced_and_safe(self):
        self.assertEqual(cmux_council.session_name("council-42"), "consensus-council-42")
        with self.assertRaises(cmux_council.UsageError):
            cmux_council.session_name("../../other-session")


class ManifestTests(unittest.TestCase):
    def manifest(self, command: list[str] | None = None) -> dict:
        return {
            "session_id": "council-42",
            "workspace": "/work/project",
            "seats": [
                {
                    "id": "grok",
                    "command": command or ["grok", "--permission-mode", "plan", "--minimal"],
                },
                {
                    "id": "codex",
                    "command": ["codex", "--sandbox", "read-only", "--no-alt-screen"],
                },
            ],
        }

    def test_plan_creates_a_workspace_and_starts_each_interactive_cli(self):
        plan = cmux_council.build_start_plan(self.manifest())
        self.assertEqual(plan[0], ["cmux", "list-workspaces", "--json"])
        self.assertEqual(plan[1], ["cmux", "new-workspace"])
        self.assertEqual(plan[2], ["cmux", "list-workspaces", "--json"])
        self.assertEqual(plan[3][0:2], ["cmux", "select-workspace"])
        self.assertEqual(plan[4], ["cmux", "identify", "--json"])

    def test_headless_claude_command_is_rejected(self):
        manifest = self.manifest(["claude", "--print", "answer this"])
        with self.assertRaisesRegex(cmux_council.UsageError, "interactive"):
            cmux_council.build_start_plan(manifest)

    def test_headless_codex_exec_is_rejected(self):
        manifest = self.manifest(["codex", "exec", "answer this"])
        with self.assertRaisesRegex(cmux_council.UsageError, "interactive"):
            cmux_council.build_start_plan(manifest)

    def test_duplicate_seat_ids_are_rejected(self):
        manifest = self.manifest()
        manifest["seats"][1]["id"] = "grok"
        with self.assertRaisesRegex(cmux_council.UsageError, "unique"):
            cmux_council.build_start_plan(manifest)


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
        self.assertEqual(receipt["agent_message"], '{"answer":"new answer"}')

    def test_collect_rejects_invalid_json_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "seat.json"
            output.write_text("not json", encoding="utf-8")
            with self.assertRaisesRegex(cmux_council.UsageError, "valid JSON"):
                cmux_council.collect_artifact("grok", 1, output)

    def test_state_records_the_surface_from_identify(self):
        identify = json.dumps({"workspace": {"id": "workspace:3"}, "surface": {"id": "surface:7"}})
        context = cmux_council.parse_identify(identify)
        self.assertEqual(context["workspace_id"], "workspace:3")
        self.assertEqual(context["surface_id"], "surface:7")

    def test_workspace_diff_requires_exactly_one_new_workspace(self):
        before = '{"workspaces":[{"id":"workspace:1"}]}'
        after = '{"workspaces":[{"id":"workspace:1"},{"id":"workspace:2"}]}'
        self.assertEqual(cmux_council.new_workspace_id(before, after), "workspace:2")
        with self.assertRaisesRegex(cmux_council.UsageError, "exactly one"):
            cmux_council.new_workspace_id(before, before)


class CmuxInvocationTests(unittest.TestCase):
    def test_missing_cmux_is_reported_as_a_usage_error(self):
        with mock.patch("cmux_council.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(cmux_council.UsageError, "not found"):
                cmux_council.run_cmux(["cmux", "ping"])

    def test_start_runs_each_seat_in_its_new_focused_workspace(self):
        manifest = ManifestTests().manifest()
        identify_first = subprocess_result('{"workspace":{"id":"workspace:3"},"surface":{"id":"surface:7"}}')
        identify_second = subprocess_result('{"workspace":{"id":"workspace:4"},"surface":{"id":"surface:8"}}')
        before_first = subprocess_result('{"workspaces":[]}')
        after_first = subprocess_result('{"workspaces":[{"id":"workspace:3"}]}')
        before_second = subprocess_result('{"workspaces":[{"id":"workspace:3"}]}')
        after_second = subprocess_result('{"workspaces":[{"id":"workspace:3"},{"id":"workspace:4"}]}')
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest["workspace"] = temp_dir
            with mock.patch("cmux_council.run_cmux", side_effect=[before_first, subprocess_result(""), after_first, subprocess_result(""), identify_first, subprocess_result(""), subprocess_result(""), before_second, subprocess_result(""), after_second, subprocess_result(""), identify_second, subprocess_result(""), subprocess_result("")]) as run_cmux:
                state = cmux_council.start_session(manifest, cmux_bin="cmux")
        self.assertEqual(run_cmux.call_args_list[0].args[0], ["cmux", "list-workspaces", "--json"])
        self.assertEqual(state["seats"][0]["surface_id"], "surface:7")
        self.assertEqual(state["seats"][1]["surface_id"], "surface:8")


def subprocess_result(stdout: str):
    class Result:
        returncode = 0
        stderr = ""

        def __init__(self, value: str):
            self.stdout = value

    return Result(stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
