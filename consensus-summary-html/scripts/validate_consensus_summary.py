#!/usr/bin/env python3
"""Validate the mechanical contract of a consensus summary HTML file."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


REQUIRED_IDS = {
    "overview",
    "verdict",
    "agreements",
    "divergences",
    "evidence",
    "confidence",
    "next-step",
    "limits",
}
REQUIRED_ROLES = {
    "next-step",
    "answer-confidence",
    "diversity-confidence",
}
PLACEHOLDER_PATTERNS = (
    "<!-- SLOT",
    "{{",
    "}}",
    "TODO",
    "REPLACE_ME",
    "Replace with",
    "SESSION_ID",
    "YYYY-MM-DD",
)
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class SummaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.ids: set[str] = set()
        self.roles: dict[str, list[str]] = {}
        self.role_counts: dict[str, int] = {}
        self.tags: list[str] = []
        self.attrs: list[dict[str, str]] = []
        self.text_by_role: dict[str, list[str]] = {}
        self.role_stack: list[tuple[str, str, int]] = []
        self.depth = 0
        self.title_text: list[str] = []
        self.in_title = False
        self.has_doctype = False
        self.external_script = False
        self.external_stylesheet = False
        self.seat_rows = 0
        self.in_seat_table = False
        self.in_tbody = False

    def handle_decl(self, decl: str) -> None:
        if decl.lower().startswith("doctype html"):
            self.has_doctype = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = {key: value or "" for key, value in attrs}
        self.tags.append(tag.lower())
        self.attrs.append(normalized)
        is_void = tag.lower() in VOID_TAGS
        if not is_void:
            self.depth += 1
        if "id" in normalized:
            self.ids.add(normalized["id"])
        if "data-role" in normalized:
            role = normalized["data-role"]
            self.roles.setdefault(role, [])
            self.text_by_role.setdefault(role, [])
            self.role_counts[role] = self.role_counts.get(role, 0) + 1
            if not is_void:
                self.role_stack.append((role, tag.lower(), self.depth))
        if tag.lower() == "title":
            self.in_title = True
        if tag.lower() == "script" and "src" in normalized:
            self.external_script = True
        if tag.lower() == "link" and normalized.get("rel", "").lower() == "stylesheet":
            self.external_stylesheet = True
        if normalized.get("class", "").split() and "seat-table" in normalized.get("class", "").split():
            self.in_seat_table = True
        if self.in_seat_table and tag.lower() == "tbody":
            self.in_tbody = True
        if self.in_tbody and tag.lower() == "tr":
            self.seat_rows += 1

    def handle_endtag(self, tag: str) -> None:
        if self.role_stack and self.role_stack[-1][1] == tag.lower() and self.role_stack[-1][2] == self.depth:
            self.role_stack.pop()
        if tag.lower() == "title":
            self.in_title = False
        if self.in_tbody and tag.lower() == "tbody":
            self.in_tbody = False
        if self.in_seat_table and tag.lower() == "table":
            self.in_seat_table = False
        if tag.lower() not in VOID_TAGS:
            self.depth = max(0, self.depth - 1)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_text.append(data)
        for role, _tag, _depth in self.role_stack:
            self.text_by_role[role].append(data)

    def handle_entityref(self, name: str) -> None:
        self.handle_data(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.handle_data(f"&#{name};")


def nonempty(parts: list[str]) -> bool:
    return bool("".join(parts).strip())


def validate(path: Path) -> tuple[list[str], dict[str, object]]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"file not found: {path}"], {}
    except UnicodeDecodeError as exc:
        return [f"file is not UTF-8: {exc}"], {}

    lowered_text = text.lower()
    for marker in PLACEHOLDER_PATTERNS:
        if marker.lower() in lowered_text:
            errors.append(f"placeholder token remains: {marker}")

    parser = SummaryParser()
    try:
        parser.feed(text)
        parser.close()
    except Exception as exc:  # HTMLParser is permissive, but report parser failures clearly.
        errors.append(f"HTML parser failed: {exc}")

    if not parser.has_doctype:
        errors.append("missing <!DOCTYPE html>")
    if "html" not in parser.tags:
        errors.append("missing html element")
    if "head" not in parser.tags or "body" not in parser.tags:
        errors.append("missing head or body element")
    if not nonempty(parser.title_text):
        errors.append("title is empty")
    if "meta" not in parser.tags:
        errors.append("missing meta charset and viewport elements")
    missing_ids = sorted(REQUIRED_IDS - parser.ids)
    if missing_ids:
        errors.append("missing required section ids: " + ", ".join(missing_ids))
    missing_roles = sorted(REQUIRED_ROLES - parser.roles.keys())
    if missing_roles:
        errors.append("missing required data roles: " + ", ".join(missing_roles))
    for role in REQUIRED_ROLES:
        if role in parser.roles and not nonempty(parser.text_by_role.get(role, [])):
            errors.append(f"data-role={role!r} has no visible value")
    if parser.role_counts.get("next-step", 0) != 1:
        errors.append("data-role='next-step' must appear exactly once")
    if "h1" not in parser.tags:
        errors.append("missing visible h1 question")
    if "table" not in parser.tags or parser.seat_rows < 1:
        errors.append("seat table must contain at least one body row")
    if not re.search(r"class=[\"'][^\"']*\bsource(?:-label)?\b", text, re.I):
        errors.append("missing a source label or source block")
    if parser.external_script:
        errors.append("external script dependency found; keep JavaScript inline")
    if parser.external_stylesheet:
        errors.append("external stylesheet dependency found; keep CSS inline")
    if not re.search(r"<html\b[^>]*\blang=[\"'][^\"']+[\"']", text, re.I):
        errors.append("html element must declare a language")
    if not re.search(r"<meta\b[^>]*charset=", text, re.I):
        errors.append("missing meta charset")
    if not re.search(r"<meta\b[^>]*name=[\"']viewport[\"']", text, re.I):
        errors.append("missing viewport meta")

    summary = {
        "path": str(path),
        "required_ids": sorted(REQUIRED_IDS),
        "seat_rows": parser.seat_rows,
        "roles": sorted(parser.roles),
        "role_counts": dict(sorted(parser.role_counts.items())),
        "errors": errors,
    }
    return errors, summary


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the self-contained HTML contract for a consensus summary."
    )
    parser.add_argument("html_file", type=Path, help="HTML file to validate")
    parser.add_argument("--json", action="store_true", help="emit a JSON result to stdout")
    args = parser.parse_args(argv)

    errors, summary = validate(args.html_file)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
    else:
        print(f"OK: {args.html_file} matches the consensus summary contract.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
