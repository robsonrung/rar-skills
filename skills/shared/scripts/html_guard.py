#!/usr/bin/env python3
"""Markup safety floor for self-contained HTML pages a model writes or a script renders.

Usage: python3 html_guard.py <page.html> --template <template.html> [--allow-comments] [--extra-tags a,b]

Prints one problem per line and exits 0 only when there are none. The page must carry CSP below, use
only allowlisted markup and URLs, and keep the template's single inline script unchanged.

Python's HTMLParser and browsers tokenize some constructs differently, so a page that only looks safe
to Python could still run script in a browser. The checks reject those constructs outright rather than
model them: comments, CDATA, processing instructions, raw-text and foreign elements, a raw `<` inside
a tag, repeated attributes, and title, style or script anywhere but their one expected place.
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
       "font-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'")
CSP_META = f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'

TAGS = frozenset("""
html head meta title style script body header nav main section article aside footer div span p a
h1 h2 h3 h4 h5 h6 ul ol li dl dt dd table caption thead tbody tfoot tr th td colgroup col details summary
code pre kbd em strong b i small sub sup mark abbr time blockquote br hr figure figcaption img button
svg g path rect circle ellipse line polyline polygon text tspan defs marker desc
""".split())
GLOBAL_ATTRS = frozenset({'class', 'id', 'role', 'lang', 'title', 'dir'})
TAG_ATTRS = {
    'meta': {'charset', 'name', 'content', 'http-equiv'}, 'a': {'href'}, 'img': {'src', 'alt', 'width', 'height'},
    'button': {'type', 'onclick'}, 'g': {'onclick'}, 'th': {'scope', 'colspan', 'rowspan'},
    'td': {'colspan', 'rowspan'}, 'col': {'span'}, 'colgroup': {'span'}, 'details': {'open'},
    'time': {'datetime'}, 'ol': {'start'},
}
SVG_TAGS = frozenset({'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'text',
                      'tspan', 'defs', 'marker', 'desc', 'pattern'})
SVG_ATTRS = frozenset({
    'viewbox', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'dx', 'dy',
    'points', 'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin',
    'fill-opacity', 'stroke-opacity', 'opacity', 'transform', 'marker-end', 'marker-start', 'text-anchor',
    'dominant-baseline', 'refx', 'refy', 'markerwidth', 'markerheight', 'orient', 'xmlns',
    'preserveaspectratio', 'font-size', 'font-weight', 'font-family', 'font-style'})
# Constructs the two tokenizers can disagree on; no page needs them.
DIFFERENTIALS = re.compile(r'<!\[|--!>|<!---?>|<\?|</?(?:iframe|object|embed|form|base|frame|frameset|noscript|'
                           r'template|xmp|plaintext|noembed|noframes|math|textarea|listing|select|image)\b', re.I)
RASTER_DATA = re.compile(r'data:image/(?:png|jpeg|gif|webp)[;,]', re.I)
CSS_URL = re.compile(r'url\(\s*([^)]*)\)', re.I)
SECRETS = re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_[A-Za-z0-9]{30,}'
                     r'|\bsk-[A-Za-z0-9_-]{32,}|\bxox[abprs]-[A-Za-z0-9-]{10,}')
VOID = frozenset({'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track',
                  'wbr'})


class _Node:
    def __init__(self, tag, attrs, parent, raw_tag):
        self.tag, self.attrs, self.parent, self.raw = tag, dict(attrs), parent, ''
        self.repeated = len(attrs) != len({k for k, _ in attrs})
        self.markup_in_tag = '<' in raw_tag[1:]

    def ancestors(self):
        node = self.parent
        while node is not None:
            yield node
            node = node.parent


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nodes, self.cur, self.other, self.comments = [], None, [], False

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs, self.cur, self.get_starttag_text() or '')
        self.nodes.append(node)
        if tag not in VOID:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        self.nodes.append(_Node(tag, attrs, self.cur, self.get_starttag_text() or ''))

    def handle_endtag(self, tag):
        node = self.cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None:
            self.cur = node.parent

    def handle_data(self, data):
        if self.cur is not None and self.cur.tag in ('script', 'style'):
            self.cur.raw += data

    def handle_comment(self, data):
        self.comments = True

    def handle_decl(self, decl):
        if decl.strip().lower() != 'doctype html':
            self.other.append(f'<!{decl}>')

    def unknown_decl(self, data):
        self.other.append(f'<![{data[:20]}')

    def handle_pi(self, data):
        self.other.append(f'<?{data[:20]}')


def template_script(html: str) -> str:
    """The content of the first inline <script> in a template, the only script a page may carry."""
    match = re.search(r'<script>(.*?)</script>', html, re.S)
    return match.group(1) if match else ''


def csp_directives(value: str) -> dict[str, tuple[str, ...]]:
    parts = (p.split() for p in value.split(';') if p.strip())
    return {p[0].lower(): tuple(p[1:]) for p in parts}


def safe_url(tag: str, value: str) -> bool:
    url = re.sub(r'[\t\n\r]', '', value).strip(''.join(map(chr, range(0x21))))  # as browsers do
    if tag == 'img':
        return bool(RASTER_DATA.match(url))
    scheme = re.match(r'([a-zA-Z][a-zA-Z0-9+.-]*):', url)
    if scheme:
        return scheme.group(1).lower() == 'https'
    return not re.match(r'[/\\]{2}', url)  # from disk, //host is file://host


def problems(html: str, *, template_script: str, extra_tags=(), extra_attrs=None, onclick: str | None = None,
             allow_comments: bool = False) -> list[str]:
    """Return every markup-safety problem in `html`; an empty list means the page passes.

    template_script: the one inline script the page must carry, byte for byte.
    extra_tags:      tags beyond TAGS that this page type needs.
    extra_attrs:     {tag: {attr, ...}} or {tag: {attr: regex}}; a regex must fullmatch the value.
    onclick:         regex an onclick value must fullmatch; by default a call of a function the
                     template script defines, with no argument, true, false, or one quoted word list.
    allow_comments:  accept HTML comments, for checking a template that still carries its slots.
    """
    found: list[str] = []
    parser = _Parser()
    parser.feed(html)
    parser.close()
    nodes = parser.nodes
    tags = TAGS | set(extra_tags)
    extra = {t: (a if isinstance(a, dict) else dict.fromkeys(a)) for t, a in (extra_attrs or {}).items()}
    if onclick is None:
        names = '|'.join(re.findall(r'function\s+(\w+)\s*\(', template_script)) or '(?!)'
        onclick = rf"(?:{names})\((?:'[\w -]*'|true|false)?\)"

    for n in nodes:
        if n.tag not in tags:
            found.append(f'<{n.tag}> is not allowed')
            continue
        allowed = GLOBAL_ATTRS | TAG_ATTRS.get(n.tag, set()) | (SVG_ATTRS if n.tag in SVG_TAGS else set())
        for k, v in n.attrs.items():
            v = v or ''
            if k in extra.get(n.tag, {}):
                pattern = extra[n.tag][k]
                if pattern and not re.fullmatch(pattern, v):
                    found.append(f'{n.tag}[{k}={v[:40]!r}] does not match {pattern!r}')
            elif not (k in allowed or k.startswith(('data-', 'aria-'))):
                found.append(f'{n.tag}[{k}] is not allowed')
            if k.startswith('on') and not (k == 'onclick' and re.fullmatch(onclick, v)):
                found.append(f'{n.tag}[{k}={v[:40]!r}] is not a known handler')
            if k in ('href', 'src') and not safe_url(n.tag, v):
                found.append(f'{n.tag}[{k}={v[:40]!r}] is not a safe URL')
            if 'url(' in v.lower() and not all(re.fullmatch(r'#[\w-]+', u.strip('\'" ')) for u in CSS_URL.findall(v)):
                found.append(f'{n.tag}[{k}] references something other than url(#id)')
        if n.repeated:
            found.append(f'<{n.tag}> repeats an attribute')
        if n.markup_in_tag:
            found.append(f'<{n.tag}> has a raw < inside the tag; escape it as &lt;')
        parent = n.parent.tag if n.parent else ''
        if n.tag in ('style', 'script') and (parent not in ('head', 'body')
                                             or any(a.tag == 'svg' for a in n.ancestors())):
            found.append(f'<{n.tag}> outside head or body')
        if n.tag == 'title' and parent != 'head':
            found.append('<title> outside head')
        if n.tag == 'meta' and (n.attrs.get('http-equiv') or 'content-security-policy').lower() != 'content-security-policy':
            found.append(f'meta[http-equiv={n.attrs["http-equiv"]}] is not allowed')

    csp = [n for n in nodes if n.tag == 'meta' and (n.attrs.get('http-equiv') or '').lower() == 'content-security-policy']
    if len(csp) != 1 or csp_directives(csp[0].attrs.get('content') or '') != csp_directives(CSP):
        found.append(f'the page needs exactly one CSP meta with: {CSP}')
    elif csp[0].parent is None or csp[0].parent.tag != 'head' or any(
            n.tag in ('style', 'script', 'img') for n in nodes[:nodes.index(csp[0])]):
        found.append('the CSP meta must sit in head before any style, script, or image')
    for tag in ('script', 'style', 'title'):
        if len(re.findall(rf'<{tag}\b', html, re.I)) > 1:
            found.append(f'more than one <{tag}>')
    if not any(n.tag == 'title' for n in nodes):
        found.append('<title> is missing')
    if any(n.tag == 'script' and n.raw != template_script for n in nodes):
        found.append('the inline script must be the template script, unchanged')
    for n in nodes:
        if n.tag == 'style':
            bad = [u for u in CSS_URL.findall(n.raw) if not re.fullmatch(r'#[\w-]+', u.strip('\'" '))
                   and not RASTER_DATA.match(u.strip('\'" '))]
            if bad or '@import' in n.raw.lower():
                found.append(f'<style> loads something outside the page: {(bad or ["@import"])[:3]}')
    found += [f'parser-ambiguous markup: {m}' for m in sorted(set(DIFFERENTIALS.findall(html)), key=str.lower)]
    found += [f'{o} is not allowed' for o in dict.fromkeys(parser.other)]
    if not allow_comments and (parser.comments or '<!--' in html):
        found.append('a finished page carries no HTML comments')
    if SECRETS.search(html):
        found.append('a secret-shaped string; cite the name, not the value')
    return list(dict.fromkeys(found))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('page', type=Path)
    ap.add_argument('--template', type=Path, required=True, help='template whose inline script the page must carry')
    ap.add_argument('--allow-comments', action='store_true')
    ap.add_argument('--extra-tags', default='', help='comma-separated tags beyond the base allowlist')
    args = ap.parse_args(argv)
    try:
        page, template = args.page.read_text(encoding='utf-8'), args.template.read_text(encoding='utf-8')
    except OSError as exc:
        print(f'cannot read: {exc}', file=sys.stderr)
        return 2
    found = problems(page, template_script=template_script(template), allow_comments=args.allow_comments,
                     extra_tags=[t for t in args.extra_tags.split(',') if t])
    for p in found:
        print(p)
    print('OK' if not found else f'FAILED: {len(found)} problem(s)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
