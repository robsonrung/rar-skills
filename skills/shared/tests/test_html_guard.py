#!/usr/bin/env python3
"""Markup safety floor shared by the HTML page skills."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import html_guard  # noqa: E402

SCRIPT = "\n  function jump(id) { location.hash = id; }\n  function setAll(open) {}\n  function filterPriority(set) {}\n"
PAGE = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
{html_guard.CSP_META}
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page</title>
<style>body {{ color: #123; }}</style>
</head>
<body>
<button type="button" onclick="setAll(true)">Expand</button>
<svg viewBox="0 0 10 10"><defs><marker id="arr"><path d="M0 0"/></marker></defs>
<g onclick="jump('F01')"><line x1="0" y1="0" x2="5" y2="5" marker-end="url(#arr)"/></g></svg>
<p class="lede" id="F01">Body</p>
<script>{SCRIPT}</script>
</body>
</html>"""


def problems(html, **kwargs):
    return html_guard.problems(html, template_script=SCRIPT, **kwargs)


def inject(markup, page=PAGE):
    return page.replace('<p class="lede"', markup + '<p class="lede"', 1)


class Guard(unittest.TestCase):
    def assertRejects(self, html, fragment, **kwargs):
        found = problems(html, **kwargs)
        self.assertTrue(any(fragment in p for p in found), f"{fragment!r} not in {found}")

    def test_baseline_passes(self):
        self.assertEqual(problems(PAGE), [])

    def test_allowed_calls_and_urls_pass(self):
        html = inject("<button onclick=\"filterPriority('P0 P1')\">x</button><a href=\"#F01\">a</a>"
                      "<a href=\"docs/x.html\">b</a><a href=\"https://example.com\">c</a>"
                      "<img src=\"data:image/png;base64,iVBOR\" alt=\"chart\">")
        self.assertEqual(problems(html), [])

    def test_content_security_policy(self):
        weakened = html_guard.CSP.replace("connect-src 'none'", "connect-src *")
        cases = [PAGE.replace(html_guard.CSP_META, ""), PAGE.replace(html_guard.CSP, weakened),
                 PAGE.replace(html_guard.CSP_META, html_guard.CSP_META * 2)]
        for html in cases:
            with self.subTest(html=html[:0]):
                self.assertRejects(html, "exactly one CSP meta")
        late = PAGE.replace(html_guard.CSP_META, "").replace("</style>", "</style>" + html_guard.CSP_META)
        self.assertRejects(late, "before any style")
        reordered = html_guard.CSP.replace("default-src 'none'; ", "") + "; default-src 'none'"
        self.assertEqual(problems(PAGE.replace(html_guard.CSP, reordered)), [])

    def test_event_handlers(self):
        for markup in ('<p onmouseover="alert(1)">x</p>', "<button onclick=\"fetch('//x')\">x</button>",
                       "<button onclick=\"jump('x');alert(1)\">x</button>", '<button onclick="eval(1)">x</button>'):
            with self.subTest(markup=markup):
                self.assertRejects(inject(markup), "not a known handler")

    def test_unsafe_urls(self):
        for url in ("javascript:alert(1)", "java&#9;script:alert(1)", "&#1;javascript:alert(1)", "JaVaScRiPt:x",
                    "vbscript:x", "data:text/html,x", "data:image/svg+xml,x", "http://example.com", "//example.com", "\\\\host\\share", "/\\host"):
            with self.subTest(url=url):
                self.assertRejects(inject(f'<a href="{url}">x</a>'), "safe URL")
        for src in ("data:image/svg+xml,x", "https://example.com/x.png", "x.png"):
            with self.subTest(src=src):
                self.assertRejects(inject(f'<img src="{src}" alt="">'), "safe URL")

    def test_css_and_attribute_urls(self):
        self.assertRejects(inject('<svg><rect fill="url(https://x/y)"/></svg>'), "url(#id)")
        self.assertRejects(PAGE.replace("color: #123;", "background: url(//x/y);"), "outside the page")
        self.assertRejects(PAGE.replace("body {", "@import 'x.css'; body {"), "outside the page")

    def test_disallowed_markup(self):
        for markup in ('<object data="x"></object>', '<iframe srcdoc="x"></iframe>', '<form action="x"></form>',
                       '<base href="https://x">', '<meta http-equiv="refresh" content="0;url=https://x">',
                       '<link rel="stylesheet" href="https://x">', '<svg><a xlink:href="javascript:x">x</a></svg>',
                       '<svg><set attributeName="href" to="javascript:x"/></svg>',
                       '<svg><animate attributeName="href" values="javascript:x"/></svg>',
                       '<svg><foreignObject><p>x</p></foreignObject></svg>', '<svg><use href="#x"/></svg>',
                       '<p style="background:url(x)">x</p>', '<embed src="x">', '<input value="x">'):
            with self.subTest(markup=markup):
                self.assertRejects(inject(markup), "not allowed")

    def test_parser_differentials(self):
        cases = {
            "repeats an attribute": ['<a href="#F01" href="javascript:x">x</a>'],
            "raw < inside the tag": ['<span title="</title><img src=x onerror=alert(1)>">x</span>'],
            "outside head or body": ["<svg><style><img src=x onerror=alert(1)></style></svg>",
                                     "<div><style>p{}</style></div>"],
            # Python 3.13+ reads <title> as RCDATA; inside SVG a browser parses the <img> as markup.
            "<title> outside head": ["<svg><title><img src=x onerror=alert(1)></title></svg>"],
            "more than one <title>": ["<svg><title>x</title></svg>"],
            "parser-ambiguous markup": ["<![CDATA[x]]>", "<!-- x --!><img src=x>", "<!--->", "<!-->", "<?x?>",
                                        '<textarea><p title="</textarea><img src=x>"></textarea>',
                                        '<noscript><p title="</noscript><img src=x>"></noscript>',
                                        "<math><mi>x</mi></math>", "<xmp><img src=x></xmp>",
                                        "<image src=x onerror=alert(1)>"],
        }
        for fragment, markups in cases.items():
            for markup in markups:
                with self.subTest(markup=markup):
                    self.assertRejects(inject(markup), fragment)

    def test_comments(self):
        self.assertRejects(inject("<!-- note -->"), "no HTML comments")
        self.assertRejects(inject("</ x>"), "no HTML comments")
        self.assertEqual(problems(inject("<!-- SLOT: x -->"), allow_comments=True), [])

    def test_script(self):
        self.assertRejects(PAGE.replace("<script>", "<script>alert(1);", 1), "template script, unchanged")
        self.assertRejects(inject("<script>alert(1)</script>"), "more than one <script>")
        self.assertRejects(PAGE.replace("<script>", '<script src="https://x/y.js">', 1), "not allowed")
        self.assertRejects(PAGE, "not a known handler", onclick=r"setAll\(true\)")

    def test_secret_value(self):
        self.assertRejects(inject("<p>AKIAABCDEFGHIJKLMNOP</p>"), "secret-shaped")

    def test_extra_markup(self):
        html = inject('<span style="--value: 70%">x</span><svg><pattern id="g" patternunits="x"/></svg>')
        self.assertRejects(html, "span[style] is not allowed")
        extra = {"extra_tags": ("pattern",), "extra_attrs": {"pattern": {"patternunits"}, "span": {"style": r"--value: ?\d{1,3}%"}}}
        self.assertEqual(problems(html, **extra), [])
        self.assertRejects(html.replace("--value: 70%", "background: red"), "does not match", **extra)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            page, template = Path(tmp) / "page.html", Path(tmp) / "template.html"
            page.write_text(inject("<p onclick=\"alert(1)\">x</p>"), encoding="utf-8")
            template.write_text(PAGE, encoding="utf-8")
            run = lambda p: subprocess.run([sys.executable, str(SCRIPTS / "html_guard.py"), str(p), "--template", str(template)],
                                           capture_output=True, text=True)
            self.assertEqual(run(template).returncode, 0)
            bad = run(page)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("not a known handler", bad.stdout)


if __name__ == "__main__":
    unittest.main()
