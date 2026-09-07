#!/usr/bin/env python3
"""Validate the mechanical contract of an architecture orientation page."""

from __future__ import annotations

import re
import sys
from pathlib import Path


REQUIRED_IDS = {"overview", "flow", "next"}
PLACEHOLDERS = ("<!-- SLOT", "{{", "}}", "TODO", "Replace with", "REPLACE_ME", "path/to")


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: validate_explain_architecture.py <file.html>", file=sys.stderr)
        return 2
    try:
        html = Path(argv[0]).read_text(encoding="utf-8")
    except OSError as error:
        print(f"FAIL: cannot read file: {error}", file=sys.stderr)
        return 2

    failures: list[str] = []
    ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', html))
    section_tags = re.findall(r'<section\b[^>]*>', html, re.I)
    sections = [
        tag for tag in section_tags
        if re.search(r'\bclass=["\'][^"\']*\bcard\b[^"\']*["\']', tag, re.I)
        and re.search(r'\bid=["\'][^"\']+["\']', tag, re.I)
    ]
    anchors = set(re.findall(r'href=["\']#([^"\']+)["\']', html))
    jumps = set(re.findall(r"jump\(['\"]([^'\"]+)['\"]\)", html))

    checks = {
        "doctype": bool(re.search(r'<!doctype html>', html, re.I)),
        "language": bool(re.search(r'<html\b[^>]*\blang=["\'][^"\']+["\']', html, re.I)),
        "title": bool(re.search(r'<title>[^<]+</title>', html, re.I)),
        "metadata": bool(re.search(r'<meta\b[^>]*charset=', html, re.I)) and bool(re.search(r'<meta\b[^>]*name=["\']viewport["\']', html, re.I)),
        "no external resources": not re.search(r'(?:src|href)=["\']https?://', html, re.I),
        "map": "<svg" in html,
        "section count": 4 <= len(sections) <= 6,
        "core sections": REQUIRED_IDS <= ids,
        "navigation": anchors <= ids and jumps <= ids and "function jump(" in html,
        "source citation": bool(re.search(r'[A-Za-z0-9_./-]+:\d+(?:-\d+)?', html)),
        "no placeholders": not any(token.lower() in html.lower() for token in PLACEHOLDERS),
    }

    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
        if not passed:
            failures.append(name)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
