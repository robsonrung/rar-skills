#!/usr/bin/env python3
"""Validate an html-explainer output file.

Usage: python3 validate_explainer.py <file.html> [--depth orientation|walkthrough] [--template]

Checks (each prints PASS/FAIL; exit 0 only if all pass):
  1. doctype, lang, charset, viewport, and a non-empty <title>
  2. Markup safety (shared/scripts/html_guard.py): the CSP meta, only the template's markup and
     URLs, the template script unchanged, nothing external, no comments
  3. At least one inline <svg>
  4. Numbered sections (card sections other than sec-bigpicture and sec-stack):
     orientation 4-6 with sec-bigpicture, sec-flow, and sec-next present;
     walkthrough 3-9 with at least 5 details.drill panels
  5. Every TOC anchor (href="#...") and jump() target resolves to an element id
  6. Every .code block contains a .code-src source bar, and a path:line citation exists
  7. No double-escaped entities (&amp;lt; / &amp;gt;)
  8. No stray raw '<' inside <pre> blocks (only span/b/i/em/br tags allowed),
     which would mean an unescaped generic got swallowed by the parser
  9. jump() and setAll() script hooks present
 10. No leftover template slots (<!-- SLOT, sec-example)

--template relaxes the count floors, the comment rule, and the slot check so the bundled template
itself validates.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _root in HERE.parents:
    if (_root / "shared" / "scripts" / "html_guard.py").is_file():
        sys.path.insert(0, str(_root / "shared" / "scripts"))
        break
import html_guard  # noqa: E402

TEMPLATE = (HERE.parent / "assets" / "template.html").read_text(encoding="utf-8")
GLANCE_IDS = {"sec-bigpicture", "sec-stack"}
ORIENTATION_IDS = {"sec-bigpicture", "sec-flow", "sec-next"}
# Markup the template uses beyond html_guard's base allowlist.
EXTRA_TAGS = ("pattern",)
EXTRA_ATTRS = {"pattern": {"patternunits"}}


def validate(html: str, depth: str = "walkthrough", template_mode: bool = False) -> list[tuple[str, bool, str]]:
    results = []

    def check(name: str, ok, detail: str = "") -> None:
        results.append((name, bool(ok), "" if ok else detail))

    title = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    head_ok = (
        bool(re.search(r"<!doctype html>", html, re.I))
        and bool(re.search(r'<html\b[^>]*\blang="[^"]+"', html))
        and bool(re.search(r"<meta\b[^>]*charset=", html, re.I))
        and bool(re.search(r'<meta\b[^>]*name="viewport"', html))
        and bool(title and title.group(1).strip())
    )
    check("doctype, lang, charset, viewport, title", head_ok)

    unsafe = html_guard.problems(html, template_script=html_guard.template_script(TEMPLATE), extra_tags=EXTRA_TAGS,
                                 extra_attrs=EXTRA_ATTRS, allow_comments=template_mode)
    check("markup safety (html_guard)", not unsafe, "; ".join(unsafe[:6]))

    check("has inline SVG", "<svg" in html)

    sections = re.findall(r'<section class="card" id="([^"]+)"', html)
    numbered = [s for s in sections if s not in GLANCE_IDS]
    drills = len(re.findall(r'<details class="drill"', html))
    ids = set(re.findall(r'id="([^"]+)"', html))
    if template_mode:
        check("numbered sections (>= 1)", len(numbered) >= 1, f"found {len(numbered)}")
        check("drill panels (>= 1)", drills >= 1, f"found {drills}")
    elif depth == "orientation":
        check("numbered sections (4-6)", 4 <= len(numbered) <= 6, f"found {len(numbered)}")
        missing = sorted(ORIENTATION_IDS - ids)
        check("map, flow, and next sections", not missing, f"missing: {missing}")
    else:
        check("numbered sections (3-9)", 3 <= len(numbered) <= 9, f"found {len(numbered)}")
        check("drill panels (>= 5)", drills >= 5, f"found {drills}")

    dangling = sorted(set(re.findall(r'href="#([^"]+)"', html)) - ids)
    check("all #anchors resolve", not dangling, f"dangling: {dangling}")
    bad_jumps = sorted(set(re.findall(r"jump\('([^']+)'\)", html)) - ids)
    check("all jump() targets resolve", not bad_jumps, f"dangling: {bad_jumps}")

    code_blocks = len(re.findall(r'<div class="code">', html))
    code_srcs = len(re.findall(r'<div class="code-src">', html))
    check("every .code has a .code-src", code_blocks == code_srcs,
          f"{code_blocks} code blocks vs {code_srcs} source bars")
    check("path:line citation present", re.search(r"[A-Za-z0-9_./-]+\.[A-Za-z0-9]+:\d+", html))

    check("no double-escaped entities", "&amp;lt;" not in html and "&amp;gt;" not in html)

    allowed = {"span", "b", "i", "em", "br", "pre"}
    stray = [tag for pre in re.findall(r"<pre>(.*?)</pre>", html, re.DOTALL)
             for tag in re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)", pre) if tag.lower() not in allowed]
    check("no raw tags inside <pre> (unescaped '<'?)", not stray, f"suspicious tags: {sorted(set(stray))[:8]}")

    check("jump()/setAll() script present", "function jump(" in html and "function setAll(" in html)

    if not template_mode:
        leftovers = [token for token in ("<!-- SLOT", 'id="sec-example"') if token in html]
        check("no leftover template slots", not leftovers, f"found: {leftovers}")
    return results


def parse_args(argv: list[str]) -> tuple[str, str, bool] | None:
    depth = "walkthrough"
    template_mode = False
    paths = []
    items = iter(argv)
    for arg in items:
        if arg == "--template":
            template_mode = True
        elif arg == "--depth":
            depth = next(items, "")
        elif arg.startswith("--depth="):
            depth = arg.split("=", 1)[1]
        else:
            paths.append(arg)
    if len(paths) != 1 or depth not in {"orientation", "walkthrough"}:
        return None
    return paths[0], depth, template_mode


def main() -> int:
    parsed = parse_args(sys.argv[1:])
    if parsed is None:
        print("usage: validate_explainer.py <file.html> [--depth orientation|walkthrough] [--template]", file=sys.stderr)
        return 2
    path, depth, template_mode = parsed
    try:
        html = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"FAIL cannot read file: {e}", file=sys.stderr)
        return 2
    results = validate(html, depth, template_mode)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    failures = sum(not ok for _, ok, _ in results)
    print(f"\n{'OK' if failures == 0 else 'FAILED'}: {failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
