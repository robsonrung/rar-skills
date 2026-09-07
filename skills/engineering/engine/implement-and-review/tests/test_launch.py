#!/usr/bin/env python3
"""Offline regression tests for the approved-route launcher."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


SKILL_DIR = Path(__file__).resolve().parents[1]
LAUNCH_PATH = SKILL_DIR / "scripts" / "launch.py"
SPEC = importlib.util.spec_from_file_location("implement_and_review_launch", LAUNCH_PATH)
assert SPEC and SPEC.loader
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="implement-and-review-launch-")
        self.root = Path(self.temporary.name).resolve()
        self.task = self.root / "task.md"
        self.brief = self.root / "brief.md"
        self.task.write_text(
            "# Approved task\n\nAcceptance: command succeeds\n\n**Status:** ready-for-agent\n",
            encoding="utf-8",
        )
        self.brief.write_text("Derived notes must not replace the contract.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def route(
        self,
        route_id: str,
        role: str,
        model: str,
        **overrides: object,
    ) -> dict[str, object]:
        route: dict[str, object] = {
            "id": route_id,
            "task_id": "task1",
            "input_path": "task.md",
            "track": "api",
            "role": role,
            "seat": "astra",
            "runner": "codex",
            "model": model,
            "model_verification": "required",
            "effort": "high",
            "effort_control": "runner",
            "mode": "runner",
            "unavailable": {"action": "block"},
        }
        route.update(overrides)
        return route

    def plan(self) -> tuple[Path, dict[str, object], dict[str, object]]:
        scope = {
            "inputs": [
                {
                    "path": "task.md",
                    "content_sha256": launcher.content_digest(self.task),
                }
            ]
        }
        implementer = self.route("impl-api", "implementer", "gpt-6-astra")
        reviewer = self.route("review-api", "reviewer", "claude-fable-5-1", runner="claude", seat="fable")
        routes = [implementer, reviewer]
        approval = {
            "status": "approved",
            "decided_at": "2026-09-06T00:00:00Z",
            "reference": "test approval",
            "scope_digest": launcher.canonical_digest(launcher.normalized_scope_inputs(scope["inputs"])),
            "routes_digest": launcher.canonical_digest(launcher.normalized_routes(routes)),
        }
        plan = {"schema_version": 1, "scope": scope, "approval": approval, "routes": routes}
        path = self.root / "routing-plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return path, implementer, reviewer

    def test_status_only_transition_preserves_scope_but_acceptance_change_blocks(self) -> None:
        path, _, _ = self.plan()
        launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)

        self.task.write_text(
            "# Approved task\n\nAcceptance: command succeeds\n\n**Status:** done\n",
            encoding="utf-8",
        )
        launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)

        self.task.write_text(
            "# Approved task\n\nAcceptance: a different command succeeds\n\n**Status:** done\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "changed after approval"):
            launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)

    def test_non_dry_draft_plan_rejects_before_creating_artifacts(self) -> None:
        plan_path, _, _ = self.plan()
        draft = json.loads(plan_path.read_text(encoding="utf-8"))
        draft["approval"]["status"] = "draft"
        draft_path = self.root / "draft-routing-plan.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        arguments = Namespace(
            session_id="draft",
            task_id="task1",
            routing_plan=str(draft_path),
            working_dir=str(self.root),
            track_briefs=[["api", str(self.brief)]],
            isolation="working-tree",
            timeout=1,
            base=None,
            worktrees_dir=None,
            allow_dirty=True,
            force=False,
            dry_run=False,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_launch(arguments)
        self.assertFalse((self.root / ".ai-workflow" / "impl-review" / "draft").exists())

    def test_draft_dry_run_is_an_explicit_zero_write_preview(self) -> None:
        plan_path, _, _ = self.plan()
        draft = json.loads(plan_path.read_text(encoding="utf-8"))
        draft["approval"]["status"] = "draft"
        draft_path = self.root / "draft-routing-plan.json"
        draft_path.write_text(json.dumps(draft), encoding="utf-8")
        arguments = Namespace(
            session_id="draft-preview",
            task_id="task1",
            routing_plan=str(draft_path),
            working_dir=str(self.root),
            track_briefs=[["api", str(self.brief)]],
            isolation="working-tree",
            timeout=1,
            base=None,
            worktrees_dir=None,
            allow_dirty=True,
            force=False,
            dry_run=True,
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(arguments), 0)
        preview = json.loads(output.getvalue())
        self.assertEqual(preview["status"], "unapproved_preview")
        self.assertTrue(preview["approval_preview"])
        self.assertFalse((self.root / ".ai-workflow" / "impl-review" / "draft-preview").exists())

    def test_unknown_task_and_track_reject_before_creating_artifacts(self) -> None:
        plan_path, _, _ = self.plan()
        cases = (("unknown-task", "unknown", "api"), ("unknown-track", "task1", "unknown"))
        for session_id, task_id, track in cases:
            with self.subTest(task_id=task_id, track=track):
                arguments = Namespace(
                    session_id=session_id,
                    task_id=task_id,
                    routing_plan=str(plan_path),
                    working_dir=str(self.root),
                    track_briefs=[[track, str(self.brief)]],
                    isolation="working-tree",
                    timeout=1,
                    base=None,
                    worktrees_dir=None,
                    allow_dirty=True,
                    force=False,
                    dry_run=False,
                )
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        launcher.cmd_launch(arguments)
                self.assertFalse((self.root / ".ai-workflow" / "impl-review" / session_id).exists())

    def test_non_git_sequential_native_launch_creates_a_pending_manifest(self) -> None:
        self.assertIsNone(launcher.maybe_repo_root(self.root))
        plan_path, _, _ = self.plan()
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for route in plan["routes"]:
            route["mode"] = "native"
        plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        arguments = Namespace(
            session_id="native-nogit",
            task_id="task1",
            routing_plan=str(plan_path),
            working_dir=str(self.root),
            track_briefs=[["api", str(self.brief)]],
            isolation="working-tree",
            timeout=1,
            base=None,
            worktrees_dir=None,
            allow_dirty=False,
            force=False,
            dry_run=False,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(arguments), 0)
        manifest_path = self.root / ".ai-workflow" / "impl-review" / "native-nogit" / "task1" / "launch-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        implementation = manifest["tracks"]["api"]["implementation"]
        self.assertIsNone(manifest["repo_root"])
        self.assertEqual(manifest["isolation"], "working-tree")
        self.assertEqual(implementation["mode"], "native")
        self.assertEqual(implementation["status"], "orchestrator-managed")
        self.assertIn("pending", implementation)
        self.assertNotIn("job_id", implementation)

    def test_bound_brief_keeps_the_approved_contract(self) -> None:
        path, _, _ = self.plan()
        routing = launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)
        contract = routing["scope_inputs"]["task.md"]
        rendered, binding = launcher.render_bound_brief(
            contract,
            self.brief,
            launcher.WRITE_BOUNDARY,
            "Derived implementation notes",
        )

        self.assertIn("# Approved task", rendered)
        self.assertIn("Acceptance: command succeeds", rendered)
        self.assertIn("Derived notes must not replace the contract.", rendered)
        self.assertIn("If it conflicts with the contract, stop", rendered)
        self.assertEqual(binding["contract_path"], str(self.task))
        self.assertEqual(binding["contract_content_sha256"], launcher.content_digest(self.task))

    def test_review_requires_a_completed_successful_implementation_receipt(self) -> None:
        track = {"implementation": {"mode": "runner", "job_id": "codex-12345678"}}
        with mock.patch.object(launcher, "job_snapshot", return_value=({}, False)):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    launcher.implementation_ready(track, self.root)
        with mock.patch.object(
            launcher,
            "job_snapshot",
            return_value=({"success": False, "error": "missing receipt"}, True),
        ):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    launcher.implementation_ready(track, self.root)

    def test_died_cancelled_and_malformed_jobs_are_terminal_failures(self) -> None:
        entry = {"mode": "runner", "job_id": "codex-12345678", "effective_route": self.route("impl", "implementer", "gpt-6-astra")}
        for status in ("died", "cancelled"):
            with self.subTest(status=status), mock.patch.object(
                launcher, "jobs_query", return_value={"status": status}
            ):
                snapshot, terminal = launcher.job_snapshot(entry, str(self.root))
                self.assertTrue(terminal)
                self.assertFalse(snapshot["success"])

        with mock.patch.object(launcher, "jobs_query", side_effect=[{"status": "completed"}, {}]):
            snapshot, terminal = launcher.job_snapshot(entry, str(self.root))
        self.assertTrue(terminal)
        self.assertFalse(snapshot["success"])
        self.assertEqual(snapshot["error"], "completed runner job has no successful result")

    def test_failed_dispatch_is_persisted_in_the_manifest(self) -> None:
        plan_path, _, _ = self.plan()
        arguments = Namespace(
            session_id="s1",
            task_id="task1",
            routing_plan=str(plan_path),
            working_dir=str(self.root),
            track_briefs=[["api", str(self.brief)]],
            isolation="working-tree",
            timeout=1,
            base=None,
            worktrees_dir=None,
            allow_dirty=True,
            force=False,
            dry_run=False,
        )
        with mock.patch.object(
            launcher,
            "dispatch_route",
            side_effect=launcher.RunnerLaunchError("simulated start failure"),
        ):
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    launcher.cmd_launch(arguments)

        manifest_path = self.root / ".ai-workflow" / "impl-review" / "s1" / "task1" / "launch-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        implementation = manifest["tracks"]["api"]["implementation"]
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(implementation["status"], "failed")
        self.assertIn("simulated start failure", implementation["error"])

    def test_cleanup_rejects_foreign_paths_and_dry_run_does_not_claim_removal(self) -> None:
        foreign_manifest = {
            "working_root": str(self.root),
            "session_id": "s1",
            "task_id": "task1",
            "isolation": "worktree",
            "worktrees_dir": str(self.root / "worktrees"),
        }
        foreign_track = {
            "branch": "impl/task1-api-s1",
            "working_dir": str(self.root / "other"),
        }
        with self.assertRaisesRegex(ValueError, "launcher-owned worktree"):
            launcher.track_working_dir(foreign_manifest, "api", foreign_track)

        worktrees_dir = self.root / "worktrees"
        working_dir = worktrees_dir / "api"
        branch = "impl/task1-api-s1"
        manifest = {
            "working_root": str(self.root),
            "repo_root": str(self.root),
            "session_id": "s1",
            "task_id": "task1",
            "isolation": "worktree",
            "worktrees_dir": str(worktrees_dir),
            "tracks": {
                "api": {
                    "branch": branch,
                    "working_dir": str(working_dir),
                    "worktree": {"status": "created", "path": str(working_dir), "branch": branch},
                }
            },
        }
        arguments = Namespace(
            dry_run=True,
            force=False,
            delete_branches=False,
            working_dir=str(self.root),
        )
        git_result = subprocess.CompletedProcess(["git"], 0, stdout=f"{branch}\n", stderr="")
        output = io.StringIO()
        with mock.patch.object(launcher, "load_manifest", return_value=(manifest, self.root / "launch-manifest.json")), \
             mock.patch.object(launcher, "maybe_repo_root", return_value=self.root), \
             mock.patch.object(launcher, "worktree_exists", return_value=True), \
             mock.patch.object(launcher, "git", return_value=git_result), \
             contextlib.redirect_stdout(output), \
             contextlib.redirect_stderr(io.StringIO()):
            return_code = launcher.cmd_cleanup(arguments)
        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["removed_worktrees"], [])
        self.assertEqual(payload["planned_worktrees"], [str(working_dir)])

    def test_rejects_effort_not_supported_by_the_selected_runner(self) -> None:
        route = self.route(
            "impl-fable",
            "implementer",
            "claude-fable-5-1",
            runner="claude",
            seat="fable",
            effort="ultra",
        )
        with self.assertRaisesRegex(ValueError, "not supported"):
            launcher.validate_route(route)

    def test_rejects_dcode_before_any_dispatch(self) -> None:
        route = self.route(
            "impl-dcode",
            "implementer",
            "configured-by-dcode",
            runner="dcode",
            effort=None,
            effort_control="runtime",
            model_verification="allow_unverified",
        )
        with self.assertRaisesRegex(ValueError, "not supported by this launcher"):
            launcher.validate_route(route)

    def test_receipt_policy_requires_verified_or_explicitly_allows_unverified(self) -> None:
        required_route = self.route("impl", "implementer", "gpt-6-astra")
        verified = {
            "success": True,
            "effective_runner": "codex",
            "configured_model": "gpt-6-astra",
            "effective_model": "gpt-6-astra",
            "requested_effort": "high",
            "effort_clamped": False,
            "model_receipt": {
                "status": "verified",
                "source": "native_event",
                "observed_model": "gpt-6-astra",
            },
        }
        self.assertIsNone(launcher.receipt_error(required_route, verified))

        unverified_route = dict(required_route, model_verification="allow_unverified")
        unverified = {
            "success": True,
            "effective_runner": "codex",
            "configured_model": "gpt-6-astra",
            "effective_model": None,
            "requested_effort": "high",
            "effort_clamped": False,
            "model_receipt": {
                "status": "unverified",
                "source": "configured_model",
                "observed_model": None,
            },
        }
        self.assertIsNotNone(launcher.receipt_error(required_route, unverified))
        self.assertIsNone(launcher.receipt_error(unverified_route, unverified))


if __name__ == "__main__":
    unittest.main(verbosity=2)
