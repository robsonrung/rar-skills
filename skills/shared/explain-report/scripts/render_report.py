#!/usr/bin/env python3
"""Render an evidence linked coding report as offline HTML and Markdown.

Requires the Python standard library and the collection's shared/scripts/html_guard.py. validate_report(data) returns a
list of schema or reference errors, and never executes report content. The HTML
is written only when it passes shared/scripts/html_guard.py (page_problems).
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
import sys
import textwrap
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
for _root in (HERE, *HERE.parents):
    if (_root / "shared" / "scripts" / "html_guard.py").is_file():
        sys.path.insert(0, str(_root / "shared" / "scripts"))
        break
import html_guard  # noqa: E402

TEMPLATE = HERE.parent / "assets" / "report_template.html"
# Markup this page needs beyond the shared allowlist: the search box, the toast, and external source links.
GUARD_EXTRAS = {
    "extra_tags": ("input", "label"),
    "extra_attrs": {
        "input": {"type": "search", "placeholder": None, "autocomplete": "off"},
        "label": {"for": None},
        "a": {"target": "_blank", "rel": "noopener noreferrer"},
        "div": {"hidden": None},
    },
}

VERSION = "1.0"
ENTITY_GROUPS = ("decisions", "areas", "checks", "evidence", "execution", "deviations", "requirements")
SECTIONS = {"overview", "architecture", "decisions", "areas", "checks", "evidence", "execution", "rollout", "deviations", "coverage", "sources", "requirements"}
RESERVED_IDS = SECTIONS | {"search", "expand", "collapse", "theme", "print", "copy", "export", "toast"}
CHECK_STATES = {"planned", "passed", "failed", "blocked", "not_run"}
EVIDENCE_STATES = {"observed", "inferred", "proposed", "unknown"}
METHODS = {"test", "static", "manual", "review", "formal"}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,79}$")


def valid_url(value):
    # Characters that could end a Markdown <autolink> or an HTML attribute must arrive percent-encoded.
    if not isinstance(value, str) or any(ord(c) <= 32 or c in '<>"\\`' for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password
    except ValueError:
        return False


def validate_report(data):
    """Return all detected structural and provenance errors, without I/O."""
    errors = []
    if not isinstance(data, dict):
        return ["The report must be a JSON object."]
    if data.get("schema_version") != 1 or isinstance(data.get("schema_version"), bool):
        errors.append("schema_version must be 1.")
    if not isinstance(data.get("kind"), str) or data.get("kind") not in {"plan", "implementation"}:
        errors.append("kind must be plan or implementation.")
    for key in ("report_id", "title", "generated_at", "revision"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} must be a nonempty string.")
    for key in ("snapshot", "summary"):
        if not isinstance(data.get(key), dict):
            errors.append(f"{key} must be an object.")
    snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    for key in ("repository", "base", "head", "worktree", "scope"):
        if not isinstance(snapshot.get(key), str) or not snapshot[key].strip():
            errors.append(f"snapshot.{key} must be a nonempty string; use an explicit unknown when unavailable.")
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    for key in ("problem", "impact", "solution", "why", "scope", "out_of_scope"):
        if not isinstance(summary.get(key), str) or not summary[key].strip():
            errors.append(f"summary.{key} must be a nonempty string.")
    for owner, key in ((snapshot, "limitations"), (data, "risks"), (data, "questions")):
        if key in owner and (not isinstance(owner[key], list) or any(not isinstance(s, str) for s in owner[key])):
            errors.append(f"{key} must be a list of strings.")

    groups, ids, id_group = {}, {}, {}
    string_fields = {
        "decisions": ("title", "status", "context", "choice", "rationale", "revisit_when"),
        "areas": ("name", "path", "symbol", "change_type", "why", "before", "after", "risk"),
        "checks": ("criterion", "method", "status", "command", "environment", "result", "limitations"),
        "evidence": ("label", "type", "status", "location", "revision", "excerpt", "limitations"),
        "execution": ("title", "detail"),
        "deviations": ("decision", "planned", "actual", "reason", "consequence"),
        "requirements": ("text", "status"),
    }
    for group in ENTITY_GROUPS:
        items = data.get(group, [])
        if not isinstance(items, list):
            errors.append(f"{group} must be a list.")
            items = []
        groups[group] = items
        for i, item in enumerate(items):
            where = f"{group}[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{where} must be an object.")
                continue
            ident = item.get("id")
            if not isinstance(ident, str) or not ID_RE.fullmatch(ident):
                errors.append(f"{where}.id must start with a letter and contain only letters, numbers or underscores.")
            elif ident.lower() in {v.lower() for v in ids} or ident.lower() in RESERVED_IDS:
                errors.append(f"Duplicate or reserved id: {ident}.")
            else:
                ids[ident], id_group[ident] = item, group
            for field in string_fields[group]:
                if not isinstance(item.get(field), str):
                    errors.append(f"{where}.{field} must be a string.")
            if group == "checks":
                if not isinstance(item.get("status"), str) or item.get("status") not in CHECK_STATES:
                    errors.append(f"{where}.status is invalid.")
                if not isinstance(item.get("method"), str) or item.get("method") not in METHODS:
                    errors.append(f"{where}.method is invalid.")
                if item.get("status") == "passed" and not item.get("evidence"):
                    errors.append(f"{where}: a passed check requires evidence.")
                if item.get("status") == "passed" and (not isinstance(item.get("result"), str) or not item["result"].strip()):
                    errors.append(f"{where}: a passed check requires an actual result.")
                if "exit_code" in item and item["exit_code"] is not None and (not isinstance(item["exit_code"], int) or isinstance(item["exit_code"], bool)):
                    errors.append(f"{where}.exit_code must be an integer or null.")
                if item.get("status") == "passed" and item.get("exit_code") not in (None, 0):
                    errors.append(f"{where}: a passed check cannot have a nonzero exit code.")
                for optional in ("executed_at", "revision"):
                    if optional in item and not isinstance(item[optional], str):
                        errors.append(f"{where}.{optional} must be a string.")
            if group == "evidence":
                if not isinstance(item.get("status"), str) or item.get("status") not in EVIDENCE_STATES:
                    errors.append(f"{where}.status is invalid.")
                if item.get("url") and not valid_url(item["url"]):
                    errors.append(f"{where}.url must be a safe absolute HTTPS URL.")
            if group == "requirements" and (not isinstance(item.get("status"), str) or item["status"] not in {"proposed", "met", "unmet", "unknown"}):
                errors.append(f"{where}.status must be proposed, met, unmet or unknown.")

    def refs(item, field, target_group, where):
        values = item.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            errors.append(f"{where}.{field} must be a list of IDs.")
            return
        for value in values:
            if id_group.get(value) != target_group:
                errors.append(f"{where}.{field} references missing {target_group} ID {value}.")

    for group, items in groups.items():
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            where = f"{group}[{i}]"
            if group != "evidence":
                refs(item, "evidence", "evidence", where)
            if group == "decisions":
                refs(item, "areas", "areas", where)
                for field in ("alternatives", "precedents"):
                    if not isinstance(item.get(field, []), list):
                        errors.append(f"{where}.{field} must be a list.")
                for j, precedent in enumerate(item.get("precedents", []) if isinstance(item.get("precedents", []), list) else []):
                    if not isinstance(precedent, dict):
                        errors.append(f"{where}.precedents[{j}] must be an object.")
                        continue
                    for field in ("path", "symbol", "reason", "difference"):
                        if not isinstance(precedent.get(field), str):
                            errors.append(f"{where}.precedents[{j}].{field} must be a string.")
                    refs(precedent, "evidence", "evidence", f"{where}.precedents[{j}]")
                for j, alternative in enumerate(item.get("alternatives", []) if isinstance(item.get("alternatives", []), list) else []):
                    if not isinstance(alternative, dict):
                        errors.append(f"{where}.alternatives[{j}] must be an object.")
                        continue
                    for field in ("option", "benefit", "cost", "rejected_because"):
                        if not isinstance(alternative.get(field), str):
                            errors.append(f"{where}.alternatives[{j}].{field} must be a string.")
                if not isinstance(item.get("tradeoffs", []), list) or any(not isinstance(t, str) for t in item.get("tradeoffs", [])):
                    errors.append(f"{where}.tradeoffs must be a list of strings.")
            if group == "areas":
                refs(item, "decisions", "decisions", where)
                for field in ("diff", "diff_status"):
                    if field in item and not isinstance(item[field], str):
                        errors.append(f"{where}.{field} must be a string.")
                if not isinstance(item.get("details", []), list) or any(not isinstance(t, str) for t in item.get("details", [])):
                    errors.append(f"{where}.details must be a list of strings.")
            if group == "execution":
                refs(item, "depends_on", "execution", where)
                refs(item, "checks", "checks", where)
            if group == "requirements":
                refs(item, "areas", "areas", where)
                refs(item, "checks", "checks", where)
            if group == "deviations" and item.get("decision") and (not isinstance(item["decision"], str) or id_group.get(item["decision"]) != "decisions"):
                errors.append(f"{where}.decision references a missing decision.")
            if group == "checks" and item.get("status") == "passed":
                evid = item.get("evidence", [])
                if isinstance(evid, list) and not any(isinstance(e, str) and ids.get(e, {}).get("status") == "observed" for e in evid):
                    errors.append(f"{where}: a passed check requires at least one observed evidence item.")

    architecture = data.get("architecture", {})
    if not isinstance(architecture, dict):
        errors.append("architecture must be an object.")
        architecture = {}
    available_sections = {"overview", "decisions", "areas", "checks", "evidence"}
    for optional in ("requirements", "execution", "rollout", "sources"):
        if data.get(optional):
            available_sections.add(optional)
    if data.get("kind") == "implementation":
        available_sections.update({"deviations", "coverage"})
    if any(isinstance(architecture.get(side), dict) and architecture[side].get("nodes") for side in ("before", "after")):
        available_sections.add("architecture")
    for state in ("before", "after"):
        graph = architecture.get(state)
        if graph is None:
            continue
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes", []), list) or not isinstance(graph.get("edges", []), list):
            errors.append(f"architecture.{state} must contain nodes and edges lists.")
            continue
        node_ids = set()
        for i, node in enumerate(graph.get("nodes", [])):
            where = f"architecture.{state}.nodes[{i}]"
            if not isinstance(node, dict):
                errors.append(f"{where} must be an object.")
                continue
            ident = node.get("id")
            if not isinstance(ident, str) or not ID_RE.fullmatch(ident) or ident in node_ids:
                errors.append(f"{where}.id is invalid or duplicated within its graph.")
            else:
                node_ids.add(ident)
            for field in ("label", "detail", "target"):
                if not isinstance(node.get(field), str):
                    errors.append(f"{where}.{field} must be a string.")
            if isinstance(node.get("target"), str) and node["target"].lstrip("#") not in set(ids) | available_sections:
                errors.append(f"{where}.target does not identify a report section or entity.")
        for i, edge in enumerate(graph.get("edges", [])):
            if not isinstance(edge, dict) or not isinstance(edge.get("from"), str) or not isinstance(edge.get("to"), str) or edge.get("from") not in node_ids or edge.get("to") not in node_ids or not isinstance(edge.get("label"), str):
                errors.append(f"architecture.{state}.edges[{i}] has invalid endpoints or label.")
    if "plan" in data:
        if not isinstance(data["plan"], dict):
            errors.append("plan must be an object.")
        else:
            for field in ("report_id", "revision", "sha256", "status"):
                if not isinstance(data["plan"].get(field), str):
                    errors.append(f"plan.{field} must be a string.")
    for field in ("rollout", "coverage"):
        if field in data and not isinstance(data[field], dict):
            errors.append(f"{field} must be an object.")
    rollout = data.get("rollout", {}) if isinstance(data.get("rollout", {}), dict) else {}
    for key in ("strategy", "rollback", "observability", "data_compatibility"):
        if key in rollout and not isinstance(rollout[key], str):
            errors.append(f"rollout.{key} must be a string.")
    coverage = data.get("coverage", {}) if isinstance(data.get("coverage", {}), dict) else {}
    for field in ("changed_paths", "unexplained"):
        if not isinstance(coverage.get(field, []), list) or any(not isinstance(t, str) for t in coverage.get(field, [])):
            errors.append(f"coverage.{field} must be a list of paths.")
    if not isinstance(coverage.get("excluded", []), list):
        errors.append("coverage.excluded must be a list.")
    else:
        for item in coverage.get("excluded", []):
            if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not isinstance(item.get("reason"), str) or not item.get("reason", "").strip():
                errors.append("Each excluded coverage path requires a path and a reason.")
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        errors.append("sources must be a list.")
    else:
        for i, source in enumerate(sources):
            if not isinstance(source, dict) or not isinstance(source.get("title"), str) or not valid_url(source.get("url")) or not isinstance(source.get("note", ""), str):
                errors.append(f"sources[{i}] requires a title and a safe HTTPS URL.")
    return errors


def esc(value):
    return html.escape(str(value), quote=True)


def paragraph(value, cls=""):
    return f'<p class="{esc(cls)}">{esc(value)}</p>' if value else ""


def field(label, value, code=False):
    content = f'<code>{esc(value)}</code>' if code else esc(value)
    return f'<div class="field"><span class="field-label">{esc(label)}</span><div>{content or "Not supplied"}</div></div>'


def badge(value):
    css = re.sub(r"[^a-z_]+", "", str(value).lower())
    return f'<span class="badge status-{css}">{esc(str(value).replace("_", " "))}</span>'


def links(values, label="Evidence"):
    if not values:
        return ""
    return f'<div class="link-row"><span>{esc(label)}</span>' + "".join(f'<a class="reference" href="#{esc(v)}">{esc(v)}</a>' for v in values) + "</div>"


def bullet_list(items, cls=""):
    if not items:
        return ""
    return f'<ul class="{esc(cls)}">' + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def section(ident, eyebrow, title, description, content):
    return f'<section id="{ident}" class="report-section"><div class="section-heading"><span class="eyebrow">{esc(eyebrow)}</span><h2>{esc(title)}</h2>{paragraph(description,"section-description")}</div>{content}</section>'


def collapsible(ident, title, label, inner, subtitle=""):
    return f'<details id="{esc(ident)}" class="detail-card searchable" data-search><summary><span class="item-id">{esc(ident)}</span><span class="summary-main"><strong>{esc(title)}</strong>{paragraph(subtitle,"summary-subtitle")}</span>{badge(label)}<span class="chevron" aria-hidden="true">⌄</span></summary><div class="detail-body">{inner}</div></details>'


def graph_html(graph, state):
    nodes, edges = graph.get("nodes", []), graph.get("edges", [])
    if not nodes:
        return ""
    index = {n["id"]: i for i, n in enumerate(nodes)}
    incoming = {n["id"]: 0 for n in nodes}
    outgoing = {n["id"]: [] for n in nodes}
    for edge in edges:
        incoming[edge["to"]] += 1
        outgoing[edge["from"]].append(edge["to"])
    ready = [n["id"] for n in nodes if incoming[n["id"]] == 0]
    levels, rank = [], {}
    while ready:
        current, ready = ready, []
        for offset in range(0, len(current), 3):
            group = current[offset:offset+3]
            levels.append(group)
            for ident in group:
                rank[ident] = len(levels)-1
        for ident in current:
            for target in outgoing[ident]:
                incoming[target] -= 1
                if incoming[target] == 0:
                    ready.append(target)
    remaining = [n["id"] for n in nodes if n["id"] not in rank]
    for offset in range(0, len(remaining), 3):
        group = remaining[offset:offset+3]
        levels.append(group)
        for ident in group:
            rank[ident] = len(levels)-1
    width, node_w, node_h, row_gap = 930, 244, 88, 88
    height = max(150, len(levels)*(node_h+row_gap)+8)
    coords = {}
    for r, group in enumerate(levels):
        row_width = len(group)*node_w+(len(group)-1)*62
        start = (width-row_width)/2
        for col, ident in enumerate(group):
            coords[ident] = (start+col*(node_w+62), 20+r*(node_h+row_gap))
    parts = [f'<svg class="architecture-svg" role="img" aria-labelledby="graph-title-{state}" aria-describedby="graph-desc-{state}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg"><desc id="graph-desc-{state}">Directed relationships between components. Components link to the related explanation. Every relationship is also listed below.</desc><defs><marker id="arrow-{state}" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" class="arrowhead"/></marker></defs>']
    for i, edge in enumerate(edges):
        sx, sy = coords[edge["from"]]
        tx, ty = coords[edge["to"]]
        if edge["from"] == edge["to"]:
            x1, y1, x2, y2 = sx+node_w, sy+node_h/3, tx+node_w, ty+node_h*2/3
            side = min(width-10, x1+56)
            path = f"M{x1},{y1} C{side},{y1-40} {side},{y2+40} {x2+4},{y2}"
            lx, ly = side-12, y1-12
        elif rank[edge["to"]] > rank[edge["from"]]:
            x1, y1, x2, y2 = sx+node_w/2, sy+node_h, tx+node_w/2, ty-4
            mid = (y1+y2)/2
            path = f"M{x1},{y1} C{x1},{mid} {x2},{mid} {x2},{y2}"
            lx, ly = (x1+x2)/2, mid-8
        else:
            x1, y1, x2, y2 = sx+node_w, sy+node_h/2, tx+node_w, ty+node_h/2
            side = min(width-12, max(x1,x2)+32+(i%3)*9)
            path = f"M{x1},{y1} C{side},{y1} {side},{y2} {x2+4},{y2}"
            lx, ly = side-12, (y1+y2)/2-8
        parts.append(f'<path d="{path}" class="graph-edge" marker-end="url(#arrow-{state})"/><text x="{lx}" y="{ly}" class="edge-label" text-anchor="middle">{esc(edge["label"][:42])}</text>')
    for node in nodes:
        x, y = coords[node["id"]]
        target = node["target"].lstrip("#")
        lines = textwrap.wrap(node["label"], width=27)[:2] or [node["id"]]
        parts.append(f'<a href="#{esc(target)}"><desc>{esc(node["label"]+": "+node["detail"])}</desc><rect class="graph-node" x="{x}" y="{y}" width="{node_w}" height="{node_h}" rx="12"/>')
        for j, line in enumerate(lines):
            parts.append(f'<text x="{x+18}" y="{y+29+j*19}" class="node-title">{esc(line)}</text>')
        parts.append(f'<text x="{x+18}" y="{y+72}" class="node-hint">Explore {esc(target)} ↗</text></a>')
    parts.append("</svg>")
    relation_items = []
    for edge in edges:
        source, target = nodes[index[edge["from"]]], nodes[index[edge["to"]]]
        relation_items.append(f'<li><a href="#{esc(source["target"].lstrip("#"))}">{esc(source["label"])}</a><span class="relation-label">{esc(edge["label"])}</span><a href="#{esc(target["target"].lstrip("#"))}">{esc(target["label"])}</a></li>')
    components = "".join(f'<a class="component-link" href="#{esc(n["target"].lstrip("#"))}"><strong>{esc(n["label"])}</strong><span>{esc(n["detail"])}</span></a>' for n in nodes)
    return f'<article class="graph-panel"><h3 id="graph-title-{state}">{esc(graph.get("title",state.title()))}</h3><div class="graph-scroll">{"".join(parts)}</div><div class="component-grid">{components}</div><details class="relationship-details"><summary>Read all {len(edges)} relationships</summary><ul class="relationship-list">{"".join(relation_items)}</ul></details></article>'


def coverage_rows(data):
    coverage = data.get("coverage", {})
    areas = {}
    for area in data.get("areas", []):
        areas.setdefault(area["path"], []).append(area["id"])
    exclusions = {item["path"]: item["reason"] for item in coverage.get("excluded", [])}
    explicit_unknown = set(coverage.get("unexplained", []))
    rows = []
    for path in dict.fromkeys(coverage.get("changed_paths", []) + coverage.get("unexplained", [])):
        if path in explicit_unknown:
            rows.append((path, "Unexplained", [], "A complete explanation is still required."))
        elif path in areas:
            rows.append((path, "Explained", areas[path], ""))
        elif path in exclusions:
            rows.append((path, "Excluded", [], exclusions[path]))
        else:
            rows.append((path, "Unexplained", [], "No explanation or exclusion was supplied."))
    return rows


def check_revision_warnings(data):
    """Surface different evidence revisions without declaring them invalid."""
    evidence = {e["id"]: e for e in data.get("evidence", [])}
    head = data["snapshot"]["head"]
    warnings = {}
    for check in data.get("checks", []):
        revisions = []
        if check.get("revision") and check["revision"] != head:
            revisions.append(check["revision"])
        for ident in check.get("evidence", []):
            item = evidence[ident]
            if item["status"] == "observed" and item["revision"] and item["revision"] != head:
                revisions.append(item["revision"])
        revisions = list(dict.fromkeys(revisions))
        if revisions:
            warnings[check["id"]] = "Recorded evidence revision: " + "; ".join(revisions) + ". Report head: " + head + ". Confirm that the environment and limitations explain this difference."
    return warnings


def render_html(data):
    summary, snapshot = data["summary"], data["snapshot"]
    completed = data["kind"] == "implementation"
    checks = data.get("checks", [])
    unverified = [c for c in checks if c["status"] != "passed"]
    revision_warnings = check_revision_warnings(data)
    coverage = coverage_rows(data)
    unknown_paths = [row[0] for row in coverage if row[1] == "Unexplained"]
    intro = '<div class="overview-grid">' + "".join(f'<article class="overview-card"><span class="field-label">{esc(label)}</span><p>{esc(value)}</p></article>' for label, value in [("The problem",summary["problem"]),("Why it matters",summary["impact"]),("The solution",summary["solution"]),("Why this approach",summary["why"])]) + "</div>"
    intro += '<div class="scope-strip">'+field("In scope",summary["scope"])+field("Outside scope",summary["out_of_scope"])+"</div>"
    counts = [(len(data.get("decisions",[])),"decisions","decisions"),(len(data.get("areas",[])),"code areas","areas"),(sum(c["status"] == "passed" for c in checks),"checks passed","checks"),(len(unverified),"checks unverified","checks")]
    intro += '<div class="stats">'+"".join(f'<a href="#{target}" class="stat"><strong>{count}</strong><span>{esc(label)}</span></a>' for count,label,target in counts)+"</div>"
    material = ""
    if data.get("risks"):
        material += '<div><h3>Material risks</h3>'+bullet_list(data["risks"])+"</div>"
    attention_checks = unverified if completed else [c for c in unverified if c["status"] != "planned"]
    if attention_checks:
        material += '<div><h3>Validation still open</h3><ul>'+"".join(f'<li><a href="#{esc(c["id"])}">{esc(c["criterion"])}</a> {badge(c["status"])}</li>' for c in attention_checks)+"</ul></div>"
    if not completed:
        planned_count = sum(c["status"] == "planned" for c in checks)
        if planned_count:
            intro += f'<p class="planned-note">{planned_count} checks are planned. <a href="#checks">Explore the acceptance and validation strategy</a>.</p>'
    if not checks:
        material += '<div><h3>Validation evidence is missing</h3><p>No checks were supplied. Correctness has not been established by this report.</p></div>'
    open_requirements = [r for r in data.get("requirements", []) if r["status"] in {"unmet", "unknown"}]
    if open_requirements:
        material += '<div><h3>Acceptance still open</h3><ul>' + "".join(f'<li><a href="#{esc(r["id"])}">{esc(r["text"])}</a> {badge(r["status"])}</li>' for r in open_requirements) + '</ul></div>'
    if revision_warnings:
        material += '<div><h3>Validation uses a different revision</h3><ul>' + "".join(f'<li><a href="#{esc(ident)}">{esc(ident)}</a>, {esc(warning)}</li>' for ident, warning in revision_warnings.items()) + '</ul></div>'
    if unknown_paths:
        material += '<div><h3>Changed paths without explanation</h3>'+bullet_list(unknown_paths)+"</div>"
    if snapshot.get("limitations"):
        material += '<div><h3>Evidence boundaries</h3>'+bullet_list(snapshot["limitations"])+"</div>"
    if completed and not data.get("coverage", {}).get("changed_paths"):
        material += '<div><h3>Changed path manifest is missing</h3><p>Completeness cannot be assessed without a manifest of the inspected change.</p></div>'
    if material:
        intro += '<aside class="attention-panel" aria-label="Risks and limitations">'+material+"</aside>"
    if data.get("questions"):
        intro += '<aside class="question-panel"><h3>Decisions for the reader</h3>'+bullet_list(data["questions"])+"</aside>"
    if data.get("plan"):
        plan = data["plan"]
        intro += '<details class="snapshot plan-identity"><summary>Original plan and comparison identity</summary><div class="snapshot-grid">' + "".join(field(label, plan[key], key == "sha256") for label, key in [("Report", "report_id"), ("Revision", "revision"), ("Plan content SHA256", "sha256"), ("Baseline status", "status")]) + '</div></details>'
    intro += '<details class="snapshot"><summary>Report identity and inspected snapshot</summary><div class="snapshot-grid">'+"".join(field(label,snapshot.get(key,"Not supplied"),key in {"base","head","worktree"}) for label,key in [("Repository","repository"),("Base","base"),("Head","head"),("Working tree","worktree"),("Inspection scope","scope")])+field("Generated",data["generated_at"])+field("Report revision",data["revision"])+field("Report ID",data["report_id"])+"</div><p class=muted>This report describes the snapshot above. It does not monitor subsequent changes.</p></details>"
    content = section("overview","01 · Start here","Understand the change", "Read the purpose and risks first, then follow any component, decision or evidence link.", intro)

    if data.get("requirements"):
        req_cards = []
        for r in data["requirements"]:
            inner = links(r.get("areas", []), "Implementation areas") + links(r.get("checks", []), "Validation") + links(r.get("evidence", []))
            if not inner:
                inner = paragraph("No traceability links were supplied. This requirement needs explicit implementation and validation coverage.", "warning-text")
            req_cards.append(collapsible(r["id"], r["text"], r["status"], inner))
        content += section("requirements", "Acceptance coverage", "What success requires", "Follow each requirement to the affected code, validation and supporting evidence.", "".join(req_cards))

    architecture = data.get("architecture",{})
    graphs = "".join(graph_html(architecture[state],state) for state in ("before","after") if architecture.get(state))
    if graphs:
        content += section("architecture","02 · System view","How the solution fits", "Select a component to inspect the decision or code area behind it.",graphs)

    cards = []
    for d in data.get("decisions",[]):
        inner = field("Context",d["context"])+field("Chosen approach",d["choice"])+field("Reason",d["rationale"])
        if d.get("alternatives"):
            inner += '<h4>Alternatives considered</h4><div class="table-scroll"><table><thead><tr><th>Option</th><th>Benefit</th><th>Cost</th><th>Why not chosen</th></tr></thead><tbody>'+"".join("<tr>"+"".join(f"<td>{esc(a[k])}</td>" for k in ("option","benefit","cost","rejected_because"))+"</tr>" for a in d["alternatives"])+"</tbody></table></div>"
        if d.get("tradeoffs"):
            inner += '<h4>Tradeoffs accepted</h4>'+bullet_list(d["tradeoffs"])
        if d.get("precedents"):
            inner += '<h4>Existing repository precedents</h4>'
            for p in d["precedents"]:
                inner += '<div class="precedent">'+field("Path",p["path"],True)+field("Symbol",p["symbol"],True)+field("Why it applies",p["reason"])+field("Important difference",p["difference"])+links(p.get("evidence",[]))+"</div>"
        inner += field("Revisit this decision when",d["revisit_when"])+links(d.get("areas",[]),"Code areas")+links(d.get("evidence",[]))
        inner += f'<div class="review-note js-only"><div data-note="{esc(d["id"])}"></div><span class="note-hint">Notes stay in this browser when storage is available. Export them to keep a portable copy. Notes do not approve or change code.</span></div>'
        cards.append(collapsible(d["id"],d["title"],d["status"],inner,d["choice"]))
    content += section("decisions","03 · Design rationale","Architectural decisions", "Each decision connects its rationale, alternatives, repository precedents and affected code.", "".join(cards) or paragraph("No architectural decisions were supplied."))

    cards=[]
    for a in data.get("areas",[]):
        inner=field("File or area",a["path"],True)+field("Symbol",a["symbol"],True)+field("Why it changes",a["why"])
        inner+='<div class="before-after"><div>'+field("Before",a["before"])+"</div><div>"+field("After" if completed else "Proposed",a["after"])+"</div></div>"
        inner+=field("Risk or coupling",a["risk"])+bullet_list(a.get("details",[]))+links(a.get("decisions",[]),"Decisions")+links(a.get("evidence",[]))
        related_requirements = [r for r in data.get("requirements", []) if a["id"] in r.get("areas", [])]
        inner += links([r["id"] for r in related_requirements], "Acceptance")
        inner += links(list(dict.fromkeys(c for r in related_requirements for c in r.get("checks", []))), "Validation")
        if a.get("diff"):
            inner+=f'<details class="diff-block"><summary>Inspect the focused code excerpt · {esc(a.get("diff_status","Scope not supplied"))}</summary><pre><code>{esc(a["diff"])}</code></pre></details>'
        cards.append(collapsible(a["id"],a["name"],a["change_type"],inner,a["path"]))
    content+=section("areas","04 · Code map","What changes and why", "Understand the behavioral change before opening a focused excerpt.","".join(cards) or paragraph("No code areas were supplied."))

    if completed:
        deviations=[]
        for d in data.get("deviations",[]):
            inner=field("Planned",d["planned"])+field("Implemented",d["actual"])+field("Reason for the difference",d["reason"])+field("Consequence",d["consequence"])+links([d["decision"]] if d.get("decision") else [],"Decision")+links(d.get("evidence",[]))
            deviations.append(collapsible(d["id"],d["actual"],"deviation",inner,d["reason"]))
        content+=section("deviations","05 · Reconciliation","Plan compared with implementation", "A departure from the plan needs an explicit reason and consequence.","".join(deviations) or paragraph("No deviations were recorded. This means only that none were supplied for this report; it is not an independent conformance finding."))
        rows="".join(f'<tr><td><code>{esc(path)}</code></td><td>{badge(status.lower())}</td><td>{links(ids,"Area") if ids else esc(reason)}</td></tr>' for path,status,ids,reason in coverage)
        cov='<div class="table-scroll"><table><thead><tr><th>Changed path</th><th>Coverage</th><th>Explanation or exclusion</th></tr></thead><tbody>'+rows+"</tbody></table></div>" if rows else paragraph("No changed path manifest was supplied. Completeness cannot be assessed.","warning-text")
        content+=section("coverage","06 · Change coverage","Account for every changed path", "Paths are classified from the supplied manifest and the explanations in this report.",cov)

    cards=[]
    for c in checks:
        inner=field("Validation method",c["method"])+field("Command or procedure",c["command"],True)+field("Environment",c["environment"])+field("Actual result" if c["status"]!="planned" else "Expected result",c["result"])+field("Limits of this evidence",c["limitations"])+links(c.get("evidence",[]))
        if "exit_code" in c:
            inner += field("Exit code", "Not recorded" if c["exit_code"] is None else str(c["exit_code"]), True)
        if c.get("executed_at"):
            inner += field("Executed at", c["executed_at"])
        if c.get("revision"):
            inner += field("Check revision", c["revision"], True)
        if c["id"] in revision_warnings:
            inner += paragraph(revision_warnings[c["id"]], "warning-text")
        cards.append(collapsible(c["id"],c["criterion"],c["status"],inner,c["method"]))
    content+=section("checks","07 · Validation" if completed else "05 · Validation","What has been demonstrated" if completed else "How the plan will be validated", "Tests, review, static analysis and formal methods are distinct forms of evidence. A check result applies only to its recorded environment.","".join(cards) or paragraph("No checks were supplied. Correctness has not been established by this report.","warning-text"))

    if data.get("execution"):
        steps=[]
        for s in data["execution"]:
            steps.append(f'<article class="step-card searchable" id="{esc(s["id"])}" data-search><span class="item-id">{esc(s["id"])}</span><h3>{esc(s["title"])}</h3>{paragraph(s["detail"])}{links(s.get("depends_on",[]),"Depends on")}{links(s.get("checks",[]),"Validation")}</article>')
        content+=section("execution","08 · Delivery" if completed else "06 · Delivery","Implementation sequence", "Follow dependency links to understand ordering and the checks that close each step.",'<div class="step-grid">'+"".join(steps)+"</div>")
    rollout=data.get("rollout",{})
    if rollout:
        content+=section("rollout","09 · Operations" if completed else "07 · Operations","Rollout, observation and recovery", "Make operational assumptions explicit before the change reaches users.",'<div class="rollout-grid">'+"".join('<article class="plain-card">'+field(label,rollout.get(key,"Not supplied"))+"</article>" for label,key in [("Rollout strategy","strategy"),("Rollback","rollback"),("Observability","observability"),("Data and compatibility","data_compatibility")])+"</div>")
    cards=[]
    for e in data.get("evidence",[]):
        inner=field("Evidence type",e["type"])+field("Location",e["location"],True)+field("Revision or snapshot",e["revision"],True)+field("Limits",e["limitations"])
        if e.get("excerpt"):
            inner+='<h4>Recorded excerpt</h4><pre><code>'+esc(e["excerpt"])+"</code></pre>"
        if e.get("url"):
            inner+=f'<p><a href="{esc(e["url"])}" target="_blank" rel="noopener noreferrer">Open original source ↗</a></p>'
        used_by=[x["id"] for g in ENTITY_GROUPS if g!="evidence" for x in data.get(g,[]) if e["id"] in x.get("evidence",[]) or any(e["id"] in p.get("evidence",[]) for p in x.get("precedents",[]))]
        inner+=links(used_by,"Used by")
        cards.append(collapsible(e["id"],e["label"],e["status"],inner,e["location"]))
    content+=section("evidence","10 · Provenance" if completed else "08 · Provenance","Inspect the evidence", "Observed facts, inferences, proposals and unknowns stay visibly distinct.","".join(cards) or paragraph("No supporting evidence was supplied.","warning-text"))
    if data.get("sources"):
        content+=section("sources","Reference material","Sources and design references","External references inform a decision; they do not establish what the repository contains.",'<ol class="sources-list">'+"".join(f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["title"])}</a>{paragraph(s.get("note",""))}</li>' for s in data["sources"])+"</ol>")
    nav_sections=[("overview","Overview"),("requirements","Acceptance"),("architecture","System view"),("decisions","Decisions"),("areas","Code map"),("deviations","Plan versus work"),("coverage","Coverage"),("checks","Validation"),("execution","Sequence"),("rollout","Rollout"),("evidence","Evidence"),("sources","Sources")]
    nav="".join(f'<a href="#{ident}">{esc(label)}</a>' for ident,label in nav_sections if f'<section id="{ident}"' in content)
    meta={k:data[k] for k in ("report_id","title","kind","generated_at","revision")}
    meta["snapshot"]=snapshot
    if data.get("plan"):
        meta["plan"] = data["plan"]
    meta["decisions"]=[{"id":d["id"],"title":d["title"]} for d in data.get("decisions",[])]
    # "(" only occurs inside JSON strings; encoding it keeps report text from forming url( in the attribute.
    meta_json=esc(json.dumps(meta,ensure_ascii=False).replace("(","\\u0028"))
    digest=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    plan_header = ""
    if completed and data.get("plan"):
        plan_header = '<p class="plan-header">Plan ' + esc(data["plan"]["report_id"]) + ', revision ' + esc(data["plan"]["revision"]) + ', ' + esc(data["plan"]["status"]) + '</p>'
    replacements={"TITLE":esc(data["title"]),"SUBTITLE":esc(data.get("subtitle","")),"KIND":"Implementation report" if completed else "Coding plan","REVISION":esc(data["revision"]),"DEMO":'<span class="demo-badge">Illustrative example, synthetic repository</span>' if snapshot["repository"].startswith("Illustrative") else "","NAV":nav,"CONTENT":content,"META":meta_json,"DIGEST":digest,"GENERATED":esc(data["generated_at"]),"PLAN":plan_header}
    output=TEMPLATE.read_text(encoding="utf-8")
    return re.sub(r"@@([A-Z]+)@@", lambda match: replacements.get(match[1], match[0]), output)


def md_text(value):
    return str(value).replace("\\","\\\\").replace("[","\\[").replace("]","\\]").replace("*","\\*").replace("_","\\_").replace("<","&lt;").replace(">","&gt;")


def md_link(ident):
    return f"[{md_text(ident)}](#{ident.lower()})"


def secret_fields(value, where="report"):
    """Paths of input strings that look like secrets. Scanning the input, not only the rendered output,
    matters because Markdown escaping (`_` to `\\_`) can split a token the output scan would miss."""
    if isinstance(value, str):
        return [where] if html_guard.SECRETS.search(value) else []
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in secret_fields(v, f"{where}.{k}")]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in secret_fields(v, f"{where}[{i}]")]
    return []


def page_problems(page):
    """Shared markup-safety problems in a rendered page; an empty list means it passes html_guard."""
    script = html_guard.template_script(TEMPLATE.read_text(encoding="utf-8"))
    return html_guard.problems(page, template_script=script, **GUARD_EXTRAS)


def render_markdown(data):
    """Export every report claim, evidence item and implementation detail."""
    out=[]
    def line(value=""):
        out.append(value)
    def heading(level,text,ident=None):
        line()
        if ident in SECTIONS:
            line(f'<a id="{ident}"></a>')
        line("#"*level+" "+(f"{ident} · " if ident else "")+md_text(text)); line()
    def item(label,value):
        line(f"**{md_text(label)}:** {md_text(value) if value else 'Not supplied'}"); line()
    def refs(label,values):
        if values:
            line(f"**{label}:** "+", ".join(md_link(v) for v in values)); line()
    def listing(values):
        for i,value in enumerate(values,1):
            line(f"{i}. {md_text(value)}")
        if values: line()
    def code(value):
        fence="`"*max(3,max((len(m.group())+1 for m in re.finditer(r"`+",value)),default=3))
        line(fence+"text"); line(value); line(fence); line()
    heading(1,data["title"])
    line(md_text(data.get("subtitle",""))); line()
    if data["snapshot"]["repository"].startswith("Illustrative"):
        line("**Illustrative example, synthetic repository.**"); line()
    for label,key in [("Report ID","report_id"),("Kind","kind"),("Revision","revision"),("Generated","generated_at")]: item(label,data[key])
    if data.get("plan"):
        heading(2,"Plan baseline")
        for label,key in [("Plan report","report_id"),("Plan revision","revision"),("Plan content SHA256","sha256"),("Baseline status","status")]: item(label,data["plan"][key])
    heading(2,"Overview","overview")
    for label,key in [("Problem","problem"),("Impact","impact"),("Solution","solution"),("Rationale","why"),("Scope","scope"),("Outside scope","out_of_scope")]: item(label,data["summary"][key])
    heading(3,"Material risks"); listing(data.get("risks",[]))
    heading(3,"Questions for the reader"); listing(data.get("questions",[]))
    heading(3,"Inspected snapshot")
    for key,value in data["snapshot"].items():
        if isinstance(value,list): item(key.replace("_"," ").title(),"; ".join(value))
        else: item(key.replace("_"," ").title(),value)
    line("This report describes the recorded snapshot. It does not monitor subsequent changes."); line()
    unverified=[c for c in data.get("checks",[]) if c["status"]!="passed"]
    if unverified:
        heading(3,"Validation still open")
        for c in unverified:
            line(f"1. {md_link(c['id'])}, {md_text(c['criterion'])}, {c['status'].replace('_',' ')}")
        line()
    if not data.get("checks"):
        line("No checks were supplied. Correctness has not been established by this report."); line()
    warnings = check_revision_warnings(data)
    if warnings:
        heading(3,"Validation uses a different revision")
        for ident, warning in warnings.items():
            line(f"1. {md_link(ident)}, {md_text(warning)}")
        line()
    if data.get("requirements"):
        heading(2,"Acceptance coverage","requirements")
        for r in data["requirements"]:
            line(f'<a id="{r["id"].lower()}"></a>'); heading(3,r["text"],r["id"])
            item("Status",r["status"]); refs("Code areas",r.get("areas",[])); refs("Validation",r.get("checks",[])); refs("Evidence",r.get("evidence",[]))
    if data.get("architecture"):
        heading(2,"Architecture","architecture")
        for state in ("before","after"):
            graph=data["architecture"].get(state)
            if not graph: continue
            heading(3,graph.get("title",state.title()))
            node_lookup={n["id"]:n for n in graph.get("nodes",[])}
            for n in graph.get("nodes",[]): item(n["label"],n["detail"]); refs("Explore",[n["target"].lstrip("#")])
            heading(4,"Directed relationships")
            for e in graph.get("edges",[]):
                line(f"1. {md_text(node_lookup[e['from']]['label'])} → {md_text(node_lookup[e['to']]['label'])}, {md_text(e['label'])}")
            line()
    heading(2,"Architectural decisions","decisions")
    for d in data.get("decisions",[]):
        line(f'<a id="{d["id"].lower()}"></a>'); heading(3,d["title"],d["id"])
        for label,key in [("Status","status"),("Context","context"),("Choice","choice"),("Rationale","rationale")]: item(label,d[key])
        if d.get("alternatives"):
            heading(4,"Alternatives")
            for a in d["alternatives"]:
                for label,key in [("Option","option"),("Benefit","benefit"),("Cost","cost"),("Why not chosen","rejected_because")]: item(label,a[key])
        heading(4,"Tradeoffs"); listing(d.get("tradeoffs",[]))
        if d.get("precedents"):
            heading(4,"Repository precedents")
            for p in d["precedents"]:
                for label,key in [("Path","path"),("Symbol","symbol"),("Why it applies","reason"),("Important difference","difference")]: item(label,p[key])
                refs("Evidence",p.get("evidence",[]))
        item("Revisit when",d["revisit_when"]); refs("Code areas",d.get("areas",[])); refs("Evidence",d.get("evidence",[]))
    heading(2,"Code map","areas")
    for a in data.get("areas",[]):
        line(f'<a id="{a["id"].lower()}"></a>'); heading(3,a["name"],a["id"])
        for label,key in [("Path","path"),("Symbol","symbol"),("Change type","change_type"),("Why","why"),("Before","before"),("After","after"),("Risk","risk")]: item(label,a[key])
        listing(a.get("details",[])); refs("Decisions",a.get("decisions",[])); refs("Evidence",a.get("evidence",[]))
        if a.get("diff"):
            item("Excerpt scope",a.get("diff_status","Scope not supplied")); code(a["diff"])
    if data["kind"]=="implementation":
        heading(2,"Plan compared with implementation","deviations")
        if not data.get("deviations"): line("No deviations were recorded. This is not an independent conformance finding."); line()
        for d in data.get("deviations",[]):
            line(f'<a id="{d["id"].lower()}"></a>'); heading(3,d["actual"],d["id"])
            for label,key in [("Planned","planned"),("Actual","actual"),("Reason","reason"),("Consequence","consequence")]: item(label,d[key])
            refs("Decision",[d["decision"]] if d.get("decision") else []); refs("Evidence",d.get("evidence",[]))
        heading(2,"Changed path coverage","coverage")
        rows=coverage_rows(data)
        if not rows: line("No changed path manifest was supplied. Completeness cannot be assessed."); line()
        for path,status,ids,reason in rows:
            item(path,status+ (", "+reason if reason else "")); refs("Code areas",ids)
    heading(2,"Validation","checks")
    for c in data.get("checks",[]):
        line(f'<a id="{c["id"].lower()}"></a>'); heading(3,c["criterion"],c["id"])
        for label,key in [("Status","status"),("Method","method"),("Environment","environment"),("Result","result"),("Limitations","limitations")]: item(label,c[key])
        if c["command"]: item("Command or procedure",""); code(c["command"])
        if "exit_code" in c: item("Exit code", "Not recorded" if c["exit_code"] is None else str(c["exit_code"]))
        if c.get("executed_at"): item("Executed at",c["executed_at"])
        if c.get("revision"): item("Check revision",c["revision"])
        if c["id"] in warnings: item("Revision difference",warnings[c["id"]])
        refs("Evidence",c.get("evidence",[]))
    if data.get("execution"):
        heading(2,"Implementation sequence","execution")
        for s in data["execution"]:
            line(f'<a id="{s["id"].lower()}"></a>'); heading(3,s["title"],s["id"]); line(md_text(s["detail"])); line(); refs("Depends on",s.get("depends_on",[])); refs("Checks",s.get("checks",[]))
    if data.get("rollout"):
        heading(2,"Rollout and recovery","rollout")
        for key,value in data["rollout"].items(): item(key.replace("_"," ").title(),value)
    heading(2,"Evidence","evidence")
    for e in data.get("evidence",[]):
        line(f'<a id="{e["id"].lower()}"></a>'); heading(3,e["label"],e["id"])
        for label,key in [("Status","status"),("Type","type"),("Location","location"),("Revision","revision"),("Limitations","limitations")]: item(label,e[key])
        if e["excerpt"]: code(e["excerpt"])
        if e.get("url"): line(f"[Original source](<{e['url']}>)"); line()
    if data.get("sources"):
        heading(2,"Sources","sources")
        for s in data["sources"]:
            line(f"1. [{md_text(s['title'])}](<{s['url']}>), {md_text(s.get('note',''))}")
    line(); line(f"Report renderer {VERSION}. Claims describe the supplied evidence, not an independent approval.")
    return "\n".join(out)+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",type=Path)
    parser.add_argument("--html",type=Path)
    parser.add_argument("--markdown",type=Path)
    parser.add_argument("--validate-only",action="store_true")
    args=parser.parse_args()
    try:
        data=json.loads(args.input.read_text(encoding="utf-8"))
        errors=validate_report(data)
        if errors:
            for error in errors: print("Invalid report: "+error,file=sys.stderr)
            return 2
        if args.validate_only:
            print("Report schema and references are valid.")
            return 0
        if not args.html and not args.markdown:
            parser.error("Supply --html, --markdown or --validate-only.")
        if secrets:=secret_fields(data):
            for where in secrets: print(f"Unsafe input: {where} holds a secret-shaped string; cite the name, not the value.",file=sys.stderr)
            print("Nothing written.",file=sys.stderr)
            return 1
        # Produce all bytes before writing any output.
        outputs=[]
        if args.html:
            page=render_html(data)
            problems=page_problems(page)
            if problems:
                for problem in problems: print("Unsafe page: "+problem,file=sys.stderr)
                print("Nothing written; the HTML failed shared/scripts/html_guard.py.",file=sys.stderr)
                return 1
            outputs.append((args.html,page))
        if args.markdown:
            markdown=render_markdown(data)
            if html_guard.SECRETS.search(markdown):
                print("Unsafe Markdown: a secret-shaped string; cite the name, not the value.",file=sys.stderr)
                print("Nothing written.",file=sys.stderr)
                return 1
            outputs.append((args.markdown,markdown))
        for path,body in outputs:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body,encoding="utf-8")
            print(str(path.resolve()))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f"Report generation failed: {exc}",file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
