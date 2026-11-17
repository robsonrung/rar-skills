"""snapshot_repo.py records what was inspected without leaking content and detects later changes."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "snapshot_repo.py"
SECRET_REMOTE = "https://user:hunter2-token@example.com/org/repo.git"
FILE_TEXT = "def handler():\n    return 'distinctive-file-body'\n"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


@unittest.skipUnless(shutil.which("git"), "git is required")
class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.com")
        git(self.repo, "config", "user.name", "Test")
        git(self.repo, "remote", "add", "origin", SECRET_REMOTE)
        (self.repo / "app.py").write_text(FILE_TEXT)
        (self.repo / ".gitignore").write_text("out/\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "init")
        self.out = self.tmp / "snap.json"

    def snapshot(self, *extra: str) -> subprocess.CompletedProcess:
        return run("--repo", str(self.repo), "--output", str(self.out), *extra)

    def test_output_has_no_remote_url_or_file_content(self):
        (self.repo / "app.py").write_text(FILE_TEXT + "# local edit\n")
        result = self.snapshot("--base", "HEAD", "--worktree")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.out.read_text()
        self.assertNotIn("hunter2", text)
        self.assertNotIn("example.com", text)
        self.assertNotIn("distinctive-file-body", text)
        self.assertIn("app.py", json.loads(text)["untracked_paths"] + [c["path"] for c in json.loads(text)["changes"]])

    def test_check_reports_current_then_stale(self):
        self.assertEqual(self.snapshot("--base", "HEAD", "--worktree").returncode, 0)
        current = run("--repo", str(self.repo), "--check", str(self.out))
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertEqual(json.loads(current.stdout)["status"], "current")
        (self.repo / "app.py").write_text(FILE_TEXT + "# changed after the report\n")
        stale = run("--repo", str(self.repo), "--check", str(self.out))
        self.assertEqual(stale.returncode, 1)
        self.assertEqual(json.loads(stale.stdout)["status"], "stale")

    def test_refuses_unignored_output_inside_the_repo(self):
        inside = run("--repo", str(self.repo), "--snapshot-only", "--output", str(self.repo / "snap.json"))
        self.assertEqual(inside.returncode, 2)
        self.assertFalse((self.repo / "snap.json").exists())
        ignored = run("--repo", str(self.repo), "--snapshot-only", "--output", str(self.repo / "out" / "snap.json"))
        self.assertEqual(ignored.returncode, 0, ignored.stderr)

    def test_comparison_requires_an_explicit_base(self):
        result = run("--repo", str(self.repo), "--output", str(self.out), "--head", "HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
