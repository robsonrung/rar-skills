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

    def test_claude_dispatch_requests_structured_output_and_provenance(self):
        route = self.route("review-api", "reviewer", "claude-fable-5-1", runner="claude", seat="fable")
        args = launcher.route_arguments(route, self.brief, self.root, "reviewer", 60, {"call_id": "call-1"}, True)
        self.assertEqual(args[args.index("--output-format") + 1], "stream-json")
        metadata = json.loads(args[args.index("--metadata-json") + 1])
        self.assertEqual(metadata["call_id"], "call-1")
        self.assertTrue(metadata["execution_provenance"]["resources"])

    def test_source_sharing_is_optional_but_requires_a_complete_scope(self):
        route = self.route("review-api", "reviewer", "claude-fable-5-1", runner="claude", seat="fable")
        launcher.validate_route(route)
        route["source_sharing"] = {"provider": "Anthropic", "scope": "T1 source and tests", "follow_ups": "T1 repairs",
                                   "exclusions": "credentials", "reference": "user approval"}
        launcher.validate_route(route)
        del route["source_sharing"]["reference"]
        with self.assertRaisesRegex(ValueError, "approval reference"):
            launcher.validate_route(route)

    def test_launcher_rejects_stale_context_packet(self):
        import context_packet
        packet = self.brief.with_suffix(self.brief.suffix + ".packet.json")
        context_packet.prepare(self.brief, [{"path": str(self.task), "authority": "decision", "locator": "Acceptance"}], packet)
        self.task.write_text("Changed acceptance")
        with self.assertRaisesRegex(ValueError, "decision source changed"):
            launcher.render_bound_brief({"path": self.task, "content_sha256": launcher.content_digest(self.task)}, self.brief, launcher.WRITE_BOUNDARY, "Notes")

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

    def native_plan(self) -> Path:
        path, _, _ = self.plan()
        plan = json.loads(path.read_text(encoding="utf-8"))
        implementer = next(route for route in plan["routes"] if route["role"] == "implementer")
        implementer.update({
            "mode": "native",
            "effort_control": "native",
            "native": {
                "host": "codex-app",
                "transport": "subagent",
                "capability_source": "test host capability",
                "supported_efforts": ["high", "max"],
            },
        })
        plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
        path.write_text(json.dumps(plan), encoding="utf-8")
        return path

    def launch_arguments(self, plan_path: Path, session_id: str) -> Namespace:
        return Namespace(
            session_id=session_id,
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

    def manifest_for(self, session_id: str) -> Path:
        return self.root / ".ai-workflow" / "impl-review" / session_id / "task1" / "launch-manifest.json"

    def native_receipt(self, dispatch: dict[str, object], *, context_id: str, completed_turn: int, host: str = "codex-app") -> dict[str, object]:
        return {
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
                "host": host,
                "transport": "subagent",
                "context_id": context_id,
                "parent_history": dispatch.get("parent_history", "none"),
                "role": "implementer",
                "task_id": "task1",
                "configured_model": "gpt-6-astra",
                "configured_effort": "high",
                "tool_policy": "write",
                "call_id": dispatch["call_id"],
                "input_revision": dispatch["input_revision"],
                "completed_turn": completed_turn,
            },
        }

    def record_native_arguments(self, manifest_path: Path, receipt_path: Path) -> Namespace:
        return Namespace(
            manifest=str(manifest_path),
            session_id=None,
            task_id=None,
            working_dir=None,
            track="api",
            phase="implementation",
            cycle=None,
            receipt=str(receipt_path),
            context_recovery_reason=None,
        )

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
        self.assertEqual(implementation["status"], "awaiting_native_dispatch")
        self.assertIn("pending", implementation)
        self.assertEqual(implementation["native_dispatch"]["context_action"], "start")
        self.assertNotIn("job_id", implementation)

    def test_pi_first_turn_uses_a_stable_session_path_without_writing_it(self) -> None:
        route = self.route(
            "pi-review",
            "reviewer",
            "openai/gpt-5.6-terra",
            runner="pi",
            seat="pi",
        )
        first = launcher.route_arguments(route, self.brief, self.root, "codereviewer", 1, {}, True)
        second = launcher.route_arguments(route, self.brief, self.root, "codereviewer", 1, {}, True)
        session_index = first.index("--session") + 1
        session_id = first[session_index]
        self.assertEqual(second[second.index("--session") + 1], session_id)
        self.assertEqual(Path(session_id).parent, self.brief.parent)
        self.assertFalse(Path(session_id).exists())

        other_route = {**route, "id": "pi-review-other"}
        other = launcher.route_arguments(other_route, self.brief, self.root, "codereviewer", 1, {}, True)
        self.assertNotEqual(other[other.index("--session") + 1], session_id)

        resumed = launcher.route_arguments(
            route,
            self.brief,
            self.root,
            "codereviewer",
            1,
            {},
            True,
            resume_context_id="known-pi-session",
        )
        self.assertEqual(resumed[resumed.index("--session") + 1], "known-pi-session")

    def test_native_receipt_binds_a_context_and_resume_reuses_it(self) -> None:
        plan_path = self.native_plan()
        arguments = self.launch_arguments(plan_path, "native-resume")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(arguments), 0)
        manifest_path = self.manifest_for("native-resume")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dispatch = manifest["tracks"]["api"]["implementation"]["native_dispatch"]
        receipt_path = self.root / "native-receipt-1.json"
        receipt_path.write_text(json.dumps(self.native_receipt(dispatch, context_id="impl-context", completed_turn=1)), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_record_native(self.record_native_arguments(manifest_path, receipt_path)), 0)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        context = manifest["native_contexts"]["impl-api"]
        self.assertEqual(context["context_id"], "impl-context")
        self.assertEqual(context["last_completed_turn"], 1)
        self.assertTrue(Path(context["receipt_ref"]).is_file())

        follow_up = self.root / "follow-up.md"
        follow_up.write_text("Apply the accepted review finding.\n", encoding="utf-8")
        resume = Namespace(
            manifest=str(manifest_path),
            session_id=None,
            task_id=None,
            working_dir=None,
            track="api",
            follow_up=str(follow_up),
            timeout=1,
            context_recovery_reason=None,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_resume_native(resume), 0)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        implementation = manifest["tracks"]["api"]["implementation"]
        resumed = implementation["native_dispatch"]
        self.assertEqual(resumed["context_action"], "resume")
        self.assertEqual(resumed["context_id"], "impl-context")
        self.assertEqual(manifest["native_contexts"]["impl-api"]["pending_call_id"], resumed["call_id"])

        receipt_path.write_text(json.dumps(self.native_receipt(resumed, context_id="impl-context", completed_turn=2)), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_record_native(self.record_native_arguments(manifest_path, receipt_path)), 0)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["native_contexts"]["impl-api"]["last_completed_turn"], 2)

    def test_native_receipts_preserve_recovery_evidence_and_failures_do_not_bind_context(self) -> None:
        route = self.route(
            "impl-api",
            "implementer",
            "gpt-6-astra",
            mode="native",
            effort_control="native",
            native={
                "host": "codex-app",
                "transport": "subagent",
                "capability_source": "test host capability",
                "supported_efforts": ["high", "max"],
            },
        )
        manifest = {
            "artifact_dir": str(self.root / "artifacts"),
            "task_id": "task1",
            "native_contexts": {},
        }
        first = self.native_receipt(
            {"call_id": "recovery-call-one", "input_revision": "revision-one"},
            context_id="lost-context-one",
            completed_turn=1,
        )
        second = self.native_receipt(
            {"call_id": "recovery-call-two", "input_revision": "revision-two"},
            context_id="recovered-context-two",
            completed_turn=1,
        )
        first_path = launcher.native_receipt_path(manifest, route, "implementation", None, first)
        second_path = launcher.native_receipt_path(manifest, route, "implementation", None, second)
        self.assertNotEqual(first_path, second_path)
        launcher.write_native_receipt(first_path, first)
        launcher.write_native_receipt(second_path, second)
        self.assertEqual(json.loads(first_path.read_text(encoding="utf-8"))["native_execution"]["context_id"], "lost-context-one")
        self.assertEqual(json.loads(second_path.read_text(encoding="utf-8"))["native_execution"]["context_id"], "recovered-context-two")
        with self.assertRaisesRegex(ValueError, "already exists"):
            launcher.write_native_receipt(first_path, {**first, "error": "changed receipt"})

        failed = {
            **first,
            "success": False,
            "native_execution": {
                **first["native_execution"],
                "context_id": "unverified-failure-context",
            },
        }
        persisted = launcher.persist_native_receipt(manifest, route, "implementation", None, failed, None)
        self.assertIsNone(persisted["context"])
        self.assertEqual(manifest["native_contexts"], {})

    def test_native_receipt_with_wrong_host_is_rejected_without_artifact(self) -> None:
        plan_path = self.native_plan()
        arguments = self.launch_arguments(plan_path, "native-host-mismatch")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(arguments), 0)
        manifest_path = self.manifest_for("native-host-mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dispatch = manifest["tracks"]["api"]["implementation"]["native_dispatch"]
        receipt_path = self.root / "native-host-mismatch.json"
        receipt_path.write_text(
            json.dumps(self.native_receipt(dispatch, context_id="impl-context", completed_turn=1, host="other-host")),
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_record_native(self.record_native_arguments(manifest_path, receipt_path))
        native_artifacts = manifest_path.parent / "native-receipts"
        self.assertFalse(native_artifacts.exists())

    def test_native_context_cannot_be_reused_by_a_different_role(self) -> None:
        implementer = self.route(
            "impl-api",
            "implementer",
            "gpt-6-astra",
            mode="native",
            effort_control="native",
            native={
                "host": "codex-app",
                "transport": "subagent",
                "capability_source": "test host capability",
                "supported_efforts": ["high"],
            },
        )
        reviewer = self.route(
            "review-api",
            "reviewer",
            "gpt-5.6-terra",
            mode="native",
            effort="medium",
            effort_control="native",
            native={
                "host": "codex-app",
                "transport": "subagent",
                "capability_source": "test host capability",
                "supported_efforts": ["medium"],
            },
        )
        manifest = {
            "artifact_dir": str(self.root / "artifacts"),
            "task_id": "task1",
            "native_contexts": {},
        }
        implementation_receipt = self.native_receipt(
            {"call_id": "impl-call", "input_revision": "revision-1"},
            context_id="shared-context",
            completed_turn=1,
        )
        launcher.persist_native_receipt(manifest, implementer, "implementation", None, implementation_receipt, None)
        review_receipt = {
            **implementation_receipt,
            "configured_model": "gpt-5.6-terra",
            "effective_model": "gpt-5.6-terra",
            "configured_effort": "medium",
            "effective_effort": "medium",
            "model_receipt": {
                "status": "verified",
                "source": "native_event",
                "observed_model": "gpt-5.6-terra",
            },
            "native_execution": {
                **implementation_receipt["native_execution"],
                "role": "reviewer",
                "configured_model": "gpt-5.6-terra",
                "configured_effort": "medium",
                "tool_policy": "read-only",
                "call_id": "review-call",
                "input_revision": "revision-2",
            },
        }
        with self.assertRaisesRegex(ValueError, "already owned"):
            launcher.persist_native_receipt(manifest, reviewer, "review", 1, review_receipt, None)

    def test_native_resume_has_a_follow_up_ceiling(self) -> None:
        plan_path = self.native_plan()
        arguments = self.launch_arguments(plan_path, "native-ceiling")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(arguments), 0)
        manifest_path = self.manifest_for("native-ceiling")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        dispatch = manifest["tracks"]["api"]["implementation"]["native_dispatch"]
        receipt_path = self.root / "native-ceiling-receipt.json"
        receipt_path.write_text(json.dumps(self.native_receipt(dispatch, context_id="impl-context", completed_turn=1)), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launcher.cmd_record_native(self.record_native_arguments(manifest_path, receipt_path)), 0)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tracks"]["api"]["implementation"]["resume_attempts"] = (
            launcher.MAX_REVIEW_CYCLES + launcher.MAX_EVIDENCE_RECOVERIES
        )
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        follow_up = self.root / "ceiling-follow-up.md"
        follow_up.write_text("Attempt another fix.\n", encoding="utf-8")
        resume = Namespace(
            manifest=str(manifest_path),
            session_id=None,
            task_id=None,
            working_dir=None,
            track="api",
            follow_up=str(follow_up),
            timeout=1,
            context_recovery_reason=None,
        )
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_resume_native(resume)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "ceiling_hit")

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

    def test_runner_context_keeps_two_review_turns_stable_across_polls(self) -> None:
        reviewer = self.route("review-api", "reviewer", "claude-opus-5", runner="claude", seat="opus", effort="xhigh")
        manifest = {
            "task_id": "task1",
            "tracks": {},
            "reviews": [
                {
                    "track": "api",
                    "cycle": 1,
                    "launch": {
                        "selected_route": reviewer,
                        "effective_route": reviewer,
                        "job_id": "claude-11111111",
                        "result_file": "review-1.json",
                        "input_revision": "revision-1",
                        "tool_policy": "read-only",
                    },
                },
                {
                    "track": "api",
                    "cycle": 2,
                    "launch": {
                        "selected_route": reviewer,
                        "effective_route": reviewer,
                        "job_id": "claude-22222222",
                        "result_file": "review-2.json",
                        "resume_context_id": "review-session",
                        "input_revision": "revision-2",
                        "tool_policy": "read-only",
                    },
                },
            ],
            "runner_contexts": {},
        }
        snapshot = {
            "tracks": {},
            "reviews": {
                "api:1": {"success": True, "runner_session_id": "review-session"},
                "api:2": {"success": True, "runner_session_id": "review-session"},
            },
        }
        self.assertTrue(launcher.persist_terminal_runner_contexts(manifest, snapshot))
        context = manifest["runner_contexts"]["review-api"]
        self.assertEqual(context["last_completed_turn"], 2)
        self.assertEqual(context["processed_receipt_refs"], ["review-1.json", "review-2.json"])
        stable = json.dumps(context, sort_keys=True)
        self.assertFalse(launcher.persist_terminal_runner_contexts(manifest, snapshot))
        self.assertEqual(json.dumps(manifest["runner_contexts"]["review-api"], sort_keys=True), stable)

    def test_resumed_runner_route_does_not_start_an_approved_fallback(self) -> None:
        route = self.route(
            "review-api",
            "reviewer",
            "gpt-6-astra",
            unavailable={
                "action": "use",
                "seat": "opus",
                "runner": "claude",
                "model": "claude-opus-5",
                "model_verification": "required",
                "effort": "xhigh",
                "effort_control": "runner",
                "mode": "runner",
            },
        )
        with mock.patch.object(launcher, "fire_runner", side_effect=launcher.RunnerLaunchError("resume unavailable")) as fire:
            with self.assertRaisesRegex(launcher.RunnerLaunchError, "resume unavailable"):
                launcher.dispatch_route(
                    route,
                    self.brief,
                    self.root,
                    "codereviewer",
                    1,
                    {},
                    True,
                    False,
                    resume_context={"context_id": "existing-review-session"},
                )
        fire.assert_called_once()

    def test_completed_fallback_route_stays_with_its_persistent_session(self) -> None:
        approved_route = self.route(
            "review-api",
            "reviewer",
            "gpt-6-astra",
            unavailable={
                "action": "use",
                "seat": "opus",
                "runner": "claude",
                "model": "claude-opus-5",
                "model_verification": "required",
                "effort": "xhigh",
                "effort_control": "runner",
                "mode": "runner",
            },
        )
        fallback = launcher.fallback_route(approved_route)
        assert fallback is not None
        manifest = {
            "task_id": "task1",
            "runner_contexts": {
                "review-api": {
                    "runner": "claude",
                    "context_id": "fallback-review-session",
                    "role": "reviewer",
                    "task_id": "task1",
                    "configured_model": "claude-opus-5",
                    "configured_effort": "xhigh",
                    "status": "completed",
                }
            },
        }
        route = launcher.persistent_effective_route(manifest, approved_route)
        self.assertEqual(launcher.canonical_digest(route), launcher.canonical_digest(fallback))
        context = launcher.resumable_context(manifest, route)
        self.assertIsNotNone(context)
        with mock.patch.object(
            launcher,
            "fire_runner",
            return_value={"job_id": "claude-12345678", "job_dir": None, "result_file": "review.json"},
        ) as fire:
            launch = launcher.dispatch_route(
                route,
                self.brief,
                self.root,
                "codereviewer",
                1,
                {},
                True,
                False,
                resume_context=context,
            )
        self.assertEqual(launch["effective_route"], fallback)
        arguments = fire.call_args.args[1]
        self.assertEqual(arguments[arguments.index("--resume") + 1], "fallback-review-session")

    def test_resumed_runner_context_is_reserved_and_restored_after_launch_failure(self) -> None:
        plan_path, _, reviewer = self.plan()
        routing = launcher.load_routing_plan(str(plan_path), "task1", {"api"}, True, self.root)
        artifact_dir = self.root / "artifacts"
        artifact_dir.mkdir()
        context = {
            "runner": "claude",
            "context_id": "review-session",
            "role": "reviewer",
            "task_id": "task1",
            "configured_model": "claude-fable-5-1",
            "configured_effort": "high",
            "status": "completed",
        }
        manifest = {
            "session_id": "review-reservation",
            "task_id": "task1",
            "working_root": str(self.root),
            "artifact_dir": str(artifact_dir),
            "isolation": "working-tree",
            "routing_plan": {"path": str(plan_path), "approval": routing["approval"]},
            "attempts": {"review_cycles": {}, "evidence_recoveries": {}},
            "tracks": {
                "api": {
                    "reviewer_route": reviewer,
                    "working_dir": str(self.root),
                    "branch": None,
                }
            },
            "reviews": [],
            "runner_contexts": {"review-api": context},
        }
        observed: dict[str, object] = {}

        def reject_after_reservation(*_args: object, **kwargs: object) -> dict[str, object]:
            resumed = kwargs["resume_context"]
            assert isinstance(resumed, dict)
            observed["status"] = resumed["status"]
            raise launcher.RunnerLaunchError("simulated resume launch failure")

        arguments = Namespace(
            manifest=str(self.root / "launch-manifest.json"),
            session_id=None,
            task_id=None,
            working_dir=None,
            track="api",
            review_brief=str(self.brief),
            cycle=None,
            timeout=1,
            dry_run=False,
        )
        with mock.patch.object(launcher, "load_manifest", return_value=(manifest, self.root / "launch-manifest.json")), \
             mock.patch.object(launcher, "implementation_ready"), \
             mock.patch.object(launcher, "review_source_binding", return_value={"path": "snapshot.json", "sha256": "fixture"}), \
             mock.patch.object(launcher.evidence_module(), "response_contract", return_value={}), \
             mock.patch.object(launcher, "dispatch_route", side_effect=reject_after_reservation), \
             mock.patch.object(launcher, "save_manifest"), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_review(arguments)
        self.assertEqual(observed["status"], "pending")
        self.assertEqual(context["status"], "completed")
        self.assertNotIn("pending_call_id", context)
        self.assertIs(launcher.resumable_context(manifest, reviewer), context)

    def test_execution_success_requires_structured_current_review_evidence(self) -> None:
        plan_path, _, reviewer = self.plan()
        for arguments in (["init", "-q"], ["config", "user.email", "test@example.test"], ["config", "user.name", "Test"], ["add", "."], ["commit", "-qm", "Initial fixture"]):
            subprocess.run(["git", "-C", str(self.root), *arguments], check=True, capture_output=True)
        base = subprocess.check_output(["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()
        (self.root / "source.txt").write_text("new behavior")
        manifest_path = self.manifest_for("evidence")
        artifact_dir = manifest_path.parent
        artifact_dir.mkdir(parents=True)
        requirements = artifact_dir / "requirements.json"
        requirements.write_text(json.dumps({"context": {"runtime": "fixture"}, "checks": [], "observations": [], "exclusions": {}}))
        evidence = launcher.evidence_module()
        snapshot_path = evidence.prepare(self.root, base, self.task, requirements, artifact_dir / "cycle-1", artifact_dir)
        binding = launcher.review_source_binding(str(snapshot_path), self.root, {"path": self.task}, base)
        response = {
            "snapshot_sha256": evidence.file_hash(snapshot_path),
            "coverage": [{"path": "source.txt", "outcome": "reviewed", "reason": "Read the changed behavior."}],
            "findings": [], "checks": {}, "observations": [], "summary": "No defect found.",
        }
        execution = {
            "success": True, "effective_runner": reviewer["runner"],
            "configured_model": reviewer["model"], "effective_model": reviewer["model"],
            "effective_effort": reviewer["effort"],
            "model_receipt": {"status": "verified", "source": "provider_event", "observed_model": reviewer["model"]},
            "agent_message": json.dumps(response),
        }
        routing = launcher.load_routing_plan(str(plan_path), "task1", {"api"}, True, self.root)
        manifest = launcher.initial_manifest(self.launch_arguments(plan_path, "evidence"), self.root, self.root, base, artifact_dir, None, routing)
        manifest["tracks"]["api"] = {"working_dir": str(self.root)}
        manifest["reviews"] = [{"track": "api", "cycle": 1, "working_dir": str(self.root), "source_snapshot": binding, "reviewer_route": reviewer, "launch": {"mode": "runner", "job_id": "fixture-job", "selected_route": reviewer, "effective_route": reviewer}}]
        launcher.save_manifest(manifest, manifest_path)
        arguments = Namespace(manifest=str(manifest_path), working_dir=None, session_id=None, task_id=None, track="api", cycle=1, base=base)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.cmd_verify_review(arguments), 2)
        def query(action, *_args):
            return {"status": "completed"} if action == "status" else execution
        with mock.patch.object(launcher, "jobs_query", side_effect=query), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.cmd_record_review(arguments), 0)
            self.assertEqual(launcher.cmd_verify_review(arguments), 0)
            (self.root / "source.txt").write_text("later change")
            self.assertEqual(launcher.cmd_verify_review(arguments), 2)

    def test_missing_review_snapshot_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            launcher.review_source_binding(None, self.root, {"path": self.task}, "HEAD")

    def test_active_same_track_review_blocks_another_cycle_before_poll(self) -> None:
        plan_path, _, reviewer = self.plan()
        routing = launcher.load_routing_plan(str(plan_path), "task1", {"api"}, True, self.root)
        cases = (
            ("runner-starting", "starting", "starting", "not-started"),
            ("runner-running", "running", "running", "running"),
            ("native-pending", "running", "awaiting_native_dispatch", "orchestrator-managed"),
        )
        arguments = Namespace(
            manifest=str(self.root / "launch-manifest.json"),
            session_id=None,
            task_id=None,
            working_dir=None,
            track="api",
            review_brief=str(self.brief),
            cycle=None,
            timeout=1,
            dry_run=False,
        )
        for label, record_status, launch_status, observed_status in cases:
            with self.subTest(label=label):
                manifest = {
                    "session_id": "review-active",
                    "task_id": "task1",
                    "working_root": str(self.root),
                    "artifact_dir": str(self.root / "artifacts"),
                    "isolation": "working-tree",
                    "routing_plan": {"path": str(plan_path), "approval": routing["approval"]},
                    "attempts": {"review_cycles": {}, "evidence_recoveries": {}},
                    "tracks": {
                        "api": {
                            "reviewer_route": reviewer,
                            "working_dir": str(self.root),
                            "branch": None,
                        }
                    },
                    "reviews": [
                        {
                            "track": "api",
                            "cycle": 1,
                            "status": record_status,
                            "launch": {
                                "status": launch_status,
                                "selected_route": reviewer,
                                "effective_route": reviewer,
                            },
                        }
                    ],
                    "runner_contexts": {},
                    "native_contexts": {},
                }
                snapshot = {"tracks": {}, "reviews": {"api:1": {"status": observed_status}}}
                with mock.patch.object(launcher, "load_manifest", return_value=(manifest, self.root / "launch-manifest.json")), \
                     mock.patch.object(launcher, "implementation_ready"), \
                     mock.patch.object(launcher, "poll_once", return_value=snapshot), \
                     mock.patch.object(launcher, "dispatch_route") as dispatch, \
                     contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        launcher.cmd_review(arguments)
                dispatch.assert_not_called()
                self.assertEqual(manifest["attempts"]["review_cycles"], {})

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

    def test_approved_recovery_limits_are_enforced_and_cannot_drift(self):
        path, _, _ = self.plan()
        plan = json.loads(path.read_text())
        reviewer = next(route for route in plan["routes"] if route["role"] == "reviewer")
        reviewer["recovery"] = {"review_cycles": 4, "evidence_recoveries": 2}
        plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
        path.write_text(json.dumps(plan))
        manifest = {"working_root": str(self.root), "task_id": "task1", "routing_plan": {"path": str(path), "approval": plan["approval"]}}
        self.assertEqual(launcher.recovery_limits(manifest, "api"), reviewer["recovery"])
        with mock.patch.object(launcher, "save_manifest"), contextlib.redirect_stderr(io.StringIO()):
            for cycle in range(1, 5):
                self.assertEqual(launcher.next_review_cycle(manifest, "api", None, False, path), cycle)
            with self.assertRaises(SystemExit):
                launcher.next_review_cycle(manifest, "api", None, False, path)
        self.assertEqual(manifest["attempts"]["review_cycles"]["api"], 4)
        reviewer["recovery"]["review_cycles"] = 5
        path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            launcher.recovery_limits(manifest, "api")
        for recovery in ({"review_cycles": 0, "evidence_recoveries": 1}, {"review_cycles": True, "evidence_recoveries": 1}, {"review_cycles": 3}):
            reviewer["recovery"] = recovery
            with self.assertRaises(ValueError):
                launcher.validate_route(reviewer)

    def test_invalid_evidence_packet_does_not_consume_or_dispatch_review(self):
        plan_path, _, reviewer = self.plan()
        routing = launcher.load_routing_plan(str(plan_path), "task1", {"api"}, True, self.root)
        manifest = {"working_root": str(self.root), "task_id": "task1", "isolation": "working-tree",
            "routing_plan": {"path": str(plan_path), "approval": routing["approval"]},
            "attempts": {"review_cycles": {}}, "tracks": {"api": {"reviewer_route": reviewer, "working_dir": str(self.root), "branch": None}}}
        arguments = Namespace(track="api", review_brief=str(self.brief), dry_run=False, evidence_packet=str(self.root / "missing-packet.json"))
        with mock.patch.object(launcher, "load_manifest", return_value=(manifest, self.root / "manifest.json")), \
             mock.patch.object(launcher, "implementation_ready"), \
             mock.patch.object(launcher, "poll_once", return_value={"tracks": {}, "reviews": {}}), \
             mock.patch.object(launcher, "review_source_binding", return_value={"path": "snapshot.json", "sha256": "fixture"}), \
             mock.patch.object(launcher.evidence_module(), "response_contract", return_value={}), \
             mock.patch.object(launcher, "dispatch_route") as dispatch, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_review(arguments)
        dispatch.assert_not_called()
        self.assertEqual(manifest["attempts"]["review_cycles"], {})

    def update_route_plan(self, path, *, max_bytes=None):
        plan = json.loads(path.read_text())
        plan["scope"]["inputs"][0]["content_sha256"] = launcher.content_digest(self.task)
        if max_bytes is not None:
            for route in plan["routes"]:
                route["context_budget"] = {"max_bytes": max_bytes, "reason": "Full acceptance contract is required"}
        plan["approval"]["scope_digest"] = launcher.canonical_digest(launcher.normalized_scope_inputs(plan["scope"]["inputs"]))
        plan["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(plan["routes"]))
        path.write_text(json.dumps(plan))

    def test_complete_contract_overflow_blocks_before_artifacts_or_dispatch(self):
        path = self.native_plan()
        self.task.write_text("Required acceptance case\n" * 1100)
        self.update_route_plan(path)
        args = self.launch_arguments(path, "large-contract")
        for dry_run in (False, True):
            args.dry_run = dry_run
            with mock.patch.object(launcher, "dispatch_route") as dispatch, \
                 mock.patch.object(launcher, "create_worktree") as worktree, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    launcher.cmd_launch(args)
            dispatch.assert_not_called()
            worktree.assert_not_called()
            self.assertFalse((self.root / ".ai-workflow").exists())

    def test_larger_approved_budget_records_exact_final_input_and_new_context(self):
        path = self.native_plan()
        self.task.write_text("Required acceptance case\n" * 1100)
        self.update_route_plan(path, max_bytes=40000)
        args = self.launch_arguments(path, "allowed-contract")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.cmd_launch(args), 0)
        manifest = json.loads(self.manifest_for("allowed-contract").read_text())
        track = manifest["tracks"]["api"]
        prompt = Path(track["brief"]).read_bytes()
        measurement = track["brief_binding"]["input_measurement"]
        self.assertEqual(measurement["utf8_bytes"], len(prompt))
        self.assertEqual(measurement["sha256"], launcher.file_digest(Path(track["brief"])))
        self.assertIn(self.task.read_text().strip(), prompt.decode())
        dispatch = track["implementation"]["native_dispatch"]
        self.assertEqual(dispatch["input_measurement"], measurement)
        self.assertEqual(dispatch["parent_history"], "none")
        self.assertEqual(dispatch["context_action"], "start")
        self.assertIsNone(dispatch["context_id"])
        receipt = self.native_receipt(dispatch, context_id="isolated-role", completed_turn=1)
        del receipt["native_execution"]["parent_history"]
        self.assertIn("parent_history", launcher.native_execution_error(track["implementer_route"], receipt, "task1", dispatch))
        self.update_route_plan(path, max_bytes=50000)
        # Re-signing the route digest changes approval; an old manifest cannot silently adopt it.
        self.assertNotEqual(json.loads(path.read_text())["approval"], manifest["routing_plan"]["approval"])

    def test_budget_edit_without_approval_is_rejected(self):
        path, _, _ = self.plan()
        plan = json.loads(path.read_text())
        plan["routes"][0]["context_budget"] = {"max_bytes": 30000, "reason": "More task context"}
        path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError):
            launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)

    def test_appended_review_requirements_count_before_cycle_reservation(self):
        path, _, reviewer = self.plan()
        routing = launcher.load_routing_plan(str(path), "task1", {"api"}, True, self.root)
        manifest = {"working_root": str(self.root), "task_id": "task1", "isolation": "working-tree",
            "routing_plan": {"path": str(path), "approval": routing["approval"]},
            "attempts": {"review_cycles": {}}, "tracks": {"api": {"reviewer_route": reviewer, "working_dir": str(self.root), "branch": None}}}
        args = Namespace(track="api", review_brief=str(self.brief), dry_run=False)
        large_requirements = {"coverage_paths": ["changed/file.txt"] * 2000}
        with mock.patch.object(launcher, "load_manifest", return_value=(manifest, self.root / "manifest.json")), \
             mock.patch.object(launcher, "implementation_ready"), \
             mock.patch.object(launcher, "poll_once", return_value={"tracks": {}, "reviews": {}}), \
             mock.patch.object(launcher, "review_source_binding", return_value={"path": "snapshot.json", "sha256": "fixture"}), \
             mock.patch.object(launcher.evidence_module(), "response_contract", return_value=large_requirements), \
             mock.patch.object(launcher, "dispatch_route") as dispatch, \
             mock.patch.object(launcher, "save_manifest") as save, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_review(args)
        dispatch.assert_not_called()
        save.assert_not_called()
        self.assertEqual(manifest["attempts"]["review_cycles"], {})
        self.assertNotIn("reviews", manifest)

    def test_changed_rendered_input_is_rejected_before_runner_launch(self):
        route = self.route("impl-api", "implementer", "gpt-6-astra")
        metadata = {"input_measurement": launcher.measure_rendered(self.brief.read_text())}
        self.brief.write_text("Changed after preflight")
        with mock.patch.object(launcher, "fire_runner") as fire:
            with self.assertRaisesRegex(ValueError, "changed after budget preflight"):
                launcher.dispatch_route(route, self.brief, self.root, "implementer", 10, metadata, False, False)
        fire.assert_not_called()

    def test_oversized_followup_preserves_context_and_attempt_count(self):
        path = self.native_plan()
        with contextlib.redirect_stdout(io.StringIO()):
            launcher.cmd_launch(self.launch_arguments(path, "resume-budget"))
        manifest_path = self.manifest_for("resume-budget")
        manifest = json.loads(manifest_path.read_text())
        dispatch = manifest["tracks"]["api"]["implementation"]["native_dispatch"]
        receipt_path = self.root / "first-receipt.json"
        receipt_path.write_text(json.dumps(self.native_receipt(dispatch, context_id="same-role", completed_turn=1)))
        with contextlib.redirect_stdout(io.StringIO()):
            launcher.cmd_record_native(self.record_native_arguments(manifest_path, receipt_path))
        original = manifest_path.read_bytes()
        followup = self.root / "followup.md"
        followup.write_text("x" * 23500)
        args = Namespace(manifest=str(manifest_path), session_id=None, task_id=None, working_dir=None,
            track="api", follow_up=str(followup), timeout=10, context_recovery_reason=None)
        with mock.patch.object(launcher, "dispatch_route") as dispatch_call, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                launcher.cmd_resume_native(args)
        dispatch_call.assert_not_called()
        self.assertEqual(manifest_path.read_bytes(), original)
        followup.write_text("Apply the bounded repair and rerun the affected check.")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launcher.cmd_resume_native(args), 0)
        current = json.loads(manifest_path.read_text())["tracks"]["api"]["implementation"]
        self.assertEqual(current["native_dispatch"]["context_action"], "resume")
        self.assertEqual(current["native_dispatch"]["context_id"], "same-role")
        self.assertEqual(current["native_dispatch"]["parent_history"], "none")
        self.assertEqual(current["brief_binding"]["input_measurement"]["utf8_bytes"], Path(current["brief"]).stat().st_size)


if __name__ == "__main__":
    unittest.main(verbosity=2)
