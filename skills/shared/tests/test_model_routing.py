#!/usr/bin/env python3
"""Offline guards for model routing and approved implementation routes."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
from skill_paths import skill_dir  # noqa: E402


def P(rel: str) -> Path:
    """Resolve a skill-relative path in either supported layout."""
    name, _, rest = rel.partition("/")
    root = skill_dir(name, root=REPO_ROOT)
    return root / rest if rest else root


class ModelRoutingContractTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return P(path).read_text(encoding="utf-8")

    def test_frontier_roster_has_astra_and_fable(self):
        roster = self.read("shared/references/model-roster.md")
        self.assertIn("| astra |", roster)
        self.assertIn("gpt-6-astra", roster)
        self.assertIn("| fable |", roster)
        self.assertIn("claude-fable-5-1", roster)
        self.assertIn("effective_model", roster)
        self.assertIn("not a benchmark ranking", roster)

    def test_task_routing_requires_approved_exact_routes(self):
        routing = self.read("shared/references/task-shaped-model-routing.md")
        self.assertIn("presents a model summary before any worker starts", routing)
        self.assertIn("`--disable-fallback`", routing)
        self.assertIn("unexpected runner or configured model blocks the route", routing)
        self.assertIn("model_verification: required", routing)
        self.assertIn("allow_unverified", routing)
        self.assertNotIn("escalation, never a default", routing)
        self.assertIn("Astra, `medium`", routing)
        self.assertIn("Fable, `medium`", routing)

    def test_routing_plan_binds_approval_scope_and_routes(self):
        schema = json.loads(
            self.read("shared/references/implementation-routing-plan.schema.json")
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        self.assertIn("scope", schema["required"])
        self.assertIn("approval", schema["required"])
        scope = schema["properties"]["scope"]
        self.assertIn("inputs", scope["required"])
        input_schema = scope["properties"]["inputs"]["items"]
        self.assertIn("content_sha256", input_schema["required"])
        approval = schema["properties"]["approval"]
        self.assertEqual(approval["properties"]["status"]["const"], "approved")
        self.assertEqual(
            set(approval["required"]),
            {"status", "decided_at", "reference", "scope_digest", "routes_digest"},
        )
        route = schema["definitions"]["route"]
        self.assertTrue(
            {
                "id",
                "task_id",
                "input_path",
                "track",
                "role",
                "seat",
                "runner",
                "model",
                "model_verification",
                "effort",
                "effort_control",
                "mode",
                "unavailable",
            }.issubset(route["required"])
        )
        actions = {
            option["properties"]["action"]["const"]
            for option in schema["definitions"]["unavailable"]["oneOf"]
        }
        self.assertEqual(actions, {"block", "use"})
        self.assertNotIn("dcode", schema["definitions"]["runner"]["enum"])

    def test_frontier_seats_are_opt_in_transport_probes(self):
        discovery = self.read("shared/scripts/discover_runners.py")
        self.assertIn('seat="astra"', discovery)
        self.assertIn('seat="fable"', discovery)
        self.assertIn('tier="frontier"', discovery)
        self.assertIn("only a verified model receipt can confirm", discovery)
        self.assertIn('"codex": "astra"', discovery)

    def test_codex_runner_uses_astra_and_records_clamps(self):
        runner = self.read("codex-runner/scripts/run_codex.py")
        self.assertIn('DEFAULT_MODEL = "gpt-6-astra"', runner)
        self.assertIn('"astra": "gpt-6-astra"', runner)
        self.assertIn('"codex": "gpt-6-astra"', runner)
        self.assertNotIn('"codex": "gpt-5.3-codex"', runner)
        self.assertIn('"ultra"', runner)
        self.assertIn('"requested_effort": effort', runner)
        self.assertIn('"effort_clamped": effort is not None', runner)

    def test_removed_workflow_panel_routes_stay_removed(self):
        for path in (
            "brainstorm/assets/panel-routing.toml",
            "to-prd/assets/panel-routing.toml",
            "to-tasks/assets/panel-routing.toml",
        ):
            with self.subTest(path=path):
                self.assertFalse(P(path).exists())

    def test_diverse_plan_uses_shared_task_routing(self):
        text = self.read("diverse-plan/SKILL.md")
        self.assertIn("task-shaped-model-routing.md", text)
        self.assertIn("Astra", text)
        self.assertIn("Fable", text)
        self.assertNotIn("Synthesize and enrich (Opus seat)", text)

    def test_collaborative_delivery_uses_frontier_defaults_and_approval(self):
        routing = self.read("collaborative-delivery/assets/routing.toml")
        workflow = self.read("collaborative-delivery/SKILL.md")
        self.assertIn('model = "gpt-6-astra"', routing)
        self.assertIn('model = "claude-fable-5-1"', routing)
        self.assertIn('"--effort", "medium"', routing)
        self.assertIn("approved routing plan", workflow)
        self.assertIn("serving-model receipt", workflow)

    def test_local_preferences_are_preview_only(self):
        example = (REPO_ROOT.parent / ".rar-skills" / "config.local.example.yaml").read_text(
            encoding="utf-8"
        )
        reference = self.read("shared/references/local-config.md")
        implementation = self.read("implement-tasks/SKILL.md")
        council = self.read("models-consensus/SKILL.md")
        self.assertIn("seats:", example)
        self.assertIn("models: {}", example)
        self.assertNotIn("work_engine_preferences", example)
        self.assertNotIn("runner_base_path", example)
        self.assertNotIn("quorum:", example)
        self.assertIn("Do not read it again for dispatch", reference)
        self.assertIn("config.local.yaml", implementation)
        self.assertIn("never reread it after approval", implementation)
        self.assertIn("config.local.yaml", council)
        self.assertIn("never reread it after approval", council)


if __name__ == "__main__":
    unittest.main(verbosity=2)
