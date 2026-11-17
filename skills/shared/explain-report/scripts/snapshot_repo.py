#!/usr/bin/env python3
"""Collect revision and path evidence without changing Git or reading file text.

Examples:
  python snapshot_repo.py --repo . --snapshot-only --output /tmp/state.json
  python snapshot_repo.py --repo . --base main --head HEAD --output /tmp/change.json
  python snapshot_repo.py --repo . --base main --worktree --output /tmp/work.json
  python snapshot_repo.py --repo . --check /tmp/work.json

Output belongs outside the inspected repository, or in an already ignored path.
The JSON contains file names and hashes, never file contents or remote URLs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Any

SCHEMA_VERSION = 1
MAX_FILE_BYTES = 512 * 1024 * 1024


class SnapshotError(Exception):
    """An invalid, incomplete, or inconsistent capture."""


def _git(repo: Path, *args: str, allowed: tuple[int, ...] = (0,)) -> bytes:
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"):
        env.pop(key, None)
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_LITERAL_PATHSPECS="1", LC_ALL="C")
    if args[0] == "check-ignore":
        # check-ignore accepts literal filenames, not pathspec magic.
        env.pop("GIT_LITERAL_PATHSPECS", None)
    command = ["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
               "-c", "core.untrackedCache=false", "-C", str(repo), *args]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, check=False)
    except OSError as exc:
        raise SnapshotError("Could not execute Git") from exc
    if result.returncode not in allowed:
        # Git errors can contain configuration values, so do not echo stderr.
        raise SnapshotError(f"Git {args[0]} failed with exit {result.returncode}")
    return result.stdout


def _decode(value: bytes) -> str:
    return value.decode("utf-8", "surrogateescape")


def _repo_root(repo: str | Path) -> Path:
    path = Path(repo).expanduser().resolve()
    raw = _git(path, "rev-parse", "--show-toplevel")
    return Path(_decode(raw.removesuffix(b"\n"))).resolve()


def _resolve(repo: Path, ref: str) -> str:
    if not isinstance(ref, str) or not ref or len(ref) > 512 or ref.startswith("-") or any(c in ref for c in "\x00\r\n"):
        raise SnapshotError("Invalid revision; options and control characters are forbidden")
    raw = _git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")
    value = _decode(raw).strip()
    if len(value) not in (40, 64) or any(c not in "0123456789abcdef" for c in value):
        raise SnapshotError("Revision did not resolve to one full commit identifier")
    return value


def _status(repo: Path) -> list[dict[str, Any]]:
    parts = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none").split(b"\0")
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(parts) and parts[i]:
        entry = parts[i]
        i += 1
        if len(entry) < 4 or entry[2:3] != b" ":
            raise SnapshotError("Unexpected Git status record")
        code = _decode(entry[:2])
        item: dict[str, Any] = {"path": _decode(entry[3:]), "status": code,
                                "index_status": code[0], "worktree_status": code[1]}
        if "R" in code or "C" in code:
            if i >= len(parts) or not parts[i]:
                raise SnapshotError("Incomplete rename status")
            item["original_path"] = _decode(parts[i])
            i += 1
        result.append(item)
    return sorted(result, key=lambda item: item["path"])


def _changes(repo: Path, *revisions: str, cached: bool = False) -> list[dict[str, Any]]:
    args = ["diff", "--name-status", "-z", "--find-renames=50%", "--no-ext-diff", "--no-textconv", "--ignore-submodules=none"]
    if cached:
        args.append("--cached")
    parts = _git(repo, *args, *revisions, "--").split(b"\0")
    result: list[dict[str, Any]] = []
    i = 0
    while i < len(parts) and parts[i]:
        code = _decode(parts[i])
        i += 1
        count = 2 if code.startswith(("R", "C")) else 1
        if i + count > len(parts) or any(not p for p in parts[i:i + count]):
            raise SnapshotError("Incomplete Git diff path record")
        item: dict[str, Any] = {"status": code[0], "path": _decode(parts[i + count - 1])}
        if count == 2:
            item["original_path"] = _decode(parts[i])
            if code[1:].isdigit():
                item["similarity_percent"] = int(code[1:])
        i += count
        result.append(item)
    return sorted(result, key=lambda item: (item["path"], item["status"]))


def _paths(*collections: list[dict[str, Any]]) -> list[str]:
    return sorted({item[key] for collection in collections for item in collection
                   for key in ("path", "original_path") if key in item})


def _index(repo: Path, paths: list[str]) -> list[dict[str, Any]]:
    result = []
    # Bound command size and preserve literal file names, including newlines.
    batches: list[list[str]] = []
    batch: list[str] = []
    size = 0
    for path in paths:
        length = len(os.fsencode(path)) + 1
        if batch and size + length > 24000:
            batches.append(batch)
            batch, size = [], 0
        batch.append(path)
        size += length
    if batch:
        batches.append(batch)
    for batch in batches:
        for raw in _git(repo, "ls-files", "--stage", "-z", "--", *batch).split(b"\0"):
            if not raw:
                continue
            meta, path = raw.split(b"\t", 1)
            mode, oid, stage = meta.split(b" ")
            result.append({"path": _decode(path), "mode": _decode(mode),
                           "object_id": _decode(oid), "stage": int(stage)})
    return sorted(result, key=lambda item: (item["path"], item["stage"]))


def _hash_path(repo: Path, path: str) -> dict[str, Any]:
    """Use directory descriptors so symlinks cannot lead outside the repository."""
    parts = path.removesuffix("/").split("/")
    if not parts or any(part in ("", ".", "..") for part in parts) or os.path.isabs(path):
        raise SnapshotError("Git returned an unsafe relative path")
    record: dict[str, Any] = {"path": path}
    descriptors: list[int] = []
    try:
        dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent = os.open(repo, dir_flags)
        descriptors.append(parent)
        for part in parts[:-1]:
            parent = os.open(part, dir_flags, dir_fd=parent)
            descriptors.append(parent)
        name = parts[-1]
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if stat.S_ISLNK(before.st_mode):
            target = os.readlink(name, dir_fd=parent)
            record.update(kind="symlink", sha256=hashlib.sha256(os.fsencode(target)).hexdigest())
            after = os.stat(name, dir_fd=parent, follow_symlinks=False)
        elif stat.S_ISREG(before.st_mode):
            if before.st_size > MAX_FILE_BYTES:
                return dict(record, kind="unsupported", reason="File exceeds 512 MiB capture limit", size=before.st_size, mtime_ns=before.st_mtime_ns)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            descriptors.append(fd)
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise SnapshotError("A file changed type or identity during capture")
            digest = hashlib.sha256()
            total = 0
            binary_hint = False
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                if total == 0:
                    binary_hint = b"\0" in chunk[:8192]
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise SnapshotError("A file grew beyond the capture limit during capture")
                digest.update(chunk)
            after = os.fstat(fd)
            current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino):
                raise SnapshotError("A file was replaced during capture")
            record.update(kind="file", sha256=digest.hexdigest(), size=total,
                          executable=bool(before.st_mode & 0o111), binary_hint=binary_hint)
        elif stat.S_ISDIR(before.st_mode):
            return dict(record, kind="directory", reason="Directory or submodule contents are not recursively hashed")
        else:
            return dict(record, kind="unsupported", reason="Special filesystem entry is not read")
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise SnapshotError("A file changed during capture")
        return record
    except FileNotFoundError:
        return dict(record, kind="missing")
    except OSError:
        return dict(record, kind="unsupported", reason="Entry could not be read safely without following symlink directories")
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _capture_once(repo: Path, scope: dict[str, Any]) -> dict[str, Any]:
    checkout_head = _resolve(repo, "HEAD")
    head = _resolve(repo, scope["head_ref"])
    status = _status(repo)
    base = _resolve(repo, scope["base_ref"]) if scope["base_ref"] is not None else None
    comparison_base = base
    if scope["merge_base"]:
        candidates = _decode(_git(repo, "merge-base", "--all", base, head)).splitlines()
        if len(candidates) != 1:
            raise SnapshotError("Comparison needs exactly one merge base; choose an explicit base")
        comparison_base = candidates[0]
    untracked = sorted(_decode(part) for part in _git(repo, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0") if part)
    working = scope["mode"] in ("snapshot", "worktree")
    if scope["mode"] == "snapshot":
        changes = []
    elif working:
        changes = _changes(repo, comparison_base)
    else:
        changes = _changes(repo, comparison_base, head)
    index_changes = _changes(repo, checkout_head, cached=True) if working else []
    unstaged_changes = _changes(repo) if working else []
    untracked_changes = [{"status": "?", "path": path} for path in untracked]
    if scope["mode"] == "worktree":
        # A path may appear twice if it was deleted from the index then recreated.
        changes = sorted(changes + untracked_changes, key=lambda item: (item["path"], item["status"]))
    relevant = _paths(status, changes, index_changes, unstaged_changes, untracked_changes) if working else []
    index_entries = _index(repo, relevant) if working else []
    files = [_hash_path(repo, path) for path in relevant]
    unresolved = [entry["path"] for entry in index_entries if entry["stage"] != 0]
    complete = all(item["kind"] not in ("unsupported", "directory") for item in files) and not unresolved
    if checkout_head != _resolve(repo, "HEAD") or head != _resolve(repo, scope["head_ref"]) or status != _status(repo):
        raise SnapshotError("Repository changed while capturing evidence; retry when stable")
    if base is not None and base != _resolve(repo, scope["base_ref"]):
        raise SnapshotError("Base revision changed while capturing evidence")
    return {"scope": scope, "checkout_head": checkout_head, "head_revision": head,
            "base_revision": base, "comparison_base": comparison_base,
            "dirty": bool(status), "dirty_status": status, "untracked_paths": untracked,
            "changes": changes, "index_changes": index_changes,
            "unstaged_changes": unstaged_changes, "index_entries": index_entries,
            "working_files": files, "unresolved_paths": sorted(set(unresolved)),
            "capture_complete": complete}


def collect_snapshot(repo: str | Path, *, base: str | None = None, head: str = "HEAD",
                     snapshot_only: bool = False, worktree: bool = False,
                     merge_base: bool = False) -> dict[str, Any]:
    """Return a stable capture, or raise SnapshotError. No Git state is written."""
    if snapshot_only:
        if base is not None or worktree or merge_base or head != "HEAD":
            raise SnapshotError("Snapshot mode cannot be combined with comparison options")
    elif base is None:
        raise SnapshotError("An explicit base is required for a comparison")
    if worktree and head != "HEAD":
        raise SnapshotError("Working tree comparisons require head=HEAD")
    root = _repo_root(repo)
    scope = {"mode": "snapshot" if snapshot_only else "worktree" if worktree else "committed",
             "base_ref": base, "head_ref": head, "merge_base": merge_base}
    before = _capture_once(root, scope)
    after = _capture_once(root, scope)
    if _fingerprint(before) != _fingerprint(after):
        raise SnapshotError("Comparison or working files changed during repeated capture; retry when stable")
    limitations = [
        "Ignored paths are excluded. Git status may omit files marked assume unchanged or skip worktree.",
        "Binary contents have no semantic analysis; the binary hint only checks the first 8192 bytes.",
        "Submodule contents are not recursively captured. Inspect changed submodules separately.",
        "This is a repeated consistency check, not an atomic filesystem snapshot.",
        "File names and content hashes are evidence, not a secret scan or correctness proof.",
    ]
    if scope["mode"] == "committed":
        limitations.append("Working file contents and index contents are excluded from this committed comparison; dirty status is context only.")
    if not after["capture_complete"]:
        limitations.append("Some relevant entries could not be fully captured; a matching fingerprint cannot establish freshness for those entries.")
    return {"schema_version": SCHEMA_VERSION, "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "repo_root": str(root), **after, "fingerprint": _fingerprint(after),
            "limitations": limitations}


def check_snapshot(repo: str | Path, stored: dict[str, Any]) -> dict[str, Any]:
    if stored.get("schema_version") != SCHEMA_VERSION or not isinstance(stored.get("scope"), dict):
        raise SnapshotError("Unsupported snapshot schema")
    scope = stored["scope"]
    mode = scope.get("mode")
    if mode not in ("snapshot", "worktree", "committed"):
        raise SnapshotError("Invalid stored comparison scope")
    current = collect_snapshot(repo, base=scope.get("base_ref"), head=scope.get("head_ref", "HEAD"),
                               snapshot_only=mode == "snapshot", worktree=mode == "worktree",
                               merge_base=bool(scope.get("merge_base", False)))
    stale = stored.get("fingerprint") != current["fingerprint"]
    complete = bool(stored.get("capture_complete")) and current["capture_complete"]
    return {"schema_version": SCHEMA_VERSION, "checked_at": current["captured_at"],
            "status": "stale" if stale else "current" if complete else "inconclusive",
            "stale": stale, "capture_complete": complete, "scope": current["scope"],
            "expected_fingerprint": stored.get("fingerprint"),
            "current_fingerprint": current["fingerprint"],
            "checkout_head": current["checkout_head"], "limitations": current["limitations"]}


def _write_output(repo: Path, output: str, payload: dict[str, Any]) -> None:
    target = Path(output).expanduser().resolve()
    try:
        relative = target.relative_to(repo).as_posix()
    except ValueError:
        relative = None
    if relative is not None:
        ignored = _git(repo, "check-ignore", "--", relative, allowed=(0, 1))
        if not ignored:
            raise SnapshotError("Output inside the inspected repository must already be ignored; choose an external output path")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot-only", action="store_true")
    mode.add_argument("--base")
    mode.add_argument("--check", metavar="SNAPSHOT_JSON")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--worktree", action="store_true")
    parser.add_argument("--merge-base", action="store_true")
    args = parser.parse_args(argv)
    if not args.check and not args.output:
        parser.error("--output is required when collecting a snapshot")
    if args.check and (args.head != "HEAD" or args.worktree or args.merge_base):
        parser.error("--check uses the scope stored in the snapshot")
    try:
        if args.check:
            stored = json.loads(Path(args.check).read_text(encoding="utf-8"))
            payload = check_snapshot(args.repo, stored)
            exit_code = 1 if payload["stale"] else 0 if payload["capture_complete"] else 2
        else:
            payload = collect_snapshot(args.repo, base=args.base, head=args.head,
                                       snapshot_only=args.snapshot_only, worktree=args.worktree,
                                       merge_base=args.merge_base)
            exit_code = 0 if payload["capture_complete"] else 2
        if args.output:
            _write_output(_repo_root(args.repo), args.output, payload)
        else:
            print(json.dumps(payload, indent=2, ensure_ascii=True))
        return exit_code
    except (SnapshotError, OSError, ValueError, TypeError, KeyError) as exc:
        # Do not echo arbitrary file or Git content in an error.
        message = str(exc) if isinstance(exc, SnapshotError) else "Could not read or write the snapshot JSON"
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
