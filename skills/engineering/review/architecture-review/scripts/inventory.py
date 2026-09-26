#!/usr/bin/env python3
"""Collect bounded repository metadata. Never execute project code or read file contents."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

EXCLUDED_DIRS = {'.git','.hg','.svn','node_modules','vendor','.venv','venv','__pycache__',
                 '.next','.nuxt','dist','build','coverage','.cache','.terraform','target',
                 '.idea','.vscode','.aws','.ssh','secrets','credentials','dumps','backups'}
SENSITIVE_SUFFIXES = {'.pem','.key','.p12','.pfx','.jks','.keystore','.sqlite','.db','.dump','.bak'}
MANIFESTS = {'package.json','pnpm-workspace.yaml','pyproject.toml','requirements.txt','go.mod',
             'Cargo.toml','pom.xml','build.gradle','Gemfile','composer.json','mix.exs','pubspec.yaml'}
LOCKS = {'package-lock.json','pnpm-lock.yaml','yarn.lock','bun.lock','bun.lockb','uv.lock',
         'poetry.lock','go.sum','Cargo.lock','Gemfile.lock','composer.lock'}
DOCS = {'README.md','AGENTS.md','CLAUDE.md','ARCHITECTURE.md','CONTRIBUTING.md','SECURITY.md'}

def excluded(path: Path) -> bool:
    lower = [x.lower() for x in path.parts]
    if any(x in EXCLUDED_DIRS for x in lower[:-1]):
        return True
    name = path.name.lower()
    return (name.startswith('.env') or name in ('.npmrc','.pypirc','.netrc','id_rsa','id_ed25519')
            or any(x in name for x in ('credential','secret','token','private-key'))
            or path.suffix.lower() in SENSITIVE_SUFFIXES)

def git(repo: Path, *args: str) -> str:
    binary = shutil.which('git')
    if not binary:
        raise OSError('git not available')
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    result = subprocess.run([binary,'-c','core.fsmonitor=false','-C',str(repo),*args],
                            capture_output=True, timeout=30, check=True, env=env)
    return result.stdout.decode('utf-8', errors='replace')

def collect(repo: Path, max_files: int = 20000) -> dict:
    repo = repo.resolve(strict=True)
    if not repo.is_dir():
        raise ValueError('Repository must be a directory')
    revision = 'unknown'
    notes = ['Metadata only; not a code, dependency, performance or security analysis.',
             'File size is not complexity. Excluded/generated/unavailable content is not assessed.',
             'No repository code or file contents were read. No network request was made.']
    try:
        revision = git(repo,'rev-parse','--verify','HEAD').strip()
    except (OSError,subprocess.SubprocessError):
        pass
    discovery_truncated = False
    try:
        names = git(repo,'ls-files','-z','--cached','--others','--exclude-standard').split('\0')
        candidates = sorted(set(n for n in names if n))
        method = 'git tracked and non-ignored untracked paths'
    except (OSError,subprocess.SubprocessError):
        candidates=[]
        for root,dirs,files in os.walk(repo,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d.lower() not in EXCLUDED_DIRS and not (Path(root)/d).is_symlink())
            candidates.extend(str((Path(root)/f).relative_to(repo)) for f in sorted(files))
            if len(candidates)>max_files*4:
                discovery_truncated = True
                notes.append('Fallback discovery stopped at its safety limit.')
                break
        candidates=sorted(set(candidates))
        method='filesystem fallback with fixed exclusions'
        notes.append('Fallback does not interpret custom ignore patterns; review coverage manually.')
    records=[]
    skipped=Counter()
    for raw in candidates:
        rel=Path(raw)
        if rel.is_absolute() or '..' in rel.parts or excluded(rel):
            skipped['excluded']+=1;continue
        path=repo/rel
        # Check every component before following it. Still not a security sandbox.
        if any((repo/Path(*rel.parts[:i])).is_symlink() for i in range(1,len(rel.parts)+1)):
            skipped['symlink']+=1;continue
        try:
            resolved=path.resolve(strict=True)
            resolved.relative_to(repo)
            if not resolved.is_file():
                skipped['not_regular_file']+=1;continue
            size=resolved.stat().st_size
        except (OSError,ValueError):
            skipped['unavailable_or_outside_scope']+=1;continue
        if len(records)>=max_files:
            skipped['file_limit']+=1;continue
        name=rel.name
        categories=[]
        if name in MANIFESTS or rel.suffix in ('.csproj','.sln'):categories.append('manifest')
        if name in LOCKS:categories.append('lockfile')
        if name in DOCS:categories.append('documentation_or_instructions')
        if any(x in ('test','tests','__tests__','e2e') for x in rel.parts) or any(x in name for x in ('.test.','.spec.','_test.')):categories.append('test_candidate')
        if any(x.lower() in ('migrations','schema','schemas','prisma') for x in rel.parts):categories.append('data_candidate')
        if '.github/workflows' in rel.as_posix() or name in ('Dockerfile','compose.yaml','docker-compose.yml','Jenkinsfile') or rel.suffix=='.tf':categories.append('delivery_candidate')
        records.append(dict(path=rel.as_posix(),bytes=size,extension=rel.suffix.lower() or '(none)',categories=categories))
    return dict(schema_version='1.0',root_name=repo.name,revision=revision,method=method,
                discovered_paths=len(candidates),included_files=len(records),
                truncated=discovery_truncated or bool(skipped['file_limit']),skipped=dict(skipped),
                total_included_bytes=sum(x['bytes'] for x in records),
                extensions=dict(sorted(Counter(x['extension'] for x in records).items())),
                top_level=dict(sorted(Counter(x['path'].split('/')[0] if '/' in x['path'] else '(root)' for x in records).items())),
                limitations=notes,files=records)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('repository',type=Path)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--max-files',type=int,default=20000)
    args=ap.parse_args()
    try:
        if args.max_files<1:raise ValueError('--max-files must be positive')
        repo=args.repository.resolve(strict=True)
        out=args.out.resolve()
        if out==repo or repo in out.parents:
            raise ValueError('Output must be outside the repository')
        if out.exists():raise ValueError('Output exists; choose a new path')
        result=collect(repo,args.max_files)
        out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x',encoding='utf-8') as fh:
            json.dump(result,fh,ensure_ascii=False,indent=2);fh.write('\n')
        print(f'{out}: {result["included_files"]} files; metadata only')
        return 0
    except (OSError,ValueError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr);return 1
if __name__=='__main__':
    raise SystemExit(main())
