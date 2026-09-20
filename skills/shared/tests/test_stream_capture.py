#!/usr/bin/env python3
"""Capture local fixture streams without provider calls."""
import json
import os
import signal
import time
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stream_capture import capture, progress


class StreamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "events.jsonl"

    def test_session_and_metrics_survive_timeout_without_success(self):
        event = {"type": "assistant", "session_id": "session-1", "message": {"id": "m1", "usage": {"input_tokens": 5, "output_tokens": 3}}}
        code = "import time; print(" + repr(json.dumps(event)) + ", flush=True); time.sleep(5)"
        with self.assertRaises(subprocess.TimeoutExpired):
            capture([sys.executable, "-c", code], str(self.root), dict(os.environ), 0.5, self.log)
        saved = json.loads(self.log.with_suffix(".checkpoint.json").read_text())
        self.assertEqual(saved["status"], "interrupted")
        self.assertEqual(saved["session_id"], "session-1")
        self.assertEqual(saved["metrics"]["output_tokens"], 3)
        self.assertIsNone(saved["metrics"]["reported_cost_usd"])
        self.assertFalse(saved["metrics_complete"])
        self.assertFalse(saved["terminal_observed"])

    def test_repeated_messages_do_not_double_count_and_terminal_is_authoritative(self):
        message = {"type": "assistant", "message": {"id": "one", "usage": {"input_tokens": 10, "output_tokens": 2}}}
        latest = {"type": "assistant", "message": {"id": "one", "usage": {"input_tokens": 10, "output_tokens": 4}}}
        self.assertEqual(progress([message, latest])["metrics"]["input_tokens"], 10)
        terminal = {"type": "result", "usage": {"input_tokens": 12, "output_tokens": 5}}
        self.assertEqual(progress([message, latest, terminal])["metrics"]["input_tokens"], 12)

    def test_drains_stderr_and_captures_last_line_without_newline(self):
        terminal = {"type": "result", "session_id": "one", "subtype": "success", "result": "done"}
        code = "import sys; sys.stderr.write('x' * 100000); sys.stdout.write(" + repr(json.dumps(terminal)) + ")"
        result = capture([sys.executable, "-c", code], str(self.root), dict(os.environ), 5, self.log)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stderr), 100000)
        saved = json.loads(self.log.with_suffix(".checkpoint.json").read_text())
        self.assertTrue(saved["terminal_observed"])
        with self.assertRaises(FileExistsError):
            capture([sys.executable, "-c", "pass"], str(self.root), dict(os.environ), 5, self.log)


    def test_cancellation_terminates_owned_child_and_preserves_checkpoint(self):
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        child = "import os,json,time; print(json.dumps({'session_id':'cancelled-session','pid':os.getpid()}),flush=True); time.sleep(30)"
        controller = ("import sys,os; sys.path.insert(0," + repr(str(scripts)) + "); from stream_capture import capture; "
            "capture([sys.executable,'-c'," + repr(child) + "]," + repr(str(self.root)) + ",dict(os.environ),30," + repr(str(self.log)) + ")")
        wrapper = subprocess.Popen([sys.executable, "-c", controller], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        child_pid = None
        try:
            until = time.monotonic() + 5
            checkpoint = self.log.with_suffix(".checkpoint.json")
            while not checkpoint.exists() and time.monotonic() < until:
                time.sleep(0.01)
            self.assertTrue(checkpoint.exists())
            child_pid = json.loads(self.log.read_text().splitlines()[0])["pid"]
            wrapper.send_signal(signal.SIGTERM)
            wrapper.communicate(timeout=5)
            self.assertNotEqual(wrapper.returncode, 0)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            self.assertEqual(json.loads(checkpoint.read_text())["status"], "interrupted")
        finally:
            if wrapper.poll() is None:
                wrapper.kill()
                wrapper.communicate()
            if child_pid:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
