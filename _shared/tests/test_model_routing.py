#!/usr/bin/env python3
"""Offline guards for task shaped model routing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_routing(path: str) -> dict:
    with (REPO_ROOT / path).open("rb") as handle:
        return tomllib.load(handle)


class PanelRoutingTests(unittest.TestCase):
    def test_ambiguous_planning_uses_opus_synthesis_and_codex_challenge(self):
        for path in (
            "brainstorm/assets/panel-routing.toml",
            "to-spec/assets/panel-routing.toml",
        ):
            with self.subTest(path=path):
                providers = load_routing(path)["providers"]
                self.assertEqual(providers["synthesis_anchor"]["kind"], "runner")
                self.assertEqual(providers["synthesis_anchor"]["runner"], "claude")
                self.assertEqual(providers["synthesis_anchor"]["model"], "opus")
                self.assertEqual(providers["adversarial_anchor"]["kind"], "native_codex")
                self.assertEqual(providers["adversarial_anchor"]["model"], "gpt-5.6-sol")

    def test_explicit_planning_and_delivery_keep_codex_synthesis(self):
        for path in (
            "to-tasks/assets/panel-routing.toml",
            "collaborative-delivery/assets/routing.toml",
        ):
            with self.subTest(path=path):
                providers = load_routing(path)["providers"]
                self.assertEqual(providers["synthesis_anchor"]["kind"], "native_codex")
                self.assertEqual(providers["synthesis_anchor"]["model"], "gpt-5.6-sol")
                self.assertEqual(providers["adversarial_anchor"]["model"], "opus")


class SkillRoutingContractTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return (REPO_ROOT / path).read_text(encoding="utf-8")

    def test_shared_policy_uses_seats_instead_of_version_ids(self):
        text = self.read("_shared/references/task-shaped-model-routing.md")
        self.assertNotIn("gpt-", text.lower())
        self.assertNotIn("claude-opus-", text.lower())
        self.assertIn("cost per accepted result", text)
        self.assertIn("effective model receipt", text)

    def test_diverse_plan_routes_judgment_to_opus_and_execution_check_to_codex(self):
        text = self.read("diverse-plan/SKILL.md")
        self.assertNotIn("Opus 4.8", text)
        self.assertNotIn("--effort xhigh", text)
        self.assertIn("Synthesize and enrich (Opus seat)", text)
        self.assertIn("Execution completeness check", text)

    def test_full_review_has_recall_precision_pair(self):
        skill = self.read("full-review/SKILL.md")
        prompts = self.read("full-review/references/external_prompt_template.md")
        self.assertIn("Opus `precision_root_cause`", skill)
        self.assertIn("default Codex seat + one cheap sweep seat", skill)
        self.assertIn("### `precision_root_cause`", prompts)
        self.assertIn("symptom to mechanism to cause chain", prompts)

    def test_consensus_quality_prefers_opus_and_budget_prefers_codex(self):
        protocol = self.read("models-consensus/references/poll-protocol.md")
        self.assertIn("In `quality` and `research`, default to the Opus seat", protocol)
        self.assertIn("In `budget`, use the Codex seat", protocol)

    def test_qwen_uses_cline_with_qwen38_max(self):
        roster = self.read("_shared/references/model-roster.md")
        discovery = self.read("_shared/scripts/discover_runners.py")
        runner = self.read("qwen-runner/scripts/run_qwen.py")
        self.assertIn("qwen/qwen3.8-max", roster)
        self.assertIn('execution_path="qwen_runner_via_cline"', discovery)
        self.assertIn('probe_cli="cline"', discovery)
        self.assertIn('DEFAULT_MODEL = "qwen/qwen3.8-max"', runner)
        self.assertIn("import run_cline", runner)

    def test_muse_uses_cline_with_muse_spark(self):
        roster = self.read("_shared/references/model-roster.md")
        discovery = self.read("_shared/scripts/discover_runners.py")
        runner = self.read("muse-runner/scripts/run_muse.py")
        self.assertIn("meta/muse-spark-1.1", roster)
        self.assertIn('execution_path="muse_runner_via_cline"', discovery)
        self.assertIn('DEFAULT_MODEL = "meta/muse-spark-1.1"', runner)
        self.assertIn("import run_cline", runner)


class DeliveryLauncherRoutingTests(unittest.TestCase):
    def run_dry_launch(self, *extra: str) -> dict:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            brief = temp / "frontend.md"
            brief.write_text("frontend acceptance contract", encoding="utf-8")
            command = [
                sys.executable,
                str(REPO_ROOT / "implement-and-review/scripts/launch.py"),
                "launch",
                "--session-id",
                "routing-test",
                "--fe-brief",
                str(brief),
                "--no-backend",
                "--allow-dirty",
                "--worktrees-dir",
                str(temp / "worktrees"),
                "--dry-run",
                *extra,
            ]
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(completed.stdout)

    def test_standard_frontend_defaults_to_codex_runner(self):
        manifest = self.run_dry_launch()
        frontend = manifest["tracks"]["frontend"]
        self.assertEqual(frontend["seat"], "codex")
        self.assertEqual(frontend["runner"], "codex")
        self.assertEqual(frontend["mode"], "runner")

    def test_visual_frontend_auto_selects_opus_subagent(self):
        manifest = self.run_dry_launch("--fe-seat", "opus")
        frontend = manifest["tracks"]["frontend"]
        self.assertEqual(frontend["seat"], "opus")
        self.assertEqual(frontend["runner"], "opus-subagent")
        self.assertEqual(frontend["mode"], "subagent")

    def test_visual_frontend_can_use_claude_runner(self):
        manifest = self.run_dry_launch("--fe-seat", "opus", "--fe-mode", "runner")
        frontend = manifest["tracks"]["frontend"]
        self.assertEqual(frontend["seat"], "opus")
        self.assertEqual(frontend["runner"], "claude")
        self.assertEqual(frontend["mode"], "runner")

    def test_codex_frontend_rejects_subagent_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            brief = Path(temp_dir) / "frontend.md"
            brief.write_text("frontend acceptance contract", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "implement-and-review/scripts/launch.py"),
                    "launch",
                    "--session-id",
                    "routing-test",
                    "--fe-brief",
                    str(brief),
                    "--no-backend",
                    "--allow-dirty",
                    "--dry-run",
                    "--fe-seat",
                    "codex",
                    "--fe-mode",
                    "subagent",
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("only valid with --fe-seat opus", completed.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
