#!/usr/bin/env python3
"""Render an architecture-review review.json into the self-contained report page.

Usage: python3 render_review.py <review.json> --out <report.html> [--repo <checkout>]

Validates the data (validate_review.py), fills assets/shell.html with every value escaped, and writes
the page only if it passes shared/scripts/html_guard.py. In text, `code` becomes inline code and a
known E, F, or Q id becomes a link.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _root in (HERE, *HERE.parents):
    if (_root / 'shared' / 'scripts' / 'html_guard.py').is_file():
        sys.path[:0] = [str(_root / 'shared' / 'scripts'), str(HERE)]
        break
import html_guard  # noqa: E402
import validate_review as vr  # noqa: E402

SHELL = (HERE.parent / 'assets' / 'shell.html').read_text(encoding='utf-8')
SECTIONS = [('sec-verdict', 'Verdict'), ('sec-context', 'Context'), ('sec-architecture', 'Architecture'),
            ('sec-dimensions', 'Dimensions'), ('sec-findings', 'Findings'), ('sec-strengths', 'Strengths'),
            ('sec-options', 'Options and target'), ('sec-roadmap', 'Roadmap'),
            ('sec-evidence', 'Evidence and verification')]
FINDING_ROWS = [('Observation', 'observation'), ('Impact', 'impact'), ('Recommendation', 'recommendation'),
                ('Alternatives', 'alternatives'), ('When not to act', 'when_not'), ('Acceptance', 'acceptance'),
                ('Rollback', 'rollback')]
BOX_W, BOX_H, COL_W, ROW_H = 200, 56, 260, 96


def esc(value) -> str:
    return html.escape(str(value), quote=True)


class Page:
    def __init__(self, review: dict):
        self.r = review
        self.ids = {x['id'] for x in review['evidence']['records'] + review['findings']['items']}
        self.ids |= {f'Q{i}' for i in range(1, len(review['context']['scenarios']) + 1)}

    def text(self, value) -> str:
        """Escaped text with `code` spans and links to known evidence and finding ids."""
        out = re.sub(r'\b[EFQ]\d+\b', lambda m: self.link(m.group(0)) if m.group(0) in self.ids else m.group(0), esc(value))
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', out) or 'Not reported'

    def link(self, ref: str) -> str:
        return f'<a href="#{esc(ref)}">{esc(ref)}</a>'

    def links(self, refs) -> str:
        return ' '.join(self.link(x) for x in refs)

    def ul(self, items) -> str:
        return '<ul>' + ''.join(f'<li>{self.text(x)}</li>' for x in items) + '</ul>' if items else '<p>Not reported</p>'

    def section(self, n: int, title: str, lede, body: str) -> str:
        lede_html = f'<p class="lede">{self.text(lede)}</p>' if lede is not None else ''
        return (f'<section class="card" id="{SECTIONS[n][0]}">\n<h2>{n + 1}. {esc(title)}</h2>\n'
                f'{lede_html}\n{body}\n</section>\n')

    def diagram(self, i: int, d: dict) -> str:
        boxes = {n['id']: (20 + n['col'] * COL_W, 20 + n['row'] * ROW_H) for n in d['nodes']}
        width = max(x for x, _ in boxes.values()) + BOX_W + 20
        height = max(y for _, y in boxes.values()) + BOX_H + 20
        out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(d["label"])}">',
               f'<defs><marker id="arrow{i}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="8" markerHeight="8" '
               f'orient="auto"><path d="M0 0 L10 5 L0 10 z"/></marker></defs>']
        for e in d['edges']:
            (x1, y1), (x2, y2) = boxes[e['from']], boxes[e['to']]
            (ax, ay), (bx, by) = clip(x1, y1, x2, y2), clip(x2, y2, x1, y1)
            cls = 'edge proposed' if e.get('proposed') else 'edge'
            out.append(f'<line class="{cls}" x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" marker-end="url(#arrow{i})"/>')
        for n in d['nodes']:
            x, y = boxes[n['id']]
            finding = n.get('finding')
            attrs = f' class="node clickable" onclick="jump(\'{esc(finding)}\')"' if finding else ' class="node"'
            rect = ' class="proposed"' if n.get('proposed') else ''
            out.append(f'<g{attrs}><rect{rect} x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="8"/>'
                       f'<text x="{x + 16}" y="{y + 33}">{esc(n["label"])}</text></g>')
        return '<div class="diagram">' + '\n'.join(out) + '</svg></div>'

    def table(self, head, rows) -> str:
        header = '<tr>' + ''.join(f'<th>{esc(h)}</th>' for h in head) + '</tr>\n' if head else ''
        return '<div class="scroll"><table>\n' + header + '\n'.join(rows) + '\n</table></div>'

    def render(self) -> str:
        r, t = self.r, self.text
        v, c, a = r['verdict'], r['context'], r['architecture']
        rows, findings = r['dimensions']['rows'], r['findings']['items']
        by_id = {f['id']: f for f in findings}
        counts = ', '.join(f'{sum(x["status"] == s for x in rows)} {s.replace("_", " ")}' for s in vr.STATUSES)
        nav = ''.join(f'<a href="#{sid}">{esc(name)}</a>' for sid, name in SECTIONS)
        parts = [f'<header>\n<h1>{esc(r["system"])} Architecture Review</h1>\n<p class="subtitle">{t(r["subtitle"])}</p>\n'
                 f'<nav class="toc">{nav}</nav>\n<div class="controls"><button type="button" onclick="setAll(true)">'
                 f'Expand all</button><button type="button" onclick="setAll(false)">Collapse all</button></div>\n</header>\n']
        top = '<ul>' + ''.join(f'<li>{self.link(x)} {t(by_id[x]["title"])}</li>' for x in v['top']) + '</ul>'
        parts.append(self.section(0, 'Verdict', v['lede'], f'<p>{esc(counts)}.</p>\n<h3>Decisions needed</h3>'
                                  f'{self.ul(v["decisions"])}\n<h3>Top findings</h3>{top}'))
        scenarios = [f'<tr id="Q{i}"><td>Q{i}</td><td>{t(q["stimulus"])}</td><td>{t(q["response"])}</td>'
                     f'<td>{t(q["origin"])}</td><td>{t(q["observed"])}</td></tr>' for i, q in enumerate(c['scenarios'], 1)]
        scope = [f'<tr><th>{k.title()}</th><td>{t(c[k])}</td></tr>' for k in ('revision', 'coverage', 'exclusions')]
        parts.append(self.section(1, 'Context', c['lede'], '<h3>Scope and coverage</h3>' + self.table([], scope)
                                  + '<h3>Quality Attribute Scenarios</h3>' + self.table(
                                      ['ID', 'Stimulus and environment', 'Expected response and measure', 'Origin',
                                       'Observed'], scenarios) + '<h3>Assumptions, unknowns, and open questions</h3>'
                                  + self.ul(c['assumptions'])))
        flows = ''.join(f'<details class="drill"><summary>{t(f["name"])}</summary><ol>'
                        + ''.join(f'<li>{t(s)}</li>' for s in f['steps']) + '</ol></details>' for f in a['flows'])
        diagrams = '\n'.join(self.diagram(i, d) for i, d in enumerate(a['diagrams']) if d['nodes'])
        parts.append(self.section(2, 'Implemented architecture', a['lede'], f'{diagrams}\n<h3>Flows</h3>{flows}'))
        dims = [f'<tr class="dim" id="{esc(x["id"])}" data-status="{esc(x["status"])}" data-confidence="{esc(x["confidence"])}">'
                f'<td>{esc(x["id"])}</td><td>{esc(vr.TITLES[x["id"]])}</td><td><span class="badge {esc(x["status"])}">'
                f'{esc(x["status"])}</span></td><td>{esc(x["confidence"])}</td><td class="d-note">{t(x["note"])}</td>'
                f'<td class="d-evidence">{self.links(x["evidence"])}</td></tr>' for x in rows]
        parts.append(self.section(3, 'Dimensions', r['dimensions']['lede'], self.table(
            ['ID', 'Dimension', 'Status', 'Confidence', 'Assessment', 'Evidence'], dims)))
        filters = ''.join(f'<button type="button" onclick="filterPriority(\'{k}\')">{n}</button>' for k, n in
                          (('all', 'All'), ('P0 P1', 'P0 and P1'), ('P2', 'P2'), ('P3', 'P3')))
        cards = '\n'.join(self.finding(f) for f in sorted(findings, key=lambda f: f['priority']))
        parts.append(self.section(4, 'Findings', r['findings']['lede'], f'<div class="controls">{filters}</div>\n{cards}'))
        s = r['strengths']
        strengths = '<ul>' + ''.join(f'<li id="S{i}">{t(x["text"])} {self.links(x["evidence"])}</li>'
                                     for i, x in enumerate(s['items'], 1)) + '</ul>'
        parts.append(self.section(5, 'Strengths and respected decisions', None,
                                  f'{strengths}\n<h3>Respected decisions</h3>{self.ul(s["respected"])}'))
        o = r['options']
        options = ''.join(f'<article class="option" id="O{i}" data-kind="{esc(x["kind"])}" data-position="{esc(x["position"])}">'
                          f'<h3>{t(x["title"])} <span class="badge">{esc(x["position"])}</span></h3><p>{t(x["text"])}</p></article>'
                          for i, x in enumerate(o['items'], 1))
        parts.append(self.section(6, 'Options and target', o['lede'],
                                  f'{options}\n<h3>Target and guardrails</h3><p>{t(o["target"])}</p>'))
        steps = ''.join(f'<li class="step" id="R{i}"' + (' data-first-move>' + '<span class="first-move">First move.</span> '
                                                         if x.get('first_move') else '>')
                        + f'{t(x["text"])} {self.links(x.get("findings", []))}</li>'
                        for i, x in enumerate(r['roadmap']['steps'], 1))
        parts.append(self.section(7, 'Roadmap', None, f'<ol>{steps}</ol>'))
        e = r['evidence']
        records = [f'<tr class="evidence" id="{esc(x["id"])}" data-kind="{esc(x["kind"])}"><td>{esc(x["id"])}</td>'
                   f'<td>{esc(x["kind"])}</td><td>{where(x)}</td><td>{t(x["observation"])}</td></tr>' for x in e['records']]
        checks = [f'<tr class="check" id="V{i}" data-status="{esc(x["status"])}"' + (' data-check="challenge"' if x.get('challenge') else '')
                  + f'><td>V{i}</td><td>{t(x["procedure"])}</td><td>{esc(x["status"])}</td><td>{t(x["result"])}</td></tr>'
                  for i, x in enumerate(e['checks'], 1)]
        glossary = ''.join(f'<dt>{t(g["term"])}</dt><dd>{t(g["definition"])}</dd>' for g in e['glossary'])
        parts.append(self.section(8, 'Evidence and verification', e['lede'], '<h3>Evidence register</h3>' + self.table(
            ['ID', 'Kind', 'Location or command', 'Observation'], records) + '<h3>Verification</h3>' + self.table(
            ['ID', 'Procedure', 'Status', 'Result'], checks) + (f'<h3>Glossary</h3><dl>{glossary}</dl>' if glossary else '')))
        parts.append(f'<footer>{t(r["footer"])}</footer>')
        fills = {'lang': esc(r.get('lang', 'en')), 'title': f'{esc(r["system"])} Architecture Review', 'body': ''.join(parts)}
        return re.sub(r'\{\{(lang|title|body)\}\}', lambda m: fills[m.group(1)], SHELL)

    def finding(self, f: dict) -> str:
        t, pri = self.text, esc(f['priority'])
        dl = ''.join(f'<dt>{n}</dt><dd>{t(f.get(k, ""))}</dd>' for n, k in FINDING_ROWS)
        return (f'<article class="finding" id="{esc(f["id"])}" data-priority="{pri}" data-confidence="{esc(f["confidence"])}" '
                f'data-dimension="{esc(f["dimension"])}">\n<h3><span class="badge {pri}">{pri}</span> {t(f["title"])}</h3>\n'
                f'<p>{t(f["summary"])}</p>\n<p><strong>Decision.</strong> {t(f["decision"])}</p>\n'
                f'<p>{esc(f["dimension"])}, {esc(f["confidence"])} confidence, anchor: {esc(f["anchor"])}</p>\n'
                f'<details class="drill"><summary>Details</summary><dl>{dl}<dt>Evidence</dt><dd>{self.links(f["evidence"])}</dd>'
                f'</dl></details>\n</article>')


def clip(x1, y1, x2, y2) -> tuple[int, int]:
    """Where the line from box 1's center toward box 2's center leaves box 1."""
    cx, cy, dx, dy = x1 + BOX_W / 2, y1 + BOX_H / 2, x2 - x1, y2 - y1
    s = min(BOX_W / 2 / abs(dx) if dx else float('inf'), BOX_H / 2 / abs(dy) if dy else float('inf'))
    return round(cx + dx * s), round(cy + dy * s)


def where(record: dict) -> str:
    if record.get('locations'):
        return ' '.join(f'<code class="loc">{esc(x)}</code>' for x in record['locations'])
    if record.get('command'):
        return f'<code class="cmd">{esc(record["command"])}</code>'
    return esc(record.get('source', '')) or 'Not reported'


def render(review: dict, repo: Path | None = None) -> tuple[str, list[str]]:
    """Return (page, problems); the page is empty when the data fails validation."""
    if found := vr.validate(review, repo):
        return '', found
    page = Page(review).render()
    return page, html_guard.problems(page, template_script=html_guard.template_script(SHELL))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('review', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--repo', type=Path)
    args = ap.parse_args(argv)
    try:
        page, found = render(vr.load(args.review), args.repo.resolve() if args.repo else None)
    except (OSError, ValueError) as exc:
        print(f'cannot read review: {exc}', file=sys.stderr)
        return 2
    print(''.join(f'FAIL  {m}\n' for m in found) + (f'FAILED: {len(found)} problem(s); nothing written' if found
                                                       else f'OK: wrote {args.out}'))
    if not found:
        args.out.write_text(page, encoding='utf-8')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
