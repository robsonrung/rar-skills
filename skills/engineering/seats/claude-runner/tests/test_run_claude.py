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
    def result(self, **overrides):
        return {"type": "result", "subtype": "success", "session_id": "session-1", "result": "A code example: ```json\\n{}\\n```", **overrides}

    def invoke(self, output, resume=None):
        process = subprocess.CompletedProcess([], 0, json.dumps(output) if not isinstance(output, str) else output, "")
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(runner.subprocess, "run", return_value=process) as call:
            result = runner._run_claude("Review", output_format="json", resume=resume, disable_fallback=True)
            return result, call.call_args.args[0]

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
             patch.object(runner.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 1, output=b"partial")):
            result = runner._run_claude("Review", output_format="json", disable_fallback=True)
        self.assertFalse(result["success"])
        self.assertEqual(result["stdout"], "partial")
        self.assertEqual(result["terminal_status"], "interrupted")

    def test_stream_timeout_retains_session_and_partial_usage(self):
        import stream_capture
        partial = json.dumps({"type": "system", "session_id": "new-session"}) + "\n" + json.dumps({
            "type": "assistant", "message": {"id": "message-1", "usage": {"input_tokens": 12, "output_tokens": 4}}}) + "\n"
        with patch.object(runner.shutil, "which", return_value="fixture-cli"), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None), \
             patch.object(stream_capture, "capture", side_effect=subprocess.TimeoutExpired("fixture", 1, output=partial)) as call:
            result = runner._run_claude("Review", output_format="stream-json", event_log="/tmp/fixture-events.jsonl", disable_fallback=True)
        self.assertFalse(result["success"])
        self.assertFalse(result["metrics_complete"])
        self.assertEqual(result["session_id"], "new-session")
        self.assertEqual(result["metrics"]["input_tokens"], 12)
        self.assertEqual(result["metrics"]["output_tokens"], 4)
        self.assertIn("--verbose", call.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
