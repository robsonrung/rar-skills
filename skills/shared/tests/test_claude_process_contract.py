"""Exercise the runner process boundary without credentials or provider access."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILLS = Path(__file__).resolve().parents[2]
RUNNER = SKILLS / "engineering/seats/claude-runner/scripts/run_claude.py"

# The fake accepts only local probes and a print request. It records the latter
# so a blocked preflight must leave the file absent.
FAKE_CLI = r'''
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ["FIXTURE_CONTEXT"]).open("a") as log:
    log.write(json.dumps({"cli": sys.argv[0], "cwd": os.getcwd(),
                          "token_visible": os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") == "fixture-only-token"}) + "\n")
if args == ["--version"]:
    print(os.environ.get("FIXTURE_VERSION", "2.1.281") + " (Claude Code)")
elif args[:2] == ["auth", "status"]:
    print(json.dumps({"loggedIn": False, "email": "private-fixture@example.invalid"}))
elif "--help" in args:
    print("--safe-mode --tools --strict-mcp-config --mcp-config --effort --max-turns --max-budget-usd --print")
elif "-p" in args or "--print" in args:
    Path(os.environ["FIXTURE_CALL"]).write_text(json.dumps(args))
    def option(name, default=None):
        return args[args.index(name) + 1] if name in args else default
    model = os.environ.get("FIXTURE_SERVED_MODEL", option("--model", "claude-opus-5-5"))
    allowed = option("--tools", "Read,Glob,Grep")
    tools = allowed.split(",") if allowed else []
    if os.environ.get("FIXTURE_EXTRA_TOOL"):
        tools.append("Write")
    message = json.dumps({"answer": "Use the verified result.", "key_points": ["One source."],
                          "assumptions": [], "confidence": 90})
    events = [
        {"type": "system", "subtype": "init", "session_id": "fixture-session",
         "tools": tools, "mcp_servers": []},
        {"type": "assistant", "parent_tool_use_id": None,
         "message": {"id": "fixture-message", "model": model,
                     "content": [{"type": "text", "text": message}]}},
        {"type": "result", "subtype": "success", "session_id": "fixture-session",
         "result": message, "duration_ms": 20, "total_cost_usd": 0.001,
         "usage": {"input_tokens": 10, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 0, "output_tokens": 5}},
    ]
    if option("--output-format") == "stream-json":
        for event in events:
            print(json.dumps(event), flush=True)
    else:
        print(json.dumps(events))
else:
    raise SystemExit("Unexpected fixture command")
'''


class ClaudeProcessContractTests(unittest.TestCase):
    def invoke(self, *, version="2.1.281", output_format="json", served=None, extra_tool=False,
               relative_path=False, model="claude-opus-5-5", effort="medium"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cli = root / "claude"
            cli.write_text(f"#!{sys.executable}\n" + FAKE_CLI)
            cli.chmod(0o755)
            call = root / "invoked.json"
            context = root / "contexts.jsonl"
            output = root / "receipt.json"
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith(("ANTHROPIC_", "CLAUDE_", "FIXTURE_"))}
            env.update(PATH=("." if relative_path else str(root)) + os.pathsep + os.defpath,
                       FIXTURE_VERSION=version, FIXTURE_CALL=str(call), FIXTURE_CONTEXT=str(context),
                       CLAUDE_CODE_OAUTH_TOKEN="fixture-only-token")
            if served:
                env["FIXTURE_SERVED_MODEL"] = served
            if extra_tool:
                env["FIXTURE_EXTRA_TOOL"] = "1"
            selection = []
            if model is not None:
                selection.extend(["--model", model])
            if effort is not None:
                selection.extend(["--effort", effort])
            proc = subprocess.run(
                [sys.executable, str(RUNNER), "Return the requested object.",
                 *selection,
                 "--tool-profile", "repo_read_only", "--disable-fallback",
                 "--max-turns", "3", "--max-budget-usd", "0.25",
                 "--output-format", output_format, "--output-file", str(output),
                 "--working-dir", str(root), "--json"],
                env=env, cwd=root, text=True, capture_output=True, timeout=15, check=False)
            self.assertTrue(output.exists(), proc.stdout + proc.stderr)
            receipt = json.loads(output.read_text())
            self.assertNotIn("private-fixture", json.dumps(receipt))
            self.assertNotIn("fixture-only-token", json.dumps(receipt))
            contexts = [json.loads(line) for line in context.read_text().splitlines()]
            self.assertTrue(contexts)
            expected = {"cli": str(cli.resolve()) if relative_path else str(cli),
                        "cwd": str(root.resolve()), "token_visible": True}
            self.assertTrue(all(item == expected for item in contexts), contexts)
            return proc, receipt, json.loads(call.read_text()) if call.exists() else None

    def test_old_cli_is_blocked_before_print_request(self):
        proc, receipt, arguments = self.invoke(version="2.1.275")
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(receipt["success"])
        self.assertIsNone(arguments)
        self.assertIn("2.1.280", json.dumps(receipt))
        self.assertTrue(receipt["preflight"]["blocked"])
        self.assertIsNone(receipt["auth_ok"])
        self.assertIs(receipt["print_invocation_started"], False)
        self.assertIs(receipt["metrics_complete"], True)
        self.assertGreaterEqual(receipt["metrics"]["duration_ms"], 0)
        self.assertTrue(all(value == 0 for key, value in receipt["metrics"].items() if key != "duration_ms"))
        self.assertIsNone(receipt["session_id"])
        self.assertEqual(receipt["stdout"], "")

    def test_unknown_required_version_blocks_before_print_request(self):
        proc, receipt, arguments = self.invoke(version="unknown")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(arguments)
        self.assertEqual(receipt["preflight"]["checks"]["compatibility"]["status"], "unknown")

    def test_relative_path_resolution_matches_execution_directory(self):
        proc, receipt, arguments = self.invoke(relative_path=True)
        self.assertEqual(proc.returncode, 0, receipt)
        self.assertIsNotNone(arguments)

    def test_omitted_model_and_effort_preserve_runtime_defaults(self):
        proc, receipt, arguments = self.invoke(model=None, effort=None)
        self.assertEqual(proc.returncode, 0, receipt)
        self.assertNotIn("--model", arguments)
        self.assertNotIn("--effort", arguments)
        self.assertIsNone(receipt["requested_model"])
        self.assertIsNone(receipt["configured_model"])
        self.assertIsNone(receipt["model_matches_requested"])
        self.assertEqual(receipt["preflight"]["checks"]["compatibility"]["status"], "unknown")
        self.assertEqual(receipt["preflight"]["checks"]["effort"]["status"], "unknown")

    def test_explicit_model_with_omitted_effort_preserves_runtime_effort(self):
        proc, receipt, arguments = self.invoke(effort=None)
        self.assertEqual(proc.returncode, 0, receipt)
        self.assertEqual(arguments[arguments.index("--model") + 1], "claude-opus-5-5")
        self.assertNotIn("--effort", arguments)
        self.assertEqual(receipt["preflight"]["checks"]["compatibility"]["status"], "true")
        self.assertEqual(receipt["preflight"]["checks"]["effort"]["status"], "unknown")

    def test_omitted_effort_does_not_skip_explicit_model_version_check(self):
        proc, receipt, arguments = self.invoke(version="2.1.275", effort=None)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIsNone(arguments)
        self.assertEqual(receipt["preflight"]["checks"]["compatibility"]["status"], "false")

    def test_json_and_stream_preserve_receipt_and_restrictions(self):
        for output_format in ("json", "stream-json"):
            with self.subTest(output_format=output_format):
                proc, receipt, arguments = self.invoke(output_format=output_format)
                self.assertEqual(proc.returncode, 0, receipt)
                self.assertTrue(receipt["success"])
                self.assertEqual(receipt["effective_model"], "claude-opus-5-5")
                self.assertEqual(receipt["model_receipt"]["status"], "verified")
                self.assertFalse(receipt["preflight"]["blocked"])
                self.assertIs(receipt["print_invocation_started"], True)
                self.assertEqual(receipt["preflight"]["evidence"]["provider_calls"], 0)
                self.assertEqual(receipt["preflight"]["checks"]["auth_visibility"]["status"], "unknown")
                self.assertEqual(set(arguments[arguments.index("--tools") + 1].split(",")),
                                 {"Read", "Glob", "Grep"})
                self.assertIn("--safe-mode", arguments)
                self.assertIn("--strict-mcp-config", arguments)
                self.assertEqual(json.loads(arguments[arguments.index("--mcp-config") + 1]),
                                 {"mcpServers": {}})
                self.assertEqual(arguments[arguments.index("--max-turns") + 1], "3")
                self.assertEqual(arguments[arguments.index("--max-budget-usd") + 1], "0.25")
                self.assertEqual(receipt["metrics"]["input_tokens"], 10)
                self.assertEqual(receipt["metrics"]["output_tokens"], 5)

    def test_serving_mismatch_cannot_be_a_success(self):
        proc, receipt, _ = self.invoke(served="claude-fable-5-1")
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(receipt["success"])

    def test_observed_write_tool_cannot_be_a_success(self):
        proc, receipt, _ = self.invoke(extra_tool=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(receipt["success"])


if __name__ == "__main__":
    unittest.main()
