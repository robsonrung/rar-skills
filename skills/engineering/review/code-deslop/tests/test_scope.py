"""Local temporary-repository checks. No network or repository hooks are required."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cleanup_scope", ROOT / "scripts/scope.py")
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        for name in tuple(self.env):
            if name.startswith("GIT_"):
                self.env.pop(name)
        self.env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env_patch = patch.dict(os.environ, self.env, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.g("init", "-q")
        self.g("config", "user.name", "Fixture Maintainer")
        self.g("config", "user.email", "fixture@example.invalid")
        self.write("src/base.py", "value = 1\n")
        self.g("add", ".")
        self.g("commit", "-qm", "Initial fixture")

    def g(self, *args, ok=True):
        result = subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if ok and result.returncode:
            self.fail(result.stderr.decode(errors="replace"))
        return result

    def write(self, name, contents="value = 2\n"):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents)
        return p

    def entries(self, result):
        return {item["path"]: item for item in result["files"]}

    def test_clean_scope_stays_empty(self):
        self.assertEqual(scope.collect(self.repo)["files"], [])

    def test_unborn_branch_includes_staged_and_untracked(self):
        other = Path(self.temp.name) / "unborn"
        other.mkdir()
        subprocess.run(["git", "init", "-q", str(other)], check=True, env=self.env)
        (other / "first.py").write_text("x = 1\n")
        result = scope.collect(other)
        self.assertIsNone(result["head"])
        self.assertIn("first.py", self.entries(result))

    def test_staged_unstaged_untracked_union(self):
        self.write("src/base.py")
        self.g("add", "src/base.py")
        self.write("src/base.py", "value = 3\n")
        self.write("new.py")
        entries = self.entries(scope.collect(self.repo))
        self.assertEqual(entries["src/base.py"]["changes"], ["staged", "unstaged"])
        self.assertEqual(entries["new.py"]["changes"], ["untracked"])

    def test_staged_and_unstaged_cancellation_not_hidden(self):
        self.write("src/base.py")
        self.g("add", "src/base.py")
        self.write("src/base.py", "value = 1\n")
        self.assertIn("src/base.py", self.entries(scope.collect(self.repo)))

    def test_deleted_file_is_diff_only(self):
        (self.repo / "src/base.py").unlink()
        entry = self.entries(scope.collect(self.repo))["src/base.py"]
        self.assertFalse(entry["eligible"])
        self.assertIn("deleted", entry["exclusion"])

    def test_rename_exposes_both_paths(self):
        self.g("mv", "src/base.py", "src/renamed.py")
        entries = self.entries(scope.collect(self.repo))
        self.assertEqual(set(entries), {"src/base.py", "src/renamed.py"})

    def test_ignored_untracked_files_not_included(self):
        self.write(".gitignore", "ignored/\n")
        self.write("ignored/new.py")
        self.write("visible.py")
        entries = self.entries(scope.collect(self.repo))
        self.assertNotIn("ignored/new.py", entries)
        self.assertIn("visible.py", entries)

    def test_exclusions_are_reported_not_editable(self):
        for name in (".env.local", "package-lock.json", "node_modules/pkg/x.js", "types.generated.ts", "photo.png", "key.pem"):
            self.write(name)
        entries = self.entries(scope.collect(self.repo))
        self.assertTrue(all(not entry["eligible"] for entry in entries.values()))

    def test_unusual_names_are_literal(self):
        names = ["-flag.py", "a;echo hacked.py", "tab\tname.py", "line\nname.py", "espaço.py"]
        for name in names:
            self.write(name)
        result = scope.collect(self.repo)
        self.assertEqual(set(self.entries(result)), set(names))
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_path_filter_is_literal_and_rejects_escape(self):
        self.write("src/new.py")
        self.write("src-other/new.py")
        self.assertEqual(set(self.entries(scope.collect(self.repo, paths=["src"]))), {"src/new.py"})
        for value in ("../src", "/etc", "missing", "src/*"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scope.collect(self.repo, paths=[value])

    def test_repo_scope_can_inspect_unchanged_paths(self):
        entries = self.entries(scope.collect(self.repo, "repo", paths=["src"]))
        self.assertEqual(set(entries), {"src/base.py"})

    def test_branch_requires_explicit_valid_base(self):
        for mode, base in (("branch", None), ("changed", "HEAD"), ("repo", "HEAD")):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                scope.collect(self.repo, mode, base)
        with self.assertRaises(RuntimeError):
            scope.collect(self.repo, "branch", "not-a-ref")

    def test_branch_uses_merge_base_and_includes_dirty(self):
        self.g("branch", "base")
        self.g("checkout", "-qb", "feature")
        self.write("feature.py")
        self.g("add", ".")
        self.g("commit", "-qm", "Feature")
        self.g("checkout", "-q", "base")
        self.write("base-only.py")
        self.g("add", ".")
        self.g("commit", "-qm", "Other base work")
        self.g("checkout", "-q", "feature")
        self.write("dirty.py")
        result = scope.collect(self.repo, "branch", "base")
        self.assertNotEqual(result["base_commit"], result["merge_base"])
        self.assertEqual(set(self.entries(result)), {"feature.py", "dirty.py"})

    def test_symlinks_and_ancestors_excluded(self):
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (outside / "private.py").write_text("secret = 123\n")
        (self.repo / "link.py").symlink_to(outside / "private.py")
        (self.repo / "linked-dir").symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.entries(scope.collect(self.repo))["link.py"]["eligible"])
        self.assertIn("symlink", scope.exclusion(self.repo, "linked-dir/private.py", None))

    def test_git_index_is_not_written(self):
        self.write("src/base.py")
        self.g("add", "src/base.py")
        index = self.repo / ".git/index"
        before = (index.read_bytes(), index.stat().st_mtime_ns)
        scope.collect(self.repo)
        self.assertEqual(before, (index.read_bytes(), index.stat().st_mtime_ns))

    def test_external_diff_and_fsmonitor_not_executed(self):
        sentinel = Path(self.temp.name) / "must-not-exist"
        command = f"touch '{sentinel}'"
        self.g("config", "diff.external", command)
        self.g("config", "core.fsmonitor", command)
        self.write("src/base.py")
        scope.collect(self.repo)
        self.assertFalse(sentinel.exists())

    def test_content_filters_not_executed(self):
        sentinel = Path(self.temp.name) / "filter-must-not-run"
        self.write(".gitattributes", "*.py filter=custom\n")
        self.g("config", "filter.custom.clean", f"touch '{sentinel}'; cat")
        self.g("config", "filter.custom.smudge", f"touch '{sentinel}'; cat")
        self.g("config", "filter.custom.required", "true")
        self.write("src/base.py")
        result = scope.collect(self.repo)
        self.assertIn("src/base.py", self.entries(result))
        self.assertFalse(sentinel.exists())

    def test_process_filter_not_executed(self):
        sentinel = Path(self.temp.name) / "process-must-not-run"
        self.write(".gitattributes", "*.py filter=process_test\n")
        self.g("config", "filter.process_test.process", f"touch '{sentinel}'; exit 1")
        self.g("config", "filter.process_test.required", "true")
        self.write("src/base.py")
        scope.collect(self.repo)
        self.assertFalse(sentinel.exists())

    def test_conflicts_block_cleanup(self):
        self.g("branch", "left")
        self.g("checkout", "-qb", "right")
        self.write("src/base.py", "value = 11\n")
        self.g("commit", "-qam", "Right edit")
        self.g("checkout", "-q", "left")
        self.write("src/base.py", "value = 22\n")
        self.g("commit", "-qam", "Left edit")
        self.assertNotEqual(self.g("merge", "right", ok=False).returncode, 0)
        result = scope.collect(self.repo)
        self.assertTrue(result["blocked"])
        self.assertIn("src/base.py", result["conflicts"])

    def test_non_git_directory_fails(self):
        with self.assertRaises(RuntimeError):
            scope.collect(Path(self.temp.name))

    def test_cli_emits_json(self):
        self.write("new.py")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/scope.py"), "--repo", str(self.repo)],
                                capture_output=True, text=True, timeout=30, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new.py", self.entries(json.loads(result.stdout)))


if __name__ == "__main__":
    unittest.main()
