#!/usr/bin/env python3
"""Render a validated audit into a self-contained, offline HTML report."""
from __future__ import annotations
import argparse
from collections import Counter
import html
import json
from pathlib import Path
import re
import sys
import textwrap
from validate_report import ROOT, load_validated, read_json
EN = {'adequate': 'Adequate', 'attention': 'Needs attention', 'critical': 'Critical', 'unknown': 'Unknown', 'not_applicable': 'Not applicable', 'high': 'High', 'medium': 'Medium', 'low': 'Low', 'pass': 'Passed', 'fail': 'Failed', 'not_run': 'Not run', 'blocked': 'Blocked', 'verified': 'Verified', 'failed': 'Failed', 'proposed': 'Proposed', 'keep': 'Keep current design', 'recommended': 'Recommended', 'conditional': 'Conditional', 'rejected': 'Not recommended', 'observed': 'Observed', 'declared': 'Declared', 'estimated': 'Estimated', 'demo': 'Illustrative', 'measured': 'Measured', 'agreed': 'Agreed', 'inferred': 'Inferred', 'sync': 'Synchronous', 'async': 'Asynchronous', 'dependency': 'Dependency', 'context': 'Context', 'component': 'Components', 'sequence': 'Sequence', 'deployment': 'Deployment', 'data': 'Data', 'read_only': 'Read only', 'isolated_verification': 'Isolated verification', 'code': 'Code', 'config': 'Configuration', 'documentation': 'Documentation', 'measurement': 'Measurement', 'user_input': 'User input', 'inference': 'Inference', 'hypothesis': 'Hypothesis'}

def esc(value) -> str:
    return html.escape(str(value), quote=True)

