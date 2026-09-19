#!/usr/bin/env python3
"""Offline guards for model routing and approved implementation routes."""

from __future__ import annotations

import json
import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
from skill_paths import skill_dir  # noqa: E402
import model_routing
import discover_runners

LAUNCH_PATH = REPO_ROOT / "engineering" / "engine" / "implement-and-review" / "scripts" / "launch.py"
LAUNCH_SPEC = importlib.util.spec_from_file_location("model_routing_launch", LAUNCH_PATH)
assert LAUNCH_SPEC and LAUNCH_SPEC.loader
launcher = importlib.util.module_from_spec(LAUNCH_SPEC)
LAUNCH_SPEC.loader.exec_module(launcher)


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
        self.assertEqual(config["models"]["fable"]["model"], "claude-fable-5-1")
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
        self.assertIn("native", route["properties"])
        self.assertIn("native", route["properties"]["effort_control"]["enum"])
        native = schema["definitions"]["native"]
        self.assertEqual(
            set(native["required"]),
            {"host", "transport", "capability_source", "supported_efforts"},
        )

    def test_native_route_checks_capability_and_exact_receipt(self):
        route = {
            "id": "impl-api",
            "task_id": "task1",
            "input_path": "task.md",
            "track": "api",
            "role": "implementer",
            "seat": "astra",
            "runner": "codex",
            "model": "gpt-6-astra",
            "model_verification": "required",
            "effort": "high",
            "effort_control": "native",
            "mode": "native",
            "native": {
                "host": "codex-app",
                "transport": "subagent",
                "capability_source": "checked host catalog",
                "supported_efforts": ["high", "max"],
            },
            "unavailable": {"action": "block"},
        }
        launcher.validate_route(route)
        receipt = {
            "success": True,
            "effective_runner": "codex",
            "configured_model": "gpt-6-astra",
            "effective_model": "gpt-6-astra",
            "configured_effort": "high",
            "effective_effort": "high",
            "model_receipt": {
                "status": "verified",
                "source": "native_event",
                "observed_model": "gpt-6-astra",
            },
            "native_execution": {
                "host": "codex-app",
                "transport": "subagent",
                "context_id": "impl-context",
                "role": "implementer",
                "task_id": "task1",
                "configured_model": "gpt-6-astra",
                "configured_effort": "high",
                "tool_policy": "write",
                "call_id": "impl-call",
                "input_revision": "brief-digest",
                "completed_turn": 1,
            },
        }
        self.assertIsNone(launcher.receipt_error(route, receipt))
        self.assertIsNone(
            launcher.native_execution_error(
                route,
                receipt,
                "task1",
                {"call_id": "impl-call", "input_revision": "brief-digest", "tool_policy": "write"},
            )
        )
        receipt["native_execution"]["host"] = "other-host"
        self.assertIn(
            "host or transport",
            launcher.native_execution_error(route, receipt, "task1", None),
        )

    def test_frontier_seats_are_opt_in_transport_probes(self):
        specs = {spec.seat: spec for spec in discover_runners.SEAT_SPECS}
        self.assertEqual(specs["astra"].tier, "frontier")
        self.assertEqual(specs["fable"].tier, "frontier")
        self.assertNotIn("astra", [spec.seat for spec in discover_runners.filter_specs(None)])
        self.assertEqual(discover_runners.SEAT_IDENTITIES["codex"], "astra")

    def test_codex_runner_uses_astra_and_records_clamps(self):
        spec = importlib.util.spec_from_file_location("routing_worker", P("codex-runner/scripts/run_codex.py"))
        worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worker)
        self.assertEqual(worker.DEFAULT_MODEL, model_routing.default_model("codex"))
        self.assertEqual(worker.resolve_model("codex"), worker.resolve_model("astra"))
        self.assertEqual(worker.resolve_effort(worker.resolve_model("astra"), "ultra"), "ultra")
        self.assertEqual(worker.resolve_effort(worker.resolve_model("luna"), "ultra"), "max")
        runner = self.read("codex-runner/scripts/run_codex.py")
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
        self.assertIn("shared/model-routing.json", text)
        self.assertIn("deep-analysis", text)
        self.assertNotIn("Synthesize and enrich (Opus seat)", text)

    def test_collaborative_delivery_uses_persistent_exact_routes(self):
        import tomllib
        raw = tomllib.loads(self.read("collaborative-delivery/assets/routing.toml"))
        resolved = model_routing.resolve_panel_providers(raw)
        primary = resolved["providers"]["synthesis_anchor"]
        reviewer = resolved["providers"]["adversarial_anchor"]
        self.assertNotEqual(primary["model"], reviewer["model"])
        self.assertEqual(primary["effort_control"], "native")
        self.assertEqual(reviewer["effort_control"], "runner")
        for provider in resolved["providers"].values():
            self.assertEqual(provider["session_policy"], "per-role-persistent")
        workflow = self.read("collaborative-delivery/SKILL.md")
        self.assertIn("exact model", workflow)
        self.assertIn("persistent native", workflow)

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
        self.assertIn("never reread it after approval", council)


if __name__ == "__main__":
    unittest.main(verbosity=2)
