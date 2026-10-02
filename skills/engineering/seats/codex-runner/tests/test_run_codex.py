#!/usr/bin/env python3
"""Exercise the read-only tool profile without calling a provider."""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/run_codex.py"
spec = importlib.util.spec_from_file_location("codex_tool_profile_test", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ReadOnlyProfileTests(unittest.TestCase):
    def local_cli(self, servers):
        calls = []

        def run(command, **kwargs):
            calls.append((command, kwargs))
            if command[-3:] == ["mcp", "list", "--json"]:
                overrides = {command[i + 1] for i, part in enumerate(command) if part == "-c"}
                listed = [{"name": name, "enabled": enabled and f"mcp_servers.{name}.enabled=false" not in overrides}
                          for name, enabled in servers.items()]
                return subprocess.CompletedProcess(command, 0, json.dumps(listed), "")
            last_message = command[command.index("--output-last-message") + 1]
            Path(last_message).write_text("OK")
            return subprocess.CompletedProcess(command, 0, "OK", "")
        return run, calls

    def invoke(self, servers, **kwargs):
        run, calls = self.local_cli(servers)
        with patch.object(runner.shutil, "which", return_value="/usr/bin/codex"), \
             patch.object(runner.subprocess, "run", side_effect=run):
            result = runner.run_codex("Review", model="luna", effort="low", role="researcher",
                                      disable_fallback=True, **kwargs)
        return result, calls

    def test_repo_read_only_disables_servers_and_reports_configured_isolation(self):
        result, calls = self.invoke({"repl": True, "off": False}, tool_profile="repo_read_only")
        self.assertTrue(result["success"], result)
        receipt = result["tool_profile_receipt"]
        self.assertEqual((receipt["status"], receipt["observed_mcp_servers"], receipt["observed_tools"]), ("configured", [], None))
        command, kwargs = calls[-1]
        self.assertEqual(command[:2], ["codex", "exec"])
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
        for override in (*runner.READ_ONLY_OVERRIDES, "mcp_servers.repl.enabled=false"):
            self.assertIn(override, command)
        self.assertNotIn("mcp_servers.off.enabled=false", command)
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(result["tool_profile"], "repo_read_only")

    def test_isolation_failure_never_starts_the_model(self):
        for listed in (None, [{"name": "bad name", "enabled": True}]):
            with self.subTest(listed=listed):
                run, calls = self.local_cli({})
                with patch.object(runner.shutil, "which", return_value="/usr/bin/codex"), \
                     patch.object(runner, "list_mcp_servers", return_value=listed), \
                     patch.object(runner.subprocess, "run", side_effect=run):
                    result = runner.run_codex("Review", tool_profile="repo_read_only", disable_fallback=True)
                self.assertFalse(result["success"])
                self.assertEqual(result["tool_profile_receipt"]["status"], "unverified")
                self.assertFalse(any(command[:2] == ["codex", "exec"] for command, _ in calls))

    def test_unknown_or_unenforceable_profiles_are_rejected(self):
        for profile, combined in (("no_tools", {}), ("repo_read_only", {"allow_write": True}), ("repo_read_only", {"sandbox": "workspace-write"})):
            with self.subTest(profile=profile, combined=combined):
                result, calls = self.invoke({}, tool_profile=profile, **combined)
                self.assertFalse(result["success"])
                self.assertEqual(calls, [])

    def test_tool_profile_blocks_fallback_to_another_runner(self):
        with patch.object(runner.shutil, "which", return_value=None), \
             patch.object(runner, "invoke_fallback") as fallback:
            result = runner.run_codex("Review", tool_profile="repo_read_only")
        fallback.assert_not_called()
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
