#!/usr/bin/env python3
"""Offline guards for model routing and approved implementation routes."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
from skill_paths import skill_dir  # noqa: E402
import model_routing
import discover_runners


def P(rel: str) -> Path:
    """Resolve a skill-relative path in either supported layout."""
    name, _, rest = rel.partition("/")
    root = skill_dir(name, root=REPO_ROOT)
    return root / rest if rest else root


class ModelRoutingContractTests(unittest.TestCase):
    def read(self, path: str) -> str:
        return P(path).read_text(encoding="utf-8")

    def test_frontier_roster_has_astra_and_fable(self):
        config = model_routing.load_config()
        self.assertEqual(config["models"]["astra"]["model"], "gpt-6-astra")
        self.assertEqual(config["models"]["fable"]["model"], "claude-fable-5-2")
        roster = self.read("shared/references/model-roster.md")
        self.assertIn("model-routing.json", roster)
        self.assertIn("effective_model", roster)
        self.assertIn("not a benchmark ranking", roster)

    def test_task_routing_names_current_quality_defaults_and_native_contract(self):
        routing = self.read("shared/references/task-shaped-model-routing.md")
        self.assertIn("host-model-execution.md", routing)
        self.assertIn("model-routing.json", routing)
        roles = model_routing.resolve_route("routine-function", "gpt")["roles"]
        self.assertEqual((roles["implementer"]["seat"], roles["implementer"]["effort"]), ("terra", "medium"))
        self.assertEqual((roles["reviewer"]["seat"], roles["reviewer"]["effort"]), ("astra", "high"))

    def test_frontier_seats_are_opt_in_transport_probes(self):
        specs = {spec.seat: spec for spec in discover_runners.SEAT_SPECS}
        self.assertEqual(specs["astra"].tier, "frontier")
        self.assertEqual(specs["fable"].tier, "frontier")
        self.assertNotIn("astra", [spec.seat for spec in discover_runners.filter_specs(None)])
        self.assertEqual(discover_runners.SEAT_IDENTITIES["codex"], "astra")

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
        self.assertIn("shared/model-routing.json", text)
        self.assertIn("deep-analysis", text)
        self.assertNotIn("Synthesize and enrich (Opus seat)", text)

    def test_saver_profile_is_default_and_resolves_every_route(self):
        config = model_routing.load_config()
        self.assertEqual(config["default_profile"], "saver")
        self.assertEqual(config["profiles"]["saver"]["label"], "Subscription Saver")
        for route in config["routes"]:
            for risk in config["policy"]["risk_levels"]:
                with self.subTest(route=route, risk=risk):
                    resolved = model_routing.resolve_profile(route, "saver", risk=risk, config=config)
                    self.assertEqual(resolved["profile"], "saver")

    def test_saver_pairs_cheap_implementers_with_frontier_reviewers(self):
        config = model_routing.load_config()
        cheap = {"glm", "deepseek-flash"}
        frontier_reviewers = {"astra", "opus"}
        reviewed = 0
        for route in config["routes"].values():
            family = route["families"].get("saver")
            if not family or "implementer" not in family:
                continue
            with self.subTest(route=route):
                self.assertIn(family["implementer"]["seat"], cheap | frontier_reviewers)
                self.assertIn(family["reviewer"]["seat"], frontier_reviewers)
                self.assertNotEqual(family["implementer"]["seat"], family["reviewer"]["seat"])
                reviewed += 1
        self.assertGreaterEqual(reviewed, 10)
        roles = model_routing.resolve_profile("routine-implementation", "saver", config=config)["roles"]
        self.assertEqual((roles["implementer"]["seat"], roles["implementer"]["effort"]), ("glm", "high"))
        self.assertEqual((roles["reviewer"]["seat"], roles["reviewer"]["effort"]), ("astra", "high"))

    def test_opus_5_5_seat_and_effort_scaling_metadata(self):
        config = model_routing.load_config()
        seat = config["models"]["opus"]
        self.assertEqual(seat["model"], "claude-opus-5-5")
        self.assertEqual(seat["runner"], "claude")
        self.assertEqual(seat["effort_scaling"], "non-monotonic")
        for name, entry in config["models"].items():
            if "effort_scaling" in entry:
                with self.subTest(seat=name):
                    self.assertIn(entry["effort_scaling"], model_routing.EFFORT_SCALING_VALUES)
                    self.assertTrue(entry["effort_scaling_evidence"])
        self.assertEqual(config["models"]["fable"]["effort_scaling"], "flat-above-high")
        self.assertEqual(config["models"]["astra"]["effort_scaling"], "monotonic")
        roles = model_routing.resolve_route("sensitive-implementation", "claude")["roles"]
        self.assertEqual((roles["reviewer"]["seat"], roles["reviewer"]["effort"]), ("opus", "high"))
        roles = model_routing.resolve_route("deep-analysis", "claude")["roles"]
        self.assertEqual((roles["worker"]["seat"], roles["worker"]["effort"]), ("fable", "high"))

    def test_seat_admission_requires_zdr_and_records_rejections(self):
        config = model_routing.load_config()
        admission = config["policy"]["seat_admission"]
        self.assertTrue(admission["zdr_required"])
        rejected = {entry["model"] for entry in admission["rejected"]}
        self.assertIn("xiaomi/mimo-v2.6-pro", rejected)
        registered = {entry["model"] for entry in config["models"].values()}
        self.assertFalse(rejected & registered)
        roster = self.read("shared/references/model-roster.md")
        self.assertIn("zero-data-retention", roster)

    def test_local_preferences_are_preview_only(self):
        example = (REPO_ROOT.parent / ".rar-skills" / "config.local.example.yaml").read_text(
            encoding="utf-8"
        )
        reference = self.read("shared/references/local-config.md")
        implementation = self.read("implement-tasks/SKILL.md")
        council = self.read("models-consensus/SKILL.md")
        self.assertIn("seats:", example)
        self.assertNotIn("models:", example)
        self.assertIn("model-routing.json", example)
        self.assertNotIn("work_engine_preferences", example)
        self.assertNotIn("runner_base_path", example)
        self.assertNotIn("quorum:", example)
        self.assertIn("Do not read it again for dispatch", reference)
        self.assertIn("config.local.yaml", implementation)
        self.assertIn("never reread it after approval", implementation)
        self.assertIn("config.local.yaml", council)


if __name__ == "__main__":
    unittest.main(verbosity=2)