def render(data: dict) -> str:
    terms = {x['id']: x for x in read_json(ROOT / 'assets/terms.json')}

    def label(key):
        return EN.get(key, key)

    def tag(key):
        return f'<span class="tag {esc(key)}">{esc(label(key))}</span>'

    def para(value, cls=''):
        return f'<p class="{cls}">{esc(value)}</p>'

    def bullets(items):
        return '<ul>' + ''.join((f'<li>{esc(x)}</li>' for x in items)) + '</ul>' if items else ''

    def refs(ids):
        return '<div class="refs">' + ''.join((f'<a href="#{esc(x)}">{esc(x)}</a>' for x in ids)) + '</div>' if ids else ''

    def confidence(value):
        return f"""<span class="confidence">{'Confidence'}: {esc(label(value))}</span>"""

    def field(title, text):
        return f'<div><h4>{esc(title)}</h4>{para(text)}</div>'

    def empty():
        return para('No items recorded; see scope and limitations.', 'empty')
    sections = []
    nav = []

    def section(anchor, title, description, body):
        no = f'{len(sections) + 1:02d}'
        nav.append(f'<a href="#{anchor}"><span class="nav-num">{no}</span>{esc(title)}</a>')
        sections.append(f'<section id="{anchor}"><div class="section-head"><span class="section-no">{no}</span><div><h2>{esc(title)}</h2>{para(description)}</div></div>{body}</section>')

    def table(heads, rows):
        return '<div class="table-wrap"><table><thead><tr>' + ''.join((f'<th scope="col">{esc(h)}</th>' for h in heads)) + '</tr></thead><tbody>' + ''.join(('<tr>' + ''.join(('<td>' + str(c) + '</td>' for c in row)) + '</tr>' for row in rows)) + '</tbody></table></div>'

    def diagram(d):
        nw, nh = (224, 104)
        dx, dy = (340, 193)
        margin = 28
        width = max((n['col'] for n in d['nodes'])) * dx + nw + 2 * margin
        height = max((n['row'] for n in d['nodes'])) * dy + nh + 2 * margin
        pos = {n['id']: (margin + n['col'] * dx, margin + n['row'] * dy) for n in d['nodes']}
        parts = [f"""<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="title-{d['id']} desc-{d['id']}">""", f"""<title id="title-{d['id']}">{esc(d['title'])}</title><desc id="desc-{d['id']}">{esc(d['description'])}</desc>""", '<defs>']
        for kind, color in [('sync', '#47758d'), ('async', '#087d75'), ('dependency', '#82718e')]:
            parts.append(f'''<marker id="arrow-{d['id']}-{kind}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>''')
        parts.append('</defs>')
        edge_rows = []
        for i, e in enumerate(d['edges']):
            x1, y1 = pos[e['from']]
            x2, y2 = pos[e['to']]
            if x2 > x1:
                sx, sy = (x1 + nw, y1 + nh / 2)
                ex, ey = (x2, y2 + nh / 2)
                bend = max(35, abs(ex - sx) / 2)
                path = f'M {sx} {sy} C {sx + bend} {sy} {ex - bend} {ey} {ex} {ey}'
            elif x2 < x1:
                sx, sy = (x1, y1 + nh / 2)
                ex, ey = (x2 + nw, y2 + nh / 2)
                bend = max(35, abs(ex - sx) / 2)
                path = f'M {sx} {sy} C {sx - bend} {sy} {ex + bend} {ey} {ex} {ey}'
            else:
                sx = x1 + nw / 2
                ex = x2 + nw / 2
                sy = y1 + nh if y2 > y1 else y1
                ey = y2 if y2 > y1 else y2 + nh
                path = f'M {sx} {sy} L {ex} {ey}'
            color = {'sync': '#47758d', 'async': '#087d75', 'dependency': '#82718e'}[e['kind']]
            dash = 'stroke-dasharray="6 5"' if e['kind'] == 'async' or e['basis'] in ('inferred', 'proposed') else ''
            parts.append(f'''<path d="{path}" fill="none" stroke="{color}" stroke-width="2" {dash} marker-end="url(#arrow-{d['id']}-{e['kind']})"/>''')
            lines = textwrap.wrap(e['label'], 23, break_long_words=True, break_on_hyphens=False)
            tx, ty = ((sx + ex) / 2, (sy + ey) / 2 - 10)
            if x1 == x2:
                tx += 70
                ty += 4
            label_width = min(175, max(60, max((len(s) for s in lines), default=1) * 6.5 + 14))
            parts.append(f'<rect x="{tx - label_width / 2}" y="{ty - 13}" width="{label_width}" height="{max(1, len(lines)) * 14 + 7}" rx="4" fill="#f7fafc"/>')
            for j, line in enumerate(lines):
                parts.append(f'<text class="edge-label" x="{tx}" y="{ty + j * 14}" text-anchor="middle">{esc(line)}</text>')
            edge_rows.append([esc(e['from']) + ' → ' + esc(e['to']), esc(e['label']), esc(label(e['kind'])) + ' · ' + esc(label(e['basis'])), refs(e['evidence'])])
        for n in d['nodes']:
            x, y = pos[n['id']]
            fill = '#eaf3f7' if n['kind'] in ('actor', 'external') else '#fff'
            stripe = '#087d75' if n['kind'] in ('domain', 'worker') else '#48738c'
            if n['kind'] == 'data':
                fill = '#e7f3ee'
                stripe = '#28745a'
            parts.append(f'<rect x="{x}" y="{y}" width="{nw}" height="{nh}" rx="11" fill="{fill}" stroke="#b8cad6"/><rect x="{x}" y="{y + 12}" width="4" height="{nh - 24}" rx="2" fill="{stripe}"/>')
            titlelines = textwrap.wrap(n['label'], 24, break_long_words=True, break_on_hyphens=False)
            detaillines = textwrap.wrap(n['detail'], 32, break_long_words=True, break_on_hyphens=False)
            if len(titlelines) > 2:
                titlelines[1] = titlelines[1][:21] + '…'
            if len(detaillines) > 2:
                detaillines[1] = detaillines[1][:29] + '…'
            for j, line in enumerate(titlelines[:2]):
                parts.append(f'<text class="node-title" x="{x + 16}" y="{y + 26 + j * 19}">{esc(line)}</text>')
            base = y + 28 + len(titlelines[:2]) * 19
            for j, line in enumerate(detaillines[:2]):
                parts.append(f'<text class="node-detail" x="{x + 16}" y="{base + j * 15}">{esc(line)}</text>')
            parts.append(f'''<text class="node-id" x="{x + 16}" y="{y + nh - 9}">{esc(n['id'])}</text>''')
        parts.append('</svg>')
        node_rows = [[esc(n['id']), esc(n['label']), esc(n['detail']), refs(n['evidence'])] for n in d['nodes']]
        detail = table(['Node', 'Component', 'Responsibility', 'Evidence'], node_rows)
        if edge_rows:
            detail += table(['Connection', 'Contract / action', 'Type and basis', 'Evidence'], edge_rows)
        legend = 'Arrows indicate call, message or dependency direction. Dashed paths are asynchronous, inferred or proposed; see the exact type in the table.'
        if d['view'] == 'sequence':
            legend = 'Arrows show the order of steps; each node is a step, not necessarily a service. See the table for interaction types.'
        return f'''<article class="diagram" id="{d['id']}"><div class="diagram-header">{tag(d['state'])} <span class="small muted">{esc(label(d['view']))}</span><h3>{esc(d['title'])}</h3>{para(d['description'])}</div><div class="diagram-scroll">{''.join(parts)}</div><div class="diagram-footer">{para(legend)}{refs(d['evidence'])}<details><summary>{'Read components and connections as tables'}</summary>{detail}</details></div></article>'''
    meta = data['meta']
    v = data['verdict']
    hero = f"""<header class="hero"><p class="eyebrow">{'Architecture assessment'}</p><h1>{esc(v['headline'])}</h1>{para(v['summary'], 'lead')}<div class="card-top">{tag(meta['mode'])}{confidence(v['confidence'])}</div><div class="verdict-grid"><div><div class="label">{'Does it meet current needs?'}</div>{para(v['current_fit'])}</div><div><div class="label">{'How can it grow?'}</div>{para(v['future_fit'])}</div></div>{refs(v['evidence'])}</header>"""
    known = sum((x['status'] in ('adequate', 'attention', 'critical') for x in data['dimensions']))
    applicable = sum((x['status'] != 'not_applicable' for x in data['dimensions']))
    stats = [(f'{known}/{applicable}', 'applicable dimensions assessed'), (str(len(data['strengths'])), 'documented strengths'), (str(len(data['findings'])), 'findings with evidence'), (str(sum((x['status'] == 'unknown' for x in data['dimensions']))), 'dimensions still unknown')]
    hero += '<div class="stats">' + ''.join((f'<div class="stat"><strong>{esc(a)}</strong><span>{esc(b)}</span></div>' for a, b in stats)) + '</div>'
    body = '<div class="context-grid">' + ''.join((f"""<article class="context-item"><h3>{esc(x['label'])}</h3>{para(x['value'])}{tag(x['basis'])}{refs(x['evidence'])}</article>""" for x in data['context'])) + '</div>'
    body += '<div class="panel">' + field('Scope', meta['scope']) + field('Inspection coverage', meta['coverage'])
    if meta['exclusions']:
        body += '<h4>' + 'Out of scope' + '</h4>' + bullets(meta['exclusions'])
    if meta['limitations']:
        body += '<h4>' + 'Limitations' + '</h4>' + bullets(meta['limitations'])
    if data['questions']:
        body += '<h4>' + 'Open questions that affect decisions' + '</h4>' + bullets(data['questions'])
    body += '</div>'
    section('context', 'Context and limits', 'The criterion is business fitness, not an idealized design.', body)
    current = [d for d in data['diagrams'] if d['state'] != 'proposed']
    body = ''.join((diagram(d) for d in current)) or empty()
    if data['diagram_gaps']:
        body += '<div class="panel">' + bullets(data['diagram_gaps']) + '</div>'
    section('architecture', 'Current architecture', 'Separate views for responsibilities, interfaces and flows. An import is not a network call.', body)
    counts = Counter((x['status'] for x in data['dimensions']))
    order = ['adequate', 'attention', 'critical', 'unknown', 'not_applicable']
    body = '<div class="panel"><h3>' + 'Assessment overview' + '</h3>' + para('Status distribution, not a quality score. Uncertainty and risks are not averaged away.', 'small muted')
    body += '<div class="quality-bar" role="img" aria-label="' + esc('; '.join((f'{label(k)}: {counts[k]}' for k in order))) + '">' + ''.join((f'''<span class="{k}" style="width:{counts[k] / len(data['dimensions']) * 100:.2f}%"></span>''' for k in order if counts[k])) + '</div>'
    body += '<div class="legend">' + ''.join((f'<span>{tag(k)} {counts[k]}</span>' for k in order)) + '</div></div>'
    body += f'''<div class="toolbar"><label for="report-search">{'Search'}</label><input id="report-search" type="search" placeholder="{'Dimensions and findings…'}"><label for="priority-filter">{'Findings'}</label><select id="priority-filter"><option value="all">{'All priorities'}</option>''' + ''.join((f'<option value="P{i}">P{i}</option>' for i in range(4))) + '</select></div>'
    body += '<div class="dim-grid">' + ''.join((f'''<article class="dimension searchable {d['status']}" id="{d['id']}"><div class="card-top"><span class="id mono">{d['id']}</span>{tag(d['status'])}</div><h3>{esc(d['title'])}</h3>{para(d['explanation'])}{refs(d['evidence'])}{confidence(d['confidence'])}</article>''' for d in data['dimensions'])) + '</div>'
    section('assessment', '20 dimensions', 'Fitness, risk, applicability and confidence are shown separately.', body)
    body = '<div class="grid3">' + ''.join((f'''<article class="panel" id="{s['id']}"><div class="eyebrow">{'Preserve'}</div><h3>{esc(s['title'])}</h3>{para(s['explanation'], 'small')}{refs(s['evidence'])}</article>''' for s in data['strengths'])) + '</div>' if data['strengths'] else empty()
    section('strengths', 'What works well', 'Strengths also need evidence. Changes should preserve them.', body)
    body = f"""<p class="small muted">{'Visible findings'}: <span id="filter-count" aria-live="polite">{len(data['findings'])}</span></p>"""
    for f in sorted(data['findings'], key=lambda x: (x['priority'], x['id'])):
        fields = [('Smallest useful change', f['recommendation']), ('Cost and trade-off', f['tradeoff']), ('Effort and estimate basis', f['effort']), ('Why act now', f['why_now']), ('When not to change', f['when_not']), ('How to verify', f['validation']), ('Acceptance criterion', f['acceptance']), ('Rollback', f['rollback'])]
        body += f'''<article id="{f['id']}" class="panel finding searchable {f['priority']}" data-priority="{f['priority']}"><div class="card-top"><span class="id mono">{f['id']} · <a href="#{f['dimension']}">{f['dimension']}</a></span>{tag(f['priority'])}{confidence(f['confidence'])}</div><h3>{esc(f['title'])}</h3>{field('Decision anchor: ' + terms[f['leitwort']]['term'], f['decision_statement'])}{para(f['observation'])}{para(f['impact'], 'impact')}{refs(f['evidence'])}<details><summary>{'Solution, alternatives and verification'}</summary><div class="detail-grid">''' + ''.join((field(a, b) for a, b in fields)) + '</div><h4>' + 'Alternatives' + '</h4>' + bullets(f['alternatives']) + '<h4>' + 'Rationale sources' + '</h4>' + refs(f['sources']) + '</details></article>'
    section('findings', 'Risks and improvements', 'Each finding connects an observation, its effect and a verifiable action.', body)
    body = ''
    body = ''
    for c in data['concept_applications']:
        term = terms[c['term_id']]
        state = 'Applied' if c['status'] == 'applied' else label(c['status'])
        body += (f'<article class="panel concept" id="{esc(c["id"])}">'
                 f'<div class="card-top"><span class="id mono">{esc(c["id"])}</span>'
                 f'<span class="tag {esc(c["status"])}">{esc(state)}</span></div>'
                 f'<h3>{esc(term["term"])}</h3>'
                 + para(term['definition'], 'small muted')
                 + field('Decision', c['decision'])
                 + '<div class="detail-grid">'
                 + field('Action', c['action'])
                 + field('Verification', c['verification']) + '</div>'
                 + refs(c['evidence'] + c['sources'] + c['related_findings']) + '</article>')
    section('concepts', 'Concepts in action',
            'Canonical terms constrain decisions, actions, and checks. Unknown and not applicable are explicit outcomes.',
            body or empty())
    body = ''
    if data['scenarios']:
        rows = [[f'''<strong id="{s['id']}">{esc(s['title'])}</strong>''' + para(s['stimulus'], 'small'), esc(s['environment']), esc(s['response']) + '<br><strong>' + esc(s['target']) + '</strong>', tag(s['status']) + para(s['observed'], 'small') + refs(s['evidence'])] for s in data['scenarios']]
        body += table(['Scenario / stimulus', 'Environment', 'Response and measure', 'Current status'], rows)
    if data['metrics']:
        rows = []
        for m in data['metrics']:
            current = 'Not recorded' if m['current'] is None else f"{m['current']:g} {m['unit']}"
            target = 'Not recorded' if m['target'] is None else f"{m['target']:g} {m['unit']}"
            rows.append([f'''<strong id="{m['id']}">{esc(m['title'])}</strong>''', esc(current) + '<br>' + tag(m['current_kind']), esc(target) + '<br>' + tag(m['target_kind']), esc(m['environment']) + '<br>' + esc(m['note']) + refs(m['evidence'])])
        body += '<div class="panel"><h3>' + 'Metrics and targets' + '</h3>' + table(['Metric', 'Current', 'Target', 'Conditions and basis'], rows) + '</div>'
    c = data['capacity']
    body += '<div class="panel"><h3>' + 'Capacity and growth' + '</h3>' + para(c['summary']) + '<div class="grid2"><div><h4>' + 'Explicit assumptions' + '</h4>' + bullets(c['assumptions']) + '</div><div><h4>' + 'Measurements needed' + '</h4>' + bullets(c['measurements_needed']) + '</div></div>' + field('Reassessment trigger', c['growth_trigger']) + refs(c['evidence']) + '</div>'
    section('requirements', 'Requirements and capacity', 'A target is not a measurement. Without representative workload data, capacity remains an open question.', body)
    body = '<div class="grid3">'
    for o in data['options']:
        body += f'''<article id="{o['id']}" class="panel option {o['position']}">{tag(o['position'])}<h3>{esc(o['title'])}</h3><h4>{'Benefits'}</h4>{bullets(o['benefits'])}<h4>{'Costs and risks'}</h4>{bullets(o['costs'])}<h4>{'Preconditions'}</h4>{bullets(o['preconditions'])}{field('Trade-off', o['tradeoff'])}{field('When to reconsider', o['trigger'])}{refs(o['evidence'])}{refs(o['sources'])}</article>'''
    body += '</div>' + ''.join((diagram(d) for d in data['diagrams'] if d['state'] == 'proposed'))
    section('alternatives', 'Evolution options', 'Keeping the current design is the baseline. Distribution needs a reason.', body)
    body = '<div class="roadmap">'
    for r in data['roadmap']:
        body += f'''<article class="step" id="{r['id']}"><span class="eyebrow">{esc(r['stage'])}</span><h3>{esc(r['title'])}</h3>{bullets(r['actions'])}<div class="detail-grid">{field('Owner and effort', r['owner'] + ' · ' + r['effort'])}{field('Acceptance', r['acceptance'])}{field('Rollback', r['rollback'])}</div>{refs(r['depends_on'] + r['related_findings'])}</article>'''
    body += '</div>'
    if not data['roadmap']:
        body = empty()
    section('roadmap', 'Incremental plan', 'Small steps, explicit dependencies and criteria to proceed or roll back.', body)
    rows = [[f'''<strong id="{a['id']}">{esc(a['capability'])}</strong>''', tag(a['status']), esc(a['method']), esc(a['result']) + refs(a['evidence'])] for a in data['agent_checks']]
    body = table(['Capability', 'Status', 'Verification', 'Result / limit'], rows)
    section('agents', 'Agent readiness', 'Finding and understanding code is different from safely executing and validating a task.', body)
    c = data['cost']
    body = '<div class="panel">' + para(c['summary']) + '<div class="grid2"><div><h4>' + 'Assumptions and horizon' + '</h4>' + bullets(c['assumptions']) + '</div><div><h4>' + 'Data needed for a decision' + '</h4>' + bullets(c['measurements_needed']) + '</div></div>' + refs(c['evidence']) + '</div>'
    if data['decisions_needed']:
        body += '<div class="panel"><h3>' + 'Decisions that need an owner' + '</h3>' + bullets(data['decisions_needed']) + '</div>'
    section('cost', 'Economics and decisions', 'Include operations, maintenance and migration, not just infrastructure bills.', body)
    body = '<div class="panel"><details><summary>' + 'Open the evidence register' + '</summary>'
    for e in data['evidence']:
        lines = f":{e['line_start']} to {e['line_end']}" if e['line_start'] is not None else ''
        body += f'''<article class="evidence" id="{e['id']}"><div class="card-top"><h3>{e['id']}</h3>{tag(e['kind'])}</div><p class="location mono">{esc(e['location'] + lines)}</p>{para(e['observation'])}<p class="location">{esc(e['revision'])} · {esc(e['captured_at'])} · {esc(e['environment'])}</p>'''
        if e['command']:
            body += '<p><code>' + esc(e['command']) + '</code></p>'
        if e['artifact']:
            body += para(e['artifact'], 'location')
        body += refs(e['supports']) + '</article>'
    body += '</details></div>'
    section('evidence', 'Evidence', 'Traceability by source and revision. An inference does not replace a measurement.', body)
    rows = [[f'''<code id="{v['id']}">{esc(v['command'])}</code>''', tag(v['status']), esc('Not recorded' if v['exit_code'] is None else v['exit_code']), esc(v['environment']) + '<br>' + esc(v['notes']) + ('<br>' + esc(v['artifact']) if v['artifact'] else '') + '<br><span class="muted">' + esc(v['captured_at']) + '</span>'] for v in data['verification']]
    section('verification', 'Verification record', 'Only procedures with recorded results count as executed. Structural validation does not prove the assessment.', table(['Procedure', 'Status', 'Exit', 'Environment and notes'], rows))
    body = '<div class="panel"><details><summary>' + 'References used in this assessment' + '</summary>'
    for s in data['sources']:
        body += f'''<article id="{s['id']}" class="source"><h3>{s['id']} · <a href="{esc(s['url'])}" rel="noreferrer noopener">{esc(s['title'])}</a></h3>{para(s['author'])}{para(s['application'])}{para(s['access'] + ' · ' + s['checked_at'], 'muted')}</article>'''
    body += '</details></div>'
    if data['glossary']:
        body += '<div class="panel"><h3>' + 'Glossary' + '</h3><dl class="glossary">' + ''.join(('<div><dt>' + esc(g['term']) + '</dt><dd>' + esc(g['definition']) + '</dd></div>' for g in data['glossary'])) + '</dl></div>'
    section('sources', 'Sources and concepts', 'Literature guides judgment. Facts about the system must come from evidence.', body)
    replacements = dict(LANG=data['language'], TITLE=esc(meta['system'] + ' | Architecture Review'), SKIP='Skip to content', BRAND='Architecture in context', NAVLABEL='Report navigation', NAV=''.join(nav), NAVNOTE='Evidence before opinion.\nSimplicity before complexity.', META=esc(meta['system'] + ' · ' + meta['date'] + ' · ' + meta['revision']), PRINT='Print report', DEMO='<p class="demo-banner" role="note"><strong>' + 'FICTIONAL DEMONSTRATION.' + '</strong> ' + 'No real repository was audited. Example numbers, components, evidence and conclusions do not describe your system.' + '</p>' if meta['is_demo'] else '', NOSCRIPT='Content and diagrams work without JavaScript. Search, filters and automatic print preparation need JavaScript.', CONTENT=hero + ''.join(sections), FOOTER='Private, self-contained report. No external visual resources or telemetry. Bibliographic links only open when selected.')
    template = (ROOT / 'assets/report.html').read_text(encoding='utf-8')
    return re.sub('@@([A-Z]+)@@', lambda m: replacements[m.group(1)], template)

