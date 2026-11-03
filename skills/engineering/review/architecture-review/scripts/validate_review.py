#!/usr/bin/env python3
"""Check an architecture-review report.html against the template's structural contract.

Usage: python3 validate_review.py <report.html> [--repo <checkout>] [--template]

Prints PASS/FAIL per check and exits 0 only when all pass. It checks structure, not
judgment: it cannot tell whether a finding is right, only that it is complete and cited.

  --repo      also confirm every code/config path:line cites an existing file and lines in range
  --template  skip the leftover-placeholder check so the bundled template validates itself
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

DIMENSIONS = json.loads((Path(__file__).resolve().parent.parent / 'assets' / 'dimensions.json').read_text())
SECTIONS = ['sec-verdict', 'sec-context', 'sec-architecture', 'sec-dimensions', 'sec-findings',
            'sec-strengths', 'sec-options', 'sec-roadmap', 'sec-evidence']
STATUSES = {'adequate', 'attention', 'critical', 'unknown', 'not_applicable'}
CONFIDENCE = {'high', 'medium', 'low', 'unknown'}
PRIORITIES = {'P0', 'P1', 'P2', 'P3'}
EVIDENCE_KINDS = {'code', 'config', 'documentation', 'measurement', 'user_input', 'inference', 'hypothesis'}
CHECK_STATUSES = {'pass', 'fail', 'not_run', 'blocked', 'not_applicable'}
OPTION_KINDS = {'keep', 'incremental', 'structural'}
OPTION_POSITIONS = {'recommended', 'conditional', 'rejected'}
FINDING_PARTS = ['f-decision', 'f-observation', 'f-impact', 'f-recommendation', 'f-when-not',
                 'f-acceptance', 'f-rollback', 'f-evidence']
PLACEHOLDERS = re.compile(r'<!--\s*SLOT|\{\{|\bTODO\b|Replace with')
LOCATION = re.compile(r'^(?P<path>[^\s:]+):(?P<start>\d+)(?:-(?P<end>\d+))?$')
SECRETS = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}'
                     r'|\bsk-[A-Za-z0-9_-]{32,}|\bxox[abprs]-[A-Za-z0-9-]{10,}')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.children, self.parts = tag, dict(attrs), parent, [], []

    @property
    def classes(self):
        return (self.attrs.get('class') or '').split()

    def text(self):
        return re.sub(r'\s+', ' ', ''.join(p if isinstance(p, str) else p.text() for p in self.parts)).strip()

    def iter(self):
        yield self
        for child in self.children:
            yield from child.iter()

    def find(self, cls=None, tag=None):
        return [n for n in self.iter() if n is not self and (cls is None or cls in n.classes)
                and (tag is None or n.tag == tag)]

    def links(self):
        return [n.attrs['href'][1:] for n in self.iter() if n.tag == 'a' and (n.attrs.get('href') or '').startswith('#')]


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root', [], None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        self.cur.parts.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.cur)
        self.cur.children.append(node)
        self.cur.parts.append(node)

    def handle_endtag(self, tag):
        node = self.cur
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self.cur = node.parent

    def handle_data(self, data):
        if self.cur.tag not in ('script', 'style'):
            self.cur.parts.append(data)


REQUIRED_CSP = ("default-src 'none'", "connect-src 'none'", "base-uri 'none'", "form-action 'none'")
ALLOWED_ONCLICK = re.compile(r"jump\('[\w-]+'\)|setAll\((?:true|false)\)|filterPriority\('[\w ]+'\)")


# Allowlists: the page may use only this markup. Anything else (object, iframe, form, base,
# SVG animation, meta refresh, inline style, unknown attributes) fails validation.
ALLOWED_TAGS = set("""
html head meta title style script body header nav main section article aside footer div span p a
h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table caption thead tbody tfoot tr th td colgroup col details summary
code pre kbd em strong b i small sub sup mark abbr time blockquote br hr figure figcaption img button
svg g path rect circle ellipse line polyline polygon text tspan defs marker desc
""".split())
GLOBAL_ATTRS = {'class', 'id', 'role', 'lang', 'title', 'dir'}
TAG_ATTRS = {
    'meta': {'charset', 'name', 'content', 'http-equiv'}, 'a': {'href'}, 'img': {'src', 'alt', 'width', 'height'},
    'button': {'type', 'onclick'}, 'g': {'onclick', 'transform', 'fill', 'stroke'},
    'th': {'scope', 'colspan', 'rowspan'}, 'td': {'colspan', 'rowspan'}, 'col': {'span'}, 'colgroup': {'span'},
    'details': {'open'}, 'time': {'datetime'}, 'ol': {'start'},
}
SVG_ATTRS = {'viewbox', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd',
             'points', 'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'transform', 'marker-end',
             'marker-start', 'text-anchor', 'dominant-baseline', 'refx', 'refy', 'markerwidth', 'markerheight',
             'orient', 'xmlns', 'preserveaspectratio', 'font-size', 'font-weight', 'opacity'}
SVG_TAGS = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text', 'tspan',
            'defs', 'marker', 'desc'}
RASTER_DATA = re.compile(r'data:image/(?:png|jpeg|gif|webp)[;,]', re.I)


def normalized_url(value: str) -> str:
    """Normalize the way browsers do before reading a scheme."""
    return re.sub(r'[\t\n\r]', '', value).strip(''.join(map(chr, range(0x21))))


def safe_url(tag: str, value: str) -> bool:
    url = normalized_url(value)
    if tag == 'img':
        return bool(RASTER_DATA.match(url))
    scheme = re.match(r'([a-zA-Z][a-zA-Z0-9+.-]*):', url)
    return not scheme or scheme.group(1).lower() == 'https'


def markup_problems(nodes) -> list[str]:
    problems = []
    for n in nodes:
        if n.tag == '#root':
            continue
        if n.tag not in ALLOWED_TAGS:
            problems.append(f'<{n.tag}>')
            continue
        allowed = GLOBAL_ATTRS | TAG_ATTRS.get(n.tag, set()) | (SVG_ATTRS if n.tag in SVG_TAGS else set())
        for k in n.attrs:
            if not (k in allowed or k.startswith(('data-', 'aria-'))):
                problems.append(f'{n.tag}[{k}]')
        if n.tag == 'meta' and n.attrs.get('http-equiv') and n.attrs['http-equiv'].lower() != 'content-security-policy':
            problems.append(f'meta[http-equiv={n.attrs["http-equiv"]}]')
    return problems


def validate(html: str, repo: Path | None = None, template: bool = False) -> list[tuple[str, bool, str]]:
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), '' if ok else detail))

    tree = Tree()
    tree.feed(html)
    root = tree.root
    nodes = list(root.iter())
    by_id = {}
    for n in nodes:
        if 'id' in n.attrs:
            by_id.setdefault(n.attrs['id'], []).append(n)

    # Page floor (shared/references/html-page-conventions.md)
    title = next((n.text() for n in nodes if n.tag == 'title'), '')
    check('title present', title)
    check('html lang set', any(n.tag == 'html' and n.attrs.get('lang') for n in nodes))
    external = [n.attrs.get('src') or n.attrs.get('href') for n in nodes
                if (n.tag in ('script', 'img', 'iframe', 'embed', 'source') and re.match(r'(https?:)?//', n.attrs.get('src') or ''))
                or (n.tag == 'link' and re.match(r'(https?:)?//', n.attrs.get('href') or ''))]
    css_urls = re.findall(r'url\(\s*["\']?(?:https?:)?//', html)
    check('self-contained', not external and not css_urls, f'external resources: {external[:5]}')
    csp = next((n.attrs.get('content') or '' for n in nodes if n.tag == 'meta'
                and (n.attrs.get('http-equiv') or '').lower() == 'content-security-policy'), '')
    check('content security policy', all(d in csp for d in REQUIRED_CSP), f'CSP must include {REQUIRED_CSP}')
    check('one inline script', sum(n.tag == 'script' for n in nodes) <= 1
          and not any(n.tag == 'script' and n.attrs.get('src') for n in nodes), 'only one inline <script> is allowed')
    handlers = [f'{n.tag}[{k}]' for n in nodes for k, v in n.attrs.items()
                if k.startswith('on') and not (k == 'onclick' and ALLOWED_ONCLICK.fullmatch(v or ''))]
    check('only known event handlers', not handlers, f'unexpected handlers: {handlers[:5]}')
    check('only allowed markup', not markup_problems(nodes), f'not allowed: {markup_problems(nodes)[:5]}')
    bad_urls = [v for n in nodes for k, v in n.attrs.items() if k in ('href', 'src') and not safe_url(n.tag, v or '')]
    check('only safe URLs', not bad_urls, f'found: {bad_urls[:3]}')
    duplicates = sorted(i for i, v in by_id.items() if len(v) > 1)
    check('ids unique', not duplicates, f'duplicated: {duplicates[:8]}')
    dangling = sorted({h for n in nodes for h in n.links()} - set(by_id))
    jumps = sorted({t for n in nodes for t in re.findall(r"jump\('([^']+)'\)", n.attrs.get('onclick') or '')} - set(by_id))
    check('every #anchor and jump() resolves', not dangling and not jumps, f'dangling: {(dangling + jumps)[:8]}')
    check('expand/collapse controls wired', 'function setAll(' in html and 'setAll(true)' in html and 'setAll(false)' in html)
    check('no double-escaped entities', '&amp;lt;' not in html and '&amp;gt;' not in html)
    check('no secret-shaped strings', not SECRETS.search(html), 'matched a credential pattern; cite the name, not the value')
    if not template:
        leftovers = sorted(set(m.group(0) for m in PLACEHOLDERS.finditer(html)))
        check('no unresolved template placeholders', not leftovers, f'found: {leftovers}')

    # Required sections, in order
    order = [n.attrs['id'] for n in nodes if n.tag == 'section' and n.attrs.get('id') in SECTIONS]
    check('required sections present in order', order == SECTIONS, f'found: {order}')
    arch = by_id.get('sec-architecture', [None])[0]
    check('architecture section has an inline SVG diagram', arch and arch.find(tag='svg'))

    # Evidence register
    evidence = {n.attrs['id']: n for n in nodes if 'evidence' in n.classes and re.match(r'^E\d{3,}$', n.attrs.get('id', ''))}
    check('evidence register has records', evidence)
    for eid, n in evidence.items():
        kind = n.attrs.get('data-kind')
        check(f'{eid} kind', kind in EVIDENCE_KINDS, f'data-kind={kind!r}')
        if kind in ('code', 'config'):
            locs = [x.text() for x in n.find('loc')]
            check(f'{eid} cites path:line', locs and all(LOCATION.match(x) for x in locs), f'locations: {locs}')
            if repo is not None:
                for loc in locs:
                    check(f'{eid} {loc} exists at --repo', *cited_lines_exist(repo, loc))
        if kind == 'measurement':
            check(f'{eid} records its command', any(x.text() for x in n.find('cmd')), 'add <code class="cmd">')

    def cites(node):
        return [i for i in node.links() if i in evidence]

    # Dimensions
    rows = [n for n in nodes if n.tag == 'tr' and 'dim' in n.classes]
    expected = [d['id'] for d in DIMENSIONS]
    check('D01-D20 each present once, in order', [r.attrs.get('id') for r in rows] == expected,
          f'found: {[r.attrs.get("id") for r in rows]}')
    titles = {d['id']: d['title'] for d in DIMENSIONS}
    for r in rows:
        did, status, conf = r.attrs.get('id'), r.attrs.get('data-status'), r.attrs.get('data-confidence')
        check(f'{did} status', status in STATUSES, f'data-status={status!r}')
        check(f'{did} confidence', conf in CONFIDENCE, f'data-confidence={conf!r}')
        check(f'{did} title', titles.get(did, '?') in r.text(), f'expected {titles.get(did)!r}')
        check(f'{did} status shown as text', status and status in r.text())
        if status == 'unknown':
            check(f'{did} unknown is not high confidence', conf != 'high')
        if status in ('adequate', 'attention', 'critical'):
            check(f'{did} rated status cites evidence', cites(r), 'link at least one E record')
        else:
            check(f'{did} gives a reason', any(x.text() for x in r.find('d-note')))

    # Findings
    findings = [n for n in nodes if n.tag == 'article' and 'finding' in n.classes]
    for f in findings:
        fid = f.attrs.get('id', '?')
        pri, conf, dim = f.attrs.get('data-priority'), f.attrs.get('data-confidence'), f.attrs.get('data-dimension')
        check(f'{fid} id', re.match(r'^F\d+$', fid), 'use F01, F02, ...')
        check(f'{fid} priority', pri in PRIORITIES, f'data-priority={pri!r}')
        check(f'{fid} confidence', conf in CONFIDENCE, f'data-confidence={conf!r}')
        check(f'{fid} dimension', dim in titles, f'data-dimension={dim!r}')
        if pri in ('P0', 'P1'):
            check(f'{fid} P0/P1 needs high or medium confidence', conf in ('high', 'medium'))
        parts = {cls: ' '.join(x.text() for x in f.find(cls)) for cls in FINDING_PARTS}
        missing = [c for c, t in parts.items() if not t]
        check(f'{fid} complete', not missing, f'missing or empty: {missing}')
        check(f'{fid} cites evidence', cites(f.find('f-evidence')[0]) if f.find('f-evidence') else False,
              'link at least one E record in f-evidence')
        anchor = (f.attrs.get('data-leitwort') or '').strip().lower()
        check(f'{fid} names a decision anchor', anchor, 'set data-leitwort')
        if anchor:
            check(f'{fid} anchor drives the decision', anchor in parts['f-decision'].lower(),
                  f'{anchor!r} missing from f-decision')
            check(f'{fid} anchor recurs in the action or check',
                  anchor in (parts['f-recommendation'] + ' ' + parts['f-acceptance']).lower(),
                  f'{anchor!r} missing from f-recommendation and f-acceptance')
    status_of = {r.attrs.get('id'): r.attrs.get('data-status') for r in rows}
    for did in sorted(d for d, s in status_of.items() if s == 'critical'):
        check(f'{did} critical has a P0/P1 finding',
              any(f.attrs.get('data-dimension') == did and f.attrs.get('data-priority') in ('P0', 'P1') for f in findings))

    # Options and roadmap
    options = [n for n in nodes if n.tag == 'article' and 'option' in n.classes]
    check('options carry kind and position', options and all(
        o.attrs.get('data-kind') in OPTION_KINDS and o.attrs.get('data-position') in OPTION_POSITIONS for o in options),
        'each option needs data-kind (keep, incremental, structural) and data-position (recommended, conditional, rejected)')
    check('keeping the current architecture is an option', any(o.attrs.get('data-kind') == 'keep' for o in options))
    check('at most one recommended option', sum(o.attrs.get('data-position') == 'recommended' for o in options) <= 1)
    check('at most three first moves', sum('data-first-move' in n.attrs for n in nodes) <= 3)

    # Verification
    checks = [n for n in nodes if n.tag == 'tr' and 'check' in n.classes]
    check('verification records procedures', checks)
    for c in checks:
        check(f'{c.attrs.get("id", "?")} status', c.attrs.get('data-status') in CHECK_STATUSES,
              f'data-status={c.attrs.get("data-status")!r}')
    if any(f.attrs.get('data-priority') in ('P0', 'P1') for f in findings):
        check('challenge pass recorded for P0/P1 findings', any(c.attrs.get('data-check') == 'challenge' for c in checks),
              'add a verification row with data-check="challenge"')
    return results


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


def main(argv: list[str]) -> int:
    args, repo, template = [], None, False
    it = iter(argv)
    for a in it:
        if a == '--repo':
            repo = Path(next(it, '')).resolve()
        elif a == '--template':
            template = True
        else:
            args.append(a)
    if len(args) != 1:
        print(__doc__.strip().splitlines()[2], file=sys.stderr)
        return 2
    try:
        html = Path(args[0]).read_text(encoding='utf-8')
    except OSError as exc:
        print(f'FAIL cannot read file: {exc}', file=sys.stderr)
        return 2
    results = validate(html, repo, template)
    failures = 0
    for name, ok, detail in results:
        if not ok:
            failures += 1
            print(f'FAIL  {name}' + (f' - {detail}' if detail else ''))
    print(f'{"OK" if not failures else "FAILED"}: {len(results)} checks, {failures} failure(s)')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
