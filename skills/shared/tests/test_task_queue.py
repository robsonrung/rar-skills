#!/usr/bin/env python3
"""Offline contracts for the read only task queue controller."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SHARED = Path(__file__).resolve().parents[1]
SCRIPTS = SHARED / "scripts"
sys.path.insert(0, str(SCRIPTS))
import review_evidence
import task_queue as queue


LAUNCH_PATH = SHARED.parent / "engineering" / "engine" / "implement-and-review" / "scripts" / "launch.py"
LAUNCH_SPEC = importlib.util.spec_from_file_location("task_queue_test_launcher", LAUNCH_PATH)
assert LAUNCH_SPEC and LAUNCH_SPEC.loader
launcher = importlib.util.module_from_spec(LAUNCH_SPEC)
LAUNCH_SPEC.loader.exec_module(launcher)


class TaskQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="task-queue-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "project"
        self.root.mkdir()
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.prd = self.root / "prd.md"
        self.prd.write_text("# Feature\n\n**Status:** approved\n", encoding="utf-8")

    def inventory(self, root: Path) -> dict[str, dict[str, str]]:
        entries = {}
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
            relative = str(path.relative_to(root))
            if path.is_symlink():
                entries[relative] = {"kind": "symlink", "target": str(path.readlink())}
            elif path.is_dir():
                entries[relative] = {"kind": "directory"}
            elif path.is_file():
                entries[relative] = {"kind": "file", "sha256": queue.file_sha256(path)}
            else:
                entries[relative] = {"kind": "other"}
        return entries

    def write_task(
        self,
        task_id: str,
        *,
        status: str = "ready-for-agent",
        task_type: str = "AFK",
        verdict: str = "proceed",
        decision: str = "none",
        blocked_by: str = "none",
    ) -> Path:
        path = self.root / "tasks" / f"{task_id}-example.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(
            f"# {task_id}: Example\n\n"
            f"**Type:** {task_type}\n"
            f"**Status:** {status}\n"
            "**Parent:** prd.md\n"
            "**Covers:** Feature outcome\n\n"
            "## What to build\n"
            "Provide the observable feature path.\n\n"
            "## Acceptance contract\n"
            "A focused check passes.\n\n"
            "## Gates\n"
            "1. Lenses run: none\n"
            f"2. Verdict: {verdict}\n"
            "3. Required changes and resolved findings: none\n"
            f"4. Decision required: {decision}\n"
            "5. Security: standard; trigger: no exposed security surface\n"
            "6. Test lens: none\n\n"
            "## Rollback note\n"
            "Restore the previous behavior.\n\n"
            "## Expected review focus\n"
            "Check the contract and changed behavior.\n\n"
            "## Parallelization\n"
            "Use the declared write scope.\n\n"
            "## Blocked by\n"
            f"{blocked_by}\n",
            encoding="utf-8",
        )
        return path

    def queue_config(
        self,
        task_ids: list[str],
        *,
        statuses: dict[str, str] | None = None,
        dependencies: dict[str, list[str]] | None = None,
        paths: dict[str, list[str]] | None = None,
        surfaces: dict[str, list[str]] | None = None,
        concurrency: dict | None = None,
        approval_record: str | None = None,
        merge_plans: list[dict] | None = None,
    ) -> Path:
        statuses = statuses or {}
        dependencies = dependencies or {}
        paths = paths or {}
        surfaces = surfaces or {}
        tasks = []
        for task_id in task_ids:
            self.write_task(task_id, status=statuses.get(task_id, "ready-for-agent"))
            tasks.append({
                "id": task_id,
                "manifest": f"tasks/{task_id}-example.md",
                "launch_manifest": f"artifacts/{task_id}/launch-manifest.json",
                "blocked_by": dependencies.get(task_id, []),
                "write_paths": paths.get(task_id, [f"src/{task_id}.py"]),
                "shared_surfaces": surfaces.get(task_id, []),
            })
        value = {
            "schema_version": 1,
            "id": "feature",
            "parent_prd": "prd.md",
            "concurrency": concurrency or {"max_active": 3, "isolation": "worktree"},
            "tasks": tasks,
            "merge_plans": merge_plans or [],
        }
        if approval_record is not None:
            value["approval_record"] = approval_record
        path = self.root / "queue.json"
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")
        return path

    def route(self, task_id: str, role: str) -> dict:
        if role == "implementer":
            return {
                "id": f"{task_id}-implementer",
                "task_id": task_id,
                "input_path": f"tasks/{task_id}-example.md",
                "track": "main",
                "role": role,
                "seat": "astra",
                "runner": "codex",
                "model": "gpt-6-astra",
                "model_verification": "required",
                "effort": "high",
                "effort_control": "runner",
                "mode": "runner",
                "unavailable": {"action": "block"},
            }
        return {
            "id": f"{task_id}-reviewer",
            "task_id": task_id,
            "input_path": f"tasks/{task_id}-example.md",
            "track": "main",
            "role": role,
            "seat": "fable",
            "runner": "claude",
            "model": "claude-fable-5-1",
            "model_verification": "required",
            "effort": "high",
            "effort_control": "runner",
            "mode": "runner",
            "unavailable": {"action": "block"},
        }

    def integration_reviewer_route(self, task_id: str) -> dict:
        route = self.route(f"integration-{task_id}", "reviewer")
        route["input_path"] = f"tasks/{task_id}-example.md"
        return route

    def routing_plan(self, task_ids: list[str], *, status: str = "approved", path: Path | None = None) -> Path:
        path = path or self.root / "routing-plan.json"
        scope = {
            "inputs": [
                {"path": "queue.json", "content_sha256": launcher.content_digest(self.root / "queue.json")},
                {"path": "prd.md", "content_sha256": launcher.content_digest(self.prd)},
                *[
                    {
                        "path": f"tasks/{task_id}-example.md",
                        "content_sha256": launcher.content_digest(self.root / "tasks" / f"{task_id}-example.md"),
                    }
                    for task_id in task_ids
                ],
            ]
        }
        routes = [
            route
            for task_id in task_ids
            for route in (
                self.route(task_id, "implementer"),
                self.route(task_id, "reviewer"),
                self.integration_reviewer_route(task_id),
            )
        ]
        approval = {
            "status": status,
            "decided_at": "2026-10-02T00:00:00Z",
            "reference": "test-response",
            "scope_digest": launcher.canonical_digest(launcher.normalized_scope_inputs(scope["inputs"])),
            "routes_digest": launcher.canonical_digest(launcher.normalized_routes(routes)),
        }
        path.write_text(json.dumps({"schema_version": 1, "scope": scope, "approval": approval, "routes": routes}, indent=2), encoding="utf-8")
        return path

    def legacy_routing_plan(self, queue_path: Path, task_ids: list[str]) -> Path:
        queue_locator = str(queue_path.relative_to(self.root))
        scope = {
            "inputs": [
                {"path": queue_locator, "content_sha256": launcher.content_digest(queue_path)},
                {"path": "prd.md", "content_sha256": launcher.content_digest(self.prd)},
            ]
        }
        routes = []
        for task_id in task_ids:
            for role in ("implementer", "reviewer"):
                route = self.route(task_id, role)
                route["input_path"] = queue_locator
                routes.append(route)
        approval = {
            "status": "approved",
            "decided_at": "2026-10-02T00:00:00Z",
            "reference": "test-response",
            "scope_digest": launcher.canonical_digest(launcher.normalized_scope_inputs(scope["inputs"])),
            "routes_digest": launcher.canonical_digest(launcher.normalized_routes(routes)),
        }
        path = self.root / "legacy-routing-plan.json"
        path.write_text(
            json.dumps({"schema_version": 1, "scope": scope, "approval": approval, "routes": routes}, indent=2),
            encoding="utf-8",
        )
        return path

    def ledger(
        self,
        plan: Path,
        *,
        calls: dict | None = None,
        integration: dict | None = None,
        limits: dict[str, int] | None = None,
        attempts: dict[str, int] | None = None,
    ) -> Path:
        calls = calls or {}
        routes = json.loads(plan.read_text(encoding="utf-8"))["routes"]
        route_ids = [route["id"] for route in routes]
        limits = limits or {"total_role_calls": 20, **{route_id: 4 for route_id in route_ids}}
        if attempts is None:
            attempts = {"total_role_calls": len(calls)}
            for call in calls.values():
                route = call.get("intent", {}).get("route", {}) if isinstance(call, dict) else {}
                route_id = route.get("id") if isinstance(route, dict) else None
                if isinstance(route_id, str):
                    attempts[route_id] = attempts.get(route_id, 0) + 1
        path = self.artifacts / "run-state.json"
        path.write_text(json.dumps({
            "attempts": attempts,
            "call_ledger": {
                "plan": {"path": str(plan.relative_to(self.root)), "sha256": queue.file_sha256(plan)},
                "limits": limits,
                "calls": calls,
            },
            "integration_evidence": integration or {},
        }, indent=2), encoding="utf-8")
        return path

    def manifest(self, task_id: str, plan: Path) -> Path:
        routing = json.loads(plan.read_text(encoding="utf-8"))
        path = self.artifacts / task_id / "launch-manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "skill": "implement-and-review",
            "task_id": task_id,
            "working_root": str(self.root),
            "isolation": "working-tree",
            "routing_plan": {"path": str(plan.relative_to(self.root)), "approval": routing["approval"]},
            "tracks": {
                "main": {
                    "implementer_route": self.route(task_id, "implementer"),
                    "reviewer_route": self.route(task_id, "reviewer"),
                }
            },
            "status": "running",
        }, indent=2), encoding="utf-8")
        return path

    def git(self, *args: str) -> None:
        result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def current_integration(self, task_id: str, plan: Path, *, review_scope=None, output=None) -> tuple[Path, dict, dict]:
        self.manifest(task_id, plan)
        requirements = self.artifacts / "requirements.json"
        requirements.write_text(json.dumps({
            "context": {"runtime": "fixture"},
            "checks": [{
                "id": "app-baseline",
                "command": [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; assert Path('app.txt').read_text(encoding='utf-8') == 'baseline\\n'",
                ],
                "cwd": ".",
                "timeout_seconds": 10,
                "inputs": ["app.txt"],
                "fresh": True,
            }],
            "observations": [],
            "exclusions": {},
            **({"review_scope": review_scope} if review_scope else {}),
        }), encoding="utf-8")
        snapshot_path = review_evidence.prepare(
            self.root,
            "HEAD",
            self.root / "tasks" / f"{task_id}-example.md",
            requirements,
            output or self.artifacts / "integration",
            artifact_dir=self.artifacts,
        )
        check = review_evidence.run_check(snapshot_path, "app-baseline")
        response = {
            "snapshot_sha256": review_evidence.file_hash(snapshot_path),
            "coverage": [],
            "findings": [],
            "checks": {"app-baseline": str(check)},
            "observations": [],
            "summary": "Current combined review is ready.",
            **({"scope_approval": review_evidence.digest(review_scope)} if review_scope else {}),
        }
        execution = {"success": True, "agent_message": json.dumps(response)}
        review_evidence.record_review(snapshot_path, response, execution)
        review_path = snapshot_path.parent / "review.json"
        integration = {
            "snapshot": {"path": str(snapshot_path.relative_to(self.root)), "sha256": queue.file_sha256(snapshot_path)},
            "base": "HEAD",
            "launch_manifest": str((self.artifacts / task_id / "launch-manifest.json").relative_to(self.root)),
        }
        reviewer_calls = {
            "combined-review": {
                "status": "completed",
                "intent": {
                    "route": self.integration_reviewer_route(task_id),
                    "review_snapshot": {"path": str(snapshot_path), "sha256": queue.file_sha256(snapshot_path)},
                },
                "review": {"path": str(review_path), "sha256": queue.file_sha256(review_path)},
                "review_status": "ready",
            }
        }
        return snapshot_path, integration, reviewer_calls

    def commit_source(self) -> None:
        self.git("init", "-q")
        self.git("add", "app.txt", "prd.md", "queue.json", "routing-plan.json", "tasks")
        self.git("-c", "user.name=Tests", "-c", "user.email=tests@example.invalid", "commit", "-qm", "Fixture")

    def test_canonical_digest_matches_launcher_without_loading_engine(self) -> None:
        samples = [
            "Text\r\n**Status:** ready-for-agent\r\n",
            "Text\n**Status:** draft\n",
            "Text\n**Status:** done\nTrailing\n",
            "Text\n**Status:** done later\n",
        ]
        for text in samples:
            with self.subTest(text=text):
                expected = hashlib.sha256(launcher.canonical_task_text(text).encode("utf-8")).hexdigest()
                self.assertEqual(queue.canonical_text_sha256(text), expected)
        config = self.queue_config(["T1"], statuses={"T1": "draft"})
        with mock.patch.object(queue, "launcher_module", side_effect=AssertionError("engine must not load")):
            preview = queue.approval_inputs(config, self.root)
        self.assertEqual(preview["tasks"][0]["status"], "draft")

    def test_approval_inputs_builds_prospective_route_scope_without_writes(self) -> None:
        config = self.queue_config(["T1"], statuses={"T1": "draft"})
        draft = self.routing_plan(["T1"], status="draft", path=self.root / "draft-routing-plan.json")
        before = self.inventory(self.root)
        preview = queue.approval_inputs(config, self.root, draft)
        prospective = preview["prospective_routing"]
        expected = preview["tasks"][0]["prospective_ready_content_sha256"]
        row = next(item for item in prospective["scope_inputs"] if item["path"] == "tasks/T1-example.md")
        self.assertEqual(row["content_sha256"], expected)
        self.assertEqual(prospective["scope_digest"], launcher.canonical_digest(prospective["scope_inputs"]))
        self.assertEqual(prospective["routes_digest"], launcher.canonical_digest(launcher.normalized_routes(json.loads(draft.read_text())["routes"])))
        self.assertEqual(before, self.inventory(self.root))

    def test_approval_inputs_rejects_unsettled_canonical_gates(self) -> None:
        config = self.queue_config(["T1"], statuses={"T1": "draft"})
        draft = self.routing_plan(["T1"], status="draft", path=self.root / "draft-routing-plan.json")
        task = self.root / "tasks/T1-example.md"
        original = task.read_text(encoding="utf-8")
        cases = [
            ("**Status:** draft", "**Status:**  draft", r"exact \*\*Status:\*\* draft"),
            ("2. Verdict: proceed", "2. Verdict: revise", "verdict is revise"),
            ("4. Decision required: none", "4. Decision required: route selection", "unresolved decision"),
            ("5. Security: standard; trigger: no exposed security surface", "", "Security: deep or standard"),
        ]
        for before, after, message in cases:
            with self.subTest(message=message):
                task.write_text(original.replace(before, after), encoding="utf-8")
                with self.assertRaisesRegex(queue.QueueError, message):
                    queue.approval_inputs(config, self.root, draft)
        task.write_text(original, encoding="utf-8")

    def test_graph_and_canonical_ownership_fail_closed(self) -> None:
        config = self.queue_config(["T1"], paths={"T1": []})
        with self.assertRaisesRegex(queue.QueueError, "owned write_paths"):
            queue.load_queue(config, self.root)
        for blockers, message in (({"T1": ["T1"]}, "cannot block itself"), ({"T1": ["T9"]}, "missing blockers"),
                                  ({"T1": ["T2"], "T2": ["T1"]}, "dependency cycle")):
            with self.subTest(blockers=blockers):
                config = self.queue_config(list(blockers), dependencies=blockers)
                with self.assertRaisesRegex(queue.QueueError, message):
                    queue.load_queue(config, self.root)

    def test_legacy_multi_task_and_published_contracts_keep_canonical_state(self) -> None:
        legacy = self.root / "tasks-draft.md"
        legacy.write_text(
            "# Task Queue: Feature\n\n**Status:** approved\n**Parent:** prd.md\n\n"
            "# T1: First\n**Status:** draft\n## Blocked by\nnone\n\n"
            "# T2: Second\n**Status:** draft\n## Blocked by\nT1\n",
            encoding="utf-8",
        )
        embedded = queue.load_queue(legacy, self.root)
        self.assertEqual([task.id for task in embedded.tasks], ["T1", "T2"])
        self.assertEqual(embedded.tasks[1].blocked_by, ("T1",))
        self.write_task("T1", status="ready-for-agent", blocked_by="none")
        self.write_task("T2", status="ready-for-agent", blocked_by="T1")
        published = queue.load_queue(legacy, self.root)
        self.assertEqual([task.status for task in published.tasks], ["ready-for-agent", "ready-for-agent"])
        self.assertEqual(published.tasks[1].blocked_by, ("T1",))

    def test_scheduler_orders_ready_tasks_and_clamps_working_tree_concurrency(self) -> None:
        config = self.queue_config(
            ["T10", "T2", "T1"],
            dependencies={"T10": ["T1"]},
            concurrency={"max_active": 3},
        )
        plan = self.routing_plan(["T1", "T2", "T10"])
        ledger = self.ledger(plan)
        before = self.inventory(self.root)
        result = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual(result["queue"]["configured_max_active"], 3)
        self.assertEqual(result["queue"]["max_active"], 1)
        self.assertEqual([item["id"] for item in result["ready"]], ["T1"])
        self.assertEqual(result["blocked"][0]["id"], "T2")
        self.assertEqual(before, self.inventory(self.root))

    def test_scheduler_projects_initial_call_ceilings_for_each_selected_task(self) -> None:
        config = self.queue_config(
            ["T1", "T2", "T3"],
            concurrency={"max_active": 3, "isolation": "worktree"},
        )
        plan = self.routing_plan(["T1", "T2", "T3"])
        route_ids = [route["id"] for route in json.loads(plan.read_text(encoding="utf-8"))["routes"]]
        limits = {"total_role_calls": 1, **{route_id: 2 for route_id in route_ids}}
        result = queue.schedule(config, plan, self.ledger(plan, limits=limits), self.root)
        self.assertEqual([item["id"] for item in result["ready"]], ["T1"])
        self.assertEqual([item["id"] for item in result["blocked"]], ["T2", "T3"])
        self.assertTrue(all("total_role_calls" in item["reasons"][0] for item in result["blocked"]))

        limits["total_role_calls"] = 3
        limits["T1-implementer"] = 1
        exhausted = queue.schedule(
            config,
            plan,
            self.ledger(plan, limits=limits, attempts={"total_role_calls": 1, "T1-implementer": 1}),
            self.root,
        )
        self.assertEqual([item["id"] for item in exhausted["ready"]], ["T2", "T3"])
        self.assertEqual([item["id"] for item in exhausted["blocked"]], ["T1"])
        self.assertIn("T1-implementer", exhausted["blocked"][0]["reasons"][0])

    def test_scheduler_rejects_ledger_attempt_counters_below_recorded_calls(self) -> None:
        config = self.queue_config(["T1"])
        plan = self.routing_plan(["T1"])
        calls = {"recorded": {"status": "completed", "intent": {"route": self.route("T1", "implementer")}}}
        ledger = self.ledger(plan, calls=calls, attempts={"total_role_calls": 0, "T1-implementer": 0})
        with self.assertRaisesRegex(queue.QueueError, "attempts.*lower than recorded calls"):
            queue.schedule(config, plan, ledger, self.root)

    def test_scheduler_serializes_directory_overlap_until_an_exact_merge_plan_allows_it(self) -> None:
        def project(config: Path) -> dict:
            plan = self.routing_plan(["T1", "T2"])
            return queue.schedule(config, plan, self.ledger(plan), self.root)

        config = self.queue_config(
            ["T1", "T2"],
            paths={"T1": ["src"], "T2": ["src/a.py"]},
            concurrency={"max_active": 2, "isolation": "worktree"},
        )
        without_plan = project(config)
        self.assertEqual([item["id"] for item in without_plan["ready"]], ["T1"])
        self.assertIn("src/a.py", without_plan["blocked"][0]["reasons"][0])

        config = self.queue_config(
            ["T1", "T2"],
            paths={"T1": ["src"], "T2": ["src"]},
            concurrency={"max_active": 2, "isolation": "worktree"},
            merge_plans=[{
                "id": "narrow-api",
                "tasks": ["T1", "T2"],
                "write_paths": ["src/a.py"],
                "shared_surfaces": [],
            }],
        )
        narrow_plan = project(config)
        self.assertEqual([item["id"] for item in narrow_plan["ready"]], ["T1"])
        self.assertIn("src", narrow_plan["blocked"][0]["reasons"][0])

        config = self.queue_config(
            ["T1", "T2"],
            paths={"T1": ["src"], "T2": ["src/a.py"]},
            concurrency={"max_active": 2, "isolation": "worktree"},
            merge_plans=[{
                "id": "narrow-api",
                "tasks": ["T1", "T2"],
                "write_paths": ["src/a.py"],
                "shared_surfaces": [],
            }],
        )
        exact_plan = project(config)
        self.assertEqual([item["id"] for item in exact_plan["ready"]], ["T1", "T2"])

    def test_scheduler_uses_exact_named_migration_interface_and_security_surfaces(self) -> None:
        for paths, message in ((["db/migrations/one.py"], "migration paths need"),
                               (["src/security/one.py"], "security paths need")):
            with self.subTest(message=message):
                config = self.queue_config(["T1"], paths={"T1": paths}, surfaces={"T1": []})
                with self.assertRaisesRegex(queue.QueueError, message):
                    queue.load_queue(config, self.root)

        config = self.queue_config(
            ["T1", "T2", "T3", "T4", "T5", "T6", "T7"],
            paths={
                "T1": ["db/migrations/accounts.py"],
                "T2": ["db/migrations/billing.py"],
                "T3": ["src/security/auth.py"],
                "T4": ["src/security/audit.py"],
                "T5": ["src/api/one.py"],
                "T6": ["src/api/two.py"],
                "T7": ["src/api/three.py"],
            },
            surfaces={
                "T1": ["migration:accounts"],
                "T2": ["migration:billing"],
                "T3": ["security:auth"],
                "T4": ["security:audit"],
                "T5": ["interface:public-api"],
                "T6": ["interface:public-api"],
                "T7": ["interface:private-api"],
            },
            concurrency={"max_active": 7, "isolation": "worktree"},
        )
        plan = self.routing_plan(["T1", "T2", "T3", "T4", "T5", "T6", "T7"])
        result = queue.schedule(config, plan, self.ledger(plan), self.root)
        self.assertEqual([item["id"] for item in result["ready"]], ["T1", "T2", "T3", "T4", "T5", "T7"])
        self.assertEqual([item["id"] for item in result["blocked"]], ["T6"])
        self.assertIn("interface:public-api", result["blocked"][0]["reasons"][0])

    def batch_integration(self, *, rename_task=False, members=2):
        task_ids = [f"T{number}" for number in range(1, members + 2)]
        config = self.queue_config(task_ids, dependencies={task_ids[-1]: task_ids[:-1]},
                                   concurrency={"max_active": 1, "isolation": "working-tree"})
        (self.root / "app.txt").write_text("baseline\n")
        contract = self.root / "batch-contract.md"
        contract.write_text("Review both canonical tasks on the combined state and all affected interactions.\n")
        plan = self.routing_plan(task_ids)
        route = self.route("integration-batch", "reviewer")
        route["input_path"] = "batch-contract.md"
        value = json.loads(plan.read_text())
        value["routes"].append(route)
        value["scope"]["inputs"].append({"path": "batch-contract.md", "content_sha256": launcher.content_digest(contract)})
        value["approval"]["scope_digest"] = launcher.canonical_digest(launcher.normalized_scope_inputs(value["scope"]["inputs"]))
        value["approval"]["routes_digest"] = launcher.canonical_digest(launcher.normalized_routes(value["routes"]))
        plan.write_text(json.dumps(value))
        self.commit_source()
        self.git("add", "batch-contract.md")
        self.git("-c", "user.name=Tests", "-c", "user.email=tests@example.invalid", "commit", "-qm", "Batch contract fixture")
        originals, entries, calls = {}, {}, {}
        for task_id in task_ids[:-1]:
            original, entry, call = self.current_integration(task_id, plan, output=self.artifacts / task_id / "prior")
            originals[task_id], entries[task_id] = original, entry
            calls[task_id] = call["combined-review"]
        (self.root / "additional.txt").write_text("ordinary later source change\n")
        rows = {}
        for task_id, original in originals.items():
            old = review_evidence.load_record(original)
            target = review_evidence.prepare(self.root, "HEAD", old["contract"]["path"], old["requirements"]["path"],
                                             self.artifacts / task_id / "current", artifact_dir=self.artifacts,
                                             previous_reviews=[original.parent / "review.json"])
            review_evidence.run_check(target, "app-baseline")
            packet = review_evidence.prepare_packet(target, self.artifacts / f"{task_id}.packet.json", observations=[])
            rows[task_id] = {"snapshot": review_evidence.evidence_link(target), "prior_review": review_evidence.evidence_link(original.parent / "review.json"),
                             "evidence_packet": review_evidence.evidence_link(packet)}
        if rename_task:
            rows["T3"] = rows.pop("T2")
        target_value = review_evidence.load_record(target)
        capture = self.artifacts / "environment.txt"
        capture.write_text("Current environment inspection output")
        environment = {"to_source_id": target_value["source_id"], "context_id": review_evidence.digest({"runtime": "fixture"})}
        environment.update({key: {"reason": "Current inspection", "evidence": [review_evidence.evidence_link(capture)]}
                            for key in ("runtime", "dependencies", "external_state", "base_interactions", "configuration", "schema")})
        environment_path = self.artifacts / "environment.json"
        environment_path.write_text(json.dumps(environment))
        requirements = self.artifacts / "batch-requirements.json"
        requirements.write_text(json.dumps({"context": {"runtime": "fixture"}, "checks": [], "observations": [], "exclusions": {},
                                           "batch": {"tasks": rows, "interactions": ["both task callers"], "environment": review_evidence.evidence_link(environment_path)}}))
        batch = review_evidence.prepare(self.root, "HEAD", contract, requirements, self.artifacts / "batch",
                                        artifact_dir=self.artifacts, previous_reviews=[path.parent / "review.json" for path in originals.values()])
        response_contract = review_evidence.response_contract(batch)
        response = {"snapshot_sha256": review_evidence.file_hash(batch), "checks": {}, "observations": [], "findings": [], "summary": "Combined contracts assessed.",
                    "coverage": [{"path": path, "outcome": "reviewed", "reason": "Assessed source and callers."} for path in response_contract["coverage_paths"]],
                    "batch_approval": response_contract["batch_approval"], "interactions": {"both task callers": "Both task acceptance paths remain correct."},
                    "endorsements": {key: {"snapshot_sha256": row["snapshot_sha256"], "coverage_paths": row["coverage_paths"], "acceptance": "Full task acceptance assessed."}
                                     for key, row in response_contract["endorsement_contracts"].items()}}
        review_evidence.record_review(batch, response, {"success": True, "agent_message": json.dumps(response)})
        calls["batch"] = {"status": "completed", "intent": {"route": route, "review_snapshot": review_evidence.evidence_link(batch)},
                          "review": review_evidence.evidence_link(batch.parent / "review.json"), "review_status": "ready"}
        for entry in entries.values():
            entry["batch_review"] = review_evidence.evidence_link(batch)
        return config, plan, entries, calls

    def test_one_batch_call_releases_two_retained_tasks_and_a_new_task(self):
        config, plan, entries, calls = self.batch_integration()
        projected = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
        self.assertEqual(projected["integrated"], ["T1", "T2"])
        self.assertEqual([task["id"] for task in projected["ready"]], ["T3"])
        self.assertEqual(len(calls), 3)

    def test_batch_projection_record_loads_scale_with_members(self):
        counts = []
        for members in (2, 4, 8):
            case = TaskQueueTests()
            case.setUp()
            self.addCleanup(case.doCleanups)
            config, plan, entries, calls = case.batch_integration(members=members)
            with mock.patch.object(review_evidence, "load_record", wraps=review_evidence.load_record) as loads:
                result = queue.schedule(config, plan, case.ledger(plan, calls=calls, integration=entries), case.root)
            self.assertEqual(len(result["integrated"]), members)
            counts.append(loads.call_count)
        self.assertLessEqual(counts[1], counts[0] * 2.5)
        self.assertLessEqual(counts[2], counts[0] * 5)

    def test_projection_rechecks_cached_source_and_logs_before_return(self):
        config, plan, entries, calls = self.batch_integration()
        original = queue.batch_dispatch_reasons
        batch = review_evidence.load_record(entries["T1"]["batch_review"]["path"])
        target = Path(batch["requirements"]["value"]["batch"]["tasks"]["T1"]["snapshot"]["path"])
        log = target.parent / "checks/app-baseline/stdout.log"
        before = log.read_bytes()
        for path in (log, self.root / "app.txt"):
            content = path.read_bytes()
            def drift(*args):
                result = original(*args)
                path.write_bytes(content + b"changed during projection")
                return result
            with mock.patch.object(queue, "batch_dispatch_reasons", side_effect=drift):
                with self.assertRaisesRegex(queue.QueueError, "changed during validation"):
                    queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
            path.write_bytes(content)
        self.assertEqual(log.read_bytes(), before)
        self.assertEqual(queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)["integrated"], ["T1", "T2"])

    def test_projection_detects_repointed_evidence_symlink(self):
        config, plan, entries, calls = self.batch_integration()
        batch = review_evidence.load_record(entries["T1"]["batch_review"]["path"])
        target = Path(batch["requirements"]["value"]["batch"]["tasks"]["T1"]["snapshot"]["path"])
        log = target.parent / "checks/app-baseline/stdout.log"
        matching = self.artifacts / "matching-output.txt"
        matching.write_bytes(log.read_bytes())
        changed = self.artifacts / "changed-output.txt"
        changed.write_bytes(matching.read_bytes() + b"changed capture")
        duplicate = self.artifacts / "duplicate-output.txt"
        duplicate.write_bytes(matching.read_bytes())
        log.unlink()
        log.symlink_to(matching)
        ledger = self.ledger(plan, calls=calls, integration=entries)
        self.assertEqual(queue.schedule(config, plan, ledger, self.root)["integrated"], ["T1", "T2"])
        original = queue.batch_dispatch_reasons
        for replacement in (changed, duplicate):
            with self.subTest(replacement=replacement.name):
                def repoint(*args):
                    result = original(*args)
                    log.unlink()
                    log.symlink_to(replacement)
                    return result
                with mock.patch.object(queue, "batch_dispatch_reasons", side_effect=repoint):
                    with self.assertRaisesRegex(queue.QueueError, "changed during validation"):
                        queue.schedule(config, plan, ledger, self.root)
                log.unlink()
                log.symlink_to(matching)
        self.assertEqual(queue.schedule(config, plan, ledger, self.root)["integrated"], ["T1", "T2"])

    def test_pending_or_failed_batch_call_retains_ownership(self):
        config, plan, entries, calls = self.batch_integration()
        for status in ("pending", "failed"):
            calls["batch"]["status"] = status
            result = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
            self.assertEqual(result["integrated"], [])
            self.assertEqual(result["ready"], [])
            self.assertEqual([task["id"] for task in result["active"]], ["T1", "T2"])

    def test_missing_or_changed_pending_batch_snapshot_blocks_projection(self):
        config, plan, entries, calls = self.batch_integration()
        calls["batch"]["status"] = "pending"
        snapshot = Path(calls["batch"]["intent"]["review_snapshot"]["path"])
        original = snapshot.read_bytes()
        for action in ("change", "delete"):
            if action == "change":
                snapshot.write_bytes(original + b" ")
            else:
                snapshot.unlink()
            with self.assertRaisesRegex(queue.QueueError, "pending review ownership cannot be resolved"):
                queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
            snapshot.write_bytes(original)

    def test_batch_requires_approved_dispatch_for_original_and_current_reviews(self):
        config, plan, entries, calls = self.batch_integration()
        for missing in ("T1", "batch"):
            changed = {key: value for key, value in calls.items() if key != missing}
            result = queue.schedule(config, plan, self.ledger(plan, calls=changed, integration=entries), self.root)
            self.assertNotIn("T1", result["integrated"])
            self.assertEqual(result["ready"], [])
        calls["batch"]["intent"]["route"] = self.integration_reviewer_route("T1")
        result = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
        self.assertEqual(result["integrated"], [])
        self.assertIn("independent reviewer dispatch binding", result["required_integration"][0]["reasons"][0])

    def test_batch_rejects_task_ids_bound_to_another_canonical_contract(self):
        config, plan, entries, calls = self.batch_integration(rename_task=True)
        result = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
        self.assertEqual(result["integrated"], [])
        self.assertEqual(result["ready"], [])
        self.assertIn("canonical queue contracts", result["required_integration"][0]["reasons"][0])

    def test_repeated_batch_must_retain_all_recorded_batch_history(self):
        config, plan, entries, calls = self.batch_integration()
        first = Path(entries["T1"]["batch_review"]["path"])
        snapshot = review_evidence.load_record(first)
        response = review_evidence.load_record(first.parent / "review.json")["result"]
        previous = [row["path"] for row in snapshot["previous_reviews"]]
        for number, include_history in ((2, False), (3, True)):
            if include_history:
                previous.extend([first.parent / "review.json", second.parent / "review.json"])
            current = review_evidence.prepare(self.root, "HEAD", snapshot["contract"]["path"], snapshot["requirements"]["path"],
                                              self.artifacts / f"batch-{number}", artifact_dir=self.artifacts,
                                              previous_reviews=previous)
            result = {**response, "snapshot_sha256": review_evidence.file_hash(current)}
            review_evidence.record_review(current, result, {"success": True, "agent_message": json.dumps(result)})
            calls[f"batch-{number}"] = {**calls["batch"], "intent": {**calls["batch"]["intent"], "review_snapshot": review_evidence.evidence_link(current)},
                                         "review": review_evidence.evidence_link(current.parent / "review.json")}
            for entry in entries.values():
                entry["batch_review"] = review_evidence.evidence_link(current)
            projected = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries), self.root)
            if include_history:
                self.assertEqual(projected["integrated"], ["T1", "T2"])
            else:
                self.assertEqual(projected["integrated"], [])
                self.assertIn("omits a prior batch review", projected["required_integration"][0]["reasons"][0])
                second = current

    def test_batch_spends_one_call_and_keeps_total_budget_ceiling(self):
        config, plan, entries, calls = self.batch_integration()
        limits = {"total_role_calls": 3, **{row["id"]: 4 for row in json.loads(plan.read_text())["routes"]}}
        result = queue.schedule(config, plan, self.ledger(plan, calls=calls, integration=entries, limits=limits), self.root)
        self.assertEqual(result["integrated"], ["T1", "T2"])
        self.assertEqual(result["ready"], [])
        self.assertIn("ceiling", " ".join(result["blocked"][0]["reasons"]))

    def test_new_gate_blocking_finding_blocks_approval_preview(self):
        config = self.queue_config(["T1"])
        path = self.root / "tasks/T1-example.md"
        text = path.read_text()
        gate = {"schema_version": 1, "verdict": "proceed", "lenses_run": [], "decision_required": None,
                "blocking_findings": [{"id": "G1", "lens": "architecture", "summary": "Unresolved boundary", "evidence": ["src/boundary.py"], "status": "open", "resolution": None}],
                "advisory_findings": [], "required_changes": [], "review_focus": []}
        text = text.replace("## Rollback note", "```gate-result\n" + json.dumps(gate) + "\n```\n\n## Rollback note")
        path.write_text(text)
        with self.assertRaisesRegex(queue.QueueError, "open blocking finding"):
            queue.approval_inputs(config, self.root)

    def test_published_legacy_contract_cannot_bypass_explicit_new_gate_blockers(self):
        legacy = self.root / "tasks-draft.md"
        legacy.write_text("# Task Queue: Feature\n\n**Status:** approved\n**Parent:** prd.md\n\n# T1: Example\n**Status:** draft\n")
        path = self.write_task("T1", status="draft")
        text = path.read_text().replace("## What to build", "**Write paths:** src/T1.py\n**Shared surfaces:** none\n\n## What to build")
        path.write_text(text)
        self.assertEqual(queue.approval_inputs(legacy, self.root)["tasks"][0]["status"], "draft")
        gate = {"schema_version": 1, "verdict": "proceed", "lenses_run": [], "decision_required": None,
                "blocking_findings": [{"id": "F1", "lens": "architecture", "summary": "Unresolved boundary", "evidence": ["src/T1.py"], "status": "open", "resolution": None}],
                "advisory_findings": [], "required_changes": [], "review_focus": []}
        path.write_text(text.replace("## Rollback note", "```gate-result\n" + json.dumps(gate) + "\n```\n\n## Rollback note"))
        with self.assertRaisesRegex(queue.QueueError, "F1: open blocking finding"):
            queue.approval_inputs(legacy, self.root)

    def test_current_integration_releases_dependency_then_source_drift_blocks_it(self) -> None:
        config = self.queue_config(
            ["T1", "T2"],
            dependencies={"T2": ["T1"]},
            concurrency={"max_active": 1, "isolation": "working-tree"},
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        snapshot, integration, reviewer_calls = self.current_integration("T1", plan)
        failed_call = {"failed": {"status": "failed", "intent": {"route": self.route("T1", "implementer")}}}
        ledger = self.ledger(plan, calls={**failed_call, **reviewer_calls}, integration={"T1": integration})
        command = [
            sys.executable,
            str(SCRIPTS / "task_queue.py"),
            "schedule",
            "--root", str(self.root),
            "--queue", "queue.json",
            "--routing-plan", "routing-plan.json",
            "--ledger", "artifacts/run-state.json",
        ]
        result = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        projected = json.loads(result.stdout)
        self.assertEqual([item["id"] for item in projected["ready"]], ["T2"])
        self.assertEqual(projected["integrated"], ["T1"])
        self.assertEqual(snapshot.parent.parent, self.artifacts)
        (self.root / "app.txt").write_text("changed\n", encoding="utf-8")
        stale = queue.schedule("queue.json", "routing-plan.json", "artifacts/run-state.json", self.root)
        self.assertEqual(stale["active"][0]["id"], "T1")
        self.assertEqual(stale["blocked"][0]["id"], "T2")
        self.assertTrue(stale["required_integration"])

    def test_scoped_carry_forward_releases_dependency_and_preserves_dispatch_and_ownership(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        notes = self.artifacts / "prospective-notes.txt"
        notes.write_text("Independent notes.\n")
        scope = {"inputs": ["app.txt"], "complete": True,
                 "reason": "The fixture reads app.txt only. Notes have no runtime or build role.",
                 "changes": [{"path": "notes.txt", "content": review_evidence.evidence_link(notes),
                              "reason": "Reviewed exact notes content and confirmed no effect on task acceptance."}]}
        original, integration, calls = self.current_integration("T1", plan, review_scope=scope)
        (self.root / "notes.txt").write_bytes(notes.read_bytes())
        ledger = self.ledger(plan, calls=calls, integration={"T1": integration})
        stale = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual([row["id"] for row in stale["blocked"]], ["T2"])
        target = review_evidence.prepare(self.root, "HEAD", self.root / "tasks/T1-example.md",
                                         self.artifacts / "requirements.json", self.artifacts / "checkpoint",
                                         artifact_dir=self.artifacts, previous_reviews=[original.parent / "review.json"])
        review_evidence.run_check(target, "app-baseline")
        packet = review_evidence.prepare_packet(target, self.artifacts / "packet.json", observations=[])
        probe = self.artifacts / "environment.txt"
        probe.write_text("Current runtime and dependencies inspected; no services or base changes.")
        row = {"reason": "Current environment matches the captured fixture.", "evidence": [review_evidence.evidence_link(probe)]}
        assessment = self.artifacts / "assessment.json"
        assessment.write_text(json.dumps({"from_snapshot_sha256": review_evidence.file_hash(original),
                                         "to_source_id": review_evidence.load_record(target)["source_id"],
                                         **{key: row for key in ("runtime", "dependencies", "external_state", "base_interactions")}}))
        checkpoint = review_evidence.carry_forward(original, target, assessment, packet, self.artifacts / "carry.json")
        integration["carry_forward"] = review_evidence.evidence_link(checkpoint)
        ledger = self.ledger(plan, calls=calls, integration={"T1": integration})
        ready = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual(ready["integrated"], ["T1"])
        self.assertEqual([row["id"] for row in ready["ready"]], ["T2"])
        self.assertEqual(len(calls), 1)
        self.assertFalse((target.parent / "review.json").exists())

        for changed_calls in ({}, {**calls, "pending": {"status": "pending", "intent": {"route": self.route("T1", "implementer")}}}):
            ledger = self.ledger(plan, calls=changed_calls, integration={"T1": integration})
            blocked = queue.schedule(config, plan, ledger, self.root)
            self.assertEqual([row["id"] for row in blocked["active"]], ["T1"])
            self.assertEqual([row["id"] for row in blocked["blocked"]], ["T2"])

        limits = {"total_role_calls": 1, **{route["id"]: 4 for route in json.loads(plan.read_text())["routes"]}}
        ledger = self.ledger(plan, calls=calls, integration={"T1": integration}, limits=limits)
        exhausted = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual(exhausted["integrated"], ["T1"])
        self.assertEqual([row["id"] for row in exhausted["blocked"]], ["T2"])
        self.assertIn("total_role_calls", exhausted["blocked"][0]["reasons"][0])

        malformed_assessment = self.artifacts / "malformed-assessment.json"
        malformed_assessment.write_text("[]")
        payload = review_evidence.load_record(checkpoint)
        payload["assessment"] = review_evidence.evidence_link(malformed_assessment)
        malformed = review_evidence.write_record(self.artifacts / "malformed-checkpoint.json", payload)
        malformed_integration = {**integration, "carry_forward": review_evidence.evidence_link(malformed)}
        ledger = self.ledger(plan, calls=calls, integration={"T1": malformed_integration})
        rejected = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual([row["id"] for row in rejected["blocked"]], ["T2"])
        self.assertIn("assessment must be an object", rejected["required_integration"][0]["reasons"][0])

        ledger = self.ledger(plan, calls=calls, integration={"T1": integration})
        (self.root / "app.txt").write_text("Affected dependency\n")
        affected = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual([row["id"] for row in affected["blocked"]], ["T2"])
        self.assertTrue(affected["required_integration"])

    def test_pending_call_retains_ownership_after_a_ready_integration_snapshot(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        _, integration, reviewer_calls = self.current_integration("T1", plan)
        pending = {"pending": {"status": "pending", "intent": {"route": self.route("T1", "implementer")}}}
        ledger = self.ledger(plan, calls={**pending, **reviewer_calls}, integration={"T1": integration})
        result = queue.schedule(config, plan, ledger, self.root)
        self.assertEqual(result["active"][0]["id"], "T1")
        self.assertEqual(result["blocked"][0]["id"], "T2")

    def test_direct_review_record_does_not_release_a_dependency_without_reviewer_dispatch(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        _, integration, _ = self.current_integration("T1", plan)
        result = queue.schedule(config, plan, self.ledger(plan, integration={"T1": integration}), self.root)
        self.assertEqual([item["id"] for item in result["active"]], ["T1"])
        self.assertEqual([item["id"] for item in result["blocked"]], ["T2"])
        self.assertIn("approved reviewer dispatch binding", result["required_integration"][0]["reasons"][0])

    def test_completed_task_reviewer_call_cannot_bind_integration_evidence(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        _, integration, reviewer_calls = self.current_integration("T1", plan)
        reviewer_calls["combined-review"]["intent"]["route"] = self.route("T1", "reviewer")
        result = queue.schedule(
            config,
            plan,
            self.ledger(plan, calls=reviewer_calls, integration={"T1": integration}),
            self.root,
        )
        self.assertEqual([item["id"] for item in result["active"]], ["T1"])
        self.assertIn("approved reviewer dispatch binding", result["required_integration"][0]["reasons"][0])

    def test_changed_integration_reviewer_route_is_rejected(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        _, integration, reviewer_calls = self.current_integration("T1", plan)
        reviewer_calls["combined-review"]["intent"]["route"]["effort"] = "medium"
        with self.assertRaisesRegex(queue.QueueError, "route is not approved"):
            queue.schedule(
                config,
                plan,
                self.ledger(plan, calls=reviewer_calls, integration={"T1": integration}),
                self.root,
            )

    def test_manifest_review_record_keeps_legacy_reviewer_evidence_usable(self) -> None:
        config = self.queue_config(
            ["T1", "T2"], dependencies={"T2": ["T1"]}, concurrency={"max_active": 1, "isolation": "working-tree"}
        )
        (self.root / "app.txt").write_text("baseline\n", encoding="utf-8")
        plan = self.routing_plan(["T1", "T2"])
        self.commit_source()
        snapshot, integration, _ = self.current_integration("T1", plan)
        manifest_path = self.artifacts / "T1" / "launch-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        review_path = snapshot.parent / "review.json"
        manifest["reviews"] = [{
            "track": "main",
            "cycle": 1,
            "source_snapshot": {"path": str(snapshot), "sha256": queue.file_sha256(snapshot)},
            "reviewer_route": self.route("T1", "reviewer"),
            "review_evidence": {"path": str(review_path), "sha256": queue.file_sha256(review_path)},
        }]
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        result = queue.schedule(config, plan, self.ledger(plan, integration={"T1": integration}), self.root)
        self.assertEqual(result["integrated"], ["T1"])
        self.assertEqual([item["id"] for item in result["ready"]], ["T2"])

    def test_legacy_embedded_task_needs_a_published_contract_before_dispatch(self) -> None:
        legacy = self.root / "tasks-draft.md"
        legacy.write_text(
            "# Task Queue: Feature\n\n**Status:** approved\n**Parent:** prd.md\n\n"
            "# T1: Embedded\n**Status:** ready-for-agent\n## Blocked by\nnone\n",
            encoding="utf-8",
        )
        plan = self.legacy_routing_plan(legacy, ["T1"])
        with self.assertRaisesRegex(queue.QueueError, "derive canonical task files"):
            queue.approval_inputs(legacy, self.root, plan)
        result = queue.schedule(legacy, plan, self.ledger(plan), self.root)
        self.assertEqual(result["ready"], [])
        self.assertEqual([item["id"] for item in result["blocked"]], ["T1"])
        self.assertIn("derive canonical task files", result["blocked"][0]["reasons"][0])

    def test_combined_approval_requires_both_decisions(self) -> None:
        config = self.queue_config(["T1"], statuses={"T1": "draft"}, approval_record="artifacts/approval.json")
        draft = self.routing_plan(["T1"], status="draft", path=self.root / "draft-routing-plan.json")
        preview = queue.approval_inputs(config, self.root, draft)
        preview_path = self.artifacts / "preview.json"
        preview_path.write_text(json.dumps(preview, indent=2), encoding="utf-8")
        task = self.root / "tasks/T1-example.md"
        task.write_text(task.read_text(encoding="utf-8").replace("**Status:** draft", "**Status:** ready-for-agent"), encoding="utf-8")
        routing = preview["prospective_routing"]
        routes = json.loads(draft.read_text(encoding="utf-8"))["routes"]
        plan = self.root / "routing-plan.json"
        approval = {
            "status": "approved",
            "decided_at": "2026-10-02T00:00:00Z",
            "reference": "actual-response",
            "scope_digest": routing["scope_digest"],
            "routes_digest": routing["routes_digest"],
        }
        plan.write_text(json.dumps({"schema_version": 1, "scope": {"inputs": routing["scope_inputs"]}, "approval": approval, "routes": routes}), encoding="utf-8")
        payload = {
            "schema_version": 1,
            "decisions": ["task_queue"],
            "response_reference": "actual-response",
            "decided_at": "2026-10-02T00:00:00Z",
            "queue_file_sha256": queue.file_sha256(config),
            "preview": {"path": "artifacts/preview.json", "sha256": queue.file_sha256(preview_path)},
            "scope_digest": routing["scope_digest"],
            "routes_digest": routing["routes_digest"],
        }
        review_evidence.write_record(self.artifacts / "approval.json", payload)
        ledger = self.ledger(plan)
        with self.assertRaisesRegex(queue.QueueError, "task_queue and model_plan"):
            queue.schedule(config, plan, ledger, self.root)

    def test_combined_approval_with_both_decisions_releases_a_fresh_task(self) -> None:
        config = self.queue_config(
            ["T1"],
            statuses={"T1": "draft"},
            approval_record="artifacts/approval-complete.json",
        )
        task = self.root / "tasks/T1-example.md"
        task.write_bytes(task.read_bytes().replace(b"\n", b"\r\n"))
        draft = self.routing_plan(["T1"], status="draft", path=self.root / "draft-routing-plan.json")
        preview = queue.approval_inputs(config, self.root, draft)
        preview_path = self.artifacts / "preview-complete.json"
        preview_path.write_text(json.dumps(preview, indent=2), encoding="utf-8")
        task.write_bytes(
            task.read_bytes().replace(
                b"**Status:** draft\r\n",
                b"**Status:** ready-for-agent\r\n",
            )
        )
        routing = preview["prospective_routing"]
        routes = json.loads(draft.read_text(encoding="utf-8"))["routes"]
        plan = self.root / "routing-plan.json"
        approval = {
            "status": "approved",
            "decided_at": "2026-10-02T00:00:00Z",
            "reference": "actual-combined-response",
            "scope_digest": routing["scope_digest"],
            "routes_digest": routing["routes_digest"],
        }
        plan.write_text(json.dumps({
            "schema_version": 1,
            "scope": {"inputs": routing["scope_inputs"]},
            "approval": approval,
            "routes": routes,
        }), encoding="utf-8")
        payload = {
            "schema_version": 1,
            "decisions": ["task_queue", "model_plan"],
            "response_reference": "actual-combined-response",
            "decided_at": "2026-10-02T00:00:00Z",
            "queue_file_sha256": queue.file_sha256(config),
            "preview": {"path": "artifacts/preview-complete.json", "sha256": queue.file_sha256(preview_path)},
            "scope_digest": routing["scope_digest"],
            "routes_digest": routing["routes_digest"],
        }
        record = self.artifacts / "approval-complete.json"
        review_evidence.write_record(record, payload)
        result = queue.schedule(config, plan, self.ledger(plan), self.root)
        self.assertEqual([item["id"] for item in result["ready"]], ["T1"])
        self.assertEqual(review_evidence.load_record(record), payload)
        previous = "ready-for-agent"
        for status in ("in-progress", "done"):
            task.write_bytes(task.read_bytes().replace(
                f"**Status:** {previous}\r\n".encode("utf-8"),
                f"**Status:** {status}\r\n".encode("utf-8"),
            ))
            resumed = queue.schedule(config, plan, self.ledger(plan), self.root)
            self.assertEqual(resumed["ready"], [])
            self.assertEqual([item["id"] for item in resumed["blocked"]], ["T1"])
            previous = status
        task.write_bytes(task.read_bytes().replace(
            b"**Status:** done\r\n",
            b"**Status:** ready-for-agent\r\n",
        ))
        for status in ("ready-for-agent", "done"):
            if status == "done":
                task.write_bytes(task.read_bytes().replace(
                    b"**Status:** ready-for-agent\r\n",
                    b"**Status:** done\r\n",
                ))
            task.write_bytes(task.read_bytes().replace(
                f"**Status:** {status}\r\n".encode("utf-8"),
                f"**Status:**  {status}\r\n".encode("utf-8"),
            ))
            loaded = queue.load_queue(config, self.root)
            with self.assertRaisesRegex(queue.QueueError, "promoted status line is not exact"):
                queue.validate_combined_preview_tasks(
                    loaded,
                    preview,
                    routing["scope_inputs"],
                    self.root,
                )
            task.write_bytes(task.read_bytes().replace(
                f"**Status:**  {status}\r\n".encode("utf-8"),
                f"**Status:** {status}\r\n".encode("utf-8"),
            ))

    def test_flat_install_bundle_supports_help_preview_and_schedule(self) -> None:
        config = self.queue_config(["T1"])
        plan = self.routing_plan(["T1"])
        ledger = self.ledger(plan)
        bundle = Path(self.temporary.name) / "flat-skills"
        shutil.copytree(SHARED, bundle / "shared")
        shutil.copytree(SHARED.parent / "engineering" / "engine" / "implement-and-review", bundle / "implement-and-review")
        script = bundle / "shared" / "scripts" / "task_queue.py"
        before = self.inventory(bundle)
        commands = [
            [sys.executable, str(script), "--help"],
            [sys.executable, str(script), "approval-inputs", "--root", str(self.root), "--queue", "queue.json"],
            [
                sys.executable, str(script), "schedule", "--root", str(self.root), "--queue", "queue.json",
                "--routing-plan", "routing-plan.json", "--ledger", "artifacts/run-state.json",
            ],
        ]
        for command in commands:
            with self.subTest(command=command[2] if len(command) > 2 else "help"):
                result = subprocess.run(command, cwd=self.root.parent, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, self.inventory(bundle))


if __name__ == "__main__":
    unittest.main()