def export(data: dict, output: Path):
    output = output.resolve()
    targets = [output, output.parent / 'evidence.jsonl', output.parent / 'verification.md']
    if len(set(targets)) != 3:
        raise ValueError('Choose a distinct HTML filename')
    for path in targets:
        if path.exists():
            raise ValueError(f'Output already exists: {path}; use a new output directory')
    document = render(data)
    evidence = ''.join((json.dumps(e, ensure_ascii=False) + '\n' for e in data['evidence']))
    verification = '# Verification record\n\n'
    if data['meta']['is_demo']:
        verification += 'FICTIONAL EXAMPLE. Not a real system audit.\n\n'
    for v in data['verification']:
        command = v['command'].replace('`', '\\`')
        verification += f"## {v['id']}: {v['status']}\n\n{command}\n\n{v['notes']}\n\n"
        verification += f"Environment: {v['environment']}\n\nExit: {v['exit_code']}\n\nArtifact: {v['artifact']}\n\nDate: {v['captured_at']}\n\n"
    verification += 'This record is supplied by the audit. The renderer verifies structure, not factual truth.\n'
    output.parent.mkdir(parents=True, exist_ok=True)
    written = []
    try:
        for path, content in zip(targets, [document, evidence, verification]):
            with path.open('x', encoding='utf-8') as handle:
                written.append(path)
                handle.write(content)
    except OSError:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return targets

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('report', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    try:
        data = load_validated(args.report)
        for path in export(data, args.out):
            print(path)
        return 0
    except (OSError, ValueError, RecursionError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
if __name__ == '__main__':
    raise SystemExit(main())
