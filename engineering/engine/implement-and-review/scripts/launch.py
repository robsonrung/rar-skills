#!/usr/bin/env python3
"""launch.py — set up worktrees and fire the implement-and-review implementers.

Deterministic helper for the implement-and-review skill. It does the parts that
are pure shell/git so the orchestrator does not have to hand-issue them:

  * create one git worktree + branch per active track off a clean base
  * fire the backend implementer and the selected frontend implementer as
    tracked background jobs
  * write a launch manifest the orchestrator (and `poll`) reads back
  * poll those jobs to a consolidated status in one call

It CANNOT spawn a native Opus `Agent` subagent because that is an in-process
tool only the orchestrator has. The default frontend seat is Codex for standard
product interface work. Select --fe-seat opus for visual reconstruction or
highly creative work; --fe-mode auto then leaves a native Opus subagent pending,
while --fe-mode runner uses claude-runner.

Examples:
  # standard product interface: fire both Codex implementers
  launch.py launch --session-id feat-x \
      --fe-brief .ai-workflow/impl-review/feat-x/frontend-brief.md \
      --be-brief .ai-workflow/impl-review/feat-x/backend-brief.md

  # visual or highly creative interface: leave frontend for a native Opus seat
  launch.py launch --session-id feat-x --fe-brief fe.md --be-brief be.md --fe-seat opus

  # use the Opus runner instead of a native subagent
  launch.py launch --session-id feat-x --fe-brief fe.md --be-brief be.md \
      --fe-seat opus --fe-mode runner

  # backend-only task
  launch.py launch --session-id feat-x --be-brief be.md --no-frontend

  # one slice of a parallel build (--slice namespaces worktrees/branches/artifacts)
  launch.py launch --session-id feat-x --slice S1 --be-brief s1-be.md --fe-brief s1-fe.md
  launch.py poll --session-id feat-x --slice S1 --wait

  # poll both tracks until terminal
  launch.py poll --session-id feat-x --wait

  # remove the worktrees when done (branches kept unless --delete-branches)
  launch.py cleanup --session-id feat-x

All commands print JSON to stdout and diagnostics to stderr.
"""

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _skills_dir() -> Path:
    """Directory owning shared/scripts/ — flat installed layout or nested source checkout."""
    for parent in SKILL_ROOT.parents:
        if (parent / "shared" / "scripts" / "runner_jobs.py").is_file():
            return parent
    return SKILL_ROOT.parent


SKILLS_DIR = _skills_dir()  # holds shared/ and, in some layout, codex-runner/, claude-runner/, ...
JOBS_CLI = SKILLS_DIR / "shared" / "scripts" / "runner_jobs.py"
JOB_ID_RE = re.compile(r"\b([a-z]+-[0-9a-f]{8})\b")


def runner_script(name: str) -> Path:
    shared = str(SKILLS_DIR / "shared" / "scripts")
    if shared not in sys.path:
        sys.path.insert(0, shared)
    try:
        from skill_paths import runner_script as _resolve
    except ImportError:
        return SKILLS_DIR / f"{name}-runner" / "scripts" / f"run_{name}.py"
    return _resolve(name, root=SKILLS_DIR)


def err(*msg) -> None:
    print(*msg, file=sys.stderr)


def fail(message: str, code: int = 1) -> NoReturn:
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False))
    err(f"error: {message}")
    sys.exit(code)


def git(args, cwd=None, check=True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        fail(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
        check=False,
    )
    if proc.returncode != 0:
        fail("not inside a git repository (implement-and-review worktree mode requires git)")
    return Path(proc.stdout.strip())


# --------------------------------------------------------------------------- #
# launch
# --------------------------------------------------------------------------- #

def worktree_exists(root: Path, path: Path) -> bool:
    out = git(["worktree", "list", "--porcelain"], cwd=root).stdout
    target = str(path.resolve())
    return any(line[len("worktree "):] == target for line in out.splitlines() if line.startswith("worktree "))


def branch_exists(root: Path, branch: str) -> bool:
    return git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root, check=False).returncode == 0


