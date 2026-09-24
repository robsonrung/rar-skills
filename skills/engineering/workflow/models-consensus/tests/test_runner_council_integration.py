#!/usr/bin/env python3
"""Reconcile the actual runner envelope from a local fixture executable."""

import importlib.util
import inspect
import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_council_state as fixtures

council = fixtures.council
answer = fixtures.answer


class RunnerCouncilIntegrationTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.CouncilStateTests(methodName="runTest")
        fixture.setUp()
        self.addCleanup(fixture.temporary.cleanup)
        skills_root = Path(council.ledger.__file__).resolve().parents[2]
        wrapper = Path(os.environ.get("COUNCIL_TEST_RUNNER", str(skills_root / "engineering/seats/claude-runner/scripts/run_claude.py")))
        spec = importlib.util.spec_from_file_location("council_wrapper_integration", wrapper)
        runner = importlib.util.module_from_spec(spec)
        # An integration checkout may carry a newer receipt parser than this worktree.
        old_receipt_module = sys.modules.pop("model_receipt", None)
        try:
            spec.loader.exec_module(runner)
        finally:
            if old_receipt_module is not None:
                sys.modules["model_receipt"] = old_receipt_module
        if "tool_profile" not in inspect.signature(runner._run_claude).parameters:
            self.skipTest("requires the runner tool-profile change from the integration branch")
        fixture.document["preview"]["execution"][0]["runner"] = "claude"
        self.fixture, self.runner = fixture, runner
        self.binary_dir = fixture.root / "bin"
        self.binary_dir.mkdir()
        self.print_marker = fixture.root / "print-started"

    def invoke(self, call, tools, session, message, resume=None, version="2.1.281"):
        fixture, runner = self.fixture, self.runner
        model = fixture.document["preview"]["roles"][0]["requested_model"]
        events = [{"type": "system", "subtype": "init", "tools": tools, "mcp_servers": []},
                  {"type": "assistant", "message": {"model": model}},
                  {"type": "result", "subtype": "success", "session_id": session, "result": message}]
        executable = self.binary_dir / "claude"
        executable.write_text("#!/bin/sh\n"
                              "case \"$1\" in\n"
                              "--version) printf '%s\\n' " + shlex.quote(version) + ";;\n"
                              "auth) printf '{\"loggedIn\":false}\\n';;\n"
                              "*) printf 'print\\n' >> " + shlex.quote(str(self.print_marker)) + "; printf '%s\\n' "
                              + shlex.quote(json.dumps(events)) + ";;\nesac\n")
        executable.chmod(0o755)
        metadata = json.loads(Path(fixture.read()["call_ledger"]["calls"][call]["council"]["dispatch"]["path"]).read_text())
        with patch.dict(os.environ, {"PATH": str(self.binary_dir) + ":/usr/bin:/bin"}, clear=True), \
             patch.object(runner, "resolve_claude_oauth_token", return_value=None):
            envelope = runner.run_claude("Use the supplied brief.", working_dir=str(fixture.root), model=model, effort="high",
                                        role="researcher", tool_profile="no_tools", output_format="json", disable_fallback=True,
                                        metadata_json=json.dumps(metadata), resume=resume)
        receipt = fixture.root / (call + ".wrapper.json")
        receipt.write_text(json.dumps(envelope))
        return receipt, envelope

    def test_actual_wrapper_preserves_council_role_and_checks_session_and_tools(self):
        fixture = self.fixture
        fixture.reset()
        reservation = fixture.reserve()
        dispatch = json.loads(Path(reservation["dispatch"]["path"]).read_text())
        receipt, envelope = self.invoke("call-1", [], "context-0", "{}")
        self.assertEqual(dispatch["role"], "opening")
        self.assertEqual(envelope["role"], "researcher")
        self.assertTrue(envelope["success"], envelope)
        self.assertEqual(fixture.reconcile(receipt)["status"], "malformed")
        fixture.reserve("retry")
        receipt, envelope = self.invoke("retry", [], "new-unapproved-session", json.dumps(answer()), resume="context-0")
        self.assertEqual(envelope["session_id"], "new-unapproved-session")
        with self.assertRaisesRegex(ValueError, "recorded role context"):
            fixture.reconcile(receipt, "retry")
        receipt, envelope = self.invoke("retry", [], "context-0", json.dumps(answer()), resume="context-0")
        self.assertEqual(fixture.reconcile(receipt, "retry")["status"], "valid")
        self.assertEqual(fixture.read()["call_ledger"]["contexts"]["opening-0"], "context-0")
        fixture.reset()
        fixture.reserve()
        receipt, envelope = self.invoke("call-1", ["Read"], "context-0", json.dumps(answer()))
        self.assertEqual(envelope["tool_profile_receipt"]["status"], "violated")
        self.assertEqual(fixture.reconcile(receipt)["status"], "blocked_receipt")

    def test_old_cli_then_upgrade_recovers_first_context_with_original_budget(self):
        fixture, runner = self.fixture, self.runner
        policy = json.loads((runner._SHARED_SCRIPTS.parent / "runner-compatibility.json").read_text())
        seat = next(iter(policy["claude"]))
        model = runner.ROUTING_CONFIG["models"][seat]["model"]
        preview = fixture.document["preview"]
        preview["seats"][0]["requested_model"] = model
        preview["roles"][0]["requested_model"] = model
        preview["reported_limits"] = {"reported_cost_usd": 1}
        preview["serving_receipt"] = "required"
        for selected in preview["seats"]:
            selected["model_receipt"] = {"status": "verified", "source": "provider_event", "observed_model": selected["requested_model"]}
        fixture.reset()
        fixture.reserve()
        receipt, envelope = self.invoke("call-1", [], "first-context", json.dumps(answer()), version="2.1.275")
        self.assertFalse(self.print_marker.exists())
        self.assertIs(envelope["print_invocation_started"], False)
        self.assertEqual(envelope["terminal_status"], "preflight_blocked")
        self.assertIsNone(envelope["session_id"])
        self.assertEqual(envelope["metrics"]["reported_cost_usd"], 0)
        self.assertIsNotNone(envelope["metrics"]["duration_ms"])
        self.assertEqual(fixture.reconcile(receipt)["status"], "execution_failed")
        before = fixture.read()
        fixture.initialize()
        retry = fixture.reserve("retry")
        self.assertIsNone(retry["context_id"])
        self.assertEqual(fixture.read()["attempts"]["total_role_calls"], 2)
        self.assertEqual(fixture.read()["call_ledger"]["plan"], before["call_ledger"]["plan"])
        receipt, envelope = self.invoke("retry", [], "first-context", json.dumps(answer()))
        self.assertIs(envelope["print_invocation_started"], True)
        self.assertEqual(self.print_marker.read_text().splitlines(), ["print"])
        self.assertEqual(fixture.reconcile(receipt, "retry")["status"], "valid")
        final = fixture.read()
        self.assertEqual(final["call_ledger"]["calls"]["call-1"], before["call_ledger"]["calls"]["call-1"])
        self.assertEqual(final["call_ledger"]["contexts"]["opening-0"], "first-context")
        self.assertEqual(final["attempts"]["total_role_calls"], 2)
        self.assertEqual(final["council"]["retries"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
