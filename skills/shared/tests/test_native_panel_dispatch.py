#!/usr/bin/env python3
"""Offline compatibility tests for host-native panel roles.

The panel must leave host-native execution to the host. These tests only inspect
the pending handoff and response-recording behavior; no model command is started.

Run: python3 shared/tests/test_native_panel_dispatch.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
PANEL_ROUND = SKILLS_ROOT / "shared" / "scripts" / "panel_round.py"
RECORD_NATIVE_RESPONSE = SKILLS_ROOT / "shared" / "scripts" / "record_native_response.py"


def toml_string(value: str) -> str:
    return json.dumps(value)


def write_routing(
    directory: Path,
    *,
    kind: str,
    host: str | None = "chatgpt",
    provider: str | None = "openai",
    transport: str = "host_subagent",
    script: Path | None = None,
    runner: str | None = None,
) -> tuple[Path, Path]:
    artifact_dir = directory / "artifacts"
    values = [
        "[skill]",
        'name = "native-panel-test"',
        f"artifact_dir = {toml_string(str(artifact_dir))}",
        'required_phases = ["intake"]',
        "",
        "[providers.native_role]",
        f"kind = {toml_string(kind)}",
    ]
    if host is not None:
        values.append(f"host = {toml_string(host)}")
    if provider is not None:
        values.append(f"provider = {toml_string(provider)}")
    if script is not None:
        values.append(f"script = {toml_string(str(script))}")
    if runner is not None:
        values.append(f"runner = {toml_string(runner)}")
    values.extend(
        [
            f"transport = {toml_string(transport)}",
            'model = "gpt-6-astra"',
            'effort = "max"',
            'effort_control = "configured"',
            "",
            "[roles.native_role]",
            'provider = "native_role"',
            "",
            "[phases.intake]",
            'roles = ["native_role"]',
            "",
        ]
    )
    routing = directory / "routing.toml"
    routing.write_text("\n".join(values), encoding="utf-8")
    return routing, artifact_dir


def run_panel_process(
    routing: Path,
    artifact_dir: Path,
    *,
    role_sessions: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PANEL_ROUND),
        "--phase",
        "intake",
        "--goal",
        "Check host-native handoff.",
        "--routing",
        str(routing),
        "--out",
        str(artifact_dir),
    ]
    for role_session in role_sessions:
        command.extend(["--role-session", role_session])
    command.append("--fail-on-incomplete")
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def run_panel(
    routing: Path,
    artifact_dir: Path,
    *,
    role_sessions: tuple[str, ...] = (),
) -> tuple[subprocess.CompletedProcess[str], dict]:
    process = run_panel_process(routing, artifact_dir, role_sessions=role_sessions)
    return process, json.loads(process.stdout)


def write_fake_runner(directory: Path, runner: str) -> tuple[Path, Path]:
    invocation_log = directory / "runner-invocations.jsonl"
    script = directory / "fake_runner.py"
    script.write_text(
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
        f"invocation_log = Path({str(invocation_log)!r})\n"
        f"runner = {runner!r}\n"
        "arguments = sys.argv[1:]\n"
        "metadata = json.loads(arguments[arguments.index('--metadata-json') + 1])\n"
        "output_file = Path(arguments[arguments.index('--output-file') + 1])\n"
        "record = {'role': metadata['role'], 'arguments': arguments}\n"
        "with invocation_log.open('a', encoding='utf-8') as handle:\n"
        "    handle.write(json.dumps(record) + '\\n')\n"
        "session_id = (\n"
        "    arguments[arguments.index('--session') + 1]\n"
        "    if '--session' in arguments\n"
        "    else 'returned-' + metadata['role']\n"
        ")\n"
        "payload = {\n"
        "    'success': True,\n"
        "    'return_code': 0,\n"
        "    'effective_runner': runner,\n"
        "    'effective_provider': 'test-provider',\n"
        "    'requested_model': 'test-model',\n"
        "    'configured_model': 'test-model',\n"
        "    'effective_model': None,\n"
        "    'model_receipt': {'status': 'unverified', 'source': 'configured_model', 'observed_model': None},\n"
        "    'session_id': session_id,\n"
        "}\n"
        "output_file.write_text(json.dumps(payload), encoding='utf-8')\n"
        "print(json.dumps(payload))\n",
        encoding="utf-8",
    )
    return script, invocation_log


def write_runner_routing(
    directory: Path,
    *,
    runner: str,
    roles: tuple[str, ...],
    runner_args: tuple[str, ...] = (),
) -> tuple[Path, Path, Path]:
    artifact_dir = directory / "artifacts"
    script, invocation_log = write_fake_runner(directory, runner)
    values = [
        "[skill]",
        'name = "runner-panel-test"',
        f"artifact_dir = {toml_string(str(artifact_dir))}",
        'required_phases = ["intake"]',
        "",
        "[providers.shared]",
        'kind = "runner"',
        f"runner = {toml_string(runner)}",
        'provider = "test-provider"',
        'model = "test-model"',
        'session_policy = "per-role-persistent"',
        f"script = {toml_string(str(script))}",
        f"runner_args = {json.dumps(list(runner_args))}",
    ]
    for role in roles:
        values.extend(["", f"[roles.{role}]", 'provider = "shared"'])
    values.extend(["", "[phases.intake]", f"roles = {json.dumps(list(roles))}", ""])
    routing = directory / "runner-routing.toml"
    routing.write_text("\n".join(values), encoding="utf-8")
    return routing, artifact_dir, invocation_log


def read_invocations(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class NativePanelDispatchTests(unittest.TestCase):
    def test_generic_native_records_host_handoff_without_dispatching(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir = write_routing(root, kind="native")

            process, summary = run_panel(
                routing,
                artifact_dir,
                role_sessions=("native_role=native-context-42",),
            )

            self.assertEqual(process.returncode, 2, process.stderr)
            result = summary["latest_run"]["results"][0]
            self.assertEqual(result["status"], "awaiting_native_execution")
            self.assertEqual(result["participation"], "prompt_only")
            self.assertEqual(result["kind"], "native")
            self.assertEqual(result["host"], "chatgpt")
            self.assertEqual(result["provider"], "openai")
            self.assertEqual(result["transport"], "host_subagent")
            self.assertEqual(result["requested_model"], "gpt-6-astra")
            self.assertEqual(result["requested_effort"], "max")
            self.assertIsNone(result["session_id"])
            self.assertEqual(
                result["native_handoff"],
                {
                    "host": "chatgpt",
                    "provider": "openai",
                    "transport": "host_subagent",
                    "requested_model": "gpt-6-astra",
                    "requested_effort": "max",
                    "effort_control": "configured",
                    "context_id": "native-context-42",
                },
            )
            self.assertIsNone(result["effective_model"])
            self.assertEqual(result["model_receipt"]["status"], "unverified")
            self.assertEqual(result["model_receipt"]["source"], "not_observed")
            self.assertTrue(Path(result["prompt_path"]).exists())
            self.assertFalse(Path(result["expected_response_path"]).exists())

    def test_legacy_native_codex_is_accepted_with_legacy_host_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir = write_routing(
                root,
                kind="native_codex",
                host=None,
                provider=None,
            )

            process, summary = run_panel(routing, artifact_dir)

            self.assertEqual(process.returncode, 2, process.stderr)
            result = summary["latest_run"]["results"][0]
            self.assertEqual(result["kind"], "native_codex")
            self.assertEqual(result["provider"], "codex")
            self.assertEqual(result["host"], "codex")
            self.assertEqual(result["native_handoff"]["requested_model"], "gpt-6-astra")
            self.assertEqual(result["native_handoff"]["requested_effort"], "max")

    def test_unrelated_kind_is_rejected_without_running_its_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / "dispatched.txt"
            marker_script = root / "unexpected_dispatch.py"
            marker_script.write_text(
                "from pathlib import Path\n"
                f"Path({str(marker)!r}).write_text('dispatched', encoding='utf-8')\n",
                encoding="utf-8",
            )
            routing, artifact_dir = write_routing(
                root,
                kind="not_native",
                script=marker_script,
                runner="marker",
            )

            process, summary = run_panel(routing, artifact_dir)

            self.assertEqual(process.returncode, 2, process.stderr)
            result = summary["latest_run"]["results"][0]
            self.assertEqual(result["status"], "unknown_kind")
            self.assertEqual(result["kind"], "not_native")
            self.assertFalse(marker.exists())

    def test_two_runner_roles_keep_distinct_explicit_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir, invocation_log = write_runner_routing(
                root,
                runner="claude",
                roles=("first", "second"),
            )

            process, summary = run_panel(
                routing,
                artifact_dir,
                role_sessions=("first=first-session", "second=second-session"),
            )

            self.assertEqual(process.returncode, 0, process.stderr)
            results = {result["role"]: result for result in summary["latest_run"]["results"]}
            self.assertEqual(results["first"]["requested_session_id"], "first-session")
            self.assertEqual(results["second"]["requested_session_id"], "second-session")
            self.assertEqual(results["first"]["session_id"], "returned-first")
            self.assertEqual(results["second"]["session_id"], "returned-second")

            invocations = {item["role"]: item["arguments"] for item in read_invocations(invocation_log)}
            self.assertEqual(invocations["first"][invocations["first"].index("--resume") + 1], "first-session")
            self.assertEqual(invocations["second"][invocations["second"].index("--resume") + 1], "second-session")
            self.assertNotIn("--continue", invocations["first"])
            self.assertNotIn("--continue", invocations["second"])

    def test_supported_runners_use_their_explicit_resume_flag(self) -> None:
        expected_flags = {
            "claude": "--resume",
            "codex": "--resume",
            "grok": "--resume",
            "pi": "--session",
        }
        for runner, expected_flag in expected_flags.items():
            with self.subTest(runner=runner), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                routing, artifact_dir, invocation_log = write_runner_routing(
                    root,
                    runner=runner,
                    roles=("worker",),
                )

                process, summary = run_panel(
                    routing,
                    artifact_dir,
                    role_sessions=("worker=saved-role-session",),
                )

                self.assertEqual(process.returncode, 0, process.stderr)
                invocation = read_invocations(invocation_log)[0]
                arguments = invocation["arguments"]
                self.assertEqual(arguments[arguments.index(expected_flag) + 1], "saved-role-session")
                result = summary["latest_run"]["results"][0]
                if runner == "pi":
                    self.assertEqual(result["session_id"], "saved-role-session")
                else:
                    self.assertEqual(result["session_id"], "returned-worker")

    def test_unsupported_runner_session_does_not_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir, invocation_log = write_runner_routing(
                root,
                runner="gemini",
                roles=("worker",),
            )

            process, summary = run_panel(
                routing,
                artifact_dir,
                role_sessions=("worker=saved-role-session",),
            )

            self.assertEqual(process.returncode, 2, process.stderr)
            result = summary["latest_run"]["results"][0]
            self.assertEqual(result["status"], "session_resume_unsupported")
            self.assertEqual(result["session_id"], None)
            self.assertEqual(read_invocations(invocation_log), [])

    def test_duplicate_role_sessions_are_rejected_before_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir, invocation_log = write_runner_routing(
                root,
                runner="claude",
                roles=("first", "second"),
            )

            process = run_panel_process(
                routing,
                artifact_dir,
                role_sessions=("first=shared-session", "second=shared-session"),
            )

            self.assertNotEqual(process.returncode, 0)
            self.assertIn("cannot share one session", process.stderr)
            self.assertEqual(read_invocations(invocation_log), [])

    def test_shared_provider_session_argument_is_rejected_before_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir, invocation_log = write_runner_routing(
                root,
                runner="claude",
                roles=("first", "second"),
                runner_args=("--resume", "shared-session"),
            )

            process, summary = run_panel(routing, artifact_dir)

            self.assertEqual(process.returncode, 2, process.stderr)
            results = summary["latest_run"]["results"]
            self.assertTrue(all(result["status"] == "shared_session_argument" for result in results))
            self.assertEqual(read_invocations(invocation_log), [])

    def test_response_helper_accepts_generic_and_legacy_native_kinds(self) -> None:
        for kind in ("native", "native_codex"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                routing, artifact_dir = write_routing(root, kind=kind)
                process = subprocess.run(
                    [
                        sys.executable,
                        str(RECORD_NATIVE_RESPONSE),
                        "--phase",
                        "intake",
                        "--role",
                        "native_role",
                        "--routing",
                        str(routing),
                        "--artifact-dir",
                        str(artifact_dir),
                        "--text",
                        "A real host response.",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                payload = json.loads(process.stdout)
                self.assertTrue(Path(payload["response_path"]).exists())

    def test_response_helper_rejects_an_unrelated_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routing, artifact_dir = write_routing(root, kind="not_native")
            process = subprocess.run(
                [
                    sys.executable,
                    str(RECORD_NATIVE_RESPONSE),
                    "--phase",
                    "intake",
                    "--role",
                    "native_role",
                    "--routing",
                    str(routing),
                    "--artifact-dir",
                    str(artifact_dir),
                    "--text",
                    "This must not be recorded as native.",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("not routed to a native provider", process.stderr)
            self.assertFalse((artifact_dir / "native_responses" / "intake_native_role.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
