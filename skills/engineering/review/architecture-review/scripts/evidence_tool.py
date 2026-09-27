#!/usr/bin/env python3
"""Assemble worker evidence into the audit's evidence register.

Workers return observed facts as JSON lines (one record per line) using their own local IDs.
The coordinator assembles them here: this assigns stable E-numbered IDs, rewrites `supports`
references, removes exact duplicates, and checks every cited file and line range against the
audited checkout. It never judges a finding; it only makes evidence cheap and checkable.

Worker record fields: local_id, kind, location, line_start, line_end, observation, and
optionally revision, environment, command, artifact, excerpt, supports (local IDs).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

KINDS = {'code', 'config', 'documentation', 'measurement', 'user_input', 'inference', 'hypothesis'}


def load(paths: list[Path]) -> list[dict]:
    records = []
    for path in paths:
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f'{path}:{number}: invalid JSON ({exc.msg})') from exc
            item['_origin'] = f'{path.name}:{number}'
            records.append(item)
    return records


def check_lines(record: dict, repo: Path | None) -> list[str]:
    problems = []
    start, end = record.get('line_start'), record.get('line_end')
    if record['kind'] in ('code', 'config') and start is None:
        problems.append('code/config evidence needs line numbers')
    if (start is None) != (end is None) or (start is not None and end < start):
        problems.append('invalid line range')
    if record['kind'] == 'measurement' and not record.get('command'):
        problems.append('measurement needs the exact command')
    if repo is None or start is None or record.get('ref_differs'):
        return problems
    path = (repo / record['location']).resolve()
    if repo not in path.parents or path.is_symlink() or not path.is_file():
        return problems + [f'file not found: {record["location"]}']
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    if end > len(lines):
        return problems + [f'lines {start}-{end} exceed {len(lines)}']
    if record.get('excerpt'):
        window = ' '.join(' '.join(lines[start - 1:end]).split())
        if ' '.join(record['excerpt'].split()) not in window:
            problems.append('excerpt not found in the cited lines')
    return problems


def assemble(records: list[dict], repo: Path | None, revision: str, environment: str,
             captured_at: str, prefix: str, start: int) -> tuple[list[dict], dict, list[str]]:
    errors, id_map, seen, evidence = [], {}, {}, []
    counter = start
    for r in records:
        where = f"{r.get('_origin')} ({r.get('local_id', '?')})"
        missing = [k for k in ('local_id', 'kind', 'location', 'observation') if not r.get(k)]
        if missing:
            errors.append(f'{where}: missing {", ".join(missing)}'); continue
        if r['kind'] not in KINDS:
            errors.append(f'{where}: kind must be one of {sorted(KINDS)}'); continue
        if r['local_id'] in id_map:
            errors.append(f'{where}: duplicate local_id'); continue
        key = (r['kind'], r['location'], r.get('line_start'), r.get('line_end'), ' '.join(r['observation'].split()))
        if key in seen:
            id_map[r['local_id']] = seen[key]; continue
        problems = check_lines(r, repo)
        errors += [f'{where}: {p}' for p in problems]
        eid = f'{prefix}{counter:03d}'; counter += 1
        seen[key] = eid; id_map[r['local_id']] = eid
        record = dict(id=eid, kind=r['kind'], location=r['location'],
                      revision=r.get('revision') or revision, line_start=r.get('line_start'),
                      line_end=r.get('line_end'), observation=r['observation'],
                      captured_at=r.get('captured_at') or captured_at,
                      environment=r.get('environment') or environment,
                      command=r.get('command'), artifact=r.get('artifact'),
                      supports=list(r.get('supports') or []))
        if r.get('excerpt'):
            record['excerpt'] = r['excerpt']
        evidence.append(record)
    for e in evidence:
        mapped = []
        for local in e['supports']:
            if local not in id_map:
                errors.append(f'{e["id"]}: supports unknown local id {local}')
            else:
                mapped.append(id_map[local])
        e['supports'] = sorted(set(mapped) - {e['id']})
    return evidence, id_map, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('assemble', help='turn worker JSONL into evidence records')
    p.add_argument('inputs', nargs='+', type=Path)
    p.add_argument('--out', type=Path, required=True, help='JSON with evidence and id_map (outside the repository)')
    p.add_argument('--repo', type=Path, help='checkout of the audited revision, to check files and lines')
    p.add_argument('--revision', required=True, help='default revision label, e.g. "abc1234 plus working tree"')
    p.add_argument('--environment', default='Local read-only checkout; no project code executed')
    p.add_argument('--captured-at', required=True)
    p.add_argument('--prefix', default='E'); p.add_argument('--start', type=int, default=1)
    args = ap.parse_args()
    try:
        repo = args.repo.resolve(strict=True) if args.repo else None
        out = args.out.resolve()
        if repo and (out == repo or repo in out.parents):
            raise ValueError('Output must be outside the repository')
        evidence, id_map, errors = assemble(load(args.inputs), repo, args.revision, args.environment,
                                            args.captured_at, args.prefix, args.start)
        with out.open('x', encoding='utf-8') as fh:
            json.dump(dict(evidence=evidence, id_map=id_map, errors=errors), fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        print(f'{out}: {len(evidence)} evidence records, {len(id_map)} worker ids mapped, {len(errors)} problems')
        for e in errors:
            print('PROBLEM', e, file=sys.stderr)
        return 1 if errors else 0
    except (OSError, ValueError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
