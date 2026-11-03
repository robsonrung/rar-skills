#!/usr/bin/env python3
"""Check an architecture-review review.json against the report's structural contract.

Usage: python3 validate_review.py <review.json> [--repo <checkout>]

Prints one failure per line and exits 0 only when there are none. It checks structure, not judgment:
it cannot tell whether a finding is right, only that it is complete and cited. render_review.py runs
the same checks before it writes the page.

  --repo  also confirm every code/config path:line cites an existing file and lines in range
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DIMENSIONS = json.loads((Path(__file__).resolve().parent.parent / 'assets' / 'dimensions.json').read_text())
TITLES = {d['id']: d['title'] for d in DIMENSIONS}
STATUSES = ('adequate', 'attention', 'critical', 'unknown', 'not_applicable')
CONFIDENCE = ('high', 'medium', 'low', 'unknown')
PRIORITIES = ('P0', 'P1', 'P2', 'P3')
EVIDENCE_KINDS = ('code', 'config', 'documentation', 'measurement', 'user_input', 'inference', 'hypothesis')
CHECK_STATUSES = ('pass', 'fail', 'not_run', 'blocked', 'not_applicable')
OPTION_KINDS = ('keep', 'incremental', 'structural')
OPTION_POSITIONS = ('recommended', 'conditional', 'rejected')
FINDING_PARTS = ('title', 'summary', 'decision', 'observation', 'impact', 'recommendation', 'when_not',
                 'acceptance', 'rollback')
LOCATION = re.compile(r'^(?P<path>[^\s:]+):(?P<start>\d+)(?:-(?P<end>\d+))?$')
FINDING_ID, EVIDENCE_ID = re.compile(r'^F\d+$'), re.compile(r'^E\d{3,}$')

# The review.json schema. A key ending in '?' is optional; [x] is a list of x.
S = str
SHAPE = {
    'system': S, 'lang?': S, 'subtitle': S, 'footer': S,
    'verdict': {'lede': S, 'decisions': [S], 'top': [S]},
    'context': {'lede': S, 'revision': S, 'coverage': S, 'exclusions': S, 'assumptions': [S],
                'scenarios': [{'stimulus': S, 'response': S, 'origin': S, 'observed': S}]},
    'architecture': {'lede': S, 'flows': [{'name': S, 'steps': [S]}],
                     'diagrams': [{'label': S, 'nodes': [{'id': S, 'label': S, 'col': int, 'row': int,
                                                          'finding?': S, 'proposed?': bool}],
                                   'edges': [{'from': S, 'to': S, 'proposed?': bool}]}]},
    'dimensions': {'lede': S, 'rows': [{'id': S, 'status': S, 'confidence': S, 'note': S, 'evidence': [S]}]},
    'findings': {'lede': S, 'items': [{'id': S, 'priority': S, 'confidence': S, 'dimension': S, 'anchor': S,
                                       'alternatives?': S, 'evidence': [S], **dict.fromkeys(FINDING_PARTS, S)}]},
    'strengths': {'items': [{'text': S, 'evidence': [S]}], 'respected': [S]},
    'options': {'lede': S, 'target': S, 'items': [{'title': S, 'kind': S, 'position': S, 'text': S}]},
    'roadmap': {'steps': [{'text': S, 'first_move?': bool, 'findings?': [S]}]},
    'evidence': {'lede': S, 'records': [{'id': S, 'kind': S, 'observation': S, 'locations?': [S], 'command?': S,
                                         'source?': S}],
                 'checks': [{'procedure': S, 'status': S, 'result': S, 'challenge?': bool}],
                 'glossary': [{'term': S, 'definition': S}]},
}


def shape_problems(value, spec, path='review') -> list[str]:
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            return [f'{path}: expected an object']
        out = [f'{path}.{k}: unknown key' for k in value if k not in spec and f'{k}?' not in spec]
        for key, sub in spec.items():
            name = key.rstrip('?')
            if name in value:
                out += shape_problems(value[name], sub, f'{path}.{name}')
            elif not key.endswith('?'):
                out.append(f'{path}.{name}: missing')
        return out
    if isinstance(spec, list):
        if not isinstance(value, list):
            return [f'{path}: expected a list']
        return [p for i, v in enumerate(value) for p in shape_problems(v, spec[0], f'{path}[{i}]')]
    ok = isinstance(value, spec) and not (spec is int and isinstance(value, bool))
    return [] if ok else [f'{path}: expected {spec.__name__}']


def validate(review: dict, repo: Path | None = None) -> list[str]:
    found = shape_problems(review, SHAPE)
    if found:
        return found

    def check(ok, message):
        if not ok:
            found.append(message)

    rows = review['dimensions']['rows']
    findings = review['findings']['items']
    records = review['evidence']['records']
    evidence = {r['id'] for r in records}
    finding_ids = {f['id'] for f in findings}
    check(re.fullmatch(r'[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*', review.get('lang', 'en')), 'lang: not a language tag')

    def cites(where, refs, required=True):
        check(refs or not required, f'{where}: cite at least one evidence record')
        check(set(refs) <= evidence, f'{where}: unknown evidence {sorted(set(refs) - evidence)}')

    # Evidence register
    check(records, 'evidence.records: empty')
    check(len(evidence) == len(records), 'evidence.records: ids repeat')
    for r in records:
        rid, kind, locs = r['id'], r['kind'], r.get('locations', [])
        check(EVIDENCE_ID.match(rid), f'{rid}: use E001, E002, ...')
        check(kind in EVIDENCE_KINDS, f'{rid}: kind {kind!r} not in {EVIDENCE_KINDS}')
        if kind in ('code', 'config'):
            check(locs and all(LOCATION.match(x) for x in locs), f'{rid}: cite path:line or path:start-end')
            for loc in locs if repo is not None else ():
                ok, why = cited_lines_exist(repo, loc)
                check(ok, f'{rid}: {loc} at --repo: {why}')
        if kind == 'measurement':
            check(r.get('command', '').strip(), f'{rid}: a measurement records its exact command')

    # Dimensions
    check([r['id'] for r in rows] == list(TITLES), 'dimensions.rows: need D01-D20 once each, in order')
    for r in rows:
        did, status, conf = r['id'], r['status'], r['confidence']
        check(status in STATUSES, f'{did}: status {status!r} not in {STATUSES}')
        check(conf in CONFIDENCE, f'{did}: confidence {conf!r} not in {CONFIDENCE}')
        check(not (status == 'unknown' and conf == 'high'), f'{did}: unknown cannot carry high confidence')
        cites(did, r['evidence'], required=status in ('adequate', 'attention', 'critical'))
        check(r['note'].strip(), f'{did}: give the assessment or the reason')

    # Findings
    check(len(finding_ids) == len(findings), 'findings.items: ids repeat')
    for f in findings:
        fid, pri, conf = f['id'], f['priority'], f['confidence']
        check(FINDING_ID.match(fid), f'{fid}: use F01, F02, ...')
        check(pri in PRIORITIES, f'{fid}: priority {pri!r} not in {PRIORITIES}')
        check(conf in CONFIDENCE, f'{fid}: confidence {conf!r} not in {CONFIDENCE}')
        check(f['dimension'] in TITLES, f'{fid}: dimension {f["dimension"]!r} is not D01-D20')
        check(not (pri in ('P0', 'P1') and conf not in ('high', 'medium')), f'{fid}: P0/P1 needs high or medium confidence')
        missing = [p for p in FINDING_PARTS if not f[p].strip()]
        check(not missing, f'{fid}: empty {missing}')
        cites(fid, f['evidence'])
        anchor = f['anchor'].strip().lower()
        check(anchor, f'{fid}: name the decision anchor')
        check(anchor in f['decision'].lower(), f'{fid}: anchor {anchor!r} missing from the decision')
        check(anchor in (f['recommendation'] + ' ' + f['acceptance']).lower(),
              f'{fid}: anchor {anchor!r} missing from the recommendation and the acceptance')
    for r in rows:
        if r['status'] == 'critical':
            check(any(f['dimension'] == r['id'] and f['priority'] in ('P0', 'P1') for f in findings),
                  f'{r["id"]}: a critical dimension needs a P0/P1 finding')
    for s in review['strengths']['items']:
        cites('strength', s['evidence'])

    # Architecture
    diagrams = review['architecture']['diagrams']
    check(any(d['nodes'] for d in diagrams), 'architecture.diagrams: draw at least one diagram')
    for d in diagrams:
        names = {n['id'] for n in d['nodes']}
        check(all(0 <= n[k] <= 12 for n in d['nodes'] for k in ('col', 'row')), f'{d["label"]}: col and row run 0-12')
        check(all(e['from'] in names and e['to'] in names for e in d['edges']), f'{d["label"]}: an edge names no node')
        linked = {n['finding'] for n in d['nodes'] if 'finding' in n}
        check(linked <= finding_ids, f'{d["label"]}: unknown findings {sorted(linked - finding_ids)}')

    # Verdict, options, roadmap, verification
    top = set(review['verdict']['top'])
    check(top <= finding_ids, f'verdict.top: unknown findings {sorted(top - finding_ids)}')
    options = review['options']['items']
    check(all(o['kind'] in OPTION_KINDS and o['position'] in OPTION_POSITIONS for o in options),
          f'options: kind in {OPTION_KINDS}, position in {OPTION_POSITIONS}')
    check(any(o['kind'] == 'keep' for o in options), 'options: keeping the current architecture must be an option')
    check(sum(o['position'] == 'recommended' for o in options) <= 1, 'options: at most one recommended')
    steps = review['roadmap']['steps']
    check(sum(s.get('first_move', False) for s in steps) <= 3, 'roadmap: at most three first moves')
    refs = {x for s in steps for x in s.get('findings', [])}
    check(refs <= finding_ids, f'roadmap: unknown findings {sorted(refs - finding_ids)}')
    checks = review['evidence']['checks']
    check(checks, 'evidence.checks: record the verification procedures')
    check(all(c['status'] in CHECK_STATUSES for c in checks), f'evidence.checks: status in {CHECK_STATUSES}')
    if any(f['priority'] in ('P0', 'P1') for f in findings):
        check(any(c.get('challenge') for c in checks), 'evidence.checks: record the challenge pass for P0/P1 findings')
    return found


def cited_lines_exist(repo: Path, loc: str) -> tuple[bool, str]:
    m = LOCATION.match(loc)
    if not m:
        return False, 'not path:line'
    rel = Path(m.group('path'))
    if rel.is_absolute() or '..' in rel.parts:
        return False, 'path must be relative to the repository'
    path = repo / rel
    if not path.is_file():
        return False, 'file not found'
    start, end = int(m.group('start')), int(m.group('end') or m.group('start'))
    lines = len(path.read_text(encoding='utf-8', errors='replace').splitlines())
    return (1 <= start <= end <= lines), f'lines {start}-{end} outside 1-{lines}'


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('review', type=Path)
    ap.add_argument('--repo', type=Path)
    args = ap.parse_args(argv)
    try:
        found = validate(load(args.review), args.repo.resolve() if args.repo else None)
    except (OSError, ValueError) as exc:
        print(f'cannot read review: {exc}', file=sys.stderr)
        return 2
    for message in found:
        print(f'FAIL  {message}')
    print('OK' if not found else f'FAILED: {len(found)} problem(s)')
    return 1 if found else 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
