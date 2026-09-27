#!/usr/bin/env python3
"""Report which revision an audit is about to read, before any source is inspected.

Read-only: never fetches, checks out, stashes, or writes inside the repository. It compares
HEAD with its upstream as last fetched, counts uncommitted files, and can export a newer ref
with `git archive` into a directory outside the repository so findings can be rechecked there.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from inventory import git


def safe(repo: Path, *args: str) -> str | None:
    try:
        return git(repo, *args).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def check(repo: Path) -> dict:
    repo = repo.resolve(strict=True)
    head = safe(repo, 'rev-parse', '--verify', 'HEAD')
    if head is None:
        raise ValueError('Not a git repository with a commit; record the revision manually')
    branch = safe(repo, 'rev-parse', '--abbrev-ref', 'HEAD')
    upstream = safe(repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    ahead = behind = None
    if upstream:
        counts = safe(repo, 'rev-list', '--left-right', '--count', f'HEAD...{upstream}')
        if counts:
            ahead, behind = (int(x) for x in counts.split())
    status = safe(repo, 'status', '--porcelain', '--untracked-files=normal') or ''
    dirty = [line[3:] for line in status.splitlines() if line.strip()]
    common = safe(repo, 'rev-parse', '--git-common-dir') or '.git'
    fetch_head = (repo / common) / 'FETCH_HEAD'
    last_fetch = None
    if fetch_head.is_file():
        last_fetch = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(fetch_head.stat().st_mtime))
    upstream_head = safe(repo, 'rev-parse', '--verify', upstream) if upstream else None
    advice = []
    if behind:
        advice.append(f'HEAD is {behind} commits behind {upstream} as of the last fetch. Ask whether to audit '
                      f'{upstream} instead, or audit HEAD and recheck every finding on {upstream} '
                      '(record newer_ref_status).')
    if dirty:
        advice.append(f'{len(dirty)} uncommitted or untracked files: mark evidence from them as working-tree state.')
    if upstream and last_fetch is None:
        advice.append('No FETCH_HEAD found: the upstream comparison may be stale; do not fetch without permission.')
    if not advice:
        advice.append('HEAD matches its upstream as last fetched and the tree is clean.')
    return dict(schema_version='1.0', head=head, branch=branch, upstream=upstream,
                upstream_head=upstream_head, ahead=ahead, behind=behind,
                dirty_files=len(dirty), dirty_paths=dirty[:200], last_fetch=last_fetch,
                advice=advice,
                limitations=['No fetch was performed; the upstream reflects the last local fetch.',
                             'This check describes git state only; it does not read or judge code.'])


def export(repo: Path, ref: str, out: Path) -> dict:
    """Extract `ref` with git archive into `out`, refusing paths inside the repository."""
    repo = repo.resolve(strict=True)
    out = out.resolve()
    if out == repo or repo in out.parents:
        raise ValueError('Export directory must be outside the repository')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Export directory exists and is not empty; choose a new path')
    sha = safe(repo, 'rev-parse', '--verify', ref)
    if sha is None:
        raise ValueError(f'Unknown ref: {ref}')
    binary = ['git', '-C', str(repo), 'archive', '--format=tar', sha]
    data = subprocess.run(binary, capture_output=True, check=True, timeout=300).stdout
    out.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            target = (out / member.name).resolve()
            if out not in target.parents and target != out:
                raise ValueError(f'Refusing archive member outside the export: {member.name}')
            if member.issym() or member.islnk():
                continue
            tar.extract(member, out)
            count += member.isfile()
    return dict(ref=ref, sha=sha, directory=str(out), files=count)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('repository', type=Path)
    ap.add_argument('--out', type=Path, help='write the JSON result here (outside the repository)')
    ap.add_argument('--export-ref', help='also export this ref (for example the upstream) with git archive')
    ap.add_argument('--export-dir', type=Path, help='empty directory outside the repository for --export-ref')
    args = ap.parse_args()
    try:
        result = check(args.repository)
        if args.export_ref:
            if not args.export_dir:
                raise ValueError('--export-ref requires --export-dir')
            result['export'] = export(args.repository, args.export_ref, args.export_dir)
        text = json.dumps(result, indent=2, ensure_ascii=False) + '\n'
        if args.out:
            out = args.out.resolve()
            repo = args.repository.resolve()
            if out == repo or repo in out.parents:
                raise ValueError('Output must be outside the repository')
            with out.open('x', encoding='utf-8') as fh:
                fh.write(text)
        sys.stdout.write(text)
        return 0
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
