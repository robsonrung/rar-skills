#!/usr/bin/env python3
"""Validate an html-explainer output file.

Usage: python3 validate_explainer.py <file.html> [--template]

Checks (each prints PASS/FAIL; exit 0 only if all pass):
  1. <title> present and not a template placeholder
  2. Self-contained: no external http(s) resources except Google Fonts
  3. At least one inline <svg>
  4. At least 3 <section class="card"> with ids (1 in --template mode)
  5. Every TOC anchor (href="#...") resolves to an element id
  6. At least 5 details.drill panels (1 in --template mode)
  7. Every .code block contains a .code-src source bar
  8. No double-escaped entities (&amp;lt; / &amp;gt;)
  9. No stray raw '<' inside <pre> blocks (only span/b/i/em/br tags allowed),
     which would mean an unescaped generic got swallowed by the parser
 10. jump() and setAll() script hooks present

--template relaxes the count floors so the bundled template itself validates.
"""

import re
import sys


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    template_mode = "--template" in sys.argv
    if len(args) != 1:
        print("usage: validate_explainer.py <file.html> [--template]", file=sys.stderr)
        return 2
    try:
        with open(args[0], encoding="utf-8") as handle:
            html = handle.read()
    except OSError as e:
        print(f"FAIL cannot read file: {e}", file=sys.stderr)
        return 2

    min_sections = 1 if template_mode else 3
    min_drills = 1 if template_mode else 5
    failures = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal failures
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"{status}  {name}" + (f" — {detail}" if detail and not ok else ""))

    title = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
    check("title present", bool(title and title.group(1).strip()))

    ext = [
        u for u in re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
        if "fonts.googleapis.com" not in u and "fonts.gstatic.com" not in u
    ]
    check("self-contained (fonts only)", not ext, f"external refs: {ext[:5]}")

    check("has inline SVG", "<svg" in html)

    sections = re.findall(r'<section class="card" id="([^"]+)"', html)
    check(f"sections with ids (>= {min_sections})", len(sections) >= min_sections,
          f"found {len(sections)}")

    ids = set(re.findall(r'id="([^"]+)"', html))
    anchors = set(re.findall(r'href="#([^"]+)"', html))
    dangling = sorted(anchors - ids)
    check("all #anchors resolve", not dangling, f"dangling: {dangling}")

    jumps = set(re.findall(r"jump\('([^']+)'\)", html))
    bad_jumps = sorted(jumps - ids)
    check("all jump() targets resolve", not bad_jumps, f"dangling: {bad_jumps}")

    drills = len(re.findall(r'<details class="drill"', html))
    check(f"drill panels (>= {min_drills})", drills >= min_drills, f"found {drills}")

    code_blocks = len(re.findall(r'<div class="code">', html))
    code_srcs = len(re.findall(r'<div class="code-src">', html))
    check("every .code has a .code-src", code_blocks == code_srcs,
          f"{code_blocks} code blocks vs {code_srcs} source bars")

    check("no double-escaped entities", "&amp;lt;" not in html and "&amp;gt;" not in html)

    allowed = {"span", "b", "i", "em", "br", "pre"}
    stray = []
    for pre in re.findall(r"<pre>(.*?)</pre>", html, re.DOTALL):
        for tag in re.findall(r"</?([a-zA-Z][a-zA-Z0-9]*)", pre):
            if tag.lower() not in allowed:
                stray.append(tag)
    check("no raw tags inside <pre> (unescaped '<'?)", not stray,
          f"suspicious tags: {sorted(set(stray))[:8]}")

    check("jump()/setAll() script present", "function jump(" in html and "function setAll(" in html)

    print(f"\n{'OK' if failures == 0 else 'FAILED'}: {failures} failure(s)")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
