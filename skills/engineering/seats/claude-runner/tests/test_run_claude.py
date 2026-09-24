#!/usr/bin/env python3
"""Exercise terminal receipts without calling a provider."""
import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "scripts/run_claude.py"
spec = importlib.util.spec_from_file_location("claude_receipt_test", path)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ReceiptTests(unittest.TestCase):
    def local_cli(self, process):
        def run(command, **kwargs):
            if command[1:] == ["--version"]:
                return subprocess.CompletedProcess(command, 0, "2.1.281 (Claude Code)", "")
            if command[1:3] == ["auth", "status"]:
                return subprocess.CompletedProcess(command, 0, '{"loggedIn": false}', "")
            if isinstance(process, Exception):
                raise process
            return process
        return run

    def result(self, **overrides):
        return {"type": "result", "subtype": "success", "session_id": "session-1", "result": "A code example: ```json\\n{}\\n```", **overrides}

    def invoke(self, output, resume=None, output_format="json", **kwargs):
        text = json.dumps(output) if not isinstance(output, str) else output
        if output_format == "stream-json" and isinstance(output, list):
            text = "\n".join(json.dumps(event) for event in output)
        process = subprocess.CompletedProcess([], 0, text, "")
        kwargs.setdefault("model", "claude-opus-5-5")
        kwargs.setdefault("effort", "medium")
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner.subprocess, "run", side_effect=self.local_cli(process)) as call:
            result = runner.run_claude("Review", output_format=output_format, resume=resume, disable_fallback=True, **kwargs)
            return result, call.call_args.args[0]

    def test_json_array_and_stream_extract_primary_serving_model(self):
        for output_format in ("json", "stream-json"):
            for model in ("claude-fable-5-1", "claude-opus-5-5"):
                events = [{"type": "assistant", "message": {"model": model}}, self.result()]
                result, command = self.invoke(events, model=model, output_format=output_format)
                self.assertTrue(result["success"])
                self.assertEqual(result["effective_model"], model)
                self.assertEqual(result["model_receipt"]["status"], "verified")
                self.assertIn("--verbose", command)

    def test_model_mismatch_and_multiple_main_models_fail_receipt(self):
        events = [{"type": "assistant", "message": {"model": "claude-opus-5-5"}}, self.result()]
        result, _ = self.invoke(events, model="claude-fable-5-1")
        self.assertFalse(result["success"])
        self.assertEqual(result["terminal_status"], "invalid_receipt")
        self.assertEqual(result["effective_model"], "claude-opus-5-5")
        events.insert(0, {"type": "assistant", "message": {"model": "claude-fable-5-1"}})
        result, _ = self.invoke(events, model="claude-fable-5-1")
        self.assertFalse(result["success"])
        self.assertIsNone(result["effective_model"])

    def test_missing_evidence_stays_unverified(self):
        result, _ = self.invoke(self.result(), role="codereviewer")
        self.assertTrue(result["success"])
        self.assertEqual(result["model_receipt"]["status"], "unverified")
        self.assertEqual(result["tool_profile_receipt"]["status"], "unverified")

    def test_restricted_profiles_forward_allowlist_and_empty_mcp(self):
        for kwargs, tools in (({"role": "codereviewer"}, ["Read", "Glob", "Grep"]),
                              ({"restrict_tools": True}, ["Read", "Glob", "Grep"]),
                              ({"tool_profile": "no_tools", "role": "implementer"}, [])):
            events = [{"type": "system", "subtype": "init", "tools": tools, "mcp_servers": []}, self.result()]
            result, command = self.invoke(events, **kwargs)
            self.assertTrue(result["success"])
            self.assertEqual(command[command.index("--tools") + 1], ",".join(tools))
            self.assertIn("--safe-mode", command)
            self.assertIn("--strict-mcp-config", command)
            self.assertEqual(json.loads(command[command.index("--mcp-config") + 1]), {"mcpServers": {}})
            self.assertEqual(result["tool_profile_receipt"]["status"], "verified")

    def test_explicit_write_and_implementer_keep_normal_tools(self):
        for kwargs in ({"role": "implementer"}, {"role": "codereviewer", "allow_write": True},
                       {"role": "codereviewer", "tool_profile": "write"}):
            result, command = self.invoke(self.result(), **kwargs)
            self.assertEqual(result["tool_profile"], "write")
            self.assertNotIn("--tools", command)
            self.assertNotIn("--safe-mode", command)

    def test_tool_or_mcp_startup_violation_fails(self):
        for init in ({"tools": ["Read", "Write"], "mcp_servers": []},
                     {"tools": [], "mcp_servers": [{"name": "unexpected"}]}):
            result, _ = self.invoke([{"type": "system", "subtype": "init", **init}, self.result()], tool_profile="repo_read_only")
            self.assertFalse(result["success"])
            self.assertEqual(result["tool_profile_receipt"]["status"], "violated")
            self.assertEqual(result["terminal_status"], "invalid_receipt")

    def test_positive_limits_forward_and_invalid_limits_never_launch(self):
        result, command = self.invoke(self.result(), max_turns=3, max_budget_usd=0.25, timeout=9)
        self.assertEqual(command[command.index("--max-turns") + 1], "3")
        self.assertEqual(command[command.index("--max-budget-usd") + 1], "0.25")
        self.assertEqual(result["limits"]["timeout_seconds"], 9)
        for key in ("timeout", "max_turns", "max_budget_usd"):
            for value in (0, -1, float("inf"), float("nan"), True, "2"):
                with patch.object(runner.subprocess, "run") as call:
                    result = runner.run_claude("Review", **{key: value})
                    self.assertEqual(result["status"], "invalid_input")
                    self.assertIs(result["print_invocation_started"], False)
                    call.assert_not_called()

    def test_conflicting_authority_fails_without_launch(self):
        for kwargs in ({"allow_write": True, "restrict_tools": True},
                       {"allow_write": True, "tool_profile": "no_tools"},
                       {"restrict_tools": True, "tool_profile": "write"}, {"tool_profile": "invalid"}):
            with patch.object(runner.subprocess, "run") as call:
                result = runner.run_claude("Review", **kwargs)
                self.assertEqual(result["status"], "invalid_input")
                call.assert_not_called()

    def test_preflight_uses_injected_environment_and_blocks_without_fallback(self):
        import runner_preflight
        blocked = {"blocked": True, "reasons": ["Fixture mismatch"], "checks": {"auth_visibility": {"status": "unknown"}}}
        with patch.object(runner.shutil, "which", return_value="/fixture/claude"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value="injected-fixture-token"), \
             patch.object(runner_preflight, "check_claude", return_value=blocked) as preflight, \
             patch.object(runner.subprocess, "run") as process, \
             patch.object(runner, "invoke_fallback") as fallback:
            result = runner.run_claude("Review", model="claude-opus-5-5", effort="medium")
        self.assertFalse(result["success"])
        self.assertEqual(result["preflight"], blocked)
        self.assertIsNone(result["auth_ok"])
        self.assertEqual(preflight.call_args.kwargs["cli_path"], "/fixture/claude")
        self.assertEqual(preflight.call_args.kwargs["working_dir"], result["working_dir"])
        self.assertEqual(preflight.call_args.kwargs["env"]["CLAUDE_CODE_OAUTH_TOKEN"], "injected-fixture-token")
        self.assertNotIn("injected-fixture-token", json.dumps(result))
        process.assert_not_called()
        fallback.assert_not_called()

    def test_preflight_exception_blocks_without_exposing_exception_text(self):
        import runner_preflight
        with patch.object(runner.shutil, "which", return_value="/fixture/claude"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner_preflight, "check_claude", side_effect=ValueError("private-fixture-value")), \
             patch.object(runner.subprocess, "run") as process:
            result = runner.run_claude("Review", model="claude-opus-5-5", effort="medium")
        self.assertEqual(result["terminal_status"], "preflight_blocked")
        self.assertIs(result["print_invocation_started"], False)
        self.assertNotIn("metrics", result)
        self.assertNotEqual(result.get("metrics_complete"), True)
        self.assertIsNone(result["auth_ok"])
        self.assertNotIn("private-fixture-value", json.dumps(result))
        process.assert_not_called()

    def test_confirmed_preflight_block_has_zero_model_usage_and_measured_duration(self):
        import runner_preflight
        blocked = {"blocked": True, "reasons": ["CLI too old"], "evidence": {"provider_calls": 0}}
        with patch.object(runner.shutil, "which", return_value="/fixture/claude"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner_preflight, "check_claude", return_value=blocked), \
             patch.object(runner.time, "monotonic", side_effect=[20, 20.25]), \
             patch.object(runner.subprocess, "run") as process:
            result = runner.run_claude("Review", model="claude-opus-5-5", effort="medium")
        self.assertIs(result["print_invocation_started"], False)
        self.assertIs(result["metrics_complete"], True)
        self.assertEqual(result["metrics"]["duration_ms"], 250)
        self.assertTrue(all(value == 0 for key, value in result["metrics"].items() if key != "duration_ms"))
        self.assertIsNone(result["session_id"])
        self.assertEqual(result["stdout"], "")
        self.assertEqual(result["terminal_status"], "preflight_blocked")
        process.assert_not_called()

    def test_uncertain_launch_keeps_started_marker_and_unknown_usage(self):
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner.subprocess, "run", side_effect=self.local_cli(OSError("fixture launch error"))):
            result = runner.run_claude("Review", model="claude-opus-5-5", effort="medium")
        self.assertIs(result["print_invocation_started"], True)
        self.assertFalse(result["success"])
        self.assertNotIn("metrics", result)
        self.assertNotEqual(result.get("metrics_complete"), True)

    def test_fallback_cannot_drop_profile_or_budget(self):
        for kwargs in ({"role": "codereviewer"}, {"tool_profile": "no_tools"}, {"tool_profile": "write"},
                       {"max_turns": 2}, {"max_budget_usd": 1}, {"allow_write": True}):
            with patch.object(runner.shutil, "which", return_value=None), patch.object(runner, "invoke_fallback") as call:
                result = runner.run_claude("Review", **kwargs)
                self.assertFalse(result["success"])
                self.assertIn("Fallback blocked", result["stderr"])
                self.assertIs(result["print_invocation_started"], False)
                call.assert_not_called()

    def test_unconstrained_fallback_keeps_timeout_and_receipt(self):
        with patch.object(runner.shutil, "which", return_value=None), \
             patch.object(runner, "invoke_fallback", return_value={"success": True, "return_code": 0, "runner": "fallback"}) as call:
            result = runner.run_claude("Review", timeout=13)
            self.assertTrue(result["success"])
            self.assertEqual(call.call_args.args[2], 13)
            self.assertEqual(result["effective_runner"], "fallback")
            self.assertNotIn("print_invocation_started", result)

    def test_first_and_resumed_receipts_preserve_message_and_raw_output(self):
        for resume in (None, "session-1"):
            native = self.result(result="  Exact output\n```json\n{}\n```\n")
            result, command = self.invoke(native, resume)
            self.assertTrue(result["success"])
            self.assertEqual(result["session_id"], "session-1")
            self.assertEqual(result["agent_message"], native["result"])
            self.assertEqual(json.loads(result["stdout"]), native)
            self.assertEqual("--resume" in command, resume is not None)

    def test_missing_session_and_malformed_envelopes_are_not_success(self):
        for native in (self.result(session_id=None), self.result(result="  "), "not json", [], self.result(subtype="error_max_turns")):
            result, _ = self.invoke(native)
            self.assertFalse(result["success"])

    def test_event_array_error_and_stream_without_terminal_result_fail(self):
        self.assertFalse(runner.infer_claude_success(0, json.dumps([self.result(is_error=True)]), "json"))
        self.assertFalse(runner.infer_claude_success(0, '{"type":"assistant"}', "stream-json"))
        self.assertTrue(runner.infer_claude_success(0, json.dumps([self.result()]), "json"))

    def test_metrics_are_normalized_from_terminal_event(self):
        native = self.result(duration_ms=100, total_cost_usd=0.2, usage={"input_tokens": 2, "cache_creation_input_tokens": 3,
                            "cache_read_input_tokens": 10, "output_tokens": 5})
        result, _ = self.invoke(native)
        self.assertEqual(result["metrics"]["input_tokens"], 15)
        self.assertEqual(result["metrics"]["duration_ms"], 100)
        self.assertEqual(result["metrics"]["reported_cost_usd"], 0.2)

    def test_public_envelope_retains_dispatch_metadata(self):
        metadata = {"call_id": "call-1", "input_revision": "sha", "execution_provenance": {"resources": []}}
        with patch.object(runner, "_run_claude", return_value={"success": False, "return_code": 1}):
            result = runner.run_claude("Review", metadata_json=json.dumps(metadata))
        self.assertEqual(result["dispatch_metadata"], metadata)

    def test_timeout_keeps_partial_output_and_failed_status(self):
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner.subprocess, "run", side_effect=self.local_cli(subprocess.TimeoutExpired("fixture", 1, output=b"partial"))):
            result = runner._run_claude("Review", output_format="json", disable_fallback=True,
                                        model="claude-opus-5-5", effort="medium")
        self.assertFalse(result["success"])
        self.assertEqual(result["stdout"], "partial")
        self.assertEqual(result["terminal_status"], "interrupted")
        self.assertIs(result["print_invocation_started"], True)

    def test_stream_timeout_retains_session_and_partial_usage(self):
        import stream_capture
        partial = json.dumps({"type": "system", "session_id": "new-session"}) + "\n" + json.dumps({
            "type": "assistant", "message": {"id": "message-1", "model": "claude-opus-5-5", "usage": {"input_tokens": 12, "output_tokens": 4}}}) + '\n{"type":'
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner.subprocess, "run", side_effect=self.local_cli(None)), \
             patch.object(stream_capture, "capture", side_effect=subprocess.TimeoutExpired("fixture", 1, output=partial)) as call:
            result = runner._run_claude("Review", output_format="stream-json", event_log="/tmp/fixture-events.jsonl", disable_fallback=True,
                                        model="claude-opus-5-5", effort="medium")
        self.assertFalse(result["success"])
        self.assertFalse(result["metrics_complete"])
        self.assertIs(result["print_invocation_started"], True)
        self.assertEqual(result["session_id"], "new-session")
        self.assertEqual(result["metrics"]["input_tokens"], 12)
        self.assertEqual(result["metrics"]["output_tokens"], 4)
        self.assertEqual(result["effective_model"], "claude-opus-5-5")
        self.assertEqual(result["terminal_status"], "interrupted")
        self.assertIn("--verbose", call.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
