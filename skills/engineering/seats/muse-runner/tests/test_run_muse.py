#!/usr/bin/env python3
"""Offline checks for native permissions, records, limits, and installation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_muse", ROOT / "scripts" / "run_muse.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
FIXTURE = (ROOT / "tests" / "fixtures" / "echo.jsonl").read_text()
PROVIDER_FIXTURE = (ROOT / "tests" / "fixtures" / "provider-completed.jsonl").read_text()
REQUIRED = {"runner", "effective_runner", "effective_model", "requested_model", "configured_model",
            "model_receipt", "effective_provider", "auth_ok", "fallback_reason", "success", "return_code"}


class MuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.workspace / "config")})
        self.env.start()
        self.addCleanup(self.env.stop)

    def command(self, write=False, shell=False, provider="meta"):
        return runner.command_for("muse", self.workspace, self.workspace / "prompt", provider,
                                  "max", 7, write, shell)

    def fake_run(self, stdout=FIXTURE, code=0, **kwargs):
        with patch.object(runner.shutil, "which", return_value="muse"), \
             patch.object(runner, "preflight", return_value={}), \
             patch.object(runner, "capture", return_value=(stdout, "", code)) as capture:
            result = runner.run_muse("task", working_dir=self.workspace, **kwargs)
        return result, capture

    def test_read_tools_enforced_by_native_flags(self):
        command = self.command()
        self.assertIn("--disable-shell", command)
        self.assertIn("--disable-write", command)
        self.assertIn('permissions.default_profile=":read-only"', command)
        self.assertIn('run.toolset=["read_file","search"]', command)
        self.assertIn('run.subagent_delegation_mode="off"', command)
        self.assertIn("agents.execution_capacity=1", command)
        for flag in ("--disable-reminders", "--no-foreign-personal-context", "--disable-web-tools"):
            self.assertIn(flag, command)
        for flag in ("--yolo", "--disable-sandbox", "--disable-approval"):
            self.assertNotIn(flag, command)
        self.assertEqual(command[command.index("--contributor-mode") + 1], "off")
        self.assertEqual(command[command.index("--max-model-steps") + 1], "7")
        self.assertEqual(command[command.index("--model") + 1], runner.MODEL)
        self.assertEqual(command[command.index("--reasoning-effort") + 1], "max")

    def test_write_and_shell_are_separate_explicit_options(self):
        write = self.command(write=True)
        shell = self.command(write=True, shell=True)
        self.assertIn("--disable-shell", write)
        self.assertNotIn("--disable-write", write)
        self.assertNotIn("--disable-shell", shell)
        self.assertIn('permissions.default_profile=":ask-me"', shell)
        self.assertEqual(shell[shell.index("--approval-judge") + 1], "off")
        self.assertEqual(shell[shell.index("--approval-mode") + 1], "never")
        self.assertEqual(shell[shell.index("--sandbox-network") + 1], "restricted")
        self.assertIn('run.toolset=["read_file","search","write_file","edit_file","bash","bash_input"]', shell)
        result, capture = self.fake_run(allow_shell=True)
        self.assertFalse(result["success"])
        capture.assert_not_called()

    def test_role_does_not_grant_writes(self):
        result, capture = self.fake_run(role="implementer", provider="echo")
        self.assertTrue(result["success"])
        self.assertIn("--disable-write", capture.call_args.args[0])

    def test_echo_has_no_model_flags_or_auth_claim(self):
        command = self.command(provider="echo")
        self.assertNotIn("--model", command)
        self.assertNotIn("--reasoning-effort", command)
        result, _ = self.fake_run(provider="echo")
        self.assertTrue(result["success"])
        self.assertEqual(result["agent_message"], "echo: Runner transport check")
        self.assertEqual(result["effective_provider"], "echo")
        self.assertIsNone(result["configured_model"])
        self.assertIsNone(result["auth_ok"])
        self.assertIsNone(result["effective_model"])

    def test_configured_labels_never_become_serving_receipts(self):
        events = [json.loads(line) for line in FIXTURE.splitlines()]
        for event in events:
            event["model"] = runner.MODEL
            event["payload"]["model"] = runner.MODEL
        result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "model_unverified")
        self.assertEqual(result["configured_model"], runner.MODEL)
        self.assertIsNone(result["effective_model"])
        self.assertEqual(result["model_receipt"]["status"], "unverified")
        self.assertTrue(REQUIRED <= result.keys())

    def test_bad_or_incomplete_records_fail_closed(self):
        events = FIXTURE.splitlines()
        for content in ("", "not JSON", "[]", "{}", "\n".join(events[:-1]),
                        FIXTURE + events[-1], FIXTURE.replace('"payload_type":"run.terminal.completed"', '"payload_type":42'), FIXTURE.replace('"schema_version":1', '"schema_version":2')):
            with self.subTest(content=content[:30]):
                result, _ = self.fake_run(stdout=content)
                self.assertFalse(result["success"])
                self.assertTrue(REQUIRED <= result.keys())

    def provider_events(self):
        events = [json.loads(line) for line in PROVIDER_FIXTURE.splitlines()]
        status = next(event for event in events if event["payload_type"] == "task.lifecycle.status")
        detail = status["payload"]["event"]["details"]["facets"][1]["detail"]
        return events, status, detail

    def test_provider_completion_verifies_serving_model(self):
        result, _ = self.fake_run(stdout=PROVIDER_FIXTURE)
        self.assertTrue(result["success"])
        self.assertEqual(result["effective_model"], runner.MODEL)
        self.assertEqual(result["model_receipt"], {
            "status": "verified", "source": "provider_event", "observed_model": runner.MODEL})
        self.assertEqual(result["provider_model_receipts"][0]["response_id"], "resp_fixture")
        self.assertEqual(result["privacy_status"], "user_confirmed")

    def test_configured_or_incomplete_task_is_not_serving_proof(self):
        for missing in ("task.lifecycle.status", "task.stream.linked", "task.lifecycle.proposed",
                        "task.lifecycle.side_effect_intent", "task.lifecycle.completed", "run.lifecycle.started"):
            events, _, _ = self.provider_events()
            events = [event for event in events if event["payload_type"] != missing]
            with self.subTest(missing=missing):
                result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
                self.assertFalse(result["success"])
                self.assertEqual(result["status"], "model_unverified")
                self.assertIsNone(result["effective_model"])
                self.assertEqual(result["model_receipt"]["status"], "unverified")

    def test_unrelated_or_auxiliary_provider_status_is_not_primary_proof(self):
        for field in ("command", "run", "task", "task_stream", "causation", "child", "tool_task",
                      "unfinished_stream", "opening_stream"):
            events, status, detail = self.provider_events()
            payload = status["payload"]
            if field == "command":
                payload["command_id"] = "other-command"
            elif field == "run":
                payload["run_stream"]["id"] = "other-run"
            elif field == "task":
                payload["event"]["task_id"] = "other-task"
            elif field == "task_stream":
                payload["task_stream"]["id"] = "other-task"
            elif field == "causation":
                status["causation_id"] = "other-command"
            elif field == "child":
                intent = next(e for e in events if e["payload_type"] == "task.lifecycle.side_effect_intent")
                intent["payload"]["event"]["parent_task_id"] = "parent-task"
            elif field == "tool_task":
                proposal = next(e for e in events if e["payload_type"] == "task.lifecycle.proposed")
                proposal["payload"]["event"]["task_kind"] = "tool.read_file"
            elif field == "unfinished_stream":
                detail["stream"]["last_wire_event_type"] = "response.created"
            else:
                payload["event"]["details"]["phase"] = "opening_stream"
            with self.subTest(field=field):
                result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
                self.assertIsNone(result["effective_model"])
                self.assertEqual(result["model_receipt"]["status"], "unverified")

    def test_mismatched_and_multiple_serving_models_fail(self):
        events, _, detail = self.provider_events()
        detail["model"] = "muse-spark-1.3"
        result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "model_mismatch")
        self.assertEqual(result["effective_model"], "muse-spark-1.3")
        self.assertEqual(result["model_receipt"]["status"], "verified")
        more = [event for event in events if event["payload_type"].startswith("task.")]
        extra = json.dumps(more).replace("018f0000-0000-7000-8000-000000002710", "second-task")
        original, _, _ = self.provider_events()
        original[-1:-1] = json.loads(extra)
        result, _ = self.fake_run(stdout="\n".join(map(json.dumps, original)))
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "model_mismatch")
        self.assertEqual(result["primary_model_ids"], ["muse-spark-1.3", runner.MODEL])
        self.assertIsNone(result["effective_model"])

    def test_malformed_provider_completion_stays_in_failure_envelope(self):
        for field in ("model", "request_id", "response_id", "facets"):
            events, status, detail = self.provider_events()
            if field == "facets":
                status["payload"]["event"]["details"]["facets"] = 42
            else:
                detail[field] = {"unexpected": "object"}
            with self.subTest(field=field):
                result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
                self.assertFalse(result["success"])
                self.assertIsNone(result["effective_model"])
                self.assertTrue(REQUIRED <= result.keys())

    def test_every_completed_root_model_task_needs_a_receipt(self):
        for second_receipt in (False, True):
            events, _, _ = self.provider_events()
            more = [event for event in events if event["payload_type"].startswith("task.")
                    and (second_receipt or event["payload_type"] != "task.lifecycle.status")]
            extra = json.dumps(more).replace("018f0000-0000-7000-8000-000000002710", "second-task")
            events[-1:-1] = json.loads(extra)
            with self.subTest(second_receipt=second_receipt):
                result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)))
                self.assertEqual(result["success"], second_receipt)
                self.assertEqual(result["primary_model_ids"], [runner.MODEL])
                self.assertEqual(len(result["provider_model_receipts"]), 2 if second_receipt else 1)
                coverage = result["model_receipt_coverage"]
                self.assertEqual(len(coverage["completed_task_ids"]), 2)
                self.assertEqual(coverage["missing_task_ids"], [] if second_receipt else ["second-task"])
                self.assertEqual(coverage["complete"], second_receipt)
                self.assertEqual(result["model_receipt"]["status"], "verified" if second_receipt else "unverified")
                self.assertEqual(result["effective_model"], runner.MODEL if second_receipt else None)

    def test_echo_rejects_provider_receipt(self):
        result, _ = self.fake_run(stdout=PROVIDER_FIXTURE, provider="echo")
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "model_mismatch")

    def test_native_failure_and_step_limit_preserve_reason(self):
        events = [json.loads(line) for line in FIXTURE.splitlines()]
        events[-1]["payload_type"] = "run.terminal.failed"
        events[-1]["payload"].update(terminal="failed", reason="max model steps reached")
        result, _ = self.fake_run(stdout="\n".join(map(json.dumps, events)), code=1)
        self.assertFalse(result["success"])
        self.assertEqual(result["terminal_reason"], "max model steps reached")
        self.assertIsNone(result["auth_ok"])
        result, _ = self.fake_run(code=1)
        self.assertFalse(result["success"])

    def test_missing_cli_and_invalid_inputs_keep_envelope(self):
        with patch.object(runner.shutil, "which", return_value=None):
            result = runner.run_muse("task")
        self.assertEqual(result["return_code"], -2)
        self.assertEqual(result["status"], "seat_unavailable")
        for kwargs in ({"model": "muse-spark-1.3"}, {"effort": "ultra"}, {"timeout": 0},
                       {"max_steps": 0}, {"allow_write": True, "restrict_tools": True}):
            with self.subTest(kwargs=kwargs):
                result, capture = self.fake_run(**kwargs)
                self.assertFalse(result["success"])
                self.assertTrue(REQUIRED <= result.keys())
                capture.assert_not_called()

    def test_relative_prompt_and_metadata_budget(self):
        (self.workspace / "task.txt").write_text("A scoped task")
        result, _ = self.fake_run(prompt_files=["task.txt"], metadata_json='{"prompt_context":{},"call_id":"hidden"}')
        self.assertEqual(result["adapter_input_measurement"]["utf8_bytes"], len("A scoped task"))
        self.assertEqual(result["dispatch_metadata"]["call_id"], "hidden")
        result, capture = self.fake_run(metadata_json='{"input_measurement":{"max_bytes":1,"reason":"test"}}')
        self.assertFalse(result["success"])
        capture.assert_not_called()

    def test_startup_hooks_plugins_and_mcp_block(self):
        settings = self.workspace / "config" / "muse" / "settings.json"
        settings.parent.mkdir(parents=True)
        for key in ("hooks", "plugins", "mcpServers", "mcp_servers", "managed_hooks_path"):
            settings.write_text(json.dumps({key: {"configured": True}}))
            with self.subTest(key=key), self.assertRaises(ValueError):
                runner.check_startup_configuration(self.workspace)
        settings.unlink()
        (self.workspace / ".muse").mkdir()
        (self.workspace / ".muse" / "hooks.json").write_text("{}")
        with self.assertRaises(ValueError):
            runner.check_startup_configuration(self.workspace)

    def test_version_and_profile_preflight_no_inference(self):
        def response(command, **kwargs):
            output = "Muse Code " + runner.VERSION if command[1] == "--version" else "model:  " + runner.MODEL + "\neffort: max"
            return subprocess.CompletedProcess(command, 0, output, "")
        with patch.object(runner.subprocess, "run", side_effect=response) as run:
            result = runner.preflight("muse", self.workspace, "max")
        self.assertEqual(run.call_count, 2)
        self.assertEqual(result["model_entitlement"], "unknown")
        self.assertTrue(all("exec" not in call.args[0] for call in run.call_args_list))
        with patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "future", "")):
            with self.assertRaises(ValueError):
                runner.preflight("muse", self.workspace, "high")

    def test_timeout_kills_process_group(self):
        marker = self.workspace / "orphan.txt"
        child = "import time,pathlib;time.sleep(0.8);pathlib.Path(" + repr(str(marker)) + ").write_text('orphan')"
        parent = "import subprocess,time;subprocess.Popen(" + repr([sys.executable, "-c", child]) + ");time.sleep(10)"
        with self.assertRaises(subprocess.TimeoutExpired):
            runner.capture([sys.executable, "-c", parent], self.workspace, 0.15)
        time.sleep(0.9)
        self.assertFalse(marker.exists())
        with patch.object(runner.shutil, "which", return_value="muse"), \
             patch.object(runner, "preflight", return_value={}), \
             patch.object(runner, "capture", side_effect=subprocess.TimeoutExpired("muse", 1)):
            result = runner.run_muse("task")
        self.assertEqual(result["status"], "timeout")
        self.assertFalse(result["success"])

    def test_required_receipt_and_scoped_privacy_fail_closed(self):
        result, _ = self.fake_run(require_model_receipt=True)
        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "model_unverified")
        result, _ = self.fake_run(stdout=PROVIDER_FIXTURE, require_model_receipt=True)
        self.assertTrue(result["success"])
        result, capture = self.fake_run(metadata_json='{"privacy_evidence":{}}')
        self.assertFalse(result["success"])
        capture.assert_not_called()

    def test_cancellation_stops_native_process(self):
        ready = self.workspace / "ready"
        marker = self.workspace / "orphan"
        grandchild = "import time,pathlib;time.sleep(1);pathlib.Path(" + repr(str(marker)) + ").touch()"
        native = "import subprocess,time,pathlib;subprocess.Popen(" + repr([sys.executable, "-c", grandchild]) + ");pathlib.Path(" + repr(str(ready)) + ").touch();time.sleep(10)"
        entry = "import importlib.util; s=importlib.util.spec_from_file_location('r'," + repr(str(ROOT / "scripts/run_muse.py")) + ");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.capture(" + repr([sys.executable, "-c", native]) + "," + repr(str(self.workspace)) + ",10)"
        process = subprocess.Popen([sys.executable, "-c", entry], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=5)
            time.sleep(1.1)
            self.assertFalse(marker.exists())
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_cli_output_file_and_relative_prompt(self):
        binary = self.workspace / "muse-fixture"
        binary.write_text(
            "#!" + sys.executable + "\nimport sys\n"
            "if sys.argv[1] == '--version': print(" + repr("Muse Code " + runner.VERSION) + ")\n"
            "elif sys.argv[1] == 'model-profile': print(" + repr("model: " + runner.MODEL + "\neffort: high") + ")\n"
            "else: print(" + repr(FIXTURE) + ")\n"
        )
        binary.chmod(0o755)
        (self.workspace / "task.txt").write_text("Task from a relative file")
        output = self.workspace / "result.json"
        command = [sys.executable, str(ROOT / "scripts" / "run_muse.py"), "--prompt-file", "task.txt",
                   "--working-dir", str(self.workspace), "--provider", "echo", "--json", "--output-file", str(output)]
        env = {**os.environ, "MUSE_CLI_PATH": str(binary)}
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["output_file"], str(output))
        saved = json.loads(output.read_text())
        self.assertTrue(REQUIRED <= saved.keys())
        self.assertEqual(saved["agent_message"], "echo: Runner transport check")
        (self.workspace / "task.txt").unlink()
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(output.read_text())["success"])

    def test_optional_seat_does_not_change_defaults(self):
        config = runner.load_config()
        self.assertIn("muse-wonder-full", config["models"])
        self.assertNotIn("muse-wonder-full", config["conditional_models"])
        self.assertEqual(config["models"]["muse-wonder-full"]["privacy"]["evidence_type"], "user_confirmed")


if __name__ == "__main__":
    unittest.main()
