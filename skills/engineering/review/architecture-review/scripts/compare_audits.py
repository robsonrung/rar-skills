#!/usr/bin/env python3
"""Compare two audit.json files: what is new, resolved, re-prioritised or unchanged.

Use it for a follow-up audit of the same system, or to line up an audit with an earlier one
before folding another review in. Findings match by ID first, then by dimension and a similar
title. The comparison is structural; a reviewer still judges whether a match is the same issue.
"""
from __future__ import annotations
import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import sys
from validate_report import read_json


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


def match_findings(old: list[dict], new: list[dict], threshold: float) -> tuple[list, list, list]:
    pairs, used = [], set()
    by_id = {f['id']: f for f in new}
    remaining = []
    for f in old:
        g = by_id.get(f['id'])
        if g and similar(f['title'], g['title']) >= threshold:
            pairs.append((f, g, 'id')); used.add(g['id'])
        else:
            remaining.append(f)
    resolved = []
    for f in remaining:
        best = max((g for g in new if g['id'] not in used and g['dimension'] == f['dimension']),
                   key=lambda g: similar(f['title'], g['title']), default=None)
        if best and similar(f['title'], best['title']) >= threshold:
            pairs.append((f, best, 'title')); used.add(best['id'])
        else:
            resolved.append(f)
    added = [g for g in new if g['id'] not in used]
    return pairs, resolved, added


def compare(old: dict, new: dict, threshold: float = 0.6) -> dict:
    pairs, resolved, added = match_findings(old['findings'], new['findings'], threshold)
    changed = [dict(old=f['id'], new=g['id'], title=g['title'], matched_by=how,
                    priority=[f['priority'], g['priority']])
               for f, g, how in pairs if f['priority'] != g['priority']]
    same = [dict(old=f['id'], new=g['id'], title=g['title'], priority=g['priority'], matched_by=how)
            for f, g, how in pairs if f['priority'] == g['priority']]
    dims_old = {d['id']: d['status'] for d in old['dimensions']}
    dims = [dict(id=d['id'], title=d['title'], status=[dims_old.get(d['id']), d['status']])
            for d in new['dimensions'] if dims_old.get(d['id']) != d['status']]
    metrics_old = {m['title']: m for m in old.get('metrics', [])}
    metrics = []
    for m in new.get('metrics', []):
        o = metrics_old.get(m['title'])
        if o and (o['current'] != m['current'] or o['unit'] != m['unit']):
            metrics.append(dict(title=m['title'], unit=m['unit'], current=[o['current'], m['current']],
                                kinds=[o['current_kind'], m['current_kind']]))
    return dict(old=dict(system=old['meta']['system'], revision=old['meta']['revision'], date=old['meta']['date']),
                new=dict(system=new['meta']['system'], revision=new['meta']['revision'], date=new['meta']['date']),
                findings=dict(added=[dict(id=g['id'], title=g['title'], priority=g['priority']) for g in added],
                              resolved_or_dropped=[dict(id=f['id'], title=f['title'], priority=f['priority']) for f in resolved],
                              priority_changed=changed, unchanged=same),
                dimensions_changed=dims, metrics_changed=metrics,
                limitations=['Matching is by ID and title similarity; confirm each match against the evidence.',
                             'A finding missing from the new audit may be fixed, out of scope, or merged; check before '
                             'reporting it as resolved.'])


def markdown(result: dict) -> str:
    f = result['findings']
    out = [f"# Audit comparison\n\nOld: {result['old']['revision']} ({result['old']['date']})  \n"
           f"New: {result['new']['revision']} ({result['new']['date']})\n"]
    def section(title, rows, fmt):
        out.append(f'\n## {title} ({len(rows)})\n')
        out.extend(fmt(r) for r in rows) if rows else out.append('None.')
    section('New findings', f['added'], lambda r: f"- {r['id']} {r['priority']}: {r['title']}")
    section('Resolved or dropped', f['resolved_or_dropped'], lambda r: f"- {r['id']} {r['priority']}: {r['title']}")
    section('Priority changed', f['priority_changed'],
            lambda r: f"- {r['old']} to {r['new']}: {r['priority'][0]} to {r['priority'][1]}, {r['title']}")
    section('Dimension status changed', result['dimensions_changed'],
            lambda r: f"- {r['id']} {r['title']}: {r['status'][0]} to {r['status'][1]}")
    section('Metrics changed', result['metrics_changed'],
            lambda r: f"- {r['title']}: {r['current'][0]} to {r['current'][1]} {r['unit']}")
    out.append('\n' + ' '.join(result['limitations']) + '\n')
    return '\n'.join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('old', type=Path); ap.add_argument('new', type=Path)
    ap.add_argument('--format', choices=('markdown', 'json'), default='markdown')
    ap.add_argument('--threshold', type=float, default=0.6, help='title similarity needed to match findings')
    args = ap.parse_args()
    try:
        result = compare(read_json(args.old), read_json(args.new), args.threshold)
        sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + '\n' if args.format == 'json' else markdown(result))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