def create_worktree(root: Path, path: Path, branch: str, base: str, force: bool, dry_run: bool) -> None:
    if worktree_exists(root, path) or branch_exists(root, branch):
        if not force:
            fail(
                f"worktree {path} or branch {branch} already exists. "
                f"Re-run with a new --session-id, or pass --force to recreate."
            )
        if not dry_run:
            git(["worktree", "remove", "--force", str(path)], cwd=root, check=False)
            git(["branch", "-D", branch], cwd=root, check=False)
    if dry_run:
        err(f"[dry-run] git worktree add -b {branch} {path} {base}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    git(["worktree", "add", "-b", branch, str(path), base], cwd=root)


def fire_runner(name: str, argv: list, working_dir: Path, dry_run: bool) -> dict:
    """Run a runner with --background and return {job_id, job_dir, result_file}."""
    cmd = [sys.executable, str(runner_script(name)), *argv, "--background", "--json"]
    if dry_run:
        err(f"[dry-run] ({working_dir}) " + " ".join(shlex.quote(p) for p in cmd))
        return {"job_id": None, "job_dir": None, "result_file": None, "dry_run": True}
    proc = subprocess.run(cmd, cwd=str(working_dir), capture_output=True, text=True, check=False)
    out = (proc.stdout or "").strip()
    try:
        summary = json.loads(out)
        job_id = summary.get("job_id")
    except json.JSONDecodeError:
        summary = {}
        m = JOB_ID_RE.search(out)
        job_id = m.group(1) if m else None
    if not job_id:
        fail(
            f"could not start {name} implementer in {working_dir}. "
            f"stdout={out[:400]!r} stderr={(proc.stderr or '').strip()[:400]!r}"
        )
    return {
        "job_id": job_id,
        "job_dir": summary.get("job_dir"),
        "result_file": summary.get("result_file"),
        "pid": summary.get("pid"),
    }


def cmd_launch(args) -> int:
    root = repo_root()
    if not args.frontend and not args.backend:
        fail("both tracks disabled; enable at least one (omit --no-frontend/--no-backend)")
    if args.frontend and args.fe_seat == "codex" and args.fe_mode == "subagent":
        fail("--fe-mode subagent is only valid with --fe-seat opus")

    # validate briefs for active tracks
    fe_brief = Path(args.fe_brief).resolve() if args.fe_brief else None
    be_brief = Path(args.be_brief).resolve() if args.be_brief else None
    if args.frontend and (not fe_brief or not fe_brief.is_file()):
        fail("frontend track active but --fe-brief is missing or not a file")
    if args.backend and (not be_brief or not be_brief.is_file()):
        fail("backend track active but --be-brief is missing or not a file")

    # base + cleanliness
    base = args.base or git(["rev-parse", "HEAD"], cwd=root).stdout.strip()
    if not args.allow_dirty and git(["status", "--porcelain", "--untracked-files=no"], cwd=root).stdout.strip():
        fail("working tree has uncommitted (tracked) changes; commit/stash first or pass --allow-dirty")

    slice_id = args.slice
    artifact_dir = root / ".ai-workflow" / "impl-review" / args.session_id
    wt_base = Path(args.worktrees_dir).resolve() if args.worktrees_dir else (root.parent / ".worktrees" / f"impl-review-{args.session_id}")
    if slice_id:
        artifact_dir = artifact_dir / slice_id
        wt_base = wt_base / slice_id
    if not args.dry_run:
        artifact_dir.mkdir(parents=True, exist_ok=True)

    def branch_for(track: str) -> str:
        return f"impl/{slice_id}-{track}-{args.session_id}" if slice_id else f"impl/{track}-{args.session_id}"

    manifest = {
        "session_id": args.session_id,
        "slice": slice_id,
        "base": base,
        "repo_root": str(root),
        "worktrees_dir": str(wt_base),
        "artifact_dir": str(artifact_dir),
        "dry_run": args.dry_run,
        "tracks": {},
    }

    def setup_track(track: str, brief: Path, branch: str, wt_path: Path) -> dict:
        create_worktree(root, wt_path, branch, base, args.force, args.dry_run)
        brief_copy = artifact_dir / f"{track}-brief.md"
        if not args.dry_run:
            shutil.copyfile(brief, brief_copy)
        return {
            "active": True,
            "branch": branch,
            "worktree": str(wt_path),
            "brief": str(brief_copy),
            "working_dir": str(wt_path),
        }

    # backend first so a runner-mode frontend can build against settled contracts
    if args.backend:
        wt_be = wt_base / "backend"
        info = setup_track("backend", be_brief, branch_for("backend"), wt_be)
        info["runner"] = "codex"
        info["seat"] = "codex"
        info["mode"] = "runner"
        be_argv = [
            "--prompt-file", info["brief"],
            "--working-dir", str(wt_be),
            "--role", "implementer",
            "--effort", args.codex_effort,
            "--timeout", str(args.timeout),
            "--disable-fallback",
            "--metadata-json", json.dumps({"session": args.session_id, "slice": slice_id, "track": "backend", "phase": "implement"}),
        ]
        if args.be_model:
            be_argv += ["--model", args.be_model]
        if args.full_auto:
            be_argv += ["--full-auto"]
        info.update(fire_runner("codex", be_argv, wt_be, args.dry_run))
        manifest["tracks"]["backend"] = info

    if args.frontend:
        wt_fe = wt_base / "frontend"
        info = setup_track("frontend", fe_brief, branch_for("frontend"), wt_fe)
        fe_mode = args.fe_mode
        if fe_mode == "auto":
            fe_mode = "subagent" if args.fe_seat == "opus" else "runner"
        if args.fe_seat == "codex":
            info["runner"] = "codex"
            info["seat"] = "codex"
            info["mode"] = "runner"
            fe_argv = [
                "--prompt-file", info["brief"],
                "--working-dir", str(wt_fe),
                "--role", "implementer",
                "--effort", args.codex_effort,
                "--timeout", str(args.timeout),
                "--disable-fallback",
                "--metadata-json", json.dumps({"session": args.session_id, "slice": slice_id, "track": "frontend", "phase": "implement"}),
            ]
            if args.fe_model:
                fe_argv += ["--model", args.fe_model]
            if args.full_auto:
                fe_argv += ["--full-auto"]
            info.update(fire_runner("codex", fe_argv, wt_fe, args.dry_run))
        elif fe_mode == "runner":
            info["runner"] = "claude"
            info["seat"] = "opus"
            info["mode"] = "runner"
            fe_argv = [
                "--prompt-file", info["brief"],
                "--working-dir", str(wt_fe),
                "--model", args.fe_model or "opus",
                "--role", "implementer",
                "--allow-write",
                "--output-format", "json",
                "--timeout", str(args.timeout),
                "--disable-fallback",
                "--metadata-json", json.dumps({"session": args.session_id, "slice": slice_id, "track": "frontend", "phase": "implement"}),
            ]
            info.update(fire_runner("claude", fe_argv, wt_fe, args.dry_run))
        else:
            info["runner"] = "opus-subagent"
            info["seat"] = "opus"
            info["mode"] = "subagent"
            info["job_id"] = None
            info["pending"] = (
                f"Spawn a native Opus subagent (Agent, model='opus', write-enabled) that operates "
                f"only inside {wt_fe} using brief {info['brief']}; see references/runner-invocations.md."
            )
        manifest["tracks"]["frontend"] = info

    if not args.dry_run:
        (artifact_dir / "launch-manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# poll
# --------------------------------------------------------------------------- #

def load_manifest(args) -> dict:
    if args.manifest:
        path = Path(args.manifest)
    else:
        root = repo_root()
        path = root / ".ai-workflow" / "impl-review" / args.session_id
        if getattr(args, "slice", None):
            path = path / args.slice
        path = path / "launch-manifest.json"
    if not path.is_file():
        fail(f"manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def jobs_query(subcmd: str, job_id: str, working_dir: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(JOBS_CLI), subcmd, job_id, "--working-dir", working_dir, "--json"],
        capture_output=True, text=True,
        check=False,
    )
    try:
        return json.loads(proc.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {"status": "unknown", "raw": (proc.stdout or proc.stderr or "").strip()[:300]}


def poll_once(manifest: dict) -> dict:
    out = {"session_id": manifest.get("session_id"), "tracks": {}, "subagent_pending": []}
    terminal = True
    for track, info in manifest.get("tracks", {}).items():
        if not info.get("active"):
            continue
        if info.get("mode") == "subagent":
            out["tracks"][track] = {"mode": "subagent", "status": "orchestrator-managed", "worktree": info.get("worktree")}
            out["subagent_pending"].append(track)
            continue
        job_id = info.get("job_id")
        wd = info.get("working_dir") or info.get("worktree") or "."
        if not job_id:
            out["tracks"][track] = {"mode": info.get("mode"), "status": "not-started"}
            terminal = False
            continue
        status = jobs_query("status", job_id, wd).get("status", "unknown")
        entry = {"mode": "runner", "runner": info.get("runner"), "job_id": job_id, "working_dir": wd, "status": status}
        if status in ("completed", "failed"):
            res = jobs_query("result", job_id, wd)
            entry["success"] = res.get("success")
            entry["runner_session_id"] = res.get("session_id")
            entry["result_file"] = info.get("result_file")
        else:
            terminal = False
        out["tracks"][track] = entry
    out["all_terminal"] = terminal
    return out


def cmd_poll(args) -> int:
    manifest = load_manifest(args)
    deadline = time.time() + args.wait_timeout
    while True:
        snapshot = poll_once(manifest)
        if not args.wait or snapshot["all_terminal"] or time.time() >= deadline:
            print(json.dumps(snapshot, indent=2, ensure_ascii=False))
            # exit non-zero if any runner track failed
            failed = any(t.get("success") is False for t in snapshot["tracks"].values())
            return 1 if failed else 0
        err(f"[poll] waiting; not all terminal yet — sleeping {args.interval}s")
        time.sleep(args.interval)


# --------------------------------------------------------------------------- #
# cleanup
# --------------------------------------------------------------------------- #

def cmd_cleanup(args) -> int:
    manifest = load_manifest(args)
    root = Path(manifest["repo_root"])
    removed = []
    for info in manifest.get("tracks", {}).values():
        wt = info.get("worktree")
        if wt:
            if args.dry_run:
                err(f"[dry-run] git worktree remove {'--force ' if args.force else ''}{wt}")
            else:
                git(["worktree", "remove", *(["--force"] if args.force else []), wt], cwd=root, check=False)
            removed.append(wt)
        if args.delete_branches and info.get("branch"):
            if args.dry_run:
                err(f"[dry-run] git branch -D {info['branch']}")
            else:
                git(["branch", "-D", info["branch"]], cwd=root, check=False)
    if not args.dry_run:
        git(["worktree", "prune"], cwd=root, check=False)
    print(json.dumps({"success": True, "removed_worktrees": removed, "dry_run": args.dry_run}, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# cli
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="launch.py",
        description="Set up worktrees and fire the implement-and-review implementers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = p.add_subparsers(dest="command", required=True)

    L = sub.add_parser("launch", help="create worktrees and fire implementers")
    L.add_argument("--session-id", required=True, help="stable id; also names the artifact dir and branches")
    L.add_argument("--slice", default=None, help="slice id; namespaces worktrees/branches/artifacts so parallel slices don't collide")
    L.add_argument("--fe-brief", help="path to the frontend brief file (required if frontend active)")
    L.add_argument("--be-brief", help="path to the backend brief file (required if backend active)")
    L.add_argument("--no-frontend", dest="frontend", action="store_false", help="skip the frontend track")
    L.add_argument("--no-backend", dest="backend", action="store_false", help="skip the backend track")
    L.add_argument("--fe-seat", choices=("codex", "opus"), default="codex",
                   help="frontend implementer seat: codex for standard product UI (default), opus for visual or highly creative work")
    L.add_argument("--fe-mode", choices=("auto", "subagent", "runner"), default="auto",
                   help="frontend execution path: auto selects a Codex runner or native Opus subagent; runner forces the matching runner; subagent is Opus only")
    L.add_argument("--fe-model", default=None, help="optional model override for the selected frontend runner; defaults to the seat's roster model")
    L.add_argument("--be-model", default=None, help="optional backend model override; defaults to the Codex seat in shared/references/model-roster.md")
    L.add_argument("--codex-effort", default="high", help="Codex reasoning effort for the backend implement run")
    L.add_argument("--timeout", type=int, default=1800, help="per-implementer timeout in seconds")
    L.add_argument("--full-auto", action=argparse.BooleanOptionalAction, default=True,
                   help="run Codex backend with --full-auto (unattended write+exec); requires Phase 0 approval")
    L.add_argument("--base", default=None, help="base commit for the worktrees (default: HEAD)")
    L.add_argument("--worktrees-dir", default=None, help="override the worktree parent dir")
    L.add_argument("--allow-dirty", action="store_true", help="allow launching with a dirty working tree")
    L.add_argument("--force", action="store_true", help="recreate worktrees/branches if they already exist")
    L.add_argument("--dry-run", action="store_true", help="print the plan and manifest without doing anything")
    L.set_defaults(frontend=True, backend=True)

    P = sub.add_parser("poll", help="poll the implementer jobs to a consolidated status")
    P.add_argument("--session-id", help="session id (resolves the manifest under .ai-workflow/impl-review/)")
    P.add_argument("--slice", default=None, help="slice id (resolves the per-slice manifest)")
    P.add_argument("--manifest", help="explicit path to launch-manifest.json")
    P.add_argument("--wait", action="store_true", help="block until all runner jobs are terminal (or timeout)")
    P.add_argument("--interval", type=int, default=15, help="seconds between polls when --wait")
    P.add_argument("--wait-timeout", type=int, default=1800, help="max seconds to wait when --wait")

    C = sub.add_parser("cleanup", help="remove the session's worktrees (branches kept by default)")
    C.add_argument("--session-id", help="session id (resolves the manifest)")
    C.add_argument("--slice", default=None, help="slice id (resolves the per-slice manifest)")
    C.add_argument("--manifest", help="explicit path to launch-manifest.json")
    C.add_argument("--delete-branches", action="store_true", help="also delete the track branches")
    C.add_argument("--force", action="store_true", help="force-remove worktrees with changes")
    C.add_argument("--dry-run", action="store_true", help="print what would be removed")
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.command in ("poll", "cleanup") and not (args.session_id or args.manifest):
        fail("provide --session-id or --manifest")
    if args.command == "launch":
        return cmd_launch(args)
    if args.command == "poll":
        return cmd_poll(args)
    return cmd_cleanup(args)


if __name__ == "__main__":
    sys.exit(main())
