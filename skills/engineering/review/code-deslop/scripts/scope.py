#!/usr/bin/env python3
"""Describe a Git cleanup scope; emit paths and metadata without source text or index writes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from typing import Any

EXCLUDED_DIRS = frozenset({
    ".git", "node_modules", "vendor", "dist", "build", "coverage", "__pycache__",
    ".venv", "venv", ".next", ".nuxt", ".cache", ".terraform", "target",
    ".agents", ".claude", ".desloppify",
})
LOCKFILES = frozenset({
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml",
    "bun.lock", "bun.lockb", "poetry.lock", "uv.lock", "Pipfile.lock", "Cargo.lock",
    "composer.lock", "Gemfile.lock", "go.sum",
})
BINARY_SUFFIXES = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".exe", ".dll", ".so", ".pyc",
})
SECRET_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".keystore"})


def git(repo: Path, *args: str, allowed_codes: tuple[int, ...] = (0,),
        overrides: dict[str, str] | None = None) -> bytes:
    """Use argument arrays and disable external diff, pager and fsmonitor hooks."""
    env = os.environ.copy()
    for name in tuple(env):
        if name in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT"} or name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(name, None)
    for index, (key, value) in enumerate((overrides or {}).items()):
        env[f"GIT_CONFIG_KEY_{index}"] = key
        env[f"GIT_CONFIG_VALUE_{index}"] = value
    env["GIT_CONFIG_COUNT"] = str(len(overrides or {}))
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_PAGER": "cat", "LC_ALL": "C"})
    command = [
        "git", "--no-pager", "--no-optional-locks", "-c", "core.fsmonitor=false",
        "-c", "core.untrackedCache=false", "-C", str(repo), *args,
    ]
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env=env, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Cannot inspect Git metadata: {exc}") from exc
    if result.returncode not in allowed_codes:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"Git inspection failed: {message or result.returncode}")
    return result.stdout if result.returncode == 0 else b""


def names(data: bytes) -> set[str]:
    return {os.fsdecode(item) for item in data.split(b"\0") if item}


def prefix(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not value:
        raise ValueError(f"Use a literal repository-relative path without '..': {value!r}")
    return str(path)


def under(path: str, selected: str) -> bool:
    return selected == "." or path == selected or path.startswith(selected + "/")


def exclusion(root: Path, path: str, index_mode: str | None) -> str | None:
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else ""
    suffix = PurePosixPath(path).suffix.lower()
    if any(part in EXCLUDED_DIRS for part in parts[:-1]):
        return "excluded directory (path heuristic)"
    if name.startswith(".env") or suffix in SECRET_SUFFIXES or name in {
        "id_rsa", "id_ed25519", "credentials.json", ".npmrc", ".pypirc", ".netrc"
    }:
        return "potential secret or credential file"
    if name in LOCKFILES:
        return "lockfile; no hand editing"
    if suffix in BINARY_SUFFIXES:
        return "binary/document asset (extension heuristic)"
    if name.endswith((".min.js", ".min.css", ".map", ".generated.ts", ".pb.go")):
        return "generated output (name heuristic)"
    if index_mode == "160000":
        return "submodule"
    if index_mode == "120000":
        return "tracked symlink"
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            return "symlink or symlink ancestor"
    try:
        info = (root / path).lstat()
    except FileNotFoundError:
        return "deleted or absent; inspect diff only"
    if not stat.S_ISREG(info.st_mode):
        return "not a regular file"
    return None


def collect(repo: Path, scope: str = "changed", base: str | None = None,
            paths: list[str] | None = None) -> dict[str, Any]:
    if scope not in {"changed", "branch", "repo"}:
        raise ValueError("scope must be changed, branch, or repo")
    if (scope == "branch") != bool(base):
        raise ValueError("--base is required for branch scope and is invalid for other scopes")
    selected = [prefix(item) for item in (paths or [])]
    repo = repo.expanduser().resolve(strict=True)
    root_bytes = git(repo, "rev-parse", "--show-toplevel").removesuffix(b"\n")
    root = Path(os.fsdecode(root_bytes)).resolve(strict=True)
    head = git(root, "rev-parse", "--verify", "--quiet", "HEAD", allowed_codes=(0, 1)).decode().strip() or None
    filter_names = names(git(root, "config", "--includes", "--null", "--name-only",
                            "--get-regexp", r"^filter\..*\.(clean|smudge|process|required)$",
                            allowed_codes=(0, 1)))
    filters = {key: "false" if key.rsplit(".", 1)[-1] == "required" else ""
               for key in sorted(filter_names)}
    modes: dict[str, str] = {}
    conflicts: set[str] = set()
    for item in git(root, "ls-files", "--stage", "-z").split(b"\0"):
        if not item:
            continue
        metadata, filename = item.split(b"\t", 1)
        mode, _object, stage = metadata.split(b" ", 2)
        path = os.fsdecode(filename)
        modes[path] = mode.decode("ascii")
        if stage != b"0":
            conflicts.add(path)
    diff = ("diff", "--no-ext-diff", "--no-textconv", "--no-renames",
            "--ignore-submodules=all", "--name-only", "-z")
    changes = {
        "staged": names(git(root, *diff, "--cached", "--", overrides=filters)),
        "unstaged": names(git(root, *diff, "--", overrides=filters)),
        "untracked": names(git(root, "ls-files", "--others", "--exclude-standard", "-z")),
    }
    base_commit = merge_base = None
    if scope == "branch":
        if not head:
            raise ValueError("Branch scope requires a committed HEAD")
        base_commit = git(root, "rev-parse", "--verify", "--end-of-options",
                          str(base) + "^{commit}").decode().strip()
        ancestors = git(root, "merge-base", "--all", head, base_commit).decode().splitlines()
        if len(ancestors) != 1:
            raise ValueError("A unique merge base is required; inspect history before continuing")
        merge_base = ancestors[0]
        changes["branch"] = names(git(root, *diff, merge_base, head, "--", overrides=filters))
    candidates = set().union(*changes.values())
    if scope == "repo":
        candidates |= set(modes)
    for item in selected:
        if not any(under(path, item) for path in candidates):
            raise ValueError(f"No files in the selected scope match literal path {item!r}")
    if selected:
        candidates = {path for path in candidates if any(under(path, item) for item in selected)}
    entries = []
    for path in sorted(candidates):
        reason = exclusion(root, path, modes.get(path))
        entries.append({"path": path, "changes": sorted(k for k, v in changes.items() if path in v),
                        "index_mode": modes.get(path), "eligible": reason is None,
                        "exclusion": reason})
    warnings = [
        "Eligibility is path-based triage, not proof that a file is safe to read or edit.",
        "Generated headers, binary contents, secrets and runtime entry points are not inspected.",
        "This manifest is not a backup and does not capture original source contents.",
        "Git content filters are disabled during inspection; filter-dependent files may appear changed.",
    ]
    if not head:
        warnings.append("Unborn branch: there is no committed baseline.")
    if not entries:
        warnings.append("No files in scope. Do not expand scope automatically.")
    return {
        "schema_version": "1.0", "repository": str(root), "scope": scope,
        "path_filters": selected, "head": head, "base_ref": base,
        "base_commit": base_commit, "merge_base": merge_base,
        "blocked": bool(conflicts), "conflicts": sorted(conflicts),
        "files": entries, "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--scope", choices=("changed", "branch", "repo"), default="changed")
    parser.add_argument("--base", help="Existing local base ref, required for branch scope; never fetched")
    parser.add_argument("--path", action="append", default=[], help="Literal repo-relative file/directory filter")
    args = parser.parse_args()
    try:
        result = collect(args.repo, args.scope, args.base, args.path)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"scope: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 2 if result["blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
